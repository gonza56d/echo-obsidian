---
type: delivery
status: merged
env: both
delivered: 2026-10-30
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
- [US 25643](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25643): CLOSED 2026-10-30 on merge to dev (comment 29226297; earlier comment 29225311 lists the scope changes).
- [Tech PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj) rev 90 (2026-10-30), updated for both M6 and M7:
  - M6 checklist, M6 SQL block, Migration plan (resync + revision ids), Idempotency, Risks cell, open question 7, Backfill strategy;
  - M7 checklist and API contract;
  - 2 changelog rows.

## PRs
- [#2488](https://github.com/taller-projects/echo-backend/pull/2488) → dev, SQUASH-MERGED 2026-10-30 16:10Z as `74c17bc2` (head `fd2a2328`, CI green 24 min). Started at `5eb4b12f` ( branch `25643/external_link_source_dates`, worktree `.claude/worktrees/25643-source-dates`). Migration `nwo4dn95fdjw`, parent `5ehxknwwrxn8`.
  - Self-review r1 2026-10-30 (`/pr-review` full, 3 agents, not posted): READY WITH NITS, 0 blockers. All 6 nits fixed in `892de2e3`, pushed 2026-10-30 from worktree `.claude/worktrees/25643-source-dates-review` (branch `25643/external_link_source_dates-review`, pushed as `HEAD:25643/external_link_source_dates`; the original worktree is owned by another session). Pushed without the local suite (user asked); PR body refreshed. CI green on `892de2e3`.
  - Pedro's review 5714641271 on `892de2e3`: APPROVED, READY WITH NITS. Fixed in `fd2a2328` (pushed without the local suite, user asked): `SourceDates` moved to `external_link/schemas.py`, error text "one day from now (UTC)", `if source_dates is None`, tests (DB-level `POST /internal/organizations` stores the date + naive 422, explicit-null re-push keeps, 1900-01-01 accepted). PR body: outbound raw-SQL writers send no dates, existing orgs resync via external-links, merge collision delete can't drop dates (uq forbids it), no `ExternalLinkFilter` on purpose. PRD rev 92: accepted range in the M6 checklist + changelog row. Not answered on the PR: numeric epochs (`AwareDatetime` accepts `0` → 1970-01-01, inside the range).

## Decisions (user, 2026-10-30)
- Endpoint only, no backfill code. The one-time resync is the pipeline re-pushing links with their dates through `POST /internal/external-links`. A CSV loader script gets written only if open question 7 comes back as "export file", once that file's columns are known.
- No `now()` default. The user asked about it; the answer was that `created_at` already holds Echo's import time, which is exactly the value the metric must not use.

## How
- `SourceDates` (`external_link/schemas.py`) holds two optional `SourceDate` fields (`AwareDatetime` + range validator). No offset, or outside 1900-01-01 to tomorrow, is a 422.
  - `ExternalLinkUpsertRequest` extends it. The org create's `external_integration` is `OrganizationExternalIntegration` (`organization/schemas.py`, `ExternalIntegration` + `SourceDates`); `ExternalIntegration` stays an id pair.
  - Route + field descriptions: offset required, omitted or `null` keeps the stored date, DELETE + POST clears it.
  - `ExternalLinkResponse` returns both dates.
- `ExternalLinkService.bind(..., *, source_dates=)` → `upsert_link(source_created_at=, source_updated_at=)`.
  - On conflict, each column is `coalesce(excluded, stored)`: a date that is sent replaces the stored one, a missing one never clears it.
  - The KForce dual write and the PSA bind send no dates.
- The PRD was wrong about where the dates go: the contact, role and talent internal upserts never write `entity_external_links`. The pipeline binds through `POST /internal/external-links`, and only `POST /internal/organizations` writes a link from its own payload.
- Org-merge journal and undo need no change: they capture with `to_jsonb(row)` and restore with `jsonb_populate_record`.

## Gotchas
- Taller roles AND talents have no `jazz_hr` link rows: the JazzHR id lives only in `role.external_id` / `talent.ats_external_ids` + `jazz_person_id`. `p7w2kq9mx4rn` backfilled talent links only for single-integration tenants (Navitec in prod); the JazzHR outbox writes application links only. Until bound, Taller's new-candidate check falls back to `talent.created_at`.
- `AwareDatetime` alone accepts year 1 / 9999: with an offset that pushes the UTC value out of range, psycopg2 raises `ValueError: year ... out of range` reading the `RETURNING` row, a 500. Python's `astimezone(UTC)` raises `OverflowError` for the same values, so the validator catches that.
- Every re-push bumps `updated_at` (pre-existing). `updated_at` picks the "newest" link for outbound PATCH (`latest_link`, outbox `_linked_external_id`), role display/sort and deep links, so the resync can change the winner for entities with more than one link per platform.
- Taller re-push goes through `ensure_platform_enabled`: 400 unless Taller's `jazz_hr` integration is enabled.
- `role.open_at` is a naive `timestamp`; the coalesce is `timestamptz`, so the comparison is right only in a UTC session (Nico's ad-hoc SQL too).
- The org create only stores dates on the first bind: a re-post 409s at `ensure_external_id_unmapped` before `bind`.
- Another session's worktree is read-only (worktree-owner hook), even for a memory-file append. Work from a worktree of your own; inside it, helper scripts go under `<worktree>/.claude/worktrees/tmp/`.
- `pytest -p no:logging` disables the `caplog` fixture, which made `test_psa_intake.py` look broken. Don't use that flag on suites that use `caplog`.
- `tests/system/test_tracker_rms_sync_endpoints.py`: 7 tests fail with 403 locally on any branch (seen on the M7 branch too). The system suite isn't in CI.
- Inside an EnterWorktree session, the worktree guard refused a helper script under `/tmp` and the scratchpad. Use `<worktree>/.claude/worktrees/tmp/` (ignored).

## Evidence
- New endpoint tests: dates stored (`-03:00` normalized to UTC), a re-push without dates keeps them, a later `source_updated_at` replaces only that date, no offset → 422. Mutation caught: overwrite instead of `coalesce`.
- Local: 118 external-link tests and 58 PSA tests passed.
- Migration smoke (`<worktree>/.claude/worktrees/tmp/migration_smoke_m6.py`): `create_all` + stamp, downgrade/upgrade twice, a re-run over existing columns, and `create_all` types matching the migration's.

## Pending
- [ ] US 25643 description/AC still describe the old scope (4 upsert families + bulk, background job, NULL-only, "per (entity, platform)").
- [ ] PRD wording (range already in rev 92): Idempotency "changes nothing" -> "changes no stored date"; Backfill paragraph "fills only NULLs" vs a re-push replacing; M6 item 3 "roles and talents need jazz_hr links"; org dates resync via external-links (create 409s); response fields in the API contract; new-candidate query needs a platform filter + `min(source_created_at)` per talent, a UTC session, and an owning milestone.
- [ ] Before the resync, on prod: links per tenant/entity/platform, entities with more than one link per platform, `tenant_integrations` flags (queries in the r1 review).
- [x] Open question 7: name the pipeline owner and have them send the dates (+ bind Taller role `jazz_hr` links); then the Navitec / Taller re-push run, ≥ 95% counts per entity on the ticket, `ANALYZE entity_external_links`. **2026-11-17**: owner = Data → Task [25927](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25927) (child of 25635), handed to its owner by the user. Scope: Navitec TrackerRMS sync sends both dates on every bind + one-time re-push (prod had 0 dates: talent 31,247 · role 949 · org 5,453 links; multi-link entities talent 197 · org 59 · role 2 · contact 961 → re-push oldest `updated_at` first). Taller is post-JazzHR cutover (`tenant_integrations.jazz_hr` enabled=false → the endpoint 400s): no live pipeline; only legacy records lack dates (2,585 talents with `jazz_person_id`, 1,654 roles with a JazzHR id) → Data asked for a CSV if they still have JazzHR dates. Prod caller of POST /internal/external-links = python-httpx via the ingress (~236/day).
  - **2026-11-18 DONE.** Navitec: Juan (Data) re-pushed; prod coverage talent 100.0% (31,237/31,249) · role 98.9% (939/949) · org 100.0% (5,453/5,453); `ANALYZE entity_external_links` (it had never been analyzed: planner said 96 rows). Winner check: Juan snapshotted each entity's winning link before the push, 0 changes in 1,226 after (the DB keeps no pre-run record; the outbox stores no external_id). Going forward: the sync sends both dates since 2026-11-17 23:20Z (v0.45.0); org dates on the first bind only; touchpoints out of scope (a sync bind leaves `last_synced_at` NULL, Echo's raw-SQL outbound sets it: that's how to tell them apart). [Task 25927](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25927) Closed (comments 29367686, 29369205).
  - Taller: Data sent `taller_jazzhr_created_at_20261118.csv` (dates parsed from the JazzHR ids, UTC). Taller had no talent/role `jazz_hr` links. Loaded by [Task 25945](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25945) (Closed, comment 29369396) with a one-off psql script (attached there; CSV via stdin, dry run default, `-v apply=1`; guards tenant/jazz_hr disabled/row count): `jazz_hr` links `status='stale'` (no deep link, no outbound, role display reads `tracker_rms` only), only where the JazzHR date < Echo `created_at`, shared ids → oldest record. Prod 2026-11-18 15:15Z: 36,744 talent links / 32,200 of 37,161 talents, 998 roles. Role `open_at` already ≈ JazzHR date (median 19 h), so role dates don't move the new-candidate metric.
- [x] Metric query note (on Task 25927): `min(source_created_at)` per record, no `tracker_rms` / `status` filter (Taller's dates are `jazz_hr` stale links), UTC session for `role.open_at`.
- [x] qa / main: on main (`280a16ab`).

## Related
- [[Customer metrics M7 - metrics read endpoints (US 25644)]] · [[Customer metrics M4 - proposal versions (US 25640)]] · [[Map - TrackerRMS integration]] · [[Map - JazzHR integration]]
