---
type: delivery
status: merged
env: taller
delivered: 2026-06-25
tags: [bugfix, filters, validation]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1652"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23253"
---

# id__in filters typed as UUID (23253)

Frontend-facing `id__in`-style filters were typed as `List[str]`, so a malformed id reached Postgres and blew up with `InvalidTextRepresentation: invalid input syntax for type uuid` → 500. Typed them as `List[uuid.UUID]` so bad input fails Pydantic validation → 422.

## PRs
- [#1652](https://github.com/taller-projects/echo-backend/pull/1652) → dev — merged 2026-06-25 (dev commit `00fdc79e`)

## Notes
- Covered 8 filter files; pure-Pydantic regression test added.
- **Was never ported to kforce** — that gap resurfaced a year of drift later as half of [[Kforce Last Contacted By filter (PR 1846)]].

## Related
- [[Map - Kforce]] — the drift/backport policy this illustrates
