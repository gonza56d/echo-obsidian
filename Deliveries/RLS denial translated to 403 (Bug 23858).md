---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, rls, error-handling, repositories]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2348"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23858"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23849"
prd: ""
---

# RLS denial translated to 403 (Bug 23858)

Every write rejected by a Postgres RLS policy answered **HTTP 500**. `SQLAlchemyRepository.handle_commit_errors` only matched `IntegrityError`, and RLS raises SQLSTATE 42501 (`psycopg2.errors.InsufficientPrivilege`) wrapped in `ProgrammingError`. The known case is standalone `POST /roles` by a user whose `visible_organizations` excludes the company: the placeholder `project` INSERT trips the policy's data-scope clause. It never reproduced locally or in tests, because `ENABLE_ACCESS_CONTROL=False` keeps the admin role and the testcontainer runs as a superuser. The fix answers 403 for any RLS denial, whether it comes from repository writes or from services that commit their own session.

## Azure / docs
- [Bug 23858](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23858): In development → **In revision** (2026-09-24), GitHub PR link added.
- Filed from [US 23849](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23849) (Create Role from Open Job), where it was worked around with `ProjectService.assert_can_create_standalone_role`.

## PRs
- [#2348](https://github.com/taller-projects/echo-backend/pull/2348) → dev: **OPEN 2026-09-24**. Commit `a5072eb8` `fix(repositories): translate RLS denials to 403 instead of 500`, then `76236717` `fix(exceptions): hand non-RLS ProgrammingError to the catch-all; report RLS denials to Sentry` (self-review round 1 fixes). PR body updated to match.
- Pedro (rocha-p) review 2026-09-24: **APPROVED, READY WITH NITS** (5 nits, 0 blockers). All 5 addressed in `f200b219` `fix(repositories): address review nits on RLS denial translation` (2026-09-25), PR body aligned (prod case = `POST /applications`, behaviour-change line for non-RLS `ProgrammingError`).
- FE: none. No contract change; the FE already shows `detail` on a 403.

## How
- `app/repositories/exceptions.py`: `RowLevelSecurityError(AuthorizationError)` has a generic detail ("You do not have permission to make this change"), `error.code` `authorization_error`, and a `policy_table` attribute. `from_db_error()` returns None unless `orig` is `InsufficientPrivilege` **and** `orig.diag.message_primary` **fullmatches** `new row violates row-level security policy .*?for table "<t>"` (was a `search` over `str(orig)` until Pedro's nit). The lazy gap covers the RESTRICTIVE-named and `(USING expression)` variants.
- `handle_commit_errors`: a `ProgrammingError` branch that rolls back and raises `RowLevelSecurityError`. A non-RLS error is re-raised with no rollback, which is the old behaviour.
- `app/core/exception_handlers.py`: `programming_error_handler`, registered on all four apps (root, `/internal`, `/admin`, `/integrations`) in `main.py`. It covers the ~54 service-level direct commits that never pass through the decorator. A non-RLS error is handed to the catch-all (500 + Sentry).
- `echo_exception_handler` logs `rls_policy_violation table=… method=… path=…` at WARNING (mirrors `duplicate_constraint_violation`) **and** calls `report_rls_policy_violation(table)` (`app/core/observability.py` → `sentry_sdk.capture_message(..., level="warning", fingerprint=["rls_policy_violation", table])`), so each table gets one Sentry issue. Without it a 4xx never reaches Sentry: WARNING logs are only breadcrumbs under the default `LoggingIntegration`, and nothing alerts on Loki.
- A non-RLS `ProgrammingError` goes to `return await unhandled_exception_handler(...)`, **not** `raise exc` (see Gotchas).
- `bulk_update_stage` (`application/service.py`) catches `EchoException` per item, so an RLS denial there becomes a per-item `authorization_error` and the global handler never runs. Its `bulk_stage_move_failed` warning carries `policy_table` and it calls `report_rls_policy_violation` too (Pedro's nit), so a broken `application` policy reaches Sentry from bulk moves as well.

## Decisions
- **Only the policy form of 42501 becomes a 403.** A missing GRANT (`permission denied for table …`) shares the SQLSTATE but is a deployment bug, so it stays a 500 and goes to Sentry.
- **Both the decorator and a global handler.** The decorator keeps the repo contract (domain error + rollback, like `IntegrityError`). The handler closes the "all RLS denials" goal for direct commits and autoflush.
- Reused `authorization_error` rather than adding a new `error.code`. The FE doesn't branch on it, and no new wire value was needed.
- `assert_can_create_standalone_role` stays. It still gives a 403 that says *what* is missing, where the generic RLS 403 doesn't.

## Gotchas
- **RLS can be tested for real in unit tests.** Inside the repo session's own transaction: `CREATE ROLE` (non-superuser) + GRANTs + `ALTER TABLE … ENABLE RLS` + `CREATE POLICY` + `SET LOCAL ROLE`. The rollback (the test's, or `handle_commit_errors`'s) undoes all of it, because DDL and CREATE ROLE are transactional. Add `SET LOCAL lock_timeout` so the ALTER fails fast. See `tests/unit/test_rls_denial_translation.py`.
- On PG16, a plain `UPDATE` whose new row fails an `UPDATE USING` clause (no WITH CHECK) emits the **plain** message. `(USING expression)` only appears for ON CONFLICT DO UPDATE.
- A constructed `psycopg2` error has `diag.*`/`pgerror` = None. Since the classifier reads `diag.message_primary`, tests that build the error by hand use an `InsufficientPrivilege` subclass overriding the `diag` property (`_server_error()` in both test files). The real-RLS tests cover the genuine driver path.

- **Never re-raise from an exception handler registered on both the root app and mounted sub-apps.** A re-raise inside a mounted app reaches its `ServerErrorMiddleware`, which sends the 500 and re-raises. The error then hits the ROOT app's handler for the same type with the response already started, and Starlette raises `RuntimeError("Caught handled exception, but response already started.")`. That produces a second, misleading Sentry event, and dedupe misses it because it is a different object. Return the catch-all's response instead. The `mounted_app` test in `tests/unit/core/test_exception_handlers.py` fails with the RuntimeError if someone reverts this.
- Side effect of not re-raising: on the root app, a non-RLS `ProgrammingError` no longer passes through `AccessLoggerMiddleware`. So it shows up in Sentry as a structured `ProgrammingError` event (from `capture_exception`) instead of the `app.access` `unhandled_exception_in_request` log event, and Sentry groups it differently. The traceback is still logged by the catch-all's `logger.exception`.
- Real-RLS tests: use `commit=False` whenever the row would pass the policy. Otherwise a regression would COMMIT the CREATE ROLE, and the role is cluster-global (it survives `drop_all`).

## Verification / baseline
- Sentry baseline (90 days, measured 2026-09-24 via org Discover): the only RLS 500s are `POST /applications` on **Taller prod** (tenant `01df2012…`), table `application`. There were 3 events (2026-09-01, and 2 on 2026-09-24) in issues ECHO-BACKEND-P6 / V4. No other endpoint or environment had any. After merge these become 403 plus the `rls_policy_violation table=application` Sentry warning. Posted on 23858 (comment 28872390), along with the missing-GRANT narrowing note.

## Pending
- CI on `f200b219`, then merge → Bug 23858 **Closed**.
- **Why is the `application` INSERT RLS-denied in Taller prod?** It happened twice on 2026-09-24. Unticketed. Investigate separately (could be a user outside data scope, or a policy gap).
- qa/main promotion with the next release.

## Related
- [[Create Role from Open Job (US 23849)]] · [[OrganizationJob top_tech string default (Bug 23859)]] (sibling follow-up from the same US)
