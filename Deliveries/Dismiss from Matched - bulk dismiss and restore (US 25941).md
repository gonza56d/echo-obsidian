---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, applications, matching, navitec, bulk-actions]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2669"
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
- PR 2 (Task 25943): not started.

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
- PR 2 will add `POST /roles/{role_id}/applications/bulk-dismiss` and `bulk-restore` (`application_ids` 1-50, optional `reason`; 200 with `updated` / `failed[{id, reason}]`; reasons `not_found`, `not_in_matching`, `already_dismissed`, `not_dismissed`). `DELETE /applications/{id}` keeps its 204.
- The FE computes `isLimitReached` from the totals of the four category lists (`Candidates.tsx`), so the list and the cap must exclude dismissed rows together. They do, in the same PR.

## Decisions
- **Re-adding a dismissed candidate** (agreed with the user 2026-11-18, ships in PR 2): the unique index `uq_application_tenant_role_talent_current` stays as is, so a dismissed row keeps the role's slot. Explicit single-candidate actions (Add Candidates, apply to role and role loads, career-page apply) restore it and proceed. `bulk-stage` and `PATCH /applications/{id}` on a dismissed row fail with `dismissed`. Narrowing the index was discarded: second current row per candidate, plus an index rebuild.
- Reason: optional free text, max 500 characters. Paloma's open question (fixed list?) can change it without a schema change.
- Two PRs so nothing leaks between them: read side first (inert), then the write paths.
- `dismissed` defaults to None on the filter, not False: `TalentFilter.uses_only_profile_fields` reads any non-None field of the nested `ApplicationFilter` as "a filter is set" and would leave the fast path on every talent list.
- Not filtered: `Role.applied_talents` (no reader). `Talent.current_application_id` was first left out as "not observable". The self-review showed it is observable through `application__last_step_update__*`, so it is now filtered.

## Gotchas
- `application` has ~200k rows on Taller prod and **none on KForce** (migration `iler6qompzab` says so), despite the PRD's warning about KForce volume.
- The reporting dataset in `tests/unit/modules/public_api/test_reporting.py` is module-scoped and its tests count the tenant's matches: a test that adds one must delete it at teardown. `role_3` is the only role there with no applications.
- In a worktree session, any Bash command whose text contains "git" (a GitHub URL in a heredoc counts) is refused as too complex. Put the text in a script file inside the worktree and run that.
- Docker's disk filled up while another agent ran suites (49 MB free): Postgres containers failed with "port mapping not available", not with a disk error. The underlying error only shows in `docker logs` of a hand-started container.
- The migration was exercised by hand against a throwaway Postgres holding only `application` and `user`, not through the full alembic chain.
- A new column has no `pg_statistic` row, so `IS NULL` falls back to 0.5% selectivity. Measured on 200k rows: an estimate of 949 against 190,273 after `ANALYZE`. ADD COLUMN does not trigger autoanalyze, so a migration that adds a column every list filters on should end with `ANALYZE`.
- `Talent.is_deletable` was an uncorrelated `~exists()`. When the outer talent query joins `application`, SQLAlchemy correlates both tables away ("returned no FROM clauses due to auto-correlation"). It was latent: Sentry shows 0 events in 90 days, and the FE sends `application__last_status_update__*` only on tenants without a workflow.
- Another live session held the PR's worktree (`.claude/worktrees/25942-application-dismiss-read-side`, locked). I worked in `25942-dismiss-review-blockers` (branch `25942/dismiss-review-blockers` off the PR head) and pushed `HEAD:25942/application_dismiss_read_side`. That leaves the other worktree's local branch behind the remote.

## Pending
- Review and squash-merge of [#2669](https://github.com/taller-projects/echo-backend/pull/2669); then close Task 25942.
- PR 2 (Task 25943): bulk-dismiss / bulk-restore, `DELETE` as dismiss, the re-add semantics, structured logs `application.bulk_dismissed` / `application.bulk_restored`.
- `EXPLAIN` of the role list, counts, cap and reporting feed on dev (a Taller DB) once #2669 is deployed, before PR 2 merges (expected: no new index). Task 25942 was amended to say so (rev 4): KForce has no `application` rows.
- Out of scope, goes to Task 25943: `match_single_talent` (`POST /matches?talent_id`) upserts with `on_conflict="update"` onto a dismissed row, which nulls its score and re-evaluates it. Add it to the re-add decision list.
- Self-review nits left open: composite FK `(dismissed_by_id, tenant_id)` (free while the column is all NULL), `dismissed` missing from `MATCH_LIST_FILTERS`, `ADD CONSTRAINT ... NOT VALID`, an internal-list test via the `caller` parametrize, `_when_` test names.
- #2668 (Pedro) must re-parent onto `ljbebr6uidhl` if it merges after #2669.
- Tell the FE (US 25052 / 25051) the `dismissed=true` filter and the new response fields once #2669 is on dev.
- Open questions on the PRD: total cap counting dismissed (product), the action's name in the UI (FE + Paloma).
- qa / main promotion with the next release.

## Related
- [[Evaluate batch scoped to new candidates (PR 2334)]]: why `evaluate_batch` without `candidate_ids` is role-wide.
- [[Map - TrackerRMS integration]]: the owner/source follow-up depends on tracker-rms-api.
