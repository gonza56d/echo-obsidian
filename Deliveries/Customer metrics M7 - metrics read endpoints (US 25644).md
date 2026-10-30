---
type: delivery
status: merged
env: both
delivered: 2026-10-30
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
- [Tech PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj) rev 90 (2026-10-30): M7 checklist and API contract as built, plus a changelog row (period params, caller's tenant, metric 7, no page views, user-requested AI only, newest first).

## PRs
- [#2487](https://github.com/taller-projects/echo-backend/pull/2487) → dev, **squash-MERGED 2026-10-30 16:15Z as `83a8895a`** (head `80b5dbe5`, CI green, Pedro approved). Opened 2026-10-30 (`7f6b2095`, branch `25644/metrics-read-endpoints`, worktree `.claude/worktrees/25644-metrics-read`).
- Self-review r1 (pr-review skill, scoped, 3 agents) on `7f6b2095`: READY WITH NITS, 0 blockers, not posted. Nits 1-4 fixed in `7270f541`, pushed 2026-10-30 from worktree `.claude/worktrees/25644-metrics-nits` (branch `25644/metrics-read-nits`) with `HEAD:25644/metrics-read-endpoints`, without a local test run (user asked); PR body updated.

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

## Review r1 (2026-10-30)
- Fixed in `7270f541`:
  - The role / case-study existence check moved out of `AiSuggestionRepository` (string-literal `table()` reads with no tenant filter) into `CustomerMetricsService`, which calls `RoleService` / `ProjectCaseStudyService.filter_existing_ids`. `AiSuggestionService` cannot inject them: both inject it (DI cycle). New flow: `get_open_applied_entity_ids` → owners' `filter_existing_ids` → `count_user_outcomes(..., deleted_entity_ids)`.
  - `count_user_outcomes` filters `kind IN AiSuggestionKind`: an unknown kind (varchar, no CHECK) made the summary a 500.
  - Fixture rows: an open case study with an existing card (accepted), an open manual matching_instructions (ignored), the start edge (1 Mar 00:00), and an `entity_type`-only case.
- Left open (nits 5-7):
  - p95 evidence is per-query EXPLAIN only. No plan for `?user_id=` (could pick `ix_user_events_user_date`, page views included) or for a 730-day window. Measure on kforce-dev after merge.
  - `active_users` population (7c) includes support accounts and deactivated users, unlike `/echo-usage`. The route docstring still says `/echo-usage` "counts sessions".
  - Minor: adoption ↔ ai_suggestion/proposal module coupling, two `period_invalid` envelopes, `_actions` naming, whole-row load in `get_actions_page`, past-period `ai_outcomes` not final.
- Out of scope: PRD RLS line (the M1 `user_events` SELECT policy has no tenant check); system/platform admins without `adoption.view` see only their own events (same as `/echo-usage`).
- `/metrics` has no infra collision: the prod ingress is prefix `/` with no `/metrics` rule, and the PodMonitors scrape the worker / dispatcher ports only.

## Pedro's review (2026-10-30)
- [Review 5714640787](https://github.com/taller-projects/echo-backend/pull/2487#pullrequestreview-5714640787) on `7270f541`: APPROVED, READY WITH NITS, 0 blockers. CI on `7270f541` passed.
- Fixed in `80b5dbe5` (pushed without a local run, user asked):
  - nit 2: unknown-kind seed row;
  - nit 3: period rules parametrized across both routes;
  - nit 4: positive `user_id` case;
  - nit 5: `adoption_module` fixture removes the TenantModule row it created;
  - nit 7: `PAGE_VIEWED` comment.
- Kept as-is:
  - nit 6: importing `AiSuggestionEntityType` from `ai_suggestion.models` matches project / assessment / role / case_study services. The `str` keys are deliberate: `entity_type` is a varchar, so an enum conversion could 500 like the unknown kind did.
  - nit 1: the endpoint p95 can only be measured once dev deploys to kforce-dev.
- Questions:
  - `/metrics` prefix: no collision (prod ingress is prefix `/`, PodMonitors only on the worker / dispatcher ports); kept as the PRD/US name.
  - `event_data` exposure, `user_id` with no `data_scope`: same as `/echo-usage`; state it in the PRD.
  - US wording before closing.

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
- [x] Review: Pedro APPROVED (5714640787).
- [x] CI on `80b5dbe5` green; squash-merged to dev `83a8895a`.
- [ ] Endpoint p95 on kforce-dev after deploy (Pedro nit 1).
- [ ] PRD: `event_data` / `user_id` exposure note (Pedro question).
- [x] PRD: M7 checklist, API contract, changelog row (rev 90, 2026-10-30).
- [x] US 25644 description updated to the as-built contract and Closed (rev 6, comment 29226999).
- [ ] qa / main promotion.

## Related
- [[Customer metrics M4 - proposal versions (US 25640)]] · [[Customer metrics M3 - AI suggestion snapshots (US 25639)]] · [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]]
