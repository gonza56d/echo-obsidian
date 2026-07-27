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

- [#1911](https://github.com/taller-projects/echo-backend/pull/1911) → dev — open; formal 3-agent `/pr-review` 2026-07-27: **READY WITH NITS** (0 blockers, CI green, ticket compliance 6/6); nits addressed in `ebf77385`

## How

- `app/modules/role/routers.py::_enhance_role_with_context` pre-fetched the role with `get_by_id(role_id)` **outside** `enhance_role`'s try/except. Under pool exhaustion that checkout raised, escaped the background task, and surfaced through the ASGI stack as `unhandled_exception_in_request`; `_mark_role_failed` never ran.
- Fix = hand `enhance_role` the UUID (it accepts `Role | uuid.UUID` precisely for this; `project/service.py` already used the UUID form). Failure now logs + marks the role `FAILED` (fresh session) → `reset_for_retry` works. One less query per role creation.
- Tests (`tests/unit/test_roles.py`): helper passes the UUID through; a pool timeout on the initial fetch leaves the role `FAILED` without propagating.
- Review-nit commit `ebf77385` (2026-07-27): internal `create_role` (`internal_routers.py:55`) now hands `new_role.id` to the background task — a Role object riding across risks attribute-expiration DB access *before* the protected block (same 23808 failure class); `enhance_role` short-circuits with a warning when the role no longer exists (benign delete race — no more false-alarm CRITICAL from `_mark_role_failed`); helper typed (`req_ctx: RequestContext`, `-> None`); +1 test (missing role → no FAILED marking). 3/3 tests green, ruff clean.

## Decisions

- Chose the UUID pass-through over wrapping the helper in its own try/except: the containment + FAILED-marking machinery already lives in `enhance_role`; duplicating it in the router would be a second place to keep correct.
- Did NOT touch pool sizing / NullPool — the exhaustion is a separate, broader problem (see Pending).

## Gotchas (investigation)

- echo-backend logs unhandled request errors as Sentry **log-message events** whose `exception` string is truncated at **1024 chars** — the traceback's bottom frames are unrecoverable there. The **native-exception twin issue** (here `7585920304`, same timestamps to the second) carries the full stacktrace; always look for it.
- Sentry SQL `query` breadcrumbs are recorded at statement **start**; `httplib` breadcrumbs at **completion**. A hang therefore shows as a fixed gap after the last query breadcrumb with nothing following — here exactly 30.01s = SQLAlchemy `pool_timeout` (pool 20 + overflow 10).
- The Starlette background task runs **after** the response is sent but still inside the middleware stack: its exception logs as `unhandled_exception_in_request` (status 500 in the log) even though the wire saw 201. Don't trust that log's implied status.
- Issues endpoints 403 with the current Sentry token; events pagination (~60 pages ≈ 26 days) works. Grafana API key was expired (401) — renewal pending.
- Prod-tenant read-only checks ran via a user-provided prod JWT against `api.tallerecho.com` (tenant Taller `01df2012…` was one of the two affected): the 3 noon roles are distinct (no duplicates) and were later re-enhanced; `candidates_pipeline_count` costs ~1s even on the biggest role (1067 apps) — no persistent query problem.

## Pending

- Merge [#1911](https://github.com/taller-projects/echo-backend/pull/1911) → dev (reviewed READY WITH NITS 2026-07-27, nits addressed `ebf77385`; CI green on first commit, second-commit run pending); decide on qa/main cherry-picks (prod is where it bit).
- Follow-up (separate ticket): investigate the recurring pool exhaustion around the 03:00 UTC bulk-matching push (`PATCH /internal/applications/bulk/matching` window; even `/talents` auth checks failed on checkout in `session_validation_service.is_session_live`).
- Follow-up (separate ticket): hardening pass over other unprotected `background_tasks.add_task` call sites (`update_vector`, `refresh_contact_attributes`, …) — same unhandled-noise class.
- Renew the Grafana service-account API key (`~/.zshrc`).

## Related

- [[Map - Observability & Reliability]] · [[Roles statement timeout fix (PR 1600)]] · [[similar_role null-vector 500 (Bug 23362)]]
