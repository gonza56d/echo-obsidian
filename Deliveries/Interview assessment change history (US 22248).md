---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, bugfix, interviews, migrations, tests]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1848"
fe_prs:
  - "https://github.com/taller-projects/echo-frontend/pull/2970"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22248"
prd: ""
---

# Interview assessment change history (US 22248)

Melina's BE PR for US 22248 (reopen finished interviews + assessment change
history): reuses `InterviewHistory` with a new `ASSESSMENT_UPDATED` action, a
trigger in `InterviewService.update` on content-field changes, a paginated
`GET /assessments/interviews/{id}/change-history` endpoint, and a data
migration (`3gufg5ykw01g`) that rescues coordinator edits stranded in "BASE"
snapshots (~51 prod rows). My contribution (2026-07-17): fixed the red CI
pipeline and found + fixed a real ordering bug in the backfill migration.

## Azure / docs
- [US 22248](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22248)

## PRs
- [#1848](https://github.com/taller-projects/echo-backend/pull/1848) → dev — **open**, author Melina; my fix commits `9854cfac` + `d30bf929` pushed 2026-07-17
- FE: [#2970](https://github.com/taller-projects/echo-frontend/pull/2970) — must merge AFTER the BE PR (FE stops PATCHing the BASE snapshot and edits the interview directly)

## How
- Fix 1 — CI (5 setup errors): `InterviewFactory` is the first factory whose
  product gets **persisted** via `create_entity`; polyfactory fills optional
  UUIDs randomly → FK violations on `interviewer_id` / `created_by_id` /
  `scheduled_by_id`. Pinned all three to `None` in `tests/factories.py`
  (same rationale as `RoleFactory`).
- Fix 2 — migration no-op bug: the backfill's shared CTE has an idempotency
  guard (`NOT EXISTS` an `ASSESSMENT_UPDATED` row at `base.updated_at`), and
  the coordinator-edit seed **inserts exactly that row**. Each statement
  re-evaluates the CTE, so the interview-overwrite step (run last) always
  selected 0 rows — coordinator edits were never copied onto the interview.
  Fix: `UPGRADE_STATEMENTS` tuple as single ordered source (submission seed
  → overwrite → coordinator-edit seed LAST); `upgrade()` and the system
  tests iterate the same tuple.

## Decisions
- Fixed at factory level (not per-test fixture pins) so future persisted
  interviews are safe by default.
- Reorder over guard-rewrite: the submission seed must read pre-overwrite
  content, and the marker-planting statement simply has to run last.

## Gotchas
- **CI only runs `tests/unit`** (sh-vs-bash bug in `scripts/test.sh`) — the
  3 failing system tests that exposed the migration bug would NEVER have
  failed in CI. A green check on a data-migration PR proves nothing about
  the migration; run `scripts/test.sh all` locally.
- Polyfactory + `create_entity`: any `ModelFactory` whose schema has
  optional FK UUID fields will randomly violate FKs when persisted — check
  new factories for FK fields and pin them to `None`.
- The idempotency-marker pattern (guard on a row you also insert) makes
  statement ORDER load-bearing; keep order in one tuple that tests import.

## Pending
- Before running the backfill in prod: re-confirm divergence COUNT with a
  read-only SELECT (~51 expected, per PR description).
- Merge order: BE [#1848](https://github.com/taller-projects/echo-backend/pull/1848) first, then FE [#2970](https://github.com/taller-projects/echo-frontend/pull/2970).

(Closed 2026-07-17: CI green on both check runs after the fix push; the 30
local `test_application_*` failures were confirmed pre-existing local-only
artifacts — identical test-by-test in a pre-fix baseline run, green in CI.)

## Related
- [[Pending interview notifications (US 23321)]] — same interviews module
