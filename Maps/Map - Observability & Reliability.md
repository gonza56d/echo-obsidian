---
type: map
tags: [map, observability, sentry, performance]
---

# Map — Observability & Reliability

Sentry tooling, and the family of prod timeout/resilience fixes it keeps surfacing.

## Tooling
- [[Sentry observability rollout (US 22295)]] — release tracking, request context, dispatcher coverage, component tags
- Access: Sentry org `taller-wn`, `SENTRY_TOKEN` in `~/.zshrc`, `/sentry` skill. If `issues/*` 403s, query project events filtered by groupID.
- Logs: Grafana Loki via `/grafana` skill.

## Prod incidents / fixes in this window
- [[Roles statement timeout fix (PR 1600)]] — correlated column_property used as WHERE filter (chronic, tenant-scale)
- [[similar_role null-vector 500 (Bug 23362)]] — pgvector `<=> NULL` full scan; pool exhaustion; hotfixed to main+qa same day
- [[Deep pagination selectin fix (23553)]] — to-one joinedload evaluated pre-LIMIT
- [[Outbox poll backoff (Bug 23522)]] — dispatcher retry flood during DB read-only window
- [[Outbox flat payload fix (PR 1838)]] — prod-only 422 dead-lettering masked by lenient dev mock

## Recurring lessons
- Correlated `column_property`s are fine for SELECT projection but poison as WHERE filters or JOIN-ON conditions at scale — rewrite as set-based subqueries or pointer joins.
- A statement-timeout'd query leaves **no SQL breadcrumb in Sentry** — look for the time gap after the last recorded query.
- Dev mocks that match on path only will happily bless a broken request body.

## Known pending
- OpenAPI 500 via `partial_model` (Sentry `7600828395`, fastapi 0.139 bump; verified 1-line fix in `optional_model.py`) — **needs dev + kforce-dev PRs**.
- Keyset pagination follow-up from the deep-pagination fix.
