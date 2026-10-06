---
type: investigation
status: done
env: taller
delivered: 2026-10-06
tags: [investigation, navitec, trackerrms, outbox, external-links, duplicates]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2388"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25390"
prd: https://app.notion.com/p/383aedca11f0812c8c52cee6d9852d4b
---

# Navitec duplicated Resources from reverse push — ats_external_ids vs entity_external_links (investigation)

Investigation (2026-10-06, no ticket yet) of Navitec's report "se están
duplicando entidades con el push". Triggered by Nico's doc
"Navitec: candidates duplicados en Tracker" (Claude Doc
`claude.ai/artifact/AnunNV8eVLMVrNxeMQikc9`). Verified against `dev` code
and Echo PROD (read-only, tenant `2445fa20-f769-4f10-854e-a9e74df71ac5`).

## TL;DR

- **Confirmed. Root cause is in echo-backend.** Since
  [#1574](https://github.com/taller-projects/echo-backend/pull/1574)
  (2026-06-18, [[External links writeback (US 23126)]]) talent/application
  ids are *written* to `entity_external_links`, but the dispatcher and the
  manual "Sync to ATS" still *read* the legacy columns
  (`talent.ats_external_ids->>0`, `application.external_id`,
  `role.external_id`). tracker-rms-api stopped writing those columns the same
  day (its commit `a337769`, per Nico's doc) — **0 of 212** inbound talent
  links created since then are mirrored into `ats_external_ids`.
- A Tracker-born talent therefore has a link but an empty column. The first
  FE edit emits `talent.updated` → `OutboxRepository.get_external_id` returns
  NULL → `POST /sync/{tenant}/tracker_rms/candidate` → **new Resource**.
  The response id is then appended to the column + a second link, so Echo
  shows one talent and Tracker two Resources.
- The comment on `_DUAL_WRITE_ENTITY_TYPES` (`app/modules/outbox/repository.py`)
  literally records this as "reads migration deferred". No Azure ticket or
  PR exists for the deferred read migration (WIQL + gh search 2026-10-06).

## PROD numbers (2026-10-06)

| Measure | Value |
|---|---|
| Talents with Tracker link but empty `ats_external_ids` (exposed) | 17 (16 Tracker-born, 0 outbox events yet) |
| Applications with link but `external_id` NULL | 3 |
| Roles with link but `external_id` NULL | 3 |
| Echo-created talent Resources since 2026-06-20 | 152 |
| …of which duplicated an already-linked Resource | **28** |
| …by month (jun/jul/ago/sep/oct) | 1 / 19 / 2 / 1 / 6 |
| Application duplicates from the same mechanism | 1 (`16378`→`16427`, 2026-07-17) + 2 double-entry races (`16621/16622`, `16647/16648`) |

- Nico's doc counts 11 talent pairs (from 2026-07-24 on, incl. the
  `39357/39358` race). The **18 extra** are 2026-06-24 → 2026-07-19: two from
  the manual Sync button before the dispatcher existed in prod, the rest
  during the first prod enablement / backlog drain week
  ([[Outbox skips internal-originated emits (Bug 23656)]]). Unknown whether
  Navitec already merged those in Tracker — the stale links are still in Echo.
- Discriminator used: links written by Echo pushes carry `last_synced_at`
  (`UPSERT_ENTITY_EXTERNAL_LINK_SQL`); inbound binds via
  `ExternalLinkService.bind` leave it NULL. The 2026-06-19 14:25:44 batch is
  the backfill `p7w2kq9mx4rn` — exclude it.
- Doc timestamps labelled "UTC" are actually UTC-6 (39391 created 18:20 UTC,
  the duplicate 39393 at 18:46:33 UTC = delivery of outbox event
  `c083845a`, 3 s after the FE edit).

## Code paths with the bug (all read the column, never the link)

1. `OutboxRepository.get_external_id` — talent (`jsonb_append`), role and
   application (`scalar`) in `_ENTITY_SYNC_CONFIG`; links branch only for
   `_EXTERNAL_LINK_ENTITY_TYPES`. Used by `_deliver_tracker_rms` (PATCH vs
   POST) and `_deliver_tracker_rms_delete` (NULL → treated as "never pushed").
2. `TrackerRMSSyncService.sync_talent` — `has_external_id = bool(talent.ats_external_ids)`;
   `sync_role` / `sync_application` — `external_id is not None`.
   `sync_application` also *requires* the parent talent column and role
   column (lines ~721/742) → fails with `missing_dependency` for Tracker-born
   parents.
3. Role outbox gate `if db_role.external_id is not None` (`role/service.py`)
   → exposed roles never emit: no duplicate, but FE edits silently never
   reach Tracker. Manual Sync on such a role WOULD create a duplicate
   Opportunity.

## Constraints for the fix

- **Do not switch to links-only.** Taller has 1,654 roles with a Jazz id in
  `role.external_id` and **0** `jazz_hr` role links; the Jazz dispatcher path
  resolves roles via the same `get_external_id(..., external_platform="jazz_hr")`.
  Read `entity_external_links` filtered by platform first, fall back to the
  column.
- `ats_external_ids` is overloaded (Jazz prospect ids on Taller, Tracker ids on
  Navitec); the link table has the platform discriminator — reading it is
  strictly more correct.
- Newest-link-wins (`ORDER BY updated_at DESC`) means cleanup must delete the
  duplicate's link, or PATCHes keep targeting the Resource Navitec deletes.
- Order of operations: close the cause (code fix or the column backfill for
  the 17+3+3 exposed rows) **before** Navitec merges pairs in Tracker.

## Outcome
- [Bug 25390](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25390) filed 2026-10-06; fix PR [#2388](https://github.com/taller-projects/echo-backend/pull/2388) → dev — [[Reverse push duplicates TrackerRMS Resources - external ids read from entity_external_links (Bug 25390)]].

## Related
- [[Map - TrackerRMS integration]]
- [[External links writeback (US 23126)]] — the dual-write that left reads behind
- [[Outbox skips internal-originated emits (Bug 23656)]] — the July window where 16 of the 28 duplicates were minted
- [[ATS deep-links Open in ATS (US 23507)]]
