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
- [#2348](https://github.com/taller-projects/echo-backend/pull/2348) → dev: **OPEN 2026-09-24**. Commit `fix(repositories): translate RLS denials to 403 instead of 500`.
- FE: none. No contract change; the FE already shows `detail` on a 403.

## How
- `app/repositories/exceptions.py`: `RowLevelSecurityError(AuthorizationError)` has a generic detail ("You do not have permission to make this change"), `error.code` `authorization_error`, and a `policy_table` attribute. `from_db_error()` returns None unless `orig` is `InsufficientPrivilege` **and** the message matches `new row violates row-level security policy .*?for table "<t>"`. The lazy gap covers the RESTRICTIVE-named and `(USING expression)` variants.
- `handle_commit_errors`: a `ProgrammingError` branch that rolls back and raises `RowLevelSecurityError`. A non-RLS error is re-raised with no rollback, which is the old behaviour.
- `app/core/exception_handlers.py`: `programming_error_handler`, registered on all four apps (root, `/internal`, `/admin`, `/integrations`) in `main.py`. It covers the ~54 service-level direct commits that never pass through the decorator. A non-RLS error is **re-raised**, so it reaches the catch-all 500 + Sentry unchanged.
- `echo_exception_handler` logs `rls_policy_violation table=… method=… path=…` at WARNING. A 403 never reaches Sentry, so this keeps the signal in Loki. It mirrors `duplicate_constraint_violation`.

## Decisions
- **Only the policy form of 42501 becomes a 403.** A missing GRANT (`permission denied for table …`) shares the SQLSTATE but is a deployment bug, so it stays a 500 and goes to Sentry.
- **Both the decorator and a global handler.** The decorator keeps the repo contract (domain error + rollback, like `IntegrityError`). The handler closes the "all RLS denials" goal for direct commits and autoflush.
- Reused `authorization_error` rather than adding a new `error.code`. The FE doesn't branch on it, and no new wire value was needed.
- `assert_can_create_standalone_role` stays. It still gives a 403 that says *what* is missing, where the generic RLS 403 doesn't.

## Gotchas
- **RLS can be tested for real in unit tests.** Inside the repo session's own transaction: `CREATE ROLE` (non-superuser) + GRANTs + `ALTER TABLE … ENABLE RLS` + `CREATE POLICY` + `SET LOCAL ROLE`. The rollback (the test's, or `handle_commit_errors`'s) undoes all of it, because DDL and CREATE ROLE are transactional. Add `SET LOCAL lock_timeout` so the ALTER fails fast. See `tests/unit/test_rls_denial_translation.py`.
- On PG16, a plain `UPDATE` whose new row fails an `UPDATE USING` clause (no WITH CHECK) emits the **plain** message. `(USING expression)` only appears for ON CONFLICT DO UPDATE.
- A constructed `psycopg2` error has `diag.*`/`pgerror` = None, so the classifier matches on `str(error.orig)`. That works for real and constructed errors alike.

## Pending
- CI on #2348 (the user is watching it upstream); review; merge → Bug 23858 **Closed**.
- Sentry/Loki measurement of today's RLS 500s by endpoint (the ticket asked for it). A background agent was still running when the PR opened; add the results to the PR once in.
- The full local `tests/unit` + `tests/multitenancy` run was still in flight when the PR opened (the targeted 50 tests pass; both repo tests fail on dev without the fix).
- qa/main promotion with the next release.

## Related
- [[Create Role from Open Job (US 23849)]] · [[OrganizationJob top_tech string default (Bug 23859)]] (sibling follow-up from the same US)
