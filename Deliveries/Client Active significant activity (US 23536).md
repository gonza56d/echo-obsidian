---
type: delivery
status: shipped-prod
env: both
delivered: 2026-07-10
tags: [feature, contact, relationships, kforce]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1803"
  - "https://github.com/taller-projects/echo-backend/pull/1804"
  - "https://github.com/taller-projects/echo-backend/pull/1805"
  - "https://github.com/taller-projects/echo-backend/pull/1806"
  - "https://github.com/taller-projects/echo-backend/pull/1807"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23536"
---

# Client Active requires recent significant activity (US 23536)

Business amendment to the Client Active semantics, landed on **both environments the same day**. New rule: Client Active requires **significant activity within 12 months considering both start and end dates**, OR a **future `end_date`** — a **null end_date no longer counts as vigencia** by itself.

## PRs
- Kforce first: [#1803](https://github.com/taller-projects/echo-backend/pull/1803) → kforce-dev · [#1804](https://github.com/taller-projects/echo-backend/pull/1804) → kforce-master (cherry-pick)
- Taller port: [#1805](https://github.com/taller-projects/echo-backend/pull/1805) → dev · [#1806](https://github.com/taller-projects/echo-backend/pull/1806) → qa · [#1807](https://github.com/taller-projects/echo-backend/pull/1807) → main
- All merged 2026-07-10. PRD updated. `gone_quiet` aligned to the same activity definition (kforce only — Taller has no Re-Engage).

## Notes
- This is the rare case where **kforce was the source and Taller the port** — kforce carries the richer activity data (`activity_dates` JSONB) the rule reads.
- Supersedes the "live end_date ⇒ Active" part of the earlier gate; the [[Client Active gate relaxation (PR 1745)]] no-history branches remain.

## Related
- [[Map - Contact Relationships]] · [[Map - Kforce]]
