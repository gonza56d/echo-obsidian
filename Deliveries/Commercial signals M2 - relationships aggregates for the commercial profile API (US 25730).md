---
type: delivery
status: shipped-prod
env: both
delivered: 2026-11-03
tags: [feature, internal-api, kforce, navitec, data-team, background-job]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2500"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25730"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728"
prd: "https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C"
---

# Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)

Second signal of Juani's `tenant_commercial_profile_api` v1.1 contract: `GET /internal/commercial-signals/relationships` serves the tenant's Client / Prospect relationships grouped by type × industry × period and by type × title × period (distinct organizations, contacts, Active relationships, last start date), plus `totals` and the complete `organizations` list. Same snapshot / refresh foundation as [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]]. No FE involvement.

## Azure / docs
- [Feature 25728](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728) → [US 25730](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25730) (M2, P2). Next: M3 deals (US 25731), M4 interactions (US 25732), M5 organizations (US 25733, only if needed), API keys Task 25734.
- Request doc (the contract): [echo-backend: endpoints commercial-signals](https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C). Repo note: `docs/commercial-signals.md` ("Decisions (M2, relationships)").

## PRs
- [#2500](https://github.com/taller-projects/echo-backend/pull/2500) → dev — **MERGED** 2026-11-03 18:25Z, squash `3b9deac39` (opened on `d44ba99a`), branch `25730/commercial_signals_relationships` (worktree `.claude/worktrees/25730-cs-relationships`). Migration `h4tq9mxe2kcs` after `for6a8gqwfav`. Local: commercial-signals unit + multitenancy 41 green, relationship-state regression files 85 green; full unit + multitenancy 2425 passed / 1 failed (`test_custom_fields` manual-sync test: local `.env` `TRACKER_RMS_ENABLED_TENANT_IDS` allow-list rejects the test tenant; passes with `null`; PR comment posted). US 25730 In revision (rev 2) + PR linked + decisions comment 29248156.
- Review r1 2026-11-03: Pedro **APPROVED** (READY WITH NITS, 0 blockers, review 5754259828; CI green on `d44ba99a`). 8 nits all fixed in `5a788b9c5` (pushed; reply comment 6611531562): `refresh_all` isolates a failing signal (per-signal try → rollback + log + re-raise at the end; tenant resolved once, `_refresh_activities` / `_refresh_relationships` take the Tenant), each slice binds only its range's pre-fetched ids (`_within`), `COMMERCIAL_SIGNALS_INTERACTION_WINDOWS` (16), `relationship_is_active_expr` public, `_unnest_contact_ids`, prod counts out of docstrings, 401/422 rows + Alumni row + partial-failure test at the engine seam (`before_cursor_execute` raises on the statement binding `contact_ids`). 3 **questions open for the `main` promotion**: per-window counts of the pre-fetch on kforce-prod (equal time windows, recent weeks cluster), `EXPLAIN (ANALYZE, BUFFERS)` of one slice with the real 63k array (hashed SubPlan?), end-to-end `scripts/refresh_commercial_signals.py` on kforce-dev (`read_seconds`, Python gaps < 30 s idle-in-transaction).

## How
- Endpoint: same params as activities (`recent_since`, `limit`, `exclude_org_ids`), response `recent_since` / `source_updated_at` / `computed_at` / `totals` / `by_industry` / `by_title` / `organizations`. Rollup rows at (type, company, period) and (type, title, company, period) grain with new nullable columns `type`, `contacts`, `active_count`.
- Refresh: the per-tenant job now runs `refresh_all` (activities, then relationships; one swap each). A tenant is stale when any signal is. Relationships are read in 32 **contact-id** slices (a contact's rows land in one slice → distinct contacts add up across slices), folded in Python, industries resolved like M1.
- Active: `relationship_is_active_expr` (public since the nits commit) reused; its `last_interaction_date` term is fed from a pre-fetched set of contacts past `recent_interaction_cutoff()` (new helper in `contact/models.py`, also used by the predicate), read in 16 date windows, as `case(contact_id IN set → now(), else NULL)`. Same truth table; tests cross-check against `Relationship.state`.
- Title: `btrim(role)`, fallback to the contact's open `contact_job.role` at the company (newest start), rows with neither left out.

## Decisions (user, 2026-11-03, on kforce-prod numbers)
- `period` by `start_date` as the contract says: on KForce every Client relationship is undated (1,079,568 / 1,079,568; 0 Prospect rows) → `undated` + null `last_start_date` there; `active_relationships` is the recency signal. **Juani not told yet.**
- Prospect never Active (no Prospect arm in the rule; AC = `Relationship.state`).
- `totals` per type × period, like activities.
- Migration adds the 3 columns (checked on a throwaway pg16: upgrade / downgrade -1 / upgrade clean).
- `contact_job` title fallback kept: 9,581 of 64,070 empty roles on kforce-prod, ~half of Navitec's on dev (vs 14/94k on kforce-dev, why M1 dropped it for activities).
- `contacts` = distinct per company, summed over the group (a contact at two companies of one industry counts twice; ~0.1% ceiling on kforce-prod: 1,078,498 distinct contacts over 1,079,568 rows).

## Gotchas
- The naive per-row `contact.last_interaction_date` lookup costs ~1 ms/row on KForce (82-97 s per 1/16 slice on kforce-dev, a JOIN plans the same) → the pre-fetch design. Only 28,297 (kforce-dev) / 63,329 (kforce-prod) contacts interacted in the last 12 months.
- kforce-dev timings 2026-11-03 (laptop, read-only): pre-fetch 8.3 s over 16 windows; 1/32 slice (~32.5k rels, ~950 Active) 1.9-8.2 s company aggregate + ~1 s titles → ~3 min of reads per refresh.
- Industry is sparse: 34 of 52,570 counted companies on kforce-dev, 2,063 of 52,296 on kforce-prod → `by_industry` mostly null on KForce.
- `contact_job` is 6.6M rows on kforce-prod (118k on kforce-dev): the EXISTS probes of the active rule cost more there; not measured on prod.
- This session: the worktree guard refused shell writes to the scratchpad and long heredocs ("too complex"); the Write tool hook broke after the previous worktree was deleted ($CLAUDE_PROJECT_DIR stale). Python heredocs ≤ ~3k chars worked; apostrophes in heredoc comments seemed to trigger refusals.
- `gh pr merge` is refused by the auto-mode classifier ("merge without review") → the user merges.

## Pending
- ~~CI on `5a788b9c5` → squash-merge #2500 → close US 25730~~ done 2026-11-03: merged `3b9deac39`, US 25730 Closed + merge comment 29251879.
- Pedro's 3 questions before `main`: kforce-prod per-window counts + EXPLAIN of one slice (user runs, read-only), kforce-dev end-to-end refresh run after the dev deploy; post on the PR.
- Tell Juani: KForce relationships are all `undated` (no start dates), Prospect never Active, `contacts` approximation, `by_industry` null-heavy on KForce.
- M3 deals (US 25731): stage mapping won/lost/open/deferred still undecided; M4 interactions shape already told (period-labelled history).
- Task 25734 API keys per tenant/env + consumer smoke on kforce-dev.
- **2026-11-11**: on prod + kforce-prod since 2026-11-05 ([#2530](https://github.com/taller-projects/echo-backend/pull/2530) / [#2531](https://github.com/taller-projects/echo-backend/pull/2531), build 32641). Task 25734 closed without new keys → [[Commercial signals - consumer API keys per tenant (Task 25734)]]. echo-prod refresh verified (67 tenants daily since 11-05, no failures). What is still open lives in [[Map - Commercial signals]].

## Related
- [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]]
- [[Map - Kforce]]
- [[Map - Commercial signals]]
