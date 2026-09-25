---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, touchpoints, future-interaction, applications, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2350"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25143"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25144"
prd: "https://app.notion.com/p/3e5aedca11f0816a9118d23413fc431d"
---

# Touchpoints filter by Role (US 25143)

Navitec asked (2026-09-24, direct request, no Capa 1) to filter the Touchpoints list by Role so that, combined with the Owner filter, they can see how many candidates of a process each person is working. A touchpoint stores only the linked person, so the filter is **derived**: "touchpoints of candidates with a non-Matched application to any of these roles". Shipped as `role_id__in` on `GET /future-interactions` (and the internal list), no schema change, no flag.

## Azure / docs
- [US 25143](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25143) — BE (this note). Successor: FE [US 25144](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25144) (Role multi-select in the Touchpoints filter bar, reuses the Strategy Tracker role selector, hidden without roles permission, tooltip "Candidates applied to this role").
- PRD técnico (Tier B, Pedro): [Touchpoints — Filtro por Role — PRD Técnico](https://app.notion.com/p/3e5aedca11f0816a9118d23413fc431d). Tier B only because it adds a query param to the public contract.

## PRs
- [#2350](https://github.com/taller-projects/echo-backend/pull/2350) → dev — OPEN 2026-09-25, branch `25143/touchpoints_role_filter`, commits `b06058d5` (feature) + `e9dbc7df` (self-review r1 fixes, pushed from worktree `25143-role-filter-r1`) + `83f5c335` (full `/pr-review` r2 nits, pushed from worktree `25143-role-filter-r2`).
- FE: none yet (US 25144). Contract impact: one additive query param `role_id__in` (comma-separated UUIDs); response shape unchanged.

## How
- `FutureInteractionFilter.role_id__in` (`app/modules/future_interaction/filters.py`), consumed and cleared like `search`.
- `FutureInteractionService._resolve_roles` (after r2; typed `FutureInteractionFilter`): folds a singular `linked_entity_type` into the plural form (the internal list has no visibility step doing it), narrows `linked_entity_type__in` to candidates (short-circuits to an empty page when no candidate type survives), then asks `ApplicationService.get_talent_ids_applied_to_roles(role_ids, bound)` (new, explicit tenant predicate, `DISTINCT talent_id`, predicate `status IS NOT NULL OR workflow_step_id IS NOT NULL`) and keeps `bound ∩ answer`. `bound` = whatever an earlier step put in `linked_entity_id__in`, else the candidate refs of touchpoints (`repo.get_person_refs`).
  - Public (`list_for_viewer`): a role filter narrows `allowed_entity_types` to `{candidate}` up front → `_restrict_entity_types` → `_restrict_to_visible_people` (RLS data_scope) → `_resolve_roles` bounded by the visible candidates. One refs read, no contact lookup.
  - Internal (`list_internal`): `_resolve_search` → `_resolve_roles`. The internal app mounts `DisableRLS`, so the lookup's explicit tenant predicate is what isolates tenants there.
- `ApplicationService` injected into `FutureInteractionService` (no DI cycle: nothing under application/talent/role imports touchpoints).
- Contract: empty match → `200` empty page (never the unfiltered list); malformed UUID → `422` standard shape; contacts excluded while the filter is active.

## Decisions
- **Not** `TalentFilter.applications` (the multi-active EXISTS): `TalentRepository._gate_applications_filter` silently sets it to `None` on tenants without `MULTIPLE_ACTIVE_APPLICATIONS`, which would return the unfiltered list, exactly what the PRD forbids. `last_application_role_id__in` is wrong too (last application only, not "≥1"). A dedicated bounded query through the applications module works identically with the flag on or off.
- Bounded to the people already referenced by touchpoints (same reason as `search`): the `IN` grows with the queue, not with a role's applicant count.
- No cap on the number of role ids (PRD sizes latency for 1–10 but sets no limit; user agreed to leave it uncapped).
- Persisting `role_id`/`application_id` on the touchpoint was explicitly discarded in the PRD for this iteration (migration + FE create changes + no backfill); revisit in the KPIs follow-up.

## Self-review r1 (2026-09-25, not posted)
- `/pr-review 2350` → CHANGES REQUESTED, 1 blocker: no test for step-only applications (status NULL + `workflow_step_id` set). **Navitec prod has 0 applications with a status, 7,623 step-only, 31,939 Matched**, so that `or_` branch is the whole feature for them; dropping it kept all 16 original tests green.
- Fixed in `e9dbc7df` (user asked to fix + push): step-only test with a Matched control; perf (one refs read, no contact lookup, short-circuit); wrong docstrings (claimed RLS isolates on internal; cited a nonexistent `(talent_id, tenant_id)` index); tests for `status__in`, blank param, positive controls, internal search + role, internal cross-tenant, direct tenant-predicate test; reverted ruff-format churn in existing tests; OpenAPI descriptions. Mutation-checked: removing the step branch or the tenant predicate each fails a test. Full suite 5307 passed. PR body rewritten via `gh api`.
- Routed to PRD (not code): annex wire format → comma-separated (repeated params silently keep the last value); application RLS (`COALESCE(application.owner_id, talent.owner_id)`, vendor hides self-applied) can narrow the role match below the candidates a user-scope viewer sees — confirm with Pedro; PRD's "Rejected/Withdrawn" statuses no longer exist (removed in `f516c2428583`), equivalents count.

## Full /pr-review r2 (2026-09-25, not posted)
- Three reviewers on `e9dbc7df` → **READY WITH NITS**: architecture 14 PASS / 0 FAIL, tests & security 13 PASS / 0 FAIL, PRD 45/52 rows implemented (all 9 Azure AC), 0 blockers, CI green. Proved `status IS NOT NULL OR workflow_step_id IS NOT NULL` ⇔ `category != matched` (step FK is `ON DELETE SET NULL`, step bools NOT NULL).
- Nits fixed in `83f5c335` (user asked to fix + push; full suite 5308 passed locally): `_resolve_roles` typed as `FutureInteractionFilter`, locals renamed (`candidate_type`, `bounding_talent_ids`), singular `linked_entity_type` folded before narrowing (internal `linked_entity_type=contact` + role no longer pays a wasted lookup), derived-filter rationale kept on the filter field only (+ note that clearing `role_id__in` is load-bearing: no such column, the generic loop would 500), non-applicant control on every AND leg of the combined public test, internal owner + role positive leg, new internal singular-type test, empty talent-id bound asserted, `create_application` / `create_applicant` hoisted to `tests/factories.py` and `touchpoints_enabled` to `tests/conftest.py` (unit + multitenancy copies removed; internal file keeps its own because its helpers serve other fixtures).
- Not done: attaching the `EXPLAIN ANALYZE` plans to the US (only timings were ever saved). PRD-side items routed to Pedro: annex wire format, isolation mechanism on `/internal`, blank `role_id__in=` semantics.

## Gotchas
- **Wire format is comma-separated**, not repeated params: `FilterDepends` turns list fields into a single `str`, so `role_id__in=a&role_id__in=b` keeps only the last value. The PRD example shows repeated params and should be corrected; the FE already sends `a,b` for every other `__in`.
- data_scope cannot be exercised end to end in tests (RLS off under testcontainers). Pinned at the service seam instead: `test_role_matches_are_intersected_with_visible_people` asserts the applications module is asked only about the visible people and its answer is intersected with them, with one refs read and no contact lookup.
- A blank `role_id__in=` is **no filter** (cleared chip, like `search=""`), unlike a column `__in=` which is an empty `IN`. Pinned by `test_an_empty_role_param_is_no_filter`.
- Step-only applications need a real `WorkflowStep` in the tenant (`fk_application_workflow_step_tenant`); the `workflow_step` fixture in `TestRoleFilter` builds one.
- `ApplicationFactory` randomizes `status`; `None` turns the row into a Matched suggestion. Every test application pins `status` explicitly.
- `test_an_empty_role_param_is_no_filter` was **page-order flaky**: it asserted on the unfiltered first page (default size 50) while the module tenant holds more rows than that, all tied on the fixed `DUE_AT`, so which rows land on page 1 depends on heap order and changed with which other modules ran first (failed in a 4-file run and in the full suite, passed file-alone). Pinned in `83f5c335` to its own two people via `linked_entity_id__in`. `TestEntityTypeVisibility::test_a_candidates_only_viewer_does_not_see_contact_touchpoints` (from #1955, on dev) has the same shape and fails in the same ad-hoc orderings — pre-existing, left alone.
- Ad-hoc pytest invocations that mix `tests/multitenancy` before other unit files change row order; the CI order (`./tests/unit ./tests/multitenancy`) is the one that matters.
- Navitec prod numbers (2026-09-25, read-only `EXPLAIN ANALYZE`): 4002 touchpoints, 73 distinct candidates with touchpoints, 39.5k applications. Refs 3.6 ms, resolution 10 roles 1.7 ms (BitmapAnd on `application_role_status_idx` + `application_talent_id_idx`), 1 role 0.1 ms (unique `(tenant, role, talent)` index), page + count 0.3 ms. Criterion p95 < 1 s met by orders of magnitude.

## Pending
- Team review + merge of [#2350](https://github.com/taller-projects/echo-backend/pull/2350) (r2 nits pushed `83f5c335`, CI run 36155757935 pending at push time, 5308 green locally); dev deploy.
- Attach the `EXPLAIN ANALYZE` plans to [US 25143](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25143) — only the timings were recorded here and in the PR body; re-run on Navitec prod (read-only) if the plans are wanted.
- PRD annex: add that a blank `role_id__in=` is no filter (cleared chip) and that isolation on `/internal` is the explicit tenant predicate, not RLS.
- ~~Azure~~ done 2026-09-25: [US 25143](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25143) → In revision, assigned Gonzalo, formal "GitHub Pull Request" link added (repo internal id `db75e3ff-226f-4014-86ae-37f4bcf56c43`, reusable for future PR links).
- FE [US 25144](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25144) (unassigned); tell the FE dev the wire format is comma-separated.
- Tell Pedro: PRD contract example (repeated params) needs correcting before FE starts; data_scope covered at the seam, not end to end; confirm the application-RLS narrowing for user/vendor scope is the intended meaning.
- QA gating: feature complete (BE + FE) before qa/main promotion; QA plan in PRD §5 (3 h, multi-active tenant).
- Follow-up (outside PRD): role/touchpoint KPIs for management dashboards, where exact attribution (persist role/application on the touchpoint) gets decided.

## Related
- [[Public bulk-create touchpoints endpoint (US 24835)]] (same module, the `search` resolution pattern this reuses)
- [[Candidates Stage filter divergence (Bug 24242)]] (multi-active `applications` EXISTS and its gate)
