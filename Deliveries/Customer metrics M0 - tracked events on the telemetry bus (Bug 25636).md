---
type: delivery
status: merged
env: both
delivered:
tags: [bugfix, adoption, customer-metrics, event-bus]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2456"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25636"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)

`contact_tracked` / `company_tracked` were published on the **default** EventBus, which since the telemetry split (d22e855e, [[EventBus watchdog + telemetry bus split (Bug 25276)]]) excludes `user.event` → queued, no handler, no `user_events` row. Echo Usage "contacts / companies tracked" under-report since that release. M0 of the customer-metrics program: swap both emitters to `get_telemetry_event_bus()` + a test that proves the row is written.

## Azure / docs
- [Bug 25636](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25636) (M0, Sprint 45, In development 2026-10-22, PR link added) — child of [Feature 25635](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635); business contract [CR 25592](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592).
- Tech PRD: [Customer Metrics Event History — Technical PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj) (Approved, section 6 Milestone 0). M1-M7 = US 25637-25644.

## PRs
- [#2456](https://github.com/taller-projects/echo-backend/pull/2456) → dev — OPEN 2026-10-22 (`3c62f0f4`, branch `25636/tracked-events-telemetry-bus`). No FE impact.
  - Self-review r1 (2026-10-22, /pr-review): CHANGES REQUESTED — 1 blocker (new tests order-dependent, see Gotchas) + 2 nits. First CI run on `3c62f0f4` was red for infra only (Docker 500 pulling `pgvector/pgvector:pg16`, 6517 errors, 0 tests ran).
  - `22c7d274` (pushed 2026-10-22 from worktree `25636-tracked-events-fix`, branch `25636/tracked-events-test-order` → `HEAD:25636/tracked-events-telemetry-bus`): blocker + nits fixed, PR body refreshed. CI green on re-run (attempt 1 failed only the wall-clock `test_job_description_token.py::...linear_time[backslash-run-in-jd]`, 1.24 s vs < 1.0 s; passes locally).
  - Leo [APPROVED on `22c7d274`](https://github.com/taller-projects/echo-backend/pull/2456#pullrequestreview-5617245582) 2026-10-22 with 4 nits + follow-ups. `551c5be4` = his 2 contact test nits; `db9b4361` = his optional guard (misrouted-event warning). Nits 3 (payload `tenant_id`) and 4 (queue cap) routed to M1 per his own note, listed in the PR body. Approval not dismissed by the push.

## How
- `app/modules/contact/tracker/service.py::_emit_contact_tracked_event` and `app/modules/organization/tracker/service.py::_emit_company_tracked_event`: `get_default_event_bus` → `get_telemetry_event_bus` (function-local imports kept).
- New `tests/unit/test_tracker_adoption_events.py`: real `ContactTrackerService.persist_trackers` / `OrganizationTrackerService.add_tracker_bulk` from `app.state.injector`, then polls `user_events` (5 s) for the row the real telemetry bus writes. Fails on old code (`assert len(events) == 1`), passes with the fix.
- Same file (`22c7d274`): `add_tracker_bulk(..., emit_event=False)` writes no row, and a company re-track writes no second row. Absence is asserted after `_drain_telemetry_bus` — tracks a sentinel company and waits for its row; the bus handles events one at a time in publish order, so every earlier event has been handled by then (no fixed sleep).
- `tests/unit/background_job/test_background_job_worker.py::_bound_injector` now also saves/restores the process-global telemetry bus (`set_telemetry_event_bus`).
- `551c5be4`: contact re-track writes a 2nd row (pins per-input-id emit); `persist_trackers(..., None, ...)` writes nothing and logs no `contact_tracked.emit_failed` (without the early return the `UserEventPayload(user_id=None)` validation error is caught and logged — so "no row" alone would be vacuous; the log is the real signal).
- `db9b4361` guard: `EventBus._routes(name)` (shared with `_subscribe_from_registry`); `publish()` returns False + warns `event_bus.event_routed_elsewhere` (`event_name`, `bus`) when the bus's only/exclude config routes the event elsewhere AND no handler was subscribed directly. Tests in `tests/unit/test_event_bus.py::TestEventsPublishedOnTheWrongBus`. Mutation-checked: guard tests + unattributed test fail with the code reverted.

## Decisions
- Stopgap only (PRD): best-effort bus publish restored; M1 moves both to the durable same-transaction write.
- Test uses the real running bus instead of a mocked bus: the existing tracker tests mock the emitters, which is exactly why the regression slipped.
- Guard generalized from Leo's "TELEMETRY_EVENT_NAMES on a bus with no subscriber" to "any event the bus's only/exclude config routes elsewhere": no adoption import into `app/core`, and it also covers `integration.request` off the audit bus and functional events on the telemetry/audit buses. Refuses (returns False, no queue slot) instead of queue-then-discard; warns on EVERY occurrence (no rate limit) — a misroute is a bug to fix, so it should be loud. No current publisher hits it.
- Payload `tenant_id` NOT passed from the request context (Leo nit 3): the per-event `User.tenant_id` lookup is always the user's own tenant; M1's durable write replaces this path anyway.

## Gotchas
- `DependencyInjector.apply_bindings` starts all three buses in tests too (default / audit / telemetry), so `get_telemetry_event_bus()` is live in the unit suite. The stale "conftest doesn't start the bus" comment in `test_user_groups.py` was fixed in `22c7d274`.
- **Order-dependent test trap**: emitters read the process-GLOBAL telemetry bus, not `app.state.injector`'s. The worker tests' `_bound_injector` calls `apply_bindings()` with a mocked engine, which re-points the global; it restored only default + audit, so in the full suite (`tests/unit/background_job/` collects before `tests/unit/test_*.py`) the new tests published to a mock-backed bus and timed out — with OR without the fix. Passed alone, which is why "fails before / passes after" looked verified. Repro: `pytest tests/unit/background_job/test_background_job_worker.py::TestWorkerProcessIdentity tests/unit/test_tracker_adoption_events.py`. Only `conftest.py` and `_bound_injector` build injectors in tests.
- Contact emitter emits for every contact passed (not only newly inserted trackers), company emitter only for inserted rows; internal automated contact tracks (`source="automated"`) emit, internal company tracks pass `emit_event=False` — left as is (pre-Oct-1 behavior, routed to M1's `source` column; noted in the PR body).

## Pending
- [x] Squash-merged to dev (`ceeff2a1`, 2026-10-22). M1 continues in [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]].
- [ ] (was) CI on `db9b4361`, then squash-merge #2456 (Leo approved). Reply to Leo's review (drafted in session, not posted).
- [ ] M1 (US 25637 — these three are now in its description "Follow-ups from the M0 review" + 3 acceptance criteria, rev 2, 2026-10-22): decide whether "contacts tracked" counts re-tracks and `source="automated"` internal tracks (PRD l.84/l.107 say `/internal/*` bulk syncs write 0 rows — true for companies only); pass `tenant_id` in the payload; telemetry queue (1000) overflows on internal bulk tracks > 1000 contacts until the durable write lands.
- [ ] Nico's "resume from M0" dashboard note should say KForce "contacts tracked" is inflated by automated tracks until M1.
- [ ] Verify on dev after deploy: Echo Usage contacts/companies tracked count new tracks (AC 2); then qa / main promotion.
- [ ] Data side (Nico): dashboard note that the 2026-10 gap → deploy can't be backfilled.
- [ ] Close Bug 25636 after prod.

## Related
- [[Map - Observability & Reliability]] · [[EventBus watchdog + telemetry bus split (Bug 25276)]]
