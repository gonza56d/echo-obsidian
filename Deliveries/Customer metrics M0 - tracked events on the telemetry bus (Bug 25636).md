---
type: delivery
status: in-review
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

## How
- `app/modules/contact/tracker/service.py::_emit_contact_tracked_event` and `app/modules/organization/tracker/service.py::_emit_company_tracked_event`: `get_default_event_bus` → `get_telemetry_event_bus` (function-local imports kept).
- New `tests/unit/test_tracker_adoption_events.py`: real `ContactTrackerService.persist_trackers` / `OrganizationTrackerService.add_tracker_bulk` from `app.state.injector`, then polls `user_events` (5 s) for the row the real telemetry bus writes. Fails on old code (`assert len(events) == 1`), passes with the fix.

## Decisions
- Stopgap only (PRD): best-effort bus publish restored; M1 moves both to the durable same-transaction write.
- Test uses the real running bus instead of a mocked bus: the existing tracker tests mock the emitters, which is exactly why the regression slipped.

## Gotchas
- `DependencyInjector.__init__` starts all three buses in tests too (default / audit / telemetry), so `get_telemetry_event_bus()` is live in the unit suite — the old comment in `test_user_groups.py` ("conftest doesn't start the bus") is stale.
- Contact emitter emits for every contact passed (not only newly inserted trackers), company emitter only for inserted rows — left as is (out of M0 scope).

## Pending
- [ ] Review + squash-merge #2456; full unit + multitenancy run was still going when the PR opened.
- [ ] Verify on dev after deploy: Echo Usage contacts/companies tracked count new tracks (AC 2); then qa / main promotion.
- [ ] Data side (Nico): dashboard note that the 2026-10 gap → deploy can't be backfilled.
- [ ] Close Bug 25636 after prod.

## Related
- [[Map - Observability & Reliability]] · [[EventBus watchdog + telemetry bus split (Bug 25276)]]
