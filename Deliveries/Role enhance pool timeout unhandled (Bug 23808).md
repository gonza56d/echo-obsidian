---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, roles, background-tasks, observability, sentry]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1911"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23808"
prd: ""
---

# Role enhance pool timeout unhandled (Bug 23808)

Sentry issue [7585920278](https://taller-wn.sentry.io/issues/7585920278/) (POST `/roles` `unhandled_exception_in_request`, prod, 5 events on 2026-07-01) turned out to be the `enhance_role` **background task** crashing with an unhandled SQLAlchemy `TimeoutError: QueuePool limit of size 20 overflow 10 reached, connection timed out, timeout 30.00` during two prod **connection-pool exhaustion windows** (03:00–03:04 and ~12:46–12:56 UTC). The client always got its 201 and the role committed — but enhancement died before starting and the role stayed stuck `PENDING` (no FAILED state → no FE retry affordance). Fix: pass the UUID straight to `enhance_role(role_id)` so the fetch happens inside its protected block.

## Azure / docs

- [Bug 23808](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23808) — Active, full root-cause write-up in Repro Steps
- Sentry: [7585920278](https://taller-wn.sentry.io/issues/7585920278/) (log event) + native-exception twin issue `7585920304` (same second, full stacktrace)

## PRs

- [#1911](https://github.com/taller-projects/echo-backend/pull/1911) → dev — open. Approved by leoassontaller on the first commit (empty body). Two `/pr-review` rounds, both 2026-07-27:
  - **Round 1** → READY WITH NITS (0 blockers, ticket compliance 6/6); nits addressed in `ebf77385`.
  - **Round 2** → **CHANGES REQUESTED (1 blocker, in the tests)**: the round-1 FAILED-stage test did not guard the bug at all, and its single assertion was vacuous ~25% of the time. Fixed in `a8cb45a7` + `a35af463`. Ticket compliance re-verified 8/8 in-scope requirements; architecture 16/16 PASS.

## How

- `app/modules/role/routers.py::_enhance_role_with_context` pre-fetched the role with `get_by_id(role_id)` **outside** `enhance_role`'s try/except. Under pool exhaustion that checkout raised, escaped the background task, and surfaced through the ASGI stack as `unhandled_exception_in_request`; `_mark_role_failed` never ran.
- Fix = hand `enhance_role` the UUID so the fetch happens inside the protected block. Failure now logs + marks the role `FAILED` (fresh session) → `reset_for_retry` works. One less query per role creation.
- Review-nit commit `ebf77385`: internal `create_role` (`internal_routers.py:55`) now hands `new_role.id` to the background task — a Role object riding across risks attribute-expiration DB access *before* the protected block (same 23808 failure class); `enhance_role` short-circuits with a warning when the role no longer exists (benign delete race — no more false-alarm CRITICAL from `_mark_role_failed`); helper typed.
- Round-2 commits (2026-07-27):
  - `a8cb45a7` (tests) — the FAILED-stage test now runs through `_enhance_role_with_context` instead of calling `enhance_role` directly; seeds `enhancement_stage=PENDING` explicitly; adds the double-failure case (`_mark_role_failed`'s own fresh-session write also times out → nothing propagates, role keeps its stage, give-up log fires), the internal-router wiring case (enqueues the UUID, never the instance), and log/no-write assertions on the missing-role path.
  - `a35af463` (app) — `enhance_role` narrowed to `role_id: uuid.UUID` (the `Role | uuid.UUID` union had no callers left, and its `role_id = role.id` unwrap sat *outside* the try — the very hazard the fix closes at the call sites); `_create` now calls `self.enhance_role(new_role.id)`; never-raises contract documented; `_reload_solution_with_context` annotated.
- Verification: whole `tests/unit` suite green locally (2757 passed), ruff clean.

## Decisions

- Chose the UUID pass-through over wrapping the helper in its own try/except: the containment + FAILED-marking machinery already lives in `enhance_role`; duplicating it in the router would be a second place to keep correct.
- Did NOT touch pool sizing / NullPool — the exhaustion is a separate, broader problem (see Pending).
- Narrowed the `enhance_role` signature instead of leaving the tolerant union: with every caller on UUIDs, the union only preserved a way to reintroduce the bug.
- Accepted that the FAILED mark is **best-effort**, not guaranteed: `_mark_role_failed` needs its own connection checkout, which can time out too while the pool is still exhausted. The unconditional guarantee is only "nothing escapes the background task". Backstop = `RoleCleanupSchedulerService` sweeping stale `pending`/`enhancing` → `failed` after 15 min, plus `reset_for_retry` accepting `PENDING`. This is now locked in by a test.

## Gotchas (investigation)

- echo-backend logs unhandled request errors as Sentry **log-message events** whose `exception` string is truncated at **1024 chars** — the traceback's bottom frames are unrecoverable there. The **native-exception twin issue** (here `7585920304`, same timestamps to the second) carries the full stacktrace; always look for it.
- Sentry SQL `query` breadcrumbs are recorded at statement **start**; `httplib` breadcrumbs at **completion**. A hang therefore shows as a fixed gap after the last query breadcrumb with nothing following — here exactly 30.01s = SQLAlchemy `pool_timeout` (pool 20 + overflow 10).
- The Starlette background task runs **after** the response is sent but still inside the middleware stack: its exception logs as `unhandled_exception_in_request` (status 500 in the log) even though the wire saw 201. Don't trust that log's implied status.
- Issues endpoints 403 with the current Sentry token; events pagination (~60 pages ≈ 26 days) works. Grafana API key was expired (401) — renewal pending.
- Prod-tenant read-only checks ran via a user-provided prod JWT against `api.tallerecho.com` (tenant Taller `01df2012…` was one of the two affected): the 3 noon roles are distinct (no duplicates) and were later re-enhanced; `candidates_pipeline_count` costs ~1s even on the biggest role (1067 apps) — no persistent query problem.

## Gotchas (testing — learned in round 2)

- **A regression test must be pinned to the layer that broke.** The round-1 test called `RoleService.enhance_role(role.id)` directly, but the escaping fetch lived in the *router helper* — `enhance_role` already had its fetch inside the try on `dev`, so the test passed pre-fix. Cheap way to prove a regression test really guards: temporarily restore the old body, run it, confirm it fails, restore. Did exactly that here (raw `TimeoutError` propagated).
- **`RoleFactory` (polyfactory) randomizes enum fields even when the Pydantic schema has a default.** `enhancement_stage` on `RoleBase` defaults to `PENDING`, yet builds come out roughly uniform across pending/enhancing/enhanced/failed — so `assert stage == FAILED` passed on the seeded value alone ~25% of the time. Pin the enum in the seed helper when asserting a transition. Same class of trap as `TalentFactory.ats_external_ids` (pinned to `None` in `tests/factories.py` for the identical reason).
- **`logger.exception(...)` records at ERROR, not CRITICAL**, even when the message text starts with `"CRITICAL: "` (as `_mark_role_failed`'s give-up log does). `caplog.at_level(logging.CRITICAL, ...)` silently captures nothing.
- Testing a background-task router helper does not need the TestClient: call the router function directly with a real `BackgroundTasks()` and stub the service, then assert on `background_tasks.tasks[i].args`. Avoids the known local TestClient 404s on `/projects/{id}/roles`.

## Pending

- Merge [#1911](https://github.com/taller-projects/echo-backend/pull/1911) → dev; decide on qa/main cherry-picks (prod is where it bit).
- Re-request review: leoassontaller approved commit 1 only; `ebf77385`, `a8cb45a7` and `a35af463` all landed after that approval.
- Bug 23808 is still **Active** → move to Ready to Test; its `System.Description` is still the unfilled placeholder (whole brief lives in Repro Steps).
- Optional PR-body/ticket addenda flagged in review, not yet written: the FAILED mark is best-effort (see Decisions), and the missing-role path replaced an ERROR+CRITICAL pair with a single WARNING (matters for whoever tunes Sentry alerting).
- Follow-up (separate ticket, **not created yet**): investigate the recurring pool exhaustion around the 03:00 UTC bulk-matching push (`PATCH /internal/applications/bulk/matching` window; even `/talents` auth checks failed on checkout in `session_validation_service.is_session_live`).
- Follow-up (separate ticket, **not created yet**): hardening pass over other unprotected `background_tasks.add_task` call sites — `role_service.update_vector` at `routers.py:272`, `internal_routers.py:114` and `:225` has neither a `background_request_context` wrapper nor an internal try/except; same for ~15 `refresh_contact_attributes` / `update_talent_vector_by_id` sites. Also `app/context.py:152-155`'s unguarded `rollback()`/`remove()` in `background_request_context`'s `finally`.
- Renew the Grafana service-account API key (`~/.zshrc`).

## Related

- [[Map - Observability & Reliability]] · [[Roles statement timeout fix (PR 1600)]] · [[similar_role null-vector 500 (Bug 23362)]]
