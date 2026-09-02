---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, tenant, super-admin, access-control]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2206"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24696"
---

# Tenant list search param ignored on /admin/tenants (Bug 24696)

Access Control → Tenants (super-admin tab): typing in the search box did nothing, the grid kept every tenant. The FE sends `?search=<term>` to `GET /admin/tenants`; `TenantFilter` declared `search_model_fields = ["name"]` but never the `search` field itself, so fastapi-filter had nothing to bind the param to and silently dropped it. One-line filter fix + tests.

## Azure / docs
- [Bug 24696](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24696) — reported by Flor 2026-09-02, assigned to me. PR link posted as a comment.

## PRs
- [#2206](https://github.com/taller-projects/echo-backend/pull/2206) → dev — OPEN 2026-09-02 (branch `24696/tenant_search_filter`; `23a40dc2` fix + `60b15408` test hardening after self-review). CI green on `23a40dc2`.
- FE: none needed. FE already sends `search` and reads `Page[T]`; contract only gains an optional query param.

## How
- `app/modules/tenant/filters.py`: `search: str | None = None` + explicit `search_field_name = "search"` on `TenantFilter` (mirrors `WorkflowFilter` / user filters). fastapi-filter then ORs `ilike('%term%')` over `search_model_fields` (`name`).
- `/internal/tenants` is **not** affected despite sharing the filter: `app/modules/tenant/internal_routers.py` is never mounted (imported nowhere; `/internal` OpenAPI has zero `/tenants` paths). Dead module, removal is a separate follow-up. PR body corrected 2026-09-02.
- Tests: `tests/unit/test_tenant_admin.py::TestTenantListSearch` (module-scoped tenant "Zyxq Search Target"; positive narrows + excludes other fixture tenants + `total == 1`, negative returns empty with `total == 0`, empty `search=` returns the unfiltered list). Positive/negative verified to FAIL on `origin/dev` without the fix. 14 passed.

## Decisions
- Kept fastapi-filter's built-in `search` mechanism instead of a custom `name__ilike` wrapper — identical behaviour to the rest of the codebase, zero surface change.

## Gotchas
- **fastapi-filter silently ignores `search` unless the field is declared** on the Filter class; `search_model_fields` alone does nothing and there is no warning. Grep other filters for `search_model_fields` without a matching `search:` field before assuming search works.
- Visibility is NOT a bug: `/admin/*` uses `check_admin_auth_combined` → JWT needs `platform.admin`, then `_tenant_locked = False` + `DisableRLS`. Platform admins see ALL tenants by design; `tenant` table has no RLS at all (0 policies). Non-platform-admins get 403 on every `/admin` route.
- The ticket's example term "thaloz" does not exist in dev (reporter tested elsewhere). Dev positive cases: `search=hubspot` → 4, `search=Kenility` → 1, no search → 50.
- Local testing: `localhost:8000` is the AF-Local-Dev Supabase **Kong** gateway (returns 401 `Invalid authentication credentials` for any Bearer) — Echo had to run on 8010; Bruno `Localhost` env `HOST` switched to 8010 (revert when the AF stack is down). Bruno request: `Tenants (Admin)/Search tenants (24696)`.

## Review (self, /pr-review 2026-09-02)
- Verdict READY WITH NITS → all 3 nits fixed same day (`60b15408` + PR body): assert `total`, add empty-string search test, drop the false `/internal/tenants` claim.
- Out-of-scope observations, **unfiled**: the same `search_model_fields`-without-`search` trap exists in `OrganizationFilter`, `OrganizationPublicFilter`, `ProjectFilter`, `APIKeyFilter`, `PositionFilter` and 5 `public_api` filters (whose docstring advertises a search that does not work); dead `tenant/internal_routers.py`; CLAUDE.md "FE only hits the root app" is wrong (Access Control hits `/admin/tenants`).
- Fixture-collision check: polyfactory constrained strings are hex-only, so random tenant names can never contain `zyxq`.

## Pending
- Merge to dev (review done, waiting on a teammate approval).
- File follow-up ticket for the sibling-filter search bug + dead internal router.
- qa/main promotion (rides the next batch).
- Flip Bug 24696 to Ready to Test after dev deploy.

## Related
- [[Access Control tab (kforce port)]] (if/when a kforce twin is needed — `kforce-dev` has no `/admin` mount, N/A today)
