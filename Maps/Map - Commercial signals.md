---
type: map
tags: [map, commercial-signals, data-team, kforce]
---

# Map — Commercial signals (Feature 25728)

Juani's (data team) `tenant_commercial_profile_api` reads per-tenant aggregates from `GET /internal/commercial-signals/{activities,relationships,deals,interactions}`. They are served from a daily snapshot (`commercial_signal_snapshot` + `commercial_signal_rollup`) that the worker refreshes per tenant: `commercial_signals_refresh` background job, enqueued by an hourly tick for stale tenants. The contract is Juani's request doc [echo-backend: endpoints commercial-signals](https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C) (we have comment/suggest access only). [Feature 25728](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728) is In development.

## Status (2026-11-11)
| Delivery | Ticket | Where |
| --- | --- | --- |
| [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)\|M1 activities]] | [US 25729](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25729) Closed | prod + kforce-prod 2026-11-05 ([#2530](https://github.com/taller-projects/echo-backend/pull/2530) / [#2531](https://github.com/taller-projects/echo-backend/pull/2531), build 32641) |
| [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)\|M2 relationships]] | [US 25730](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25730) Closed | prod + kforce-prod 2026-11-05 |
| [[Commercial signals M3 - deals aggregates for the commercial profile API (US 25731)\|M3 deals]] | [US 25731](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25731) Closed | prod + kforce-prod 2026-11-05 |
| [[Commercial signals M4 - interactions aggregates for the commercial profile API (US 25732)\|M4 interactions]] | [US 25732](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25732) Closed | prod + kforce-prod 2026-11-05 (KForce opted out) |
| [[Commercial signals - KForce relationships never written + placeholder values (Bug 25822)\|Bug 25822 KForce relationships + placeholders]] | [Bug 25822](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25822) Closed | prod + kforce-prod 2026-11-10 ([#2562](https://github.com/taller-projects/echo-backend/pull/2562) / [#2563](https://github.com/taller-projects/echo-backend/pull/2563), build 32869); migration `7zmdcppifnwm` dev only |
| [[Commercial signals - consumer API keys per tenant (Task 25734)\|API keys per tenant]] | [Task 25734](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25734) Closed 2026-11-11 | no keys minted: auto-provisioned Vault dict |
| M5 organizations (paginated) | [US 25733](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25733) Being defined | waiting on Juani |

## Request doc checklist (rev 34, never ticked in the doc)
- Owner + date per endpoint: never written back in the doc.
- Daily rollup for KForce: done (refresh job). kforce-prod failed every night 11-05..11-10 until Bug 25822.
- Deal stages → won / lost / open / deferred: done in M3.
- Complete `organizations` list or a separate endpoint: open, US 25733 (M5).

## Production state
**echo-prod** (verified 2026-11-11, read-only): first refresh job 2026-11-05 00:35Z; 469 jobs (67 tenants daily, 11-05 ran twice), all completed on attempt 1, none failed or dead; 268 snapshots = 67 tenants × 4 signals, latest 11-10 19:28-19:29Z; 16-72 s per tenant; the daily start drifts 15-45 min earlier each day.

| Tenant | relationships | interactions | deals | activities |
| --- | --- | --- | --- | --- |
| Navitec | 28,227 | 9,964 | 72 | 0 |
| Taller | 1,170 | 6,514 | 359 | 0 |
| Battle Tested | 0 | 67 | 0 | 0 |

Rollup rows per signal. activities is 0 everywhere because echo-prod `contact_activity` is empty (KForce-only data); Battle Tested has no `contact_relationship` rows and no deals.

**kforce-prod** (2026-11-10, manual job `bfb649af` after Bug 25822): relationships 892,109, activities 327,522, deals 0, interactions 0 (opted out by flag). The first unattended nightly run (2026-11-11, ~01:50-02:30Z) is not checked yet.

**Keys**: see [[Commercial signals - consumer API keys per tenant (Task 25734)]].

## Remaining (the Feature closes once M5 is built or dropped)
- [ ] US 25733 M5: ask Juani whether KForce's inline `organizations` list (21,296 orgs) is acceptable, else build the paginated endpoint.
- [ ] kforce-prod: first unattended nightly refresh + KForce key suffix `518649` (Supabase SQL editor).
- [ ] Message to Juan (drafted 2026-11-10, user sends) + consumer env var `ECHO_API_KEYS_BY_TENANT` in prod + Taller tenant id `01df2012`.
- [ ] Migration `7zmdcppifnwm` (~3.6k `'NaN'` roles) rides the next dev → qa → main release after `fd6hehbo4zn7`; then confirm kforce-prod roles.
- [ ] Ticket for the echo-prod-only indexes `contact_relationship_active_idx`, `contact_relationship_active_latest_idx`.
- [ ] Close Feature 25728.

## Gotchas across the saga
- Every migration PR here hit two alembic heads at least once: run `alembic heads` after merging origin/dev, before the last push.
- echo-prod: session pooler works, the direct `db.<ref>` host times out; kforce-prod: Supabase SQL editor only.

## Related
- [[Map - Kforce]]
