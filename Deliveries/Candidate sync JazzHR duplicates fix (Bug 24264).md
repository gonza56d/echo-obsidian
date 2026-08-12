---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, jazzhr, talent, entity-resolution]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2058"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24264"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24239"
prd: ""
---

# Candidate sync JazzHR duplicates fix (Bug 24264)

The external-partner "Add Candidate" flow (`POST /talents/{ats_role_id}/sync`) both **blocked the upload** with "A record with these details already exists" **and** left **duplicate prospects in JazzHR** on every retry. Root cause: the candidate lookup matched by email only, so a real duplicate (same LinkedIn, different email) fell through to the create path and the talent INSERT collided on a unique constraint — *after* the irreversible Jazz push had already run, with no rollback for Jazz. This is the Echo-side fix; the data team owns the idempotent Jazz push + historical cleanup under Bug 24239.

## Azure / docs
- [Bug 24264](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24264) — Echo-side fix (this note).
- [Bug 24239](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24239) — original repro; data-side (idempotent `/candidates/sync_data` + Jazz dedup). Data team synced (Gonzalo).

## PRs
- [#2058](https://github.com/taller-projects/echo-backend/pull/2058) → dev — **in review** (2026-08-12)

## How
`TalentService.create_and_sync_talent` → `sync_talent_with_jazz_and_vendor` (`app/modules/talent/service.py`). Four changes:
- **A1 (core):** resolve the existing candidate with `check_duplicate(email, linkedin_url)` instead of `get_talent_by_email` — a real duplicate takes the **update** path instead of a colliding INSERT. The two tenant-unique identifiers (`tenant_email_uniq_idx`, `tenant_linkedin_url_uniq_index`) are exactly the ones that were throwing.
- **A4:** dedupe `ats_external_ids` (append-if-absent) so a stable `prospect_id` from an upserting Jazz push no longer accumulates.
- **A5:** rewrote the `set_source` `before_insert` listener (`app/modules/talent/models.py`) to run Core statements on the **flush `Connection`** instead of a nested `Session(conn)` that `commit()`-ed mid-flush — restores `create_talent` atomicity.
- **A0:** `echo_exception_handler` now logs `DuplicateError.constraint` (the client only ever sees the generic "Item already exists").

Genuine duplicate → update existing + sync to the same Jazz person, return the talent (no 400, no new duplicate) — the chosen UX.

Tests: 3 existing sync tests updated for the new collaborator; new service-level unit tests (dup-by-linkedin → update path, blocked sync makes **zero** `sync_data` calls, ats dedupe, append-new); exception-handler constraint-logging tests; real-Postgres system tests for the listener (`tests/system/test_talent_set_source.py`: new source, reuse, **atomicity-on-rollback**, vendor-link). 111 relevant tests green, lint clean.

## Decisions
- **Dropped passing `jazz_person_id` to entity-resolution** (an early plan item): it's an uncoordinated contract change and is redundant with the data team's create-or-get upsert. Echo owns "don't create-then-collide + don't accumulate ids"; the Jazz-level dedup stays with data.
- **Duplicate = update, not 409** (Gonzalo's call): a re-sync is a legitimate action (new CV, recruiter reassignment) — erroring would just re-break the flow.
- **Listener rewritten with Core `conn.execute`, not commit→flush**: `TimestampMixin` uses Python-side defaults, so the Core insert supplies `id`/timestamps explicitly; unambiguously atomic vs. relying on nested-session close semantics.

## Gotchas
- The bare "Item already exists" message maps to constraints whose names lack the substring `talent` (`DuplicateError.from_db_string`): `tenant_email_uniq_idx`, `tenant_linkedin_url_uniq_index`, `vendor_sources_pkey`. The app never logged the pgerror on a handled 400 → A0 fixes that.
- Prod blast radius (Taller, 2026-08-12): **~16,184 surplus Jazz prospects across 8,246 candidates** (one at 702) from the non-idempotent push — cleanup is data-side.
- Local unit run 404s all success-path talent endpoints (documented TestClient issue, green in CI) → the fix is tested at the **service** layer, and the listener via **system** tests.

## Pending
- Merge #2058 → dev; then qa/main promotion.
- Data team (Bug 24239): idempotent `/candidates/sync_data` (create-or-get) + honest 4xx/5xx; historical Jazz dedup (~16k).
- Confirm the exact firing constraint from prod once A0 logging lands (email vs linkedin).

## Related
- [[Map - JazzHR integration]] · [[Per-application recruiter from Jazz back-sync (Bug 24241)]] · [[Push Applications Echo to JazzHR (Feature 24051)]]
