---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, candidates, talent, filters]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2329"
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
- [#2329](https://github.com/taller-projects/echo-backend/pull/2329) → dev — OPEN 2026-09-23.

## How
- FE renders each row's Stage from `last_application.status` / `.workflow_step` (`TalentListUI.last_application`). `Talent.last_application` picks the app by the shared `last_activity_at` recency key (`GREATEST(last step update, last_status_update, created_at)`, `id` tie-break) and excludes matching-only rows (status NULL and step NULL).
- The `current_status__in` / `current_step_id__in` filter narrowed on the `Talent.current_status` / `Talent.current_step_id` column_properties, which ranked applications by `last_status_update` **alone** (no `created_at`, no `id` tie-break) and **included** matching-only rows.
- Different ranking keys → different app for a multi-application candidate → filter passes on app X's status while the row shows app Y's status.
- Fix (`app/modules/talent/models.py`): moved `current_status` / `current_step_id` into `__declare_last__` and redefined them off `last_application_subq.scalar_subquery()` — the exact app `last_application` resolves to. Same pattern as the existing `last_application_role_stage` / `last_application_rating` / `role_name` column_properties. Both are internal (talent sort + filter only), never in a response schema, so no API contract change.
- Tests (`tests/unit/test_talent_stage_filter.py`): a query-level test and an endpoint test build a candidate whose two "latest application" definitions diverge; assert the invariant the QA automation checks (every returned candidate's displayed Stage is among the selected). Both fail before the fix, pass after.

## Decisions
- **Realign the column_property, not the filter.** The column_properties feed both the Stage filter and the Stage sort (`current_step_progress_sort`, `order_by=current_status`), and are single-sourced. Aligning them to `last_application` fixes filter, sort, and display consistency in one place, and is the drift `last_activity_at`'s own docstring warns about ("shared so they cannot drift apart" — `current_status` was simply never migrated to it).
- **Covered `current_step_id` too** (workflow-step / KForce path), same defect class, one-line twin of the fix.

## Gotchas
- The Bash grep/rg output in this repo masks identifiers (`current_status`→`n`, `TalentFilter`→`ln`); use Read, not grep output, to read these files.
- `ApplicationCreate` has no `created_at`; set it in tests via `create_entity(..., extra_fields={"created_at": ...})`. The list endpoint caps `size` at 100 (200 → 422).

## Pending
- Team review + merge #2329; then dev verification, Bug → Closed, qa/main promotion.
- `Talent.current_application_id` still ranks by `last_status_update` alone (feeds only the "Last Stage Update" **date-range** filter, a different dimension) — same latent drift class, left out of scope. Consider aligning if that filter ever shows the same symptom.

## Related
- [[Map - JazzHR integration]] · [[Historical application ownership filter (US 24549)]] · [[Per-application recruiter from Jazz back-sync (Bug 24241)]]
