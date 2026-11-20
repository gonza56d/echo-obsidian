---
type: delivery
status: merged-dev
env: both
delivered: 2026-11-19
tags: [feature, applications, matching, navitec, bulk-actions]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2669"
  - "https://github.com/taller-projects/echo-backend/pull/2676"
  - "https://github.com/taller-projects/echo-backend/pull/2692"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25711"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25941"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25942"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25943"
prd: "https://app.notion.com/p/41caedca11f08126b3f0cbdf3487872c"
---

# Dismiss from Matched - bulk dismiss and restore (US 25941)

Navitec asked for bulk actions on a role's Candidates tab ([CR 25711](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25711), Pedro's technical PRD [Bulk actions en candidatos de un rol (Dismiss, Add to process)](https://app.notion.com/p/41caedca11f08126b3f0cbdf3487872c), Tier C, M1). "Remove" in Matched hard-deleted the application, so the candidate came back on the next "Get more matches". It becomes a dismiss: the row stays with `dismissed_at`, `dismissed_by_id` and `dismissed_reason`, is out of every list and count, frees room under the match cap and never returns on expand. Pedro handed me the backend of M1 on 2026-11-18. It applies to every tenant, with no feature flag.

## Azure / docs
- [CR 25711](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25711) (Pedro) → my [US 25941](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25941) with [Task 25942](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25942) (PR 1, read side) and [Task 25943](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25943) (PR 2, write side). Sprint 45.
- FE is not mine: [US 25052](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25052) (object-first bulk bar) and its child [US 25051](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25051) (bulk Add to process on `PATCH /applications/bulk-stage`, no backend change).
- Out of the PRD, follow-up: bulk owner and source. Blocked on tracker-rms-api (Juan), Feature 25482 (Leandro) and Tyler's answers.
- Repo note: `docs/application-dismiss.md` (which readers filter, what still sees a dismissed row, the re-add decision).

## PRs
- [#2669](https://github.com/taller-projects/echo-backend/pull/2669) → dev, OPEN 2026-11-18, branch `25942/application_dismiss_read_side`. PR 1: schema and read side. Inert on its own: nothing dismisses yet.
  - Self-review round 1 (2026-11-18, pr-review skill, full mode): CHANGES REQUESTED, 2 blockers (`Talent.current_application_id` left unfiltered against the ticket; the ticket's pre-merge EXPLAIN gate deferred while the new column had no planner stats). Both fixed and pushed in `c6f7ba0b`, on top of a dev merge `0606653c`. Full suite 7998 passed. Not posted to GitHub.
  - Gisel r1 (2026-11-19, CHANGES REQUESTED on `c6f7ba0b`): 1 blocker, two Alembic heads once dev (with #2668 and the merge migration `tdfsg8oyf8bq`) is merged in. Confirmed with `alembic heads` after merging dev. Fixed in `ce6de90a`: `down_revision = tdfsg8oyf8bq`; nits taken: composite FK `fk_application_dismissed_by_user_tenant` (`SET NULL (dismissed_by_id)`, NOT VALID + VALIDATE), `dismissed` moved to `ApplicationListFilter` (off `GET /talents`), `Mapped["User | None"]`, test tweaks, docs code. Reply posted, Gisel re-requested, Task 25942 commented. Full suite 8091 passed.
- [#2676](https://github.com/taller-projects/echo-backend/pull/2676) → base `25942/application_dismiss_read_side` (stacked on #2669; moves to dev when #2669 merges), OPEN 2026-11-18, branch `25943/application_bulk_dismiss`, worktree `25943-application-bulk-dismiss`. PR 2: `POST /applications/bulk-dismiss` and `bulk-restore`, `DELETE` as dismiss, the dismissed guard and the re-add paths. Full suite local: 8014 passed.
- [#2692](https://github.com/taller-projects/echo-backend/pull/2692) — release dev → qa 2026-11-20 (`deploy/qa_2026-11-20`, OPEN): carries #2669 + #2676; migration `ljbebr6uidhl` reaches qa.

## Review rounds (2026-11-19)
- [#2669](https://github.com/taller-projects/echo-backend/pull/2669) **squash-MERGED dev `069e216c`** after Gisel's r2 approval on `ef7ead93`. Task 25942 Closed.
- [#2676](https://github.com/taller-projects/echo-backend/pull/2676) retargeted to dev, dev merged in, Gisel r1 (CHANGES REQUESTED, 3 blockers) answered in `53fe9fc5`; re-review requested. Blockers, all real: (1) a dismiss committed between a move's read and write left a row in process and dismissed, fixed by an unconditional `clear_dismissal` in `update()` whenever a row leaves matching (the write is the lock); (2) `_bulk_dismissal` dropped the dismissed flag, so a match readable but not writable read as `already_dismissed`, now `not_found` and 404 on DELETE; (3) Apply to role untested, added for an external vendor on workflow and status-flow roles. Also: `/internal/matches` no longer restores, neutral bulk names, `user_id` in the logs, `ApplicationInProcessError` (code `conflict` kept for the FE). Full suite 8092 passed.

## How
- Migration `ljbebr6uidhl`: three nullable columns with no default, `fk_application_dismissed_by_user` (`ON DELETE SET NULL`), partial index `ix_application_dismissed_by_id`, and `application_score_rank` replaced to skip dismissed rows.
- `ApplicationFilter.filter()` adds `dismissed_at IS NULL`, or `IS NOT NULL` with `dismissed=true`. That covers `GET /applications`, `/applications/counts` and the internal list with no plumbing.
- Explicit `dismissed_at IS NULL` in: `get_distinct_recruiters`, `count_by_role` (the expand cap), `refresh_match_percentages`, `get_bulk_email_recipients`, `get_case_study_candidate_rows`, the case-study project gate in `TalentRepository`, `count_unclassified_applications`, `PublicApplicationFilter` and `reporting_applications_select`.
- The expand exclusion (`_talent_ids_on_role`) is deliberately not filtered: it is what keeps a dismissed candidate from coming back.
- Rematch: `talent_ids_to_reevaluate` returns None while the role has no dismissed application (role-wide `evaluate_batch`, as before) and the standing candidates once it has one.
- `ApplicationResponse` gains `dismissed_at`, `dismissed_by` (`id`, `full_name`, `profile_picture_key`) and `dismissed_reason`.
- `Talent.current_application_id` also skips dismissed rows (review blocker 1). It orders by `last_status_update DESC NULLS LAST`; step moves never set that column, so a step-backed application and a dismissed match tie at NULL.
- The migration ends with `ANALYZE application` (review blocker 2) and now sits on `uyc4kphy0brp`: #2667 merged to dev first.
- `Talent.is_deletable` gained `correlate_except(Application)`. This is a pre-existing bug fix the blocker-1 test needed: without it, any `GET /talents` with an `application__*` date filter answered 500.

## FE contract
- `GET /applications` and `/applications/counts`: new `dismissed=true`. Omitted is today's behaviour.
- PR 2 adds `POST /applications/bulk-dismiss` (`role_id`, `application_ids` 1-50, optional `reason` max 500) and `POST /applications/bulk-restore` (`role_id`, `application_ids`): 200 with `updated` / `failed[{id, reason}]`; reasons `not_found`, `not_in_matching`, `already_dismissed`, `not_dismissed`; 404 unknown role, 422 bad list. `DELETE /applications/{id}` keeps 204 / 409. A dismissed id sent to `bulk-stage` fails with `application_dismissed`; a PATCH of one answers 400 with that `error.code`.
- The FE computes `isLimitReached` from the totals of the four category lists (`Candidates.tsx`), so the list and the cap must exclude dismissed rows together. They do, in the same PR.

## Decisions
- **Re-adding a dismissed candidate** (agreed with the user 2026-11-18, ships in PR 2): the unique index `uq_application_tenant_role_talent_current` stays as is, so a dismissed row keeps the role's slot. Explicit single-candidate actions (Add Candidates, apply to role and role loads, career-page apply) restore it and proceed. `bulk-stage` and `PATCH /applications/{id}` on a dismissed row fail with `dismissed`. Narrowing the index was discarded: second current row per candidate, plus an index rebuild.
- Reason: optional free text, max 500 characters. Paloma's open question (fixed list?) can change it without a schema change.
- Two PRs so nothing leaks between them: read side first (inert), then the write paths.
- `dismissed` defaults to None on the filter, not False: `TalentFilter.uses_only_profile_fields` reads any non-None field of the nested `ApplicationFilter` as "a filter is set" and would leave the fast path on every talent list.
- Not filtered: `Role.applied_talents` (no reader). `Talent.current_application_id` was first left out as "not observable". The self-review showed it is observable through `application__last_step_update__*`, so it is now filtered.

## Decisions (PR 2)
- Routes under `/applications` with the role in the body, not the PRD's `/roles/{role_id}/applications/...` (marked adjustable there): same shape as `bulk-stage`, and no new router file.
- One guarded `UPDATE ... RETURNING` plus one read per request instead of bulk-stage's per-item commits: a dismissal has no per-item side effects (no outbox, no history), and it keeps 50 ids at two statements.
- `not_found` also covers a match the caller can see but cannot write under RLS: it does not come back from the UPDATE.
- Error code `application_dismissed` (module naming), not `dismissed` as the ticket first said; commented on Task 25943.
- `create_match_applications(restore_dismissed=...)`: only `match_single_talent_to_role` restores. Any other upsert skips dismissed rows through the `ON CONFLICT ... WHERE dismissed_at IS NULL` clause.

## Gotchas
- Merging dev into a branch stacked on a squash-merged PR conflicts in every file the squashed PR changed after the stack was cut. `git merge | tail` hid four of seven conflicts and I committed markers (local only, repaired before pushing). Read the whole merge output and `rg '^<<<<<<<'` before committing; files the stacked PR never touched are dev's.
- A conditional `UPDATE ... WHERE dismissed_at IS NOT NULL` takes no row lock when nothing matches, so it cannot close a race. The clearing write is unconditional for that reason.
- `UserFactory` leaves `first_name` or `last_name` empty in about 3 of 4 builds, and `GET /applications/recruiters` drops a recruiter with no full name. A test that asserts on that list must name its users. It made the counts test fail on CI (run of `ce6de90a`, 2026-11-19) while passing locally: the seeded random stream sits at a different position there. Fixed in `ef7ead93` by naming the recruiters in `_make_recruiter`.
- Neither git nor CI catches a second Alembic head: the merge is clean and the suite builds the schema with `create_all`. Run `alembic heads` after every dev merge on a branch that carries a migration.
- `POST /matches?talent_id=` (talent-wide matching) still answers 500 on dev (`Role.workflow_step_id`, strict xfail in `test_matching.py`), so the skip-dismissed branch of the upsert has no route to test it through.
- A worktree session cannot create a second worktree (`git -C` and sibling paths are refused): ExitWorktree keep, `git worktree add` from the main checkout, then EnterWorktree with `path`.
- `application` has ~200k rows on Taller prod and **none on KForce** (migration `iler6qompzab` says so), despite the PRD's warning about KForce volume.
- The reporting dataset in `tests/unit/modules/public_api/test_reporting.py` is module-scoped and its tests count the tenant's matches: a test that adds one must delete it at teardown. `role_3` is the only role there with no applications.
- In a worktree session, any Bash command whose text contains "git" (a GitHub URL in a heredoc counts) is refused as too complex. Put the text in a script file inside the worktree and run that.
- Docker's disk filled up while another agent ran suites (49 MB free): Postgres containers failed with "port mapping not available", not with a disk error. The underlying error only shows in `docker logs` of a hand-started container.
- The migration was exercised by hand against a throwaway Postgres holding only `application` and `user`, not through the full alembic chain.
- A new column has no `pg_statistic` row, so `IS NULL` falls back to 0.5% selectivity. Measured on 200k rows: an estimate of 949 against 190,273 after `ANALYZE`. ADD COLUMN does not trigger autoanalyze, so a migration that adds a column every list filters on should end with `ANALYZE`.
- `Talent.is_deletable` was an uncorrelated `~exists()`. When the outer talent query joins `application`, SQLAlchemy correlates both tables away ("returned no FROM clauses due to auto-correlation"). It was latent: Sentry shows 0 events in 90 days, and the FE sends `application__last_status_update__*` only on tenants without a workflow.
- Another live session held the PR's worktree (`.claude/worktrees/25942-application-dismiss-read-side`, locked). I worked in `25942-dismiss-review-blockers` (branch `25942/dismiss-review-blockers` off the PR head) and pushed `HEAD:25942/application_dismiss_read_side`. That leaves the other worktree's local branch behind the remote.

## Pending
- **Backend of M1 is complete on dev (2026-11-19):** [#2669](https://github.com/taller-projects/echo-backend/pull/2669) squash `069e216c`, [#2676](https://github.com/taller-projects/echo-backend/pull/2676) squash `3e156165` (Gisel approved r2). Tasks 25942, 25943 and US 25941 Closed.
- Merged without Pedro's sign-off on the two deviations (routes under `/applications`, `application_dismissed`): the user decided it was not needed. Gisel's approval named it as a condition.
- Done before the merge: `EXPLAIN` on dev (cap and counts on `uq_application_tenant_role_talent_current`, about 1 ms on a 920-application role; reporting count 76 ms); no Grafana alert rule or dashboard (60) reads `application_deleted_in_matching`.
- FE contract written into the description of US 25965 (Leo's new story, remove from Matched + add to process), US 25051 and US 25052, and into the PRD's Anexo Backend (changelog row 2026-11-19). 25965 overlaps 25051 (both cover bulk Add to process over `PATCH /applications/bulk-stage`).
- FE still to build: bulk Dismiss / Restore, the "Dismissed" filter, bulk Add to process. No FE PR yet.
- Open questions on the PRD: total cap counting dismissed (product), the action's name in the UI (FE + Paloma), whether the reason stays optional free text (Paloma).
- Pre-existing bug, not filed: `POST /matches?talent_id=` answers 500 (`Role.workflow_step_id`).
- Follow-up outside the PRD: bulk owner / source = Leo's US 25964 (bulk-custody, CR 25767).
- qa / main promotion with the next release.

## Related
- [[Evaluate batch scoped to new candidates (PR 2334)]]: why `evaluate_batch` without `candidate_ids` is role-wide.
- [[Map - TrackerRMS integration]]: the owner/source follow-up depends on tracker-rms-api.
