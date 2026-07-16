---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-01
tags: [bugfix, hotfix, roles, pgvector, sentry]
prs: [1693, 1695, 1696]
tickets: [23362]
---

# similar_role null-embedding 500 (Bug 23362)

Sentry `7585920278`: recurring **500 on `POST /roles`** in prod (12 events on 2026-07-01) — bad enough to exhaust the DB pool. `create_role_without_project` creates the role with `enhance_role=False`, so its embedding `vector` is NULL at response time (computed later in a background task). Serializing `RoleResponse` touches the `similar_role` property → `Role.vector.cosine_distance(NULL)` — `vector <=> NULL` can't use the pgvector index → full scan of every role in the tenant → statement timeout → 500. Latent pre-existing bug; also hit `GET /roles/{id}` for roles fetched before embedding.

## PRs
- [#1693](https://github.com/taller-projects/echo-backend/pull/1693) → dev
- [#1695](https://github.com/taller-projects/echo-backend/pull/1695) → **main** (hotfix cherry-pick)
- [#1696](https://github.com/taller-projects/echo-backend/pull/1696) → **qa** (hotfix cherry-pick)
All merged 2026-07-01.

## How
- Guard `similar_role` against a null `self.vector` (skip the cosine-distance query entirely).

## Diagnostic gotcha
- The cancelled query leaves **no SQL breadcrumb** in Sentry (killed before the integration records it) — the tell was a ~30s gap after the last logged serialization query. Useful pattern for future timeout hunts.

## Related
- [[Map - Observability & Reliability]]
