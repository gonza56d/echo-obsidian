---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, candidates, talent, filters]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2329"
  - "https://github.com/taller-projects/echo-backend/pull/2339"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24242"
prd: ""
---

# Candidates Stage filter divergence (Bug 24242)

On the Candidates list, selecting one or more **Stage** values returned candidates whose displayed Stage was **not** among the selected ones (Taller QA, and the pre-merge automation gate `candidates.feature:400/416/912`). The Stage filter and the Stage the FE renders resolved to **two different applications** for any candidate holding more than one application. Fix realigns the filter's basis to the displayed application.

## Azure / docs
- [Bug 24242](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24242) — In revision, assigned Gonzalo (reporter: Pedro / QA automation).

## PRs
- [#2329](https://github.com/taller-projects/echo-backend/pull/2329) → dev — OPEN 2026-09-23. Fix commit `a015a1d7`; self-review nits `104a1273`; Pedro r1 fixes `3c7ac0e2` (perf blocker + nits). Reply: https://github.com/taller-projects/echo-backend/pull/2329#issuecomment-5798324715
- [#2339](https://github.com/taller-projects/echo-backend/pull/2339) — release `dev` → `qa` OPEN 2026-09-23 (31 commits, 7 migrations, single head `zolvj810zl6j`); `qa` → `main` opens after it merges (qa == main until then).

## Review
- Ran `/pr-review` (scoped mode, 3 parallel reviewers) 2026-09-23: **READY WITH NITS**, zero blockers. Root cause verified in code (not the reporter's dropped-param hint — `current_status__in`/`current_step_id__in` ARE honored by `TalentFilter`; the repro returns filtered-but-wrong rows, not unfiltered). Divergence fixture verified non-vacuous.
- Nits addressed + pushed (`104a1273`): fixed stale `current_step_progress_sort` docstring; added a real `current_step_id__in` divergence test (step-history row so it fails pre-fix, passes post-fix); asserted a zero-application talent is absent from a `current_status__in` filter.
- **Pedro r1 (2026-09-23): CHANGES REQUESTED.** Blocker = perf regression on `/talents` for Taller: `Application.id == last_application_subq` added a per-talent RLS-checked PK lookup (prod count w/ 2 stages: before 2.41–2.50s → r1 3.52–4.67s; direct form 2.07s). Nits: triplicated history comments, "Three talents" docstring (fixture had four), missing tests (matching-only newest by `last_status_update`, `id` tie-break, sorts on a diverging talent), step path lacked no-app/matching-only, PR body silent on the sort behavior change. Question 1: Taller QA has `MULTIPLE_ACTIVE_APPLICATIONS` on since 2026-09-17 → FE remaps Stage to `applications__status__in` (EXISTS, "any application") → this PR doesn't fix what QA automation hits.
- **r2 `3c7ac0e2`:** local `ranked_last_application(column)` helper in `__declare_last__` = single ranking; `last_application_subq` selects `Application.id` from it, `current_status`/`current_step_id` select their column directly (no PK round-trip). One short *why* comment; `current_step_progress_sort` docstring one line. New tests (all fail on dev model, pass on fix): matching-only newest (status + step paths), `id` tie-break, zero-app on step path, `order_by=current_status` divergence, `current_step_progress` divergence (in `test_application_workflow_sort.py`). Suite 5144 passed. QA EXPLAIN (6.5k talents/43k apps, RLS, 3 runs): before 645–759ms · r1 406–972ms · r2 326–333ms. PR body rewritten: sort behavior change + "which path this validates" + perf table.
- Question 1 → user decision: **product decides** what Stage means under multi-active; PR body states it validates only the `current_status__in`/`current_step_id__in` path (flag-off tenants).
- (superseded by the QA EXPLAIN above) Open QUESTION (advisory, non-blocking): no `EXPLAIN` of `/talents?current_status__in=...` under RLS at KForce volume. The realigned properties embed `last_application_subq` (which carries a per-row `max(step_history.created_at)` subquery) — heavier per row than the old `ORDER BY last_status_update LIMIT 1`, though `deferred=True` and it reuses the already-shipped `last_application_*` pattern. `talent` is not a hot table, so risk is modest; run one EXPLAIN before merge to confirm budget.

## How
- FE renders each row's Stage from `last_application.status` / `.workflow_step` (`TalentListUI.last_application`). `Talent.last_application` picks the app by the shared `last_activity_at` recency key (`GREATEST(last step update, last_status_update, created_at)`, `id` tie-break) and excludes matching-only rows (status NULL and step NULL).
- The `current_status__in` / `current_step_id__in` filter narrowed on the `Talent.current_status` / `Talent.current_step_id` column_properties, which ranked applications by `last_status_update` **alone** (no `created_at`, no `id` tie-break) and **included** matching-only rows.
- Different ranking keys → different app for a multi-application candidate → filter passes on app X's status while the row shows app Y's status.
- Fix (`app/modules/talent/models.py`): moved `current_status` / `current_step_id` into `__declare_last__` and redefined them off `last_application_subq.scalar_subquery()` — the exact app `last_application` resolves to. Same pattern as the existing `last_application_role_stage` / `last_application_rating` / `role_name` column_properties. Both are internal (talent sort + filter only), never in a response schema, so no API contract change.
- Tests (`tests/unit/test_talent_stage_filter.py`): a query-level test and an endpoint test build a candidate whose two "latest application" definitions diverge; assert the invariant the QA automation checks (every returned candidate's displayed Stage is among the selected). Both fail before the fix, pass after.

## Decisions
- **Realign the column_property, not the filter.** The column_properties feed both the Stage filter and the Stage sort (`current_step_progress_sort`, `order_by=current_status`), and are single-sourced. Aligning them to `last_application` fixes filter, sort, and display consistency in one place, and is the drift `last_activity_at`'s own docstring warns about ("shared so they cannot drift apart" — `current_status` was simply never migrated to it).
- **Select the Stage columns straight off the ranked subquery** (Pedro r1), not via `Application.id == last_application_subq`: same "same application" guarantee, without an RLS-checked PK lookup per talent. Only `current_status`/`current_step_id` moved to the helper; the other `last_application_*` column_properties still use the PK form (out of scope, candidates for the same speedup).
- **Covered `current_step_id` too** (workflow-step / KForce path), same defect class, one-line twin of the fix — now with its own non-vacuous divergence test (needs a step-history row to force the pre-fix `last_step_update` ranking to pick the wrong app).

## Gotchas
- The Bash grep/rg output in this repo masks identifiers (`current_status`→`n`, `TalentFilter`→`ln`); use Read, not grep output, to read these files.
- `ApplicationCreate` has no `created_at`; set it in tests via `create_entity(..., extra_fields={"created_at": ...})`. The list endpoint caps `size` at 100 (200 → 422).

- EXPLAIN under RLS on QA/prod: `SET LOCAL ROLE echo_backend` alone sees **0 rows** — the talent/application policies key on `auth.jwt()`; also `set_config('request.jwt.claims', '{"sub": "<global-scope user id>"}', true)` (+ `request.tenant_id`). Script kept in session scratchpad; prod reads from Claude sessions are blocked by the auto-mode classifier.
- Only ONE default workflow per tenant (`uq_workflow_default_per_tenant`) → a `current_step_progress` test with workflows must live in `test_application_workflow_sort.py` (its `wf_workflow` is the mocked tenant's default); creating another default elsewhere collides depending on test order.

## Pending
- Pedro re-review of r2 + merge #2329; then dev verification, Bug → Closed, qa/main promotion.
- **Product decision** (Question 1): Stage under `MULTIPLE_ACTIVE_APPLICATIONS` = "any application" (EXISTS, current) or "displayed application"? Drives either a ticket on the EXISTS path or an automation/FE criterion change. QA automation `candidates.feature:400/416/912` will keep failing on multi-app candidates in Taller QA until then.
- Ticket for `current_application_id` drift (Pedro agreed it's separate) — **unfiled**.
- `Talent.current_application_id` still ranks by `last_status_update` alone (feeds only the "Last Stage Update" **date-range** filter, a different dimension) — same latent drift class, left out of scope. Consider aligning if that filter ever shows the same symptom.

## Related
- [[Map - JazzHR integration]] · [[Historical application ownership filter (US 24549)]] · [[Per-application recruiter from Jazz back-sync (Bug 24241)]]
