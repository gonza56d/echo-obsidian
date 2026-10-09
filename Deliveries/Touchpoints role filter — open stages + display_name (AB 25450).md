---
type: delivery
status: open
env: taller
delivered: 2026-10-09
tags: [feature, touchpoints, future-interaction, roles, navitec, review]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2403"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25450"
prd: ""
---

# Touchpoints role filter — open stages + display_name (AB 25450)

Role half of CR 25450 ("Touchpoints → Role and Owner filters: show only open roles (with ID) and only Navitec users"); the Owner half is #2400. Two additive changes to `GET /future-interactions/roles` (the Touchpoints Role filter options endpoint delivered in [[Touchpoint Role filter options endpoint (US 25255)]]):

1. **Only Open/Active/Filled stages.** `list_role_options_for_viewer` passes `stage__in=ROLE_OPTION_STAGES` (`[RoleStage.OPEN, ACTIVE, FILLED]`) to the existing `RoleFilter` virtual filter → `Role.role_workflow_step_id IN (SELECT id FROM role_workflow_step WHERE stage IN (...))`. By **stage, not step name**, so every tenant's workflow maps on with no per-tenant logic. Out: Draft, Paused, Closed, Archived. Navitec's "Scope of Work"/"RFP" are configured Draft → excluded until they re-stage the step (no code change).
2. **`display_name` on each option.** `TouchpointRoleOption` gains `display_name: str` = the existing flag-aware `Role.display_name` column_property (TrackerRMS external id when `role_external_id_display` + linked; Jazz job number; else `{short_id} - {name}`). SELECT is schema-driven, no repo change. `name__ilike` already matches `display_name`, so search-by-ID needed no change.

Additive: no migration, no change to existing fields, BE deployable before/after FE. Author: Patricio (`PatricioEtcheverryTaller`), branch `25450/touchpoint_role_display_name`.

## Azure / docs
- [AB#25450](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25450) — Customer Request, state Developed. Description + AC fields are **empty**; the whole Role-half spec lives in the PR #2403 body. No Notion PRD.

## PRs
- [#2403](https://github.com/taller-projects/echo-backend/pull/2403) → dev **OPEN** 2026-10-09. Author commits up to `35148473`. My nit-fix commit `3453e95f` pushed to Patricio's branch (from worktree `25450-nits`). CI was green on `35148473`; `3453e95f` pushed, CI pending at hand-off.
- FE follow-up (not opened by me): echo-frontend shows `display_name` (fallback `name`) in the Touchpoints Role filter option + chip, and keeps the ID in the stored filter value so the chip survives reload.

## Review (2026-10-09, full mode) — READY WITH NITS
`/pr-review 2403`, 3 parallel reviewers. **0 blockers.** PRD 5/5; Architecture 14 PASS / 0 FAIL / 1 N/A; Tests & Security 11 PASS / 0 FAIL / 5 N/A. CI green.
Two optional nits, both fixed by me in `3453e95f`:
- **ACTIVE stage not directly exercised** — the default workflow has no Active-stage step, so the ACTIVE arm of `ROLE_OPTION_STAGES` was only reached via the shared `IN`. Added `test_offers_a_role_in_a_custom_active_stage`: seeds a custom `RoleWorkflowStep(stage=ACTIVE)` on the tenant's default workflow, puts a role on it, asserts it is offered.
- **Untyped constant** — annotated `ROLE_OPTION_STAGES: list[RoleStage]`.
Local after fix: 132 passed (`test_future_interaction.py`) + 31 (`TestRoleOptions` + `multitenancy/test_future_interaction_isolation.py`); `ruff check app/` clean, `service.py` formatted.

## Decisions
- Rule is stage-based (data-driven), not step-name or deployment — consistent with "tenancy is data". `RoleStage` imported as the sibling module's **schema enum** (`app.modules.role_workflow.step.schemas`), the established pattern across ~15 modules; cross-module data still flows through `RoleService.get_all`.
- `display_name` is a `deferred=True` column_property whose expression carries two scalar subqueries (external-id + tenant-flag) inside a flag CASE — the "un-lazying a deferred column_property" pattern CLAUDE.md warns about, but safe here: result set is bounded to the `id__in` of roles with pending touchpoints, the heavy subquery is short-circuited for flag-OFF tenants, and `GET /roles` already projects the same column at a larger surface.
- "This also affects the role's open-days count and Roles-page grouping" is a product-accepted consequence of how Navitec stages its steps, not a code side-effect of this PR.

## Gotchas
- **`DetachedInstanceError` in the new test** when requesting the module-scoped `mocked_role_workflow` fixture directly (`conftest.py:469`, cached instance detached from its session). Fix: derive the `role_workflow_id` from an existing step (`mocked_role_workflow_steps["Open"].id`) via a `db.session.query(...).scalar()`, never touch the detached workflow object.
- Worktree session: `.env` copied into the worktree cwd; ran via `.venv/bin/python -m pytest` by absolute path; SQL echo is on by default (`LOG_LEVEL=WARNING` to read tracebacks). `ruff`/CI lint only `app/`, so the pre-existing import-order drift in `test_future_interaction.py` is left as-is (author's decision).

## Pending
- CI on `3453e95f`; Patricio's review/merge of #2403.
- Owner half #2400 (separate PR).
- FE follow-up PR on echo-frontend.
- qa/main promotion after dev merge.

## Related
- [[Touchpoint Role filter options endpoint (US 25255)]] (the endpoint this extends)
- [[Touchpoints filter by Role (US 25143)]]
