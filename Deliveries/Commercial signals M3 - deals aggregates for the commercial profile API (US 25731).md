---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, internal-api, navitec, data-team, background-job]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2509"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25731"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728"
prd: "https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C"
---

# Commercial signals M3 - deals aggregates for the commercial profile API (US 25731)

Third signal of the data team contract: `GET /internal/commercial-signals/deals` serves the tenant deals as `totals` (type x stage_category x period) and `by_group` (+ industry), plus the complete `organizations` list. Same snapshot / refresh as [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]]. No FE involvement.

## PRs
- [#2509](https://github.com/taller-projects/echo-backend/pull/2509) -> dev, **OPEN** 2026-11-03, commit `362364341`, branch `25731/commercial_signals_deals` (worktree `.claude/worktrees/25731-cs-deals`). Migration `ga7mqtjixquc` after `h4tq9mxe2kcs`. US 25731 In revision + PR linked + comments 29252287 (decisions) and 29252784 (PR).
- Local: full unit + multitenancy 7,272 passed / 1 skipped (worktree .env TRACKER_RMS_ENABLED_TENANT_IDS=null); commercial-signals suites 84 passed, module at 100%; mutation check (no html unescape, no own-org exclusion) fails 3 tests; migration up / down / up on throwaway pg16 stamped at h4tq9mxe2kcs (full chain needs Supabase auth.users).

## Decisions (Juan, data team, 2026-11-03, on echo-prod numbers)
- Prod deals: Taller 831, Navitec 219, no other tenant; kforce-dev 0 (kforce-prod count never run).
- Stage mapping (normalized: html unescape, whitespace collapsed, lowercase): won = closed won*, Agreement Signed, Navitec ended + billing; lost = closed lost*, Disqualified; deferred = deferred*, Stalled; open = the known pre-close stages and anything unknown. Prod counts: won 403 Taller + 219 Navitec, lost 266, deferred 90, open 72.
- Navitec deals are projects (all ended / billing): all won. The data team reads won as experience per line of service and computes no win rate.
- period by close_date (never null). Navitec close_date = project end, so billing until 2027 reads recent (wanted).
- Unknown stages -> open + warning `commercial_signals_deal_stages_unmapped` (tenant, stages with counts), asked by Juan.
- origin dropped: 0 of 1,050 prod deals have it, not used by the consumer.
- type raw (Navitec line of service, Taller business type); rollup `type` column unbounded (existingbusiness = 16 chars, the old limit).
- limit = top N by_group rows per type x stage_category x period.

## How
- `OrganizationDealService.aggregate_by_company` (deal module owns the query): one statement per tenant, grouped by type, raw stage, company, period.
- `_refresh_deals` maps stages in Python and folds; `_replace_snapshot` / `_industries` now shared by the three refreshes.

## Gotchas
- Prod stores `Contract &amp; Negotiation` (HTML-escaped by the HubSpot sync) and trailing-space variants (Deferred, Closed Won-In Recruiting).
- echo-prod psql from the laptop fails with EADDRNOTALLOWED off the allowed network (user reconnected).
- Worktree guard blocks Write outside the worktree (scratchpad included) and long python heredocs; apply edits with Edit, temp files inside the worktree.
- After deploy every tenant reads stale (no deals snapshot) -> one full refresh per tenant within the hour (KForce ~4 min reads).

## Pending
- Review + merge #2509 -> close US 25731.
- Watch the unmapped-stages warning in Loki after the dev deploy; add stages to the mapping.
- Feature-level: Task 25734 API keys, M4 interactions (US 25732), M5 organizations only if needed, Pedro M2 questions before main.
- Juan: industry coverage answer sent? (kforce-prod: 7% of companies, about half of activities carry industry.)

## Related
- [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]]
- [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]]
- [[Map - Kforce]]
