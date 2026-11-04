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
- Review r1 (2026-11-03): Gise CHANGES REQUESTED (blockers: no `Contract Sent` row in the stage test; none of the /deals 422 / 401 / failing-read tests relationships has) + Leo APPROVED, READY WITH NITS (prefix matching vs the exact list Juan confirmed, one-time content-hash bump at the deploy, `ActivityPeriod` in contact.activity, timing split). Both blockers verified real and fixed with the nits in `49fc2791c` (2026-11-04, pushed from worktree `.claude/worktrees/25731-cs-deals-r1`, branch `25731/commercial_signals_deals_r1`): exact stage match (no prefixes; `Closed Won-Expired` test row reads open + logged), `_rollup_row` without a `stage_category` default (activities / relationships hash unchanged, no `source_updated_at` bump), `Contract Sent` row, 4 error-path tests + midnight boundary + null type + 3-way tie under limit + no-warning test (101 passed, 84 before); docs: exact table, global mapping on purpose, how to add a rollup column. Inline replies + review reply posted on [#2509](https://github.com/taller-projects/echo-backend/pull/2509), Gise re-requested, PR body got a "Review round 1" section. Deferred: `ActivityPeriod` move (with M4), timing split, `refreshed` fixture (no leak). Azure comment 29258297 on US 25731: `totals` scope note (Leo's out-of-scope item).
- Local: full unit + multitenancy 7,272 passed / 1 skipped (worktree .env TRACKER_RMS_ENABLED_TENANT_IDS=null); commercial-signals suites 84 passed, module at 100%; mutation check (no html unescape, no own-org exclusion) fails 3 tests; migration up / down / up on throwaway pg16 stamped at h4tq9mxe2kcs (full chain needs Supabase auth.users).

## Decisions (Juan, data team, 2026-11-03, on echo-prod numbers)
- Prod deals: Taller 831, Navitec 219, no other tenant; kforce-dev 0 (kforce-prod count never run).
- Stage mapping (normalized: html unescape, whitespace collapsed, lowercase; EXACT match since review r1, the prefixes went away): won = Closed Won, Closed Won-Active, Closed Won-In Recruitment / Recruiting, Agreement Signed, Navitec ended + billing; lost = Closed Lost, Disqualified; deferred = Deferred, Deferred to next quarter, Stalled; open = the known pre-close stages and anything unknown. Prod counts: won 403 Taller + 219 Navitec, lost 266, deferred 90, open 72.
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
- A default key in `_rollup_row` lands in every signal's content hash: M2 bumped `source_updated_at` once for every tenant that way. Set a new column only in the refresh that uses it (one key set per `replace_snapshot` call keeps insertmanyvalues happy).
- Bash isolation checker in a worktree session refuses compound `gh api` commands (loops, `&&` chains, jq with `|`): one plain `gh api` per call. Worktree guard also blocks Write into the scratchpad: temp files under `<worktree>/.scratch-r1/` (untracked).
- After deploy every tenant reads stale (no deals snapshot) -> one full refresh per tenant within the hour (KForce ~4 min reads).

## Pending
- Gise re-review of `49fc2791c` -> merge #2509 -> close US 25731.
- Move `ActivityPeriod` out of contact.activity.schemas (deal, relationship and the M4 interactions import it) in the M4 PR.
- Watch the unmapped-stages warning in Loki after the dev deploy; add stages to the mapping.
- Feature-level: Task 25734 API keys, M4 interactions (US 25732), M5 organizations only if needed, Pedro M2 questions before main.
- Juan: industry coverage answer sent? (kforce-prod: 7% of companies, about half of activities carry industry.)

## Related
- [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]]
- [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]]
- [[Map - Kforce]]
