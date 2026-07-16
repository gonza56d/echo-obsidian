---
type: delivery
status: merged
env: both
delivered: 2026-07-13
tags: [bugfix, performance, orm-planner]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1817"
  - "https://github.com/taller-projects/echo-backend/pull/1820"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23553"
---

# Deep pagination timeout — selectin-load to-one relationships (23553)

Sentry `7603967913` (dev): `GET /contacts` timed out (20s `DB_STATEMENT_TIMEOUT_MS`) at `page=6087&size=10` on a ~61k-contact tenant. The schema-driven planner (`app/modules/db/code_generator.py`) only routed **collections** through `selectinload`; every **to-one** relationship became a `joinedload` LEFT JOIN. `Contact.current_job`'s JOIN-ON is a correlated "latest open job" subquery evaluated for ALL candidate rows **before** OFFSET/LIMIT → cost scales with offset. (The on-read column_property columns are NOT the problem — Postgres defers those past LIMIT.)

## PRs
- [#1817](https://github.com/taller-projects/echo-backend/pull/1817) → dev · [#1820](https://github.com/taller-projects/echo-backend/pull/1820) → kforce-dev (**separate planner copy** — parallel port, not cherry-pick) — merged 2026-07-13

## How
- Under `use_selectin=True`, to-one relationships now also go through `selectinload` → loaded via `WHERE id IN (page rows)` after LIMIT. Measured: offset 60860 drops **21.97s → 3.95s**; response shape unchanged.

## Notes / pending
- Blast radius: callers passing `use_selectin=True` (contacts list, `repo.get(response_model=...)`).
- Follow-up not done: **keyset pagination** would remove the residual O(offset) base-scan cost.

## Related
- [[Roles statement timeout fix (PR 1600)]] — sibling timeout class
- Schema-driven ORM loading docs: `vault/Echo/Practices` in echo-backend
