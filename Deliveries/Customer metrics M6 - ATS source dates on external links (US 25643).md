---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, customer-metrics, external-links, migration, trackerrms, jazzhr]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2488"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25643"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M6 - ATS source dates on external links (US 25643)

Customer metrics M6. `entity_external_links` gains `source_created_at` / `source_updated_at`: when a record was created or updated in the ATS (TrackerRMS for Navitec, JazzHR for Taller). The metrics definition of a new candidate is `coalesce(source_created_at, talent.created_at) >= role.open_at`. The backend half only: the dates arrive once the inbound pipeline sends them, and who owns that is PRD open question 7. Related: [[Customer metrics M7 - metrics read endpoints (US 25644)]], [[Map - TrackerRMS integration]], [[Map - JazzHR integration]].

## Azure / docs
- [US 25643](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25643): In revision 2026-10-30, PR linked as GitHub Pull Request, comment 29225311 lists the scope changes.
- [Tech PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj) rev 90 (2026-10-30), updated for both M6 and M7:
  - M6 checklist, M6 SQL block, Migration plan (resync + revision ids), Idempotency, Risks cell, open question 7, Backfill strategy;
  - M7 checklist and API contract;
  - 2 changelog rows.

## PRs
- [#2488](https://github.com/taller-projects/echo-backend/pull/2488) → dev, OPEN 2026-10-30 (`5eb4b12f`, branch `25643/external_link_source_dates`, worktree `.claude/worktrees/25643-source-dates`). Migration `nwo4dn95fdjw`, parent `5ehxknwwrxn8`.

## Decisions (user, 2026-10-30)
- Endpoint only, no backfill code. The one-time resync is the pipeline re-pushing links with their dates through `POST /internal/external-links`. A CSV loader script gets written only if open question 7 comes back as "export file", once that file's columns are known.
- No `now()` default. The user asked about it; the answer was that `created_at` already holds Echo's import time, which is exactly the value the metric must not use.

## How
- `SourceDates` (`external_link/external_platforms.py`) holds two optional `AwareDatetime` fields. A date without a timezone offset is a 422.
  - `ExternalLinkUpsertRequest` and `ExternalIntegration` (the org create's `external_integration`) extend it.
  - `ExternalLinkResponse` returns both dates.
- `ExternalLinkService.bind(..., source_dates=)` → `upsert_link(source_created_at=, source_updated_at=)`.
  - On conflict, each column is `coalesce(excluded, stored)`: a date that is sent replaces the stored one, a missing one never clears it.
  - The KForce dual write and the PSA bind send no dates.
- The PRD was wrong about where the dates go: the contact, role and talent internal upserts never write `entity_external_links`. The pipeline binds through `POST /internal/external-links`, and only `POST /internal/organizations` writes a link from its own payload.
- Org-merge journal and undo need no change: they capture with `to_jsonb(row)` and restore with `jsonb_populate_record`.

## Gotchas
- Taller roles have no `jazz_hr` link rows: the JazzHR id lives only in `role.external_id`. Their dates need the pipeline to bind those links first.
- `pytest -p no:logging` disables the `caplog` fixture, which made `test_psa_intake.py` look broken. Don't use that flag on suites that use `caplog`.
- `tests/system/test_tracker_rms_sync_endpoints.py`: 7 tests fail with 403 locally on any branch (seen on the M7 branch too). The system suite isn't in CI.
- Inside an EnterWorktree session, the worktree guard refused a helper script under `/tmp` and the scratchpad. Use `<worktree>/.claude/worktrees/tmp/` (ignored).

## Evidence
- New endpoint tests: dates stored (`-03:00` normalized to UTC), a re-push without dates keeps them, a later `source_updated_at` replaces only that date, no offset → 422. Mutation caught: overwrite instead of `coalesce`.
- Local: 118 external-link tests and 58 PSA tests passed.
- Migration smoke (`<worktree>/.claude/worktrees/tmp/migration_smoke_m6.py`): `create_all` + stamp, downgrade/upgrade twice, a re-run over existing columns, and `create_all` types matching the migration's.

## Pending
- [ ] CI on `5eb4b12f`, review, merge; close US 25643 on merge to dev.
- [ ] Open question 7: name the pipeline owner and have them send the dates (+ bind Taller role `jazz_hr` links); then the Navitec / Taller re-push run, ≥ 95% counts per entity on the ticket, `ANALYZE entity_external_links`.
- [ ] Tell Nico: the `coalesce(source_created_at, talent.created_at)` definition is live once dates arrive.
- [ ] qa / main promotion.

## Related
- [[Customer metrics M7 - metrics read endpoints (US 25644)]] · [[Customer metrics M4 - proposal versions (US 25640)]] · [[Map - TrackerRMS integration]] · [[Map - JazzHR integration]]
