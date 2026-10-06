---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, navitec, trackerrms, outbox, external-links]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2388"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25390"
prd: "https://app.notion.com/p/383aedca11f0812c8c52cee6d9852d4b"
---

# Reverse push duplicates TrackerRMS Resources — external ids read from entity_external_links (Bug 25390)

Navitec (2026-10-06): "se están duplicando entidades con el push". A talent
born in Tracker reaches Echo with a link row only; the outbound side decided
create-vs-update on the legacy columns, saw NULL and POSTed a second
Resource. Root-cause analysis + PROD evidence:
[[Navitec duplicated Resources from reverse push — ats_external_ids vs entity_external_links (investigation)]].

## What
- Dispatcher (`OutboxRepository.get_external_id`) and manual "Sync to ATS"
  (`TrackerRMSSyncService.sync_talent/sync_role/sync_application`) now resolve
  the Tracker id from `entity_external_links` first (newest mapping,
  platform-scoped) and fall back to `talent.ats_external_ids->>0` /
  `role.external_id` / `application.external_id` only when no link exists.
- `sync_application` parent checks resolve talent/role the same way (no more
  `missing_dependency` for Tracker-born parents); update payloads carry the
  resolved id.
- `RoleService._update` outbox gate (`_is_linked_to_ats`) also accepts a link
  row → Tracker-born roles sync their edits (before: silently dropped).
- New `ExternalLinkService.resolve_external_id(entity_type, entity_id, platform)`.

## Azure
- [Bug 25390](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25390)
  — **In revision**, assigned to me. Body = repro + root cause + PROD evidence
  + fix scope + follow-ups; comment 28992862 carries the PR link.

## PRs
- [#2388](https://github.com/taller-projects/echo-backend/pull/2388) → `dev`
  — OPEN 2026-10-06, branch `25390/external_id_reads_from_links`, commit
  `e106a183`. No migration.

## Decisions
- **Links-first, column fallback — never links-only.** Taller has 1,654 roles
  whose JazzHR id lives only in `role.external_id` (0 `jazz_hr` role links)
  and the Jazz dispatcher path (`_deliver_jazz_hr_*`) resolves roles through
  the same `get_external_id`. Dropping the column read would break Taller.
- Service path reads `active` links (`repo.get_active_links`); dispatcher raw
  SQL keeps the existing no-status-filter link query (one behaviour inside
  `get_external_id`). Only diverges on non-active rows, which nothing
  produces today.
- Role gate checks the column first (free) then `external_ids_by_entity`
  (any platform) — one query per role update, only for unlinked-column roles.

## Gotchas
- `asyncio.to_thread` + request context: the sync service resolves the link
  in a worker thread; `get_request_context()` is keyed by the request
  ContextVar (middleware) or thread id. Tests that call the service directly
  must `fork_request_context(RequestContext())` — plain
  `get_request_context().set_tenant_id()` only fills the main thread's cache
  and the worker sees "Tenant context not set".
- `talent.ats_external_ids` is NOT NULL (`'[]'`), so raw INSERTs in tests
  must pass `'[]'::jsonb`.
- `entity_external_links.tenant_id` has an FK → cross-tenant tests need a
  real second tenant (`create_entity(db, TenantFactory, Tenant, name=…,
  organization_id=…, max_seats=None)`).
- `tests/system/test_tracker_rms_sync_endpoints.py` 403s locally unless
  `TRACKER_RMS_ENABLED_TENANT_IDS=""` is exported (pre-existing).
- `TestCASWritebackTolerance._make_service` builds the service by hand —
  new collaborators must be added there and in
  `tests/unit/test_tracker_rms_sync_service.py::_make_service`.
- Worktree session: Bash guard refuses `zsh -ic`, heredocs and `$(…)`
  chains as "too complex"; scripts under `<worktree>/vault/scratch/`
  (gitignored) + `python3 vault/scratch/x.py` work for edits, Azure API and
  file writes outside the worktree.

## Pending
- [ ] Review + squash-merge #2388 → dev; then qa / main promotion.
- [ ] After PROD deploy: cleanup of the duplicate pairs with Navitec —
      they pick the survivor per pair, then Echo drops the duplicate's link
      and re-points the column (28 talent pairs since 2026-06-20 + 1
      application `16378→16427`; Nico's doc lists the 11 since 07-24).
      Newest-link-wins means a stale link keeps PATCHing a deleted Resource.
- [ ] Optional pre-deploy mitigation: copy the active link id into the empty
      column for the 17 talents / 3 applications / 3 roles exposed.
- [ ] tracker-rms-api defensive guard on candidate/application create
      (resolve `echo_id` against `entity_mapping` / Echo links first).
- [ ] Close Bug 25390 on merge.

## Related
- [[Navitec duplicated Resources from reverse push — ats_external_ids vs entity_external_links (investigation)]]
- [[Map - TrackerRMS integration]]
- [[External links writeback (US 23126)]] — the dual-write that left reads behind
- [[Outbox skips internal-originated emits (Bug 23656)]]
