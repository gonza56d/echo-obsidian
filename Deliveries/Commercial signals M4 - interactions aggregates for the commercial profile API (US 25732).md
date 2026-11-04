---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, internal-api, navitec, data-team, background-job]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2520"
  - "https://github.com/taller-projects/echo-backend/pull/2519"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25732"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728"
prd: "https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C"
---

# Commercial signals M4 - interactions aggregates for the commercial profile API (US 25732)

Fourth signal of the data team contract: `GET /internal/commercial-signals/interactions` serves the tenant's interactions as `totals` (interaction type x period) and `by_group` (industry x interaction type x period: interactions, contacts, organizations), plus the complete `organizations` list. Navitec is the consumer; KForce is opted out. Same snapshot / refresh as [[Commercial signals M3 - deals aggregates for the commercial profile API (US 25731)]]. No FE involvement.

## PRs
- [#2520](https://github.com/taller-projects/echo-backend/pull/2520) -> dev, **OPEN** 2026-11-04, commit `de296910e`, branch `25732/commercial_signals_interactions` (worktree `.claude/worktrees/25732-cs-interactions`). Migration `l4rpbl15ac7b` after `1yw2kc2or920`. US 25732 In revision (rev 2) + PR ArtifactLink + decisions comment 29264126.
- Hotfix [#2519](https://github.com/taller-projects/echo-backend/pull/2519) -> dev, **OPEN**, must merge first: dev had two alembic heads after Leo's #2514 (`t4mvdxaubidi`) landed on top of #2509 (`ga7mqtjixquc`), both revising `z2a48jp2jg9g`, so Apply migrations failed on dev + kforce-dev for `448010b47` and `9f57d3a25`. Empty merge revision `1yw2kc2or920`. #2520 carries an identical copy of the file; merge origin/dev into #2520 once #2519 lands (identical add/add merges clean).
- Local: full unit + multitenancy 7,398 passed / 1 skipped / 1 xfailed (worktree .env TRACKER_RMS_ENABLED_TENANT_IDS=null); commercial-signals suites 125 passed; 7 mutation probes caught; migration up / down / up on throwaway pg16 (build_schema, organization_id reset to NOT NULL, stamp 1yw2kc2or920).

## Decisions (user, 2026-11-04)
- No since / until (told Juan 2026-11-02, thread 33691): whole history, `period` by `date` (never null, no undated). Future-dated follow-ups read recent.
- Company chain: related_company_id -> most recent relationship WITH a company by `relationship_recency_order`, ANY type -> current open contact_job (newest start). Unresolved still counted (industry null, no org). Resolved to the tenant's own org -> dropped (same rule as every signal).
- KForce gate: opt-out `TenantFeature.DISABLE_COMMERCIAL_SIGNALS_INTERACTIONS` (empty snapshot, no reads, tick sees it fresh). Migration sets it on tenants with an enabled `kforce` integration (precedent `c8n2vr5tqk7d`, data-driven); seed_kforce_tenant.py carries it. There is no API/admin route for available_features (TenantUpdate has none), hence the migration.
- `interaction_type` raw; contacts distinct per (type, company, period) summed over the group (M2 approximation).
- 64 contact-id slices (`COMMERCIAL_SIGNALS_INTERACTION_SLICES`).

## How
- `InteractionSQLRepository.aggregate_by_company`: CTE `per_contact` (contact, type, related_company, period) -> fallback company once per contact without related company (two correlated LIMIT 1 subqueries) -> group by (type, company, period); own org filtered with `IS DISTINCT FROM` so NULL survives. Reads contact_relationship + contact_job (M2 precedent).
- Rollup reuses `type` + `contacts`; `organization_id` nullable (migration). Reads NULL-safe: `_exclusion` = `org IS NULL OR org NOT IN (...)`; `organization_ids` skips NULL.
- Parked #2509 follow-ups done here: `ActivityPeriod` -> `SignalPeriod` in import-free `app/modules/commercial_signals/period.py`; "rule" docstrings; per-row unmapped-stage assertion; `_recent_since()` reads settings; midnight tests freeze noon with `clock`; hash-invariant test; relationships/deals failure tests use `db_faults`.

## Numbers
- kforce-dev 2026-11-04: 3,049,169 interactions, 1,017,149 with related company (33%), 684,349 contacts, 64,710 in the last 365 d; types = Client Visit variants (105k null). For KForce contacts without related company the relationship / job steps almost never resolve. 1/32 slice 11.5-13.6 s cold; generated 1/64 slice 4.3-10.8 s cold, ~0.2 s warm.
- dev (NOT prod evidence): Navitec 513k interactions, 96.7% related company, 2.5% unresolved; Taller: 39 interactions resolve via Consultant relationships to Taller itself (dropped as own org).
- **Prod not measured** (classifier blocks echo-prod psql). Query file handed to the user: session scratchpad `m4_prod_q1.sql` (per tenant: interactions per resolution step + own_org + unresolved; raw types).

## Gotchas
- polyfactory can't build under a frozen `clock` (FakeDatetime -> "Unsupported type datetime"): build rows first, then `clock.set(...)`.
- `Row.count` is the tuple method: `row._mapping["count"]`; sum() over bigint comes back Decimal -> int().
- `db_faults.fail_next(statement_containing=...)` is a plain substring: "per_contact" (interactions), "FROM organization_deal" (deals), "%(contact_ids)s" (relationships aggregate).
- Worktree guard refuses `source`, redirects to the main checkout and heredocs that mention the VCS; worktree add works from inside the worktree; vault writes via a dotfile script in the worktree.
- After deploy every tenant reads stale once (no interactions snapshot) -> one full refresh per tenant on the first tick.

## Pending
- Merge #2519 -> merge origin/dev into #2520 -> `alembic heads` = 1 -> review.
- Prod numbers from the user (Navitec resolution coverage, types) -> docs + tell Juani (unresolved share, KForce opted out).
- After merge: close US 25732; Feature-level: Task 25734 API keys, M5 only if needed, qa/main promotion of M2-M4.

## Related
- [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]]
- [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]]
- [[Commercial signals M3 - deals aggregates for the commercial profile API (US 25731)]]
