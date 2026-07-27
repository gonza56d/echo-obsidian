---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, roles, filters]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1907"
  - "https://github.com/taller-projects/echo-backend/pull/1908"
  - "https://github.com/taller-projects/echo-backend/pull/1909"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23719"
prd: ""
---

# Roles company filter (Feature 23719)

The Roles section had no company filter while candidates already have one (multi-select). [Feature 23719](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23719) ("Roles - Company filter (all tenants)") asks to mirror it. Shipped as a one-field backend change: `company_id__in` on `RoleFilter`, so `GET /roles` can filter roles by one or many companies.

## Azure / docs
- [Feature 23719](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23719) — "Roles - Company filter (all tenants)", parent [22239](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22239). No child US/tasks; no PRD. PR linked via comment on the Feature.

## PRs
- [#1907](https://github.com/taller-projects/echo-backend/pull/1907) → dev — open (in review), branch `23719/role_company_filter`
- [#1908](https://github.com/taller-projects/echo-backend/pull/1908) → qa — open, cherry-pick of `94e89e28` (`cherry_pick/23719_role_company_filter_qa`); **merge commit, never squash**
- [#1909](https://github.com/taller-projects/echo-backend/pull/1909) → main — open, cherry-pick of `94e89e28` (`cherry_pick/23719_role_company_filter_main`); **merge commit, never squash; after #1908**

## How
- `app/modules/role/filters.py`: added `company_id__in: list[uuid.UUID] | None` next to the existing scalar `company_id`. Propagates to `IndependentRoleFilter` (public `GET /roles`) and `IndependentRoleFilterInternal` for free.
- `Role.company_id` is a deferred `column_property` = `(SELECT project.consumer_id WHERE project.id = role.project_id)`, so fastapi_filter's native `in_` path compiles it to a correlated subquery in WHERE — no JOIN, no row multiplication, no custom `filter()` branch needed. Same native path candidates use for `last_application_company_id__in` (an even heavier column_property).
- Tests: `tests/unit/test_role_filter.py` — 2 compile-to-SQL tests (no DB) pinning the correlated-subquery shape for both scalar `company_id` and `company_id__in`.

## Decisions
- The scalar `company_id` filter already existed and works; the actual gap vs candidates was the multi-select. Added only `__in` (stick to scope), and pinned the scalar with a test too since nothing covered it.
- Chose the native column_property path over a set-based virtual filter (`project_id IN (SELECT id FROM project WHERE consumer_id IN ...)`): per-row subplan is a PK lookup on project, roles-per-tenant is small, and it matches the candidates precedent with zero code.

## Gotchas
- `select(Role)` in compile tests pulls non-deferred column_properties (`company_name`/`company_logo`) whose subqueries contain `JOIN project` — a blanket `"JOIN" not in sql` assertion fails. Use `select(Role.id)` to pin the WHERE clause in isolation.
- `RoleFilter(...)` built directly needs `commitments=None` (known gotcha, FilterDepends default leaks a `Depends` object).

- Cherry-picks were opened while #1907 was still unmerged, so #1908/#1909 carry the feature-branch commit `94e89e28`, not dev's future squash SHA — content-identical, later dev→qa/main deploy trains resolve it as already-applied.

## Pending
- FE PR (multi-select company filter UI on Roles) — frontend-owned, not backend scope.
- Merge [#1907](https://github.com/taller-projects/echo-backend/pull/1907) → dev (squash), then [#1908](https://github.com/taller-projects/echo-backend/pull/1908) → qa and [#1909](https://github.com/taller-projects/echo-backend/pull/1909) → main (merge commits, main after qa).

## Related
- Candidates company filter precedent: `TalentFilter.last_application_company_id__in` (app/modules/talent).
