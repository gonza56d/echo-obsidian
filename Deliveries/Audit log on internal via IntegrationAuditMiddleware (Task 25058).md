---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, kforce, internal-api, audit, observability]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2323"
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
- [#2323](https://github.com/taller-projects/echo-backend/pull/2323) -> dev — OPEN 2026-09-22. Branch `25058/audit-middleware-internal-app`.
  - `/pr-review` (2026-09-22): **READY WITH NITS**, 0 blockers (architecture 13/13 PASS; tests/security 0 blockers; PRD 2/3 asks met + shim untested).
  - Nits addressed in commit `817f4e09` (`test:` follow-up): added 3 e2e cases — POST 2xx audited, legacy `X-Echo-internal` shim row (`api_key_id=None`), audit-failure-never-breaks-request; extracted `_pin_default_bus`/`_poll_audit_row` helpers. 5 `TestInternalAudit` + full file (94) green.

## How
- `internal_app = FastAPI(middleware=[Middleware(IntegrationAuditMiddleware)], strict_content_type=False)` in `app/main.py` — identical to how `integrations_app` mounts it, so it sits **inside** the InjectorMiddleware (`dp_injector.setup_injections`) and `get_request_context()` resolves the context the auth dep populated. Core change is one line.
- Both internal auth paths already populate what the middleware reads: `_verify_api_key_with_surface` (`app/permissions.py`) sets `tenant_id` + `api_key_id`; the legacy `X-Echo-internal` shim sets `tenant_id` only -> those rows carry `api_key_id=None` (a useful cutover signal).
- Docstring on `app/modules/public_api/middleware.py` generalized to "internal + integrations".
- Tests (`TestInternalAudit` in `tests/unit/test_public_api_endpoints.py`): (1) middleware mounted on the `/internal` sub-app; (2) real internal GET -> middleware -> EventBus -> handler persists an `integration_request_log` row with resolved `tenant_id`/`api_key_id`.

## Decisions
- **Reuse the table/event as-is** (my recommendation, Gonzalo approved): `/internal` and `/integrations` rows share `integration_request_log`, told apart by `http_path`. No `surface` discriminator column now — left as a follow-up if consumers need it. The PRD asked for "el mismo IntegrationAudit", so reuse is the intent.
- **All tenants, no feature flag** — it is infra symmetry with `/integrations`, not tenant behavior.

## Gotchas
- The e2e audit test must keep the `TestClient` context **open while polling** the DB: the handler persists off-thread, so exiting the `with` (lifespan shutdown) first races/kills the EventBus worker. Mirror `TestAuditPipeline` and pin `event_bus_module._default_event_bus` to the app's injector-bound bus (robust to suite ordering).
- Do **not** probe `/internal/projects` (list) or a `mocked_project` detail route in tests: polyfactory generates **float** `min_budget`/`max_budget` and the internal `ProjectResponse` requires `int` -> `ResponseValidationError` 500 depending on suite pollution. Probe a **non-existent** project id -> deterministic 404, still authenticated so the audit fires.
- Constructor-level `middleware=[...]` is NOT gated by `create_app(add_middlewares=...)` (only Sentry + CORS/SecurityHeaders are), so the audit middleware runs in the test suite too — consistent with `AccessLoggerMiddleware`/`integrations_app`, verified no regressions.

- **Commit `817f4e09` carries a forbidden `Co-Authored-By: Claude Opus 4.8` trailer** (added against CLAUDE.md by mistake; can't be removed without a force-push, which CLAUDE.local.md forbids). Branch squash-merges to dev, so **strip the trailer from the squash message at merge** (same handling as #2314).

## Pending
- Review DONE (READY WITH NITS, nits addressed). Pending: merge (**strip Opus trailer from squash msg**); then Task 25058 -> Closed, qa/main promotion. Ticket owes: write-volume estimate (ask #2) + Loki-retention confirmation (ask #3) — ops checks, not code.
- **Follow-up (this ticket's scope):** at push volume every `/internal` write emits one `integration_request_log` row (~millions from one push) + EventBus load — retention/partitioning of that table is worth a follow-up; also a `surface` discriminator column if querying by surface becomes painful.

## Related
- [[Map - Kforce]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Map - Observability & Reliability]]
