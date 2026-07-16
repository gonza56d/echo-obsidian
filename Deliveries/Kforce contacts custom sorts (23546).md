---
type: delivery
status: merged
env: kforce
delivered: 2026-07-10
tags: [bugfix, kforce, filters, contact]
prs: [1813]
tickets: [23546]
---

# Kforce: current_job_title & alias sorts on /contacts (23546)

`GET /contacts?order_by=-current_job_title` returned **422** on kforce. Root cause: kforce lacks dev's `validate_order_by` override, so the fastapi_filter library validator (a bare `hasattr` check on the model) rejected custom sort names.

## PRs
- [#1813](https://github.com/taller-projects/echo-backend/pull/1813) → kforce-dev — merged 2026-07-10

## How (copy + adapt port from dev)
- Ported the `validate_order_by` override + `current_job_title` `column_property` + custom sorts: `current_job_title`, `last_relationship`, `last_interaction_date`.
- **Kforce rule to remember**: `order_by` custom sorts must ALSO be model attributes — the library validator only checks `hasattr`.

## Notes
- Taller needs NO port (dev is the source); Taller prod was behind dev at the time.

## Related
- [[Map - Kforce]]
