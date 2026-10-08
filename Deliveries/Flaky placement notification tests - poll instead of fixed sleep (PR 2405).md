---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, tests, flaky, notifications, eventbus]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2405"
fe_prs: []
tickets: []
prd: ""
---

# Flaky placement notification tests — poll instead of fixed sleep (PR 2405)

`tests/unit/test_role_placement_notifications.py` fails intermittently on CI (spotted on **QA build 30504**, `TestNotificationContent::test_status_changed_notification_message_format` → `assert 0 > 0`). The placement notifications are produced asynchronously by the EventBus worker thread; the tests waited a fixed `time.sleep(0.5)` before querying, and on a loaded runner the worker doesn't always finish within 500 ms, so the query sees `[]`. Test race, not a product regression. Fix: poll until the expected notification lands.

## Azure / docs
- No ticket (non-ticketed flaky-test fix, `fix/` branch).
- Flaky QA build: `https://dev.azure.com/TallerInternTools/Snapshot%20Exploration/_build/results?buildId=30504`

## PRs
- [#2405](https://github.com/taller-projects/echo-backend/pull/2405) → dev — **OPEN** 2026-10-08 (branch `fix/flaky_placement_notification_poll`). Tests-only, no production code. No FE impact.

## How
- New helper `wait_for_notifications_by_kind(db, kind, *, min_count=1, timeout=5.0, poll_interval=0.05)` polls `get_notifications_by_kind` until `min_count` rows of that kind exist, returning early as soon as they do (or at timeout, so a genuine absence still fails the assertion).
- Replaced the `wait_for_notifications()` + `get_notifications_by_kind(...)` pair with the poll helper at **16 positive-assertion sites** (`assert len > 0`, `X in notified_user_ids`, content assertions on `notifications[0]`).
- Kept the fixed-sleep `wait_for_notifications()` only where it is still correct: the two negative tests that assert **zero** notifications (`test_no_notifications_on_placement_created`, `test_no_notifications_on_placement_updated`) — nothing to poll for — and the drain `wait_for_notifications(); clear_notifications(db)` steps that flush creation notifications before the status-change assertion.
- 18/18 pass locally (16.8 s).

## Decisions
- Poll-until-present over bumping the sleep: removes the race without padding the happy path (returns in ~50 ms when the worker is prompt).
- Did **not** convert the `== 0` negatives to polling — that would force a full 5 s wait on every run and invert the semantics.

## Gotchas
- `get_notifications_by_kind` opens a fresh session per call, so under Postgres READ COMMITTED each poll sees newly committed rows from the worker thread — polling works.
- Same fixed-sleep-vs-async-EventBus flake family as [[EventBus watchdog + telemetry bus split (Bug 25276)]].
- Pyright flags unused `taller_recruiter`/`project_for_notifications` params — pre-existing pytest fixtures used for DI side effects, not from this change; tests aren't linted.

## Pending
- Review + merge to dev; qa/main with the next release (tests-only, no migration).
- Consider the same poll helper for any other fixed-sleep EventBus assertions if they flake.

## Related
- [[EventBus watchdog + telemetry bus split (Bug 25276)]]
