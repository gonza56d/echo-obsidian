---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, customer-metrics, adoption, read-endpoints]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2487"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25644"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M7 - metrics read endpoints (US 25644)

Customer metrics M7, the PRD's last and nice-to-have milestone. It adds `GET /metrics/summary` and `GET /metrics/events`, behind `adoption.view` and scoped to the caller's tenant, over the history M1-M4 store (`user_events`, `ai_suggestion`, `proposal`). There is no new storage and no FE consumer yet: a client screen is a separate FE PRD. It was started before M5 FE (Flor) because nothing in M6/M7 depends on it. Builds on [[Customer metrics M4 - proposal versions (US 25640)]] and [[Customer metrics M3 - AI suggestion snapshots (US 25639)]].

## Azure / docs
- [US 25644](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25644): In revision 2026-10-30, PR linked as GitHub Pull Request, comment 29225193 lists the contract differences.
- [Tech PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj) rev 84: not yet updated; the contract differences below go in after review.

## PRs
- [#2487](https://github.com/taller-projects/echo-backend/pull/2487) → dev, OPEN 2026-10-30 (`7f6b2095`, branch `25644/metrics-read-endpoints`, worktree `.claude/worktrees/25644-metrics-read`).

## Decisions (user, 2026-10-30)
- `active_users` = metric 7 "honest adoption": distinct users with at least one action, page views excluded (SQL 7c). It is not the `/echo-usage` session count.
- Both endpoints take `period` / `period_start` / `period_end`, as `/echo-usage` does. The PRD's `from`/`to` on `/metrics/events` is dropped.
- `ai_outcomes` counts user-requested generations only; `auto` rows are out.
- Mine, part of the approved plan: caller's tenant only, with no system-admin cross-tenant mode (`ai_suggestion` and `proposal` RLS only see the request tenant); `page_viewed` excluded from both endpoints; fixed newest-first order with no `order_by`.

## How
- `app/modules/adoption/metrics_service.py`: `CustomerMetricsService`.
  - Reads `user_events` through `AdoptionDashboardRepository`: `count_acting_users`, `count_actions_by_type`, `get_actions_page`.
  - Reads AI counts through `AiSuggestionService.count_user_outcomes` and proposal counts through `ProposalService.count_exports`.
  - The period's UTC days become a `[start_at, end_at)` window over `created_at`.
- `metrics_router` in `adoption/routers.py`, mounted in `app/main.py` at `/metrics` with `Protected([Permission.AdoptionView])`.
  - `_custom_period_error` is shared with `/users/export`.
  - The new routes raise `BusinessRuleError(error_code="period_invalid")`, so the body has the standard `detail` + `error` shape.
- `_resolve_period` became public `resolve_period`; `tests/unit/test_adoption_resolve_period.py` was updated to match.
- The AI outcome rules are the same as SQL 3a. `role` / `project_case_study` are referenced with lightweight `table()` constructs; neither table has RLS.
- No migration: each `user_events` query carries `event_type <> 'page_viewed'`, so the planner uses the partial `ix_user_events_tenant_type_created`.

## Gotchas
- The `adoption.view` SELECT policy on `user_events` is `authorize(...)` with no tenant check, so every read needs an explicit `tenant_id` filter. The multitenancy test pins it: the mutation without the filter fails.
- `act_as` permission tests on `mocked_tenant` need a `TenantModule(module="adoption")` row. Without it the log says "permissions not available in tenant modules: []" and the route answers 404.
- FastAPI 0.139: `app.routes` lazies hide mounted paths; list them with `create_app().openapi()["paths"]`.
- Inside an EnterWorktree session the guard refuses python/cat heredocs and Write outside the worktree. Put helper scripts and SQL under `<worktree>/.claude/worktrees/tmp/` (gitignored).

## Evidence
- Local: 13 new tests (11 unit, 2 multitenancy), and 168 passed together with the adoption, AI-suggestion and proposal suites. The full unit suite was not run locally; CI covers it.
- Mutations caught: no tenant filter (2 failures), counting `page_viewed` (3 failures).
- kforce-dev read-only `EXPLAIN ANALYZE`, 90-day window (202,879 rows, 1,809 actions): every query 0.1-4.2 ms. Script: `<worktree>/.claude/worktrees/tmp/m7_explain_kforce_dev.sql`.

## Pending
- [ ] CI on `7f6b2095`, review (Leo / Pedro / Gise), merge.
- [ ] PRD: M7 checklist and API contract (period params, newest first, no page views, user-requested AI only, active_users = metric 7) + changelog rows.
- [ ] US 25644 description/AC to the same wording. Close it on merge to dev.
- [ ] qa / main promotion.

## Related
- [[Customer metrics M4 - proposal versions (US 25640)]] · [[Customer metrics M3 - AI suggestion snapshots (US 25639)]] · [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]]
