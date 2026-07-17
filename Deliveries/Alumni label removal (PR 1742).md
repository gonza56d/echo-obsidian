---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-07
tags: [bugfix, contact, relationships]
prs: [1742, 1743, 1744]
tickets: [23259, 19757]
---

# Legacy "Alumni" label removal — backend (PR 1742)

After [[Generic Contact Relationships (US 23240)]], the backend **still derived the legacy "Alumni" label** for ended consultants in three places (models expr, smart-search view, dashboard). Rebranded to **Consultant + relationship_state=Past**. The stale label had also broken the Consultant filter.

## PRs
- [#1742](https://github.com/taller-projects/echo-backend/pull/1742) → dev · [#1743](https://github.com/taller-projects/echo-backend/pull/1743) → qa (cherry-pick) · [#1744](https://github.com/taller-projects/echo-backend/pull/1744) → main (cherry-pick) — all merged 2026-07-07

## Notes
- FE [US 23259](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23259) is the FE-scoped half (Alumni chrome derived from state) — was "Being defined".
- Smart-search **matview recreation + FE tile follow-ups still pending** (owner-managed views, ref [19757](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/19757) — see the gotcha in [[Generic Contact Relationships (US 23240)]]).

## Related
- [[Map - Contact Relationships]]
