---
type: delivery
status: merged
env: taller
delivered: 2026-06-22
tags: [bugfix, performance, roles]
prs: [1600]
tickets: []
---

# /roles statement timeout — active_candidates_count filter (PR 1600)

Chronic prod failure: `GET /roles` hit the DB statement timeout ~2–15×/day on tenant `01df2012-…`. Root cause: the `active_candidates_count__gte` filter was applied through the `Role.active_candidates_count` **column_property** — a triple-nested correlated subquery (role → application → latest-active-app-per-talent → step history) re-evaluated **per role row** → `O(roles × applications)`.

## PRs
- [#1600](https://github.com/taller-projects/echo-backend/pull/1600) → dev — merged 2026-06-22

## How
- `roles_with_active_candidates_subquery(min_count)`: computes latest-active-application-per-talent **once** via `DISTINCT ON (talent_id)`, groups by `role_id`, `HAVING count(*) >= min_count`.
- Filter resolves as a virtual filter `Role.id IN (subquery)` instead of inlining the correlated subquery. Threshold `< 1` = no-op (preserves prior semantics).
- Migration `q4n8wd2rmk7h`: `CREATE INDEX CONCURRENTLY` composite `application_workflow_step_history(application_id, created_at)`; drops the now-redundant single-column index.

## Decisions / gotchas
- `active_candidates_count` is **filter-only** (not in responses/sorts) → the column_property itself was left unchanged.
- Tenant isolation of the set-based subquery rides on RLS on `application` — RLS is bypassed in the test harness, so a system test pins per-tenant correctness (see the RLS-not-enforced-in-tests gotcha).
- Pre-existing local 404 on `/projects/{id}/roles` route in TestClient — not a regression (fails on origin/dev too).

## Related
- [[Deep pagination selectin fix (23553)]] — sibling class of timeout (loader strategy vs filter strategy)
- [[Map - Observability & Reliability]]
