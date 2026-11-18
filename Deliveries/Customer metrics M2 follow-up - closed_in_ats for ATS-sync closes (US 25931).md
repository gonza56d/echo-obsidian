---
type: delivery
status: merged
env: both
delivered: 2026-11-18
tags: [follow-up, customer-metrics, roles, migration]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2667"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25931"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M2 follow-up - closed_in_ats for ATS-sync closes (US 25931)

Product (Paloma, Slack 2026-11-17) asked that a role the ATS sync closes without a reason not stay empty, so the customer metrics tell it apart from missing data. Follow-up of [[Customer metrics M2 follow-up - close_reason required on the user role PATCH (US 25744)]]. Feature [25635](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635).

## Azure / docs
- [US 25931](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25931): created 2026-11-17 (child of 25635, related 25744), In revision; PR link added by the Boards integration (AB# in the body), comment 29361425.
- [Tech PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj): changelog row + M2 item after merge.

## PRs
- [#2667](https://github.com/taller-projects/echo-backend/pull/2667) → dev, branch `25931/closed-in-ats`, worktree `.claude/worktrees/25931-closed-in-ats`, commit `627d93fa`. Reviewers Leo, Pedro, Gisel; assignee gonza-taller.

## What
- New `RoleCloseReason.CLOSED_IN_ATS = "closed_in_ats"` (`role.close_reason` is varchar(32): no enum migration).
- `_server_set_close_reason(old_stage, source)`: Filled → `filled` on every path; otherwise `RoleChangeSource.SYNC` (both /internal role PATCHes) with no reason → `closed_in_ats`. `ProjectService.update_role` passes `source` to `RoleService._update` (keyword-only, required).
- Public PATCH accepts the value like `filled`: FE `General.tsx` sends `close_reason: closeReason ?? serverRole.close_reason` on every save, so rejecting it would 422 any edit of a sync-closed role. No FE change.
- Migration `uyc4kphy0brp` (data only, after `gwmlolm5b3pr`): last move into Closed/Archived in `role_change_history` (DISTINCT ON role_id, created_at DESC) for roles with `closed_at` and no reason: from Filled → `filled`, by sync → `closed_in_ats`, user → stays empty. Downgrade empties `closed_in_ats` only (old code can't read it).

## Decisions
- Paloma's Q1: Navitec's filled state is Placed (stage Filled), Covered is stage Active — verified on prod 2026-11-17 (Placed 14 roles, Covered 2).
- Backfill also sets `filled` for Filled→Closed closes that predate #2499 (any source), per Paloma's rule "from the screen or the sync".
- All tenants, no flag.

## Evidence
- Dry run (read-only): prod 2 → closed_in_ats + 1 → filled (Navitec); dev 15 → closed_in_ats; kforce-prod 0. `role_change_history` prod 22k rows, dev 13.5k / 282 MB (JSONB snapshots) → seq scan < 1 s warm on dev.
- `test_roles.py` + `test_projects.py` + `test_migrations.py`: 316 passed. 8 mutants caught. alembic stamp → upgrade → downgrade -1 → upgrade on a throwaway Postgres (`tests.db_harness.build_schema` + admin role).

## Gotchas
- Local parallel full suite flaked twice (worker keyboard-interrupt, different unrelated failures, load ~8); the failing files passed serially. `DEBUG_MODE=false` needed for the outbox Sentry tests.
- Migration smoke needs the `DB_ADMIN_ROLE` (`postgres`) created: env.py runs `SET LOCAL ROLE`.
- The Azure ArtifactLink PATCH failed with "Relation already exists" (Boards auto-linked from AB#) and rolled back the state change in the same patch: send the state alone.

## Review round 1 (Pedro, review 5946706265)

Merged `origin/dev` first (`10846579`): `uyc4kphy0brp` re-chained onto `i1esl7vh6gny` (#2665, direct-hire placement fee) — both hung off `gwmlolm5b3pr`; `tests/unit/test_migrations.py` conflict = both sides appended blocks, kept both. Then `6967a111`:

- A user's **new** close (public PATCH) with `filled` / `closed_in_ats` → 422 `close_reason_not_allowed`, unless it equals what the server would set (`filled` on a Filled role: FE `RoleStatusInput.isClosingFilledRole` sends it). Re-sending a closed role's stored reason is not a new close (FE `General.tsx` re-sends `serverRole.close_reason` on every save). FE checked on `dev`: picker excludes `filled` (`SelectableRoleCloseReason`), never offers `closed_in_ats` → no FE flow hits the 422. Two tests closed an Open role with `filled`; now `other`.
- `assert_close_reason_given` → `assert_user_close_reason_valid`; `_SERVER_SET_CLOSE_REASONS`; `RoleCloseReasonNotAllowedError`.
- Migration docstring: rollback = `alembic downgrade` before reverting the image (old image 500s on `closed_in_ats`; pipeline migrates before deploy → ~minutes of 500 on the 2 prod roles during rollout). Backfill `ORDER BY ... created_at DESC, h.id DESC`.
- Tests: internal archive, reopen of a `closed_in_ats` role (re-sending the stored reason), FE's `filled` on a Filled role, the new 422 rows, backfill user-from-Filled. 2 mutants caught. Local role + migration + project modules 386 passed.
- Nit 6 (kforce-prod `role_change_history` count) not re-measured: no kforce-prod pg service. Prod re-measured 11-18: 1 `filled` + 2 `closed_in_ats`, 237 closes in 22,404 history rows.
- Out of scope: FE `RoleCloseReason` TS type lacks `closed_in_ats`.

## Pending
- [x] Squash-merged dev 2026-11-18 `f686c7ae` (Pedro APPROVED, CI green on `6967a111`) → [US 25931](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25931) Closed (comment 29369859).
- [ ] Tell Data about `closed_in_ats`: it means closed through `/internal` with no reason (the ATS sync, or any API-key caller).
- [ ] PRD changelog row + M2 item.
- [ ] qa / main with the next release (the migration runs on every env).

## Related
- [[Customer metrics M2 follow-up - close_reason required on the user role PATCH (US 25744)]] · [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]]
