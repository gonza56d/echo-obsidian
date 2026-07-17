---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-09
tags: [feature, trackerrms, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1757"
  - "https://github.com/taller-projects/echo-backend/pull/1758"
  - "https://github.com/taller-projects/echo-backend/pull/1789"
  - "https://github.com/taller-projects/echo-backend/pull/1791"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23507"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23508"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23509"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23510"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23493"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23515"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23516"
---

# ATS deep-links — "Abrir en ATS" (US 23507 + US 23493)

Expose `external_links` (TrackerRMS ids from `entity_external_links`) on API responses so the FE can render a deep-link button into the client's ATS. Built for **Navitec** (TrackerRMS), config-driven per tenant.

## PRs
- [#1757](https://github.com/taller-projects/echo-backend/pull/1757) **M1** ([tasks 23508](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23508)/[23510](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23510)) — `external_links` in talent/contact/role/organization **detail** responses + config seed — merged 2026-07-08
- [#1758](https://github.com/taller-projects/echo-backend/pull/1758) **M2** ([task 23509](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23509)) — same in **list** responses — merged 2026-07-08
- [#1789](https://github.com/taller-projects/echo-backend/pull/1789) **[US 23493](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23493)** ([tasks 23515](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23515)/[23516](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23516)) — serve the ATS logo from **Echo blob storage** (config `logo_key` + CDN URL composition) instead of hotlinking — merged 2026-07-09
- [#1791](https://github.com/taller-projects/echo-backend/pull/1791) — cherry-pick of [#1789](https://github.com/taller-projects/echo-backend/pull/1789) → qa — merged 2026-07-09

## How / notes
- Object mapping Echo↔TrackerRMS: Role→Opportunity, Talent→Resource, Application→OpportunityResource, Organization→Client (see [[Map - TrackerRMS integration]]).
- Logo asset live on CDN; **prod config auto-converts at promotion** (no manual prod step).
- [Tickets 23515](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23515)/[23516](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23516) → Ready to Test.

## Related
- [[External links writeback (US 23126)]] — the data this exposes
- [[Map - TrackerRMS integration]]
