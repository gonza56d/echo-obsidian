---
type: delivery
status: merged
env: both
delivered: 2026-09-22
tags: [feature, kforce, internal-api, audit, observability]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2323"
  - "https://github.com/taller-projects/echo-backend/pull/2339"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25058"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
prd: "https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg"
---

# Audit log on /internal via IntegrationAuditMiddleware (Task 25058)

P2-3 of Emiliano's Kforce-push PRD (priority *baja / barato*). `/internal` is where the ~1.98M-contact push lands but it ran with **no middleware** — no request trail — while `/integrations` already audits every call. This attaches the existing `IntegrationAuditMiddleware` to `internal_app` so backend-to-backend traffic is logged too. Sibling of [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] (same PRD, same Feature 24972).

## Azure / docs
- Parent: [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972) "Kforce - New Integration pipelines structure" (Nicolás)
- [Task 25058](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25058) — this PR (P2-3)
- PRD: [Pedidos a echo-backend para el push de Kforce](https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg) (Claude Doc, Emiliano) — read via Claude Docs MCP `read` (project -> node `kind: view`)

## PRs
- [#2323](https://github.com/taller-projects/echo-backend/pull/2323) -> dev — **MERGED 2026-09-22** (merge commit `51e188f3`). Branch `25058/audit-middleware-internal-app`. **Merged with a merge commit, NOT squashed** — so all three branch commits (`fafe5224`, `817f4e09`, `609a149d`) are on dev individually, and the forbidden `Co-Authored-By: Claude Opus 4.8` trailer on `817f4e09` is now **permanent in dev history** (removing it needs a force-push, which CLAUDE.local.md forbids). The plan to strip it from a squash message did not apply because the merge was not squashed. Nothing further to do — noted so it is not re-flagged.
- **`/pr-review` (2026-09-22): READY WITH NITS, 0 blockers** — nits addressed in `817f4e09` (`test:` follow-up): 3 e2e cases (POST 2xx audited, legacy `X-Echo-internal` shim row `api_key_id=None`, audit-failure isolation); extracted `_pin_default_bus`/`_poll_audit_row` helpers.
- **Pedro review (2026-09-22): CHANGES REQUESTED — 1 real blocker.** [comment](https://github.com/taller-projects/echo-backend/pull/2323#issuecomment-5778139669). Attaching the audit middleware to `internal_app` made every `/internal` request publish an `integration.request` event onto the **shared** default `EventBus` (bounded `queue.Queue(maxsize=1000)`, single worker, `put_nowait` drop-on-`queue.Full`). During the push, audit ~doubles queue traffic in the busiest window, so a functional event (placements/notifications/status) — not just an audit row — could be the one dropped. AC #3 ("verify write volume acceptable for ~2M requests") existed to rule out exactly this.
- **Blocker resolved — commit `609a149d` (pushed 2026-09-22), option 2 (isolate audit from functional events).** `dependencies.py` now builds two buses: the default bus with `exclude_events={integration.request}`, and a dedicated `AuditEventBus(only_events={integration.request})` started with `set_default=False` (so it never displaces the default singleton). The middleware publishes via `get_audit_event_bus()`. Each bus has its own queue+worker → an audit burst can only drop audit rows, never a functional event. Reply: [comment](https://github.com/taller-projects/echo-backend/pull/2323#issuecomment-5779323461). Awaiting Pedro re-review.
  - Nits in the same commit: honest `IntegrationRequestLog` docstring (POST audited; `query_params` can carry PII e.g. `?email=` → redaction tracked as follow-up); `_pin_default_bus` → `_pin_audit_bus` via `monkeypatch.setattr` (auto-reverting); new 401-audit-row test; new `TestAuditBusIsolation` (registry filtering + `set_default` guard). Queue-full drop contract already pinned by pre-existing `test_eventbus_queue_full_handling`.
  - Verification: `test_event_bus.py` 19/19, `test_public_api_endpoints.py`+shim 106/106, functional-event handlers (adoption/outbox/dispatcher) 117/117, lint clean.
- [#2339](https://github.com/taller-projects/echo-backend/pull/2339) — release `dev` → `qa` OPEN 2026-09-23 (31 commits, 7 migrations, single head `zolvj810zl6j`); `qa` → `main` opens after it merges (qa == main until then).

## How
- `internal_app = FastAPI(middleware=[Middleware(IntegrationAuditMiddleware)], strict_content_type=False)` in `app/main.py` — identical to how `integrations_app` mounts it, so it sits **inside** the InjectorMiddleware (`dp_injector.setup_injections`) and `get_request_context()` resolves the context the auth dep populated. Core change is one line.
- Both internal auth paths already populate what the middleware reads: `_verify_api_key_with_surface` (`app/permissions.py`) sets `tenant_id` + `api_key_id`; the legacy `X-Echo-internal` shim sets `tenant_id` only -> those rows carry `api_key_id=None` (a useful cutover signal).
- Docstring on `app/modules/public_api/middleware.py` generalized to "internal + integrations".
- Tests (`TestInternalAudit` in `tests/unit/test_public_api_endpoints.py`): (1) middleware mounted on the `/internal` sub-app; (2) real internal GET -> middleware -> EventBus -> handler persists an `integration_request_log` row with resolved `tenant_id`/`api_key_id`; plus (from `817f4e09`) POST 2xx audited, legacy-shim `api_key_id=None`, and audit-failure isolation.

## Decisions
- **Reuse the table/event as-is** (my recommendation, Gonzalo approved): `/internal` and `/integrations` rows share `integration_request_log`, told apart by `http_path`. No `surface` discriminator column now — left as a follow-up if consumers need it. The PRD asked for "el mismo IntegrationAudit", so reuse is the intent.
- **All tenants, no feature flag** — it is infra symmetry with `/integrations`, not tenant behavior.
- **Dedicated audit `EventBus`** (Gonzalo, resolving Pedro's blocker): audit rides its own queue+worker so a `/internal` push spike can only drop audit rows, never a functional event. Chosen over a throughput-measurement waiver (option 1) and per-event commit batching (option 3, which leaves audit on the shared queue).

## Gotchas
- The e2e audit test must keep the `TestClient` context **open while polling** the DB: the handler persists off-thread, so exiting the `with` (lifespan shutdown) first races/kills the EventBus worker. Mirror `TestAuditPipeline` and pin the app's injector-bound bus (robust to suite ordering). NOTE (post-`609a149d`): the middleware now publishes to the **audit** bus, so pin `event_bus_module._audit_event_bus` to `injector.get(AuditEventBus)` — the `_pin_audit_bus` helper does this via `monkeypatch.setattr`.
- Do **not** probe `/internal/projects` (list) or a `mocked_project` detail route in tests: polyfactory generates **float** `min_budget`/`max_budget` and the internal `ProjectResponse` requires `int` -> `ResponseValidationError` 500 depending on suite pollution. Probe a **non-existent** project id -> deterministic 404, still authenticated so the audit fires.
- Constructor-level `middleware=[...]` is NOT gated by `create_app(add_middlewares=...)` (only Sentry + CORS/SecurityHeaders are), so the audit middleware runs in the test suite too — consistent with `AccessLoggerMiddleware`/`integrations_app`, verified no regressions.

- **Commit `817f4e09` carries a forbidden `Co-Authored-By: Claude Opus 4.8` trailer** (added against CLAUDE.md by mistake). The PR was merged with a **merge commit (not squashed)**, so the trailer is now permanent on dev — it could only be removed by a force-push, which CLAUDE.local.md forbids. Lesson for next time: PRs to dev that carry a bad trailer must be **squash-merged** (where the message is editable), not merge-committed.

## Pending
- **MERGED to dev 2026-09-22** (merge commit, not squashed — Opus trailer on `817f4e09` is permanent, see PRs). Pending: Task 25058 -> Closed, qa/main promotion. Ticket owes: Loki-retention confirmation (AC #4) — ops check, not code. (AC #3 write-volume concern is resolved structurally by the dedicated audit bus, not by a throughput estimate.)
- **Follow-up (this ticket's scope):** at push volume every `/internal` write emits one `integration_request_log` row (~millions from one push) + EventBus load — retention/partitioning of that table is worth a follow-up; also a `surface` discriminator column if querying by surface becomes painful.

## Related
- [[Map - Kforce]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Map - Observability & Reliability]]
