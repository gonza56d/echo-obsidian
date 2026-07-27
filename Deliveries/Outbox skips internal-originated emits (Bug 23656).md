---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-21
tags: [bugfix, outbox, trackerrms, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1870"
  - "https://github.com/taller-projects/echo-backend/pull/1871"
  - "https://github.com/taller-projects/echo-backend/pull/1872"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23656"
---

# Outbox skips internal-originated emits (Bug 23656)

Once the outbox → TrackerRMS dispatcher was enabled in prod (~15-jul, see [[Outbox flat payload fix (PR 1838)]]) with writeback on (`OUTBOX_DISPATCHER_SKIP_WRITEBACK=false`), the integration created a **sync loop**. Navitec reported Tracker contacts reassigned to different companies, job statuses changing on their own, and data "moving around and disappearing" (sales side). Fix = never emit outbox events for changes that originate on the internal API surface.

## What
- Symptom (Navitec): Tracker contacts reassigned across companies; role status flipping on its own; "data all over the place".
- Loop mechanism: the TrackerRMS sync **writeback** re-enters Echo via `/internal` → the service re-emits an outbound event (`write_outbox`) → dispatcher poll (~70 min) re-delivers → repeat.
- The `is_sync_operation` flag was set by some internal routers (`mark_sync_context` on talent/role/application) but **never consulted** by the outbox emitters — the only gate was `external_id is not None` (`app/modules/role/service.py`).

## Azure
- [Bug 23656](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23656) — **Testing** (since 2026-07-20), assigned to me.

## PRs
- [#1870](https://github.com/taller-projects/echo-backend/pull/1870) → `dev` — **MERGED 2026-07-20** (merge commit `475a2201`). /pr-review round 1: **READY WITH NITS** (0 blockers, 6/6 ticket compliance, CI green) — all 4 nits addressed in `7781ef17`; full-loop e2e regression `1782228f`.
- [#1871](https://github.com/taller-projects/echo-backend/pull/1871) → `qa` — promotion cherry-pick (3 commits `92cdd22e`/`7781ef17`/`1782228f`), **MERGED 2026-07-21**, byte-identical to dev, no migrations.
- [#1872](https://github.com/taller-projects/echo-backend/pull/1872) → `main` — promotion cherry-pick, **MERGED 2026-07-21** → **fix in prod**.

## How
- New dedicated `is_internal` flag on `RequestContext` (`app/context.py`) — deliberately NOT reusing `is_sync_operation` to avoid changing `last_sync_at` stamping.
- `mark_internal_context` dependency (`app/permissions.py`) set **globally on the internal app's root router** (`get_internal_app_router`, `app/routers.py`) → covers 100% of `/internal`, independent of per-router `mark_sync_context`.
- Guard in `write_outbox_event` (`app/modules/outbox/writer.py`) — the single write point: if `is_internal`, return `None` and skip. Enforced at write time; never left to the dispatcher.
- Unit tests in `tests/unit/test_outbox_writer.py` (internal → no emit; non-internal → emits).
- Full-loop e2e regression (`1782228f`): `tests/system/test_outbox_loop.py` — front-facing create emits → dispatcher delivers (mocked `httpx.Client`, real Postgres; delivery success + event completed + external link persisted) → writeback PATCH via `/internal` → outbox still holds exactly the one completed event (pre-fix: a pending `contact.updated` re-appears → ping-pong). Plus a non-vacuity control: the same update outside `/internal` DOES emit. System suite → does NOT run in CI (sh-vs-bash gotcha); the CI guards remain the unit wiring tests.
- Review nits (`7781ef17`): new `tests/unit/test_outbox_internal_surface.py` pins the wiring (`mark_internal_context` asserted as a root dependency of the internal router; flag-setter test; end-to-end probe POST `/internal/contacts` → 201 + no `IntegrationOutbox` row); writer tests moved to the autouse `cleanup_request_context` fixture; `outbox_emit_skipped_internal` debug log in the guard; EventBus worker comment on the `is_internal` boundary.

## Decisions
- Guard at the **writer**, not the dispatcher (user's hard requirement: events must not even be written for internal calls).
- Dedicated `is_internal` flag rather than reusing `is_sync_operation` — the latter is a subset (only 3 internal routers) and also drives `last_sync_at`.
- Scope limited to `/internal`: public/FE app, `/admin`, `/integrations` unchanged; out-of-request (CLI/migrations/tests) defaults to emitting.

## Diagnostic evidence (prod, read-only, Navitec tenant `2445fa20-f769-4f10-854e-a9e74df71ac5`)
- `integration_outbox_delivery`: **385,243 success + 653 dead**, all `tracker_rms`; deliveries **start 15-jul** (nothing before) → 132k on 19-jul.
- `role.updated`: 477 events over **28 roles**; one role ping-ponging `Covered ↔ Archived` **every ~70 min** for 24h including overnight.
- `contact.updated`: 344,173 over 60,862 contacts; 24 contacts with `echo_organization_id` flipping between 2 orgs (or to null = "disappearing").
- Contact deaths: `PATCH /Contact/{id} returned 204 (record not found)` → stale external_ids.

## Gotchas
- `is_sync_operation` existed and was set on internal routers but only wired to `last_sync_at` (`database/base.py`, `application/repository.py`) — never to outbox suppression. Easy to mistake as already solving this.
- The `write_outbox` docstring claims the dispatcher "deduplicates per entity at fan-out" — **false**, there is no such dedup; every enqueued event becomes an HTTP call.
- `echo_organization_id` in the contact payload derives from `current_company_id` → `current_relationship_id` (volatile computed subqueries in `app/modules/contact/models.py`), so relationship churn flips the pushed company, even to null.
- A bare service call from a test thread is NOT a faithful front-facing origin: `TenantScopedRepository.get_tenant_id()` gates on `is_in_request_context()`, so outside a request tenant auto-injection is skipped and the contact INSERT falls back to `contact.tenant_id`'s hardcoded Taller `server_default` (`f8a652e6…`) → FK violation in a test DB. Wrap the leg in `background_request_context(ctx)` (same fork mechanism the EventBus uses) to get real request-like tenant stamping.
- EventBus handlers run with a **fresh** `RequestContext` on the worker thread (`event_bus.py::_process_event`) — `is_internal` does NOT propagate. No current handler writes outbox events; a future one would bypass suppression (boundary documented in a comment there since `7781ef17`).

## Pending
- **Prod re-enable**: dispatcher was disabled in prod as mitigation; the fix is **in prod since 2026-07-21** — confirm whether the dispatcher was re-enabled (Vault `OUTBOX_DISPATCHER_ENABLED` / infra values).
- This PR is **only Layer 1 (loop-break)**. Deeper hardening discussed but NOT done:
  - Change-detection before emit (emit only when a payload-relevant field changed) — kills no-op re-emit churn.
  - Coalescing + idempotency at dispatch (collapse N pending per entity to latest; guard stale backlog on re-enable).
  - Contact company semantics: stop pushing the volatile derived company, never push `null` that blanks Tracker.
  - Stale contact external_id reconciliation (the 204/404 deaths).
  - Per-tenant rate-limit / circuit-breaker + dead-letter & abnormal-volume alerts (we found out via the client, not our own monitoring).
- [x] qa/main promotion — #1871 + #1872 **merged 2026-07-21** (merge commits).

## Related
- [[Map - TrackerRMS integration]]
- [[Outbox flat payload fix (PR 1838)]] — the prod-enablement that exposed this
- [[Outbox poll backoff (Bug 23522)]]
- Pedro's role-sync follow-ups in the same subsystem (2026-07-22 → 24): [#1893](https://github.com/taller-projects/echo-backend/pull/1893) outbox sends post-update role state (stale-payload fix; cherry-picks [#1894](https://github.com/taller-projects/echo-backend/pull/1894) qa + [#1895](https://github.com/taller-projects/echo-backend/pull/1895) main) · [#1888](https://github.com/taller-projects/echo-backend/pull/1888) manual push sends `role.quantity` · [#1896](https://github.com/taller-projects/echo-backend/pull/1896) `owner_id` in job payloads · [#1900](https://github.com/taller-projects/echo-backend/pull/1900) workflow step name as status · [#1905](https://github.com/taller-projects/echo-backend/pull/1905) **open**: overlay owner_id on account_manager_id change.
