---
type: delivery
status: merged
env: taller
delivered: 2026-06-25
tags: [bugfix, contact]
prs: [1651]
tickets: [23251]
---

# Contact bulk_track duplicate-linkedin IntegrityError (Bug 23251)

Prod Sentry issue `7573252670`: `bulk_add_trackers` raised `IntegrityError` on `contact_tenant_linkedin_uniq_idx` when a bulk-track batch contained contacts whose LinkedIn URL already existed for the tenant.

## PRs
- [#1651](https://github.com/taller-projects/echo-backend/pull/1651) → dev — merged 2026-06-25

## How
- Resolve existing contacts via `ids_by_linkedin` and insert with a `NOT EXISTS` guard, so duplicates attach trackers to the existing row instead of violating the unique index.

## Related
- [[Map - Contact Relationships]] (contact-module neighborhood)
