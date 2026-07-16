---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-09
tags: [bugfix, contact, relationships, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1793"
  - "https://github.com/taller-projects/echo-backend/pull/1797"
  - "https://github.com/taller-projects/echo-backend/pull/1798"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23519"
---

# Moved-away Client contacts read Past, not Active (Bug 23519)

Amendment to [[Client Active gate relaxation (PR 1745)]]: its same-company-interaction override (branch #4) kept contacts Active even when the scrape **proved they moved away**. New guard: the override is disabled when the contact has an **ended job at the account AND an open job elsewhere** (`has_moved_to_another_company`).

## PRs
- [#1793](https://github.com/taller-projects/echo-backend/pull/1793) → dev · [#1797](https://github.com/taller-projects/echo-backend/pull/1797) → qa · [#1798](https://github.com/taller-projects/echo-backend/pull/1798) → main — merged 2026-07-09

## Impact / validation
- Navitec: 20/420 contacts flip to Past under the new guard.

## Pending
- `company_id`-exact matching edge case noted but not addressed (moved between entities that share a parent company).

## Related
- [[Client Active significant activity (US 23536)]] · [[Kforce Client Active no-job gate (Bug 23545)]] · [[Map - Contact Relationships]]
