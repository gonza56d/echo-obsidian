---
type: delivery
status: in-review
env: both
delivered:
tags: [tests, customer-metrics, adoption, events]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2484"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25641"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25642"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M5 backend - frontend event catalog tests (US 25641)

Customer metrics M5, backend half. The story asks for the six frontend event types (`warm_lead_acted`, `match_results_viewed`, `reengage_viewed`, `reengage_contact_acted`, `deal_finder_result_saved`, `active_time`) in the `POST /events` catalog with validation and dedupe, contract frozen for the frontend. All of that already shipped with M1 ([[Customer metrics M1 - user_events v2 and durable write path (US 25637)]], [#2458](https://github.com/taller-projects/echo-backend/pull/2458)): `USER_EVENT_CATALOG` in `app/modules/adoption/schemas.py`. This delivery is the missing proof: tests for every type.

## Azure / docs
- [US 25641](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25641) In revision 2026-10-29, PR linked as GitHub Pull Request + comment. Parent [Feature 25635](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635); business contract [CR 25592](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592).
- Frontend half: [US 25642](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25642) (Florencia's team), not started.
- [Tech PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj) rev 84: section 6 Milestone 5, section 7 Event catalog, Backend appendix → API contracts. No PRD change.

## PRs
- [#2484](https://github.com/taller-projects/echo-backend/pull/2484) → dev, OPEN 2026-10-29 (`94793f9d`, branch `25641/client-event-catalog-tests`, worktree `.claude/worktrees/25641-client-event-tests`). Tests only.

## How
- `tests/unit/test_client_events.py`: `_CLIENT_EVENTS` (one full catalogued payload + entity per type) and `_REQUIRED_KEYS`, built into events inside each test (no collection-time timestamps).
- Catalog pin: client-emittable types in `USER_EVENT_CATALOG` == the six. Each type stored as sent (`source = ui`, entity, `event_data` + `occurred_at`). Missing required key → `invalid_payload` per key; required-keys-only payload stored (pins which keys are optional: `match_results_viewed.filters` / `top_application_ids`, `reengage_viewed.sort`). Out-of-catalog values, entity rules (rejected + accepted alternatives), every backend-only type → `event_type_not_client_emittable`.

## Gotchas
- From an EnterWorktree session the guard refuses `source <venv>/activate` and python heredocs fed by `-`: run `<main>/.venv/bin/python -m pytest` and put helper scripts under `<worktree>/.claude/worktrees/tmp/`.

## Evidence
- 103 passed locally (64 new). Mutations (filter optional, deal finder taking a role, `reengage_viewed` not client-emittable, `chat_id` as str) → 12 failures, all four caught; schemas restored before the commit.

## Pending
- [ ] CI, review, squash-merge → close US 25641.
- [ ] AC 4 (FE event visible on dev within 5 s) waits for the FE client, US 25642.
- [ ] Tell Flor: contract frozen; filters = API param names; `occurred_at` with offset; fetch keepalive, not sendBeacon; `role_id` on cv-versions; close-reason picker; `source_notification_id` must be the caller's own notification (404 `notification_not_found`).
- [ ] After Flor's picker is on dev: `close_reason` required (422 `close_reason_required`).

## Related
- [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]] · [[Customer metrics M4 - proposal versions (US 25640)]] · [[Customer metrics M3 - AI suggestion snapshots (US 25639)]] · [[Customer metrics M2 - domain history (US 25638)]] · [[Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)]]
