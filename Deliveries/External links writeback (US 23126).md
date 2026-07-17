---
type: delivery
status: merged
env: taller
delivered: 2026-06-18
tags: [feature, trackerrms, outbox]
prs: [1574]
tickets: [23126, 23127, 23128]
prd: "Notion 383aedca — App/Talent external_links (writeback + backfill only)"
---

# External links writeback (US 23126)

Track **application** and **talent** TrackerRMS ids in `entity_external_links`, so Echo knows which TrackerRMS object each entity maps to. Scope was deliberately **writeback + backfill only** — no user-facing exposure (that came later with [[ATS deep-links Open in ATS (US 23507)]]).

## Azure / docs
- [US 23126](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23126) — parent story
- [Task 23127](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23127) (T1, writeback) · [Task 23128](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23128) (T2, backfill)
- PRD: [Tracking de external ids de Application y Talent en entity_external_links — PRD Técnico](https://app.notion.com/p/383aedca11f0812c8c52cee6d9852d4b)

## PRs
- [#1574](https://github.com/taller-projects/echo-backend/pull/1574) → dev — merged 2026-06-18

## How
- When the TrackerRMS sync service returns an id for an application/talent push, it is persisted into `entity_external_links` (same table the org/role/user entities already used — see [[Map - TrackerRMS integration]]).
- Backfill migration `p7w2kq9mx4rn` populates links for pre-existing synced entities.

## Related
- [[ATS deep-links Open in ATS (US 23507)]] — consumes these links to render "Abrir en ATS"
- [[Map - TrackerRMS integration]]
