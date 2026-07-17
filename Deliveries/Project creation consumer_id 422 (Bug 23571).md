---
type: delivery
status: merged
env: taller
delivered: 2026-07-14
tags: [bugfix, validation, projects]
prs: [1833]
tickets: [23571]
---

# POST /projects without consumer_id → 422 instead of 500 (Bug 23571)

`ProjectCreate.consumer_id` was `uuid.UUID | None = None` but the DB column is `NOT NULL` → request passed Pydantic and died at insert with an unhandled `NotNullViolation` → 500. Found while running [[Industry-agnostic Echo (PRD 398aedca)]] QA against dev.

## PRs
- [#1833](https://github.com/taller-projects/echo-backend/pull/1833) → dev — merged 2026-07-14

## How
- Made `consumer_id` required in `ProjectCreate` → standard 422 before the DB. Both existing creation paths already always provide it; response schemas unaffected (column NOT NULL ⇒ every row satisfies the stricter type). Route-level test added.
