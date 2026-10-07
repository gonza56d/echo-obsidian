---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, reliability, eventbus, notifications, adoption, infra, taller, kforce]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2381"
  - https://github.com/taller-projects/echo-backend/pull/2395
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25276"
prd:
---

# EventBus watchdog + telemetry bus split (Bug 25276)

Gisel's automation found that accepting a partner allocation in QA sometimes emits no `commitment.accepted` notification. Florencia (FE TL) traced it to a hung `EventBus` worker in one QA process. I confirmed it from Loki and fixed the class of failure: handlers now run under a per-event watchdog, adoption telemetry rides its own bus, `/health` exposes bus state and answers 503 when a bus exhausted its stuck-thread budget.

## Azure / docs
- [Bug 25276](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25276) (Sprint 45, `automation-found`, assigned Gonzalo) — In development; my investigation comment posted 2026-10-01 (corrects the timeline + infra finding).
- No PRD (incident fix). Memory of the investigation: `project_eventbus_stuck_worker_25276` + `reference_loki_grafana_access` in Claude memory.

## PRs
- [#2381](https://github.com/taller-projects/echo-backend/pull/2381) → dev **OPEN 2026-10-01** (`d22e855e` + test fix `e7d64053`, branch `25276/eventbus-watchdog`). Full unit+multitenancy run: 5710 passed; the only failure was my own DI test asserting identity against the module-global bus accessors (re-pointed by the worker tests' DependencyInjector) + a `processed`-counter race in two thread-name tests — both fixed in `e7d64053`, worker+EventBus pair green 3×.
- [#2395](https://github.com/taller-projects/echo-backend/pull/2395) `qa` → `main` release "Release qa -> main 2026-10-07" — **OPEN 2026-10-07** (head `qa` directly, merge commit; carries #2381, #2386, #2387, #2393, plus #2388 as history only since it is already on main via #2391; no migrations). qa got them via [#2392](https://github.com/taller-projects/echo-backend/pull/2392) + [#2394](https://github.com/taller-projects/echo-backend/pull/2394), both merged 2026-10-07. CI on the qa tip was still running when the PR was opened.

## How (the investigation)
- Bus `d6a83cee` = one uvicorn process, pod started 2026-09-30 21:16:16 UTC (qa `5afb7155`, template `68cd784dd8`). Loki has no `pod` label, so I isolated the worker **thread**: `[scope.get] NEW DatabaseResource scope_key=128545416709824` lands 0–1 ms after every `Event published` of that bus from 04:20 to 04:32:02 UTC; last line **04:32:03.949 = start of a `user.event` (adoption) handler**; nothing after. The ticket's `role_placement.updated` (04:35:26) was never dequeued. ~560 events queued by 19:00 UTC (max 1000, `Event queue full` never logged anywhere in 7 days).
- Same minute in QA: `statement timeout` burst on GET /roles (04:32:03–14), 9–17 s queries, `SSL connection has been closed unexpectedly` (04:32:55–04:33:07) — Supavisor shedding connections under e2e load (QA `nullpool=true`).
- Mechanism: a server-side hang is cut by `SET LOCAL statement_timeout=20s` and logged; nothing logged ⇒ the thread sat in a client-side libpq `recv` with no server statement (fresh pooler connection waiting for a backend / half-dead connection). psycopg2 has no read timeout; `connect_timeout` only covers the handshake; keepalives don't fire while the peer host is alive. Not a code regression.

## How (the fix, #2381)
- `EventBus._run_with_watchdog`: each event runs on a disposable `EventBusHandler` thread; the worker joins for `EVENT_BUS_HANDLER_TIMEOUT_SECONDS` (60). Overrun → thread abandoned (can't be killed), `event_bus.handler_stuck` error with the thread's Python stack (`sys._current_frames()`), next event proceeds. `0` = inline (old behaviour).
- `stuck_handlers` counts abandoned threads still alive; past `EVENT_BUS_MAX_STUCK_HANDLERS` (3) `is_healthy` is False (recovers if they return).
- `TelemetryEventBus` (`only_events=TELEMETRY_EVENT_NAMES` = `user.activity`/`user.event`), default bus excludes them; publishers (`AccessLoggerMiddleware`, user groups, candidate email, usage export) use `get_telemetry_event_bus()`. Same pattern as the audit bus in [[Audit log on internal via IntegrationAuditMiddleware (Task 25058)]].
- `/health` → JSON `{status, event_buses{default,telemetry,audit}}` with queue size, in-flight event/age, stuck count; 503 when degraded. `queue_size` logged live. `tcp_user_timeout=30000` in libpq connect args.

## Decisions
- Thread-per-event over a persistent replaceable handler thread: simpler, abandonment is clean (the stuck thread's own `finally` cleans its own scope keys), thread spawn is negligible next to the DB round-trips each handler does.
- Readiness degrades on **alive** stuck threads only, so a pod does not stay NotReady forever after three stalls over weeks of uptime.
- Did NOT open the infra PR: `probe.enabled: false` in `values-qa.yaml` / `values-prod.yaml` was set deliberately on 2026-03-17 (`3e3889f4f` / `4a60b3398` / `8165bc8ac`, Willian, no reason recorded; prod flipped on and off within 20 min) — needs the infra owner's context first.

## Gotchas
- Loki is reachable through Grafana's datasource proxy (uid `wPrhiDiVk`) with the VIEWER `GRAFANA_API_KEY`; the editor token is expired. Streams are `{app="echo-backend-qa"}` etc., no `pod` label.
- `count_over_time(...[R])` with `step >= R` counts the window BEFORE `start` — I first over-counted the queue (1828) that way.
- The worktree-isolation hook refuses `source scripts/venv.sh` and any bash whose text contains "git" (heredocs and GitHub URLs included); run ruff/pytest via the main checkout's `.venv/bin/*` binaries, and put vault/Azure scripts in a file inside the worktree.

## Pending
- [ ] Merge release [#2395](https://github.com/taller-projects/echo-backend/pull/2395) `qa` → `main` (merge commit; `main` needs a code-owner review), then the `echo-backend-prod` / `echo-backend-kforce-prod` approvals.
- Merged dev 2026-10-06 (`cac40d3f`, merge commit). Release [#2392](https://github.com/taller-projects/echo-backend/pull/2392) `dev` → `qa` **MERGED 2026-10-07** (with #2386 + #2387); qa → main via #2395.
- Ops (needs kubectl, I have none): find the QA pod older than 04:32 UTC whose logs contain `d6a83cee`; `py-spy dump` via ephemeral debug container if still alive (no lines from it after 14:47 UTC — likely scaled in); re-run `roles_capacity.feature:1086`.
- Infra: enable `probe.enabled` for qa/prod and point liveness at `/health` (ask Willian/Alan why it was disabled on 2026-03-17 first).
- Grafana/Loki alert on `Event queue full` + `event_bus.handler_stuck` for all envs.
- Close Bug 25276 after QA re-test; tell Florencia + Gisel the corrected timeline.

## Related
- [[Map - Observability & Reliability]] · [[Audit log on internal via IntegrationAuditMiddleware (Task 25058)]] (the bus-split pattern) · [[Outbox skips internal-originated emits (Bug 23656)]] (EventBus worker context boundary)
