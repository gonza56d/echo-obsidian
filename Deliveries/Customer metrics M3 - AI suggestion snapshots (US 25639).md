---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, adoption, customer-metrics, migration, rls, ai]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2475"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25639"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M3 - AI suggestion snapshots (US 25639)

Customer metrics M3 (metric 3, "AI leverage"). Every AI generation for the five kinds (job description, matching instructions, assessment, team composition, case study) leaves an `ai_suggestion` snapshot of what the generator returned; a user's save that CHANGES the content resolves it (`accepted` / `edited` + `changed_fields`), a new generation of the same part resolves the previous one as `regenerated`; the reporting SQL derives an open snapshot as `accepted` (applied content the entity still holds) or `ignored` (unsaved preview, deleted role / card), so metric 3 keeps the PRD's four outcomes. Builds on [[Customer metrics M2 - domain history (US 25638)]] (merged into dev squashed as `b2c1426e`, 2026-10-28).

## Azure / docs
- [US 25639](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25639) (In revision since 2026-10-27, PR linked as GitHub Pull Request). Parent [Feature 25635](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635); business contract [CR 25592](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592).
- Tech PRD: [Customer Metrics Event History](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj), section 6 Milestone 3, section 7 metric 3; **rev 77 (2026-10-28)**: correctness bullet + M3 AC rewritten for the derived outcomes, schema comment, 4 changelog rows (metric 3 definition; as-built columns; no auto events + MI-from-enhancement durability; scope / legacy endpoints out / new 404s).
- US 25639 description + AC updated 2026-10-28 (rev 3): change-only resolution, derived accepted / ignored, auto on own rows, legacy endpoints out.
- Nico's SQL: `docs/customer_metrics_m3_ai_suggestions.sql` (3a-3e; `-f`, docs/ is ignored).

## PRs
- [#2475](https://github.com/taller-projects/echo-backend/pull/2475) → `25638/domain-history` (STACKED on [#2469](https://github.com/taller-projects/echo-backend/pull/2469)), OPEN 2026-10-27, `9dddc18c` (branch `25639/ai-suggestion-snapshots` off `ad72edfe`, worktree `.claude/worktrees/25639-ai-suggestion`, upstream unset before the first push so a bare push could not land on M2). Retarget to dev after #2469 merges. Body draft in the worktree's `.claude/worktrees/tmp/pr_m3_body.md`.
- 2026-10-28: base already `dev` after #2469 merged squashed (`b2c1426e`) → PR CONFLICTING (add/add on the M2 files). Fixed with a merge of `origin/dev`, no force push: worktree `.claude/worktrees/25639-ai-suggestion-merge-dev` (branch `25639/ai-suggestion-snapshots-merge-dev`), `git read-tree --reset -u origin/dev` + `git apply --3way --index` of the `9dddc18c` diff (old git 2.39 has no `merge-tree --merge-base`) → merge commit **`feff409c`** pushed; diff vs dev = exactly the M3 commit (27 files, +2530/−115). Only overlaps with dev's newer changes: import moves in `adoption/schemas.py` and `DEFAULT_INDUSTRY` → `tenant.industry` (M3 already used it). Single head `bmyaawpi69zn`, ruff clean, full local unit + multitenancy **6892 passed** (the 4 `test_export_rfq_logic` failures seen on the M2 head are gone). PR body stacked line → "Builds on M2 (#2469, merged into dev)".
- 2026-10-28: self-review r1 fixes **`a03e9684`** pushed (user asked: both blockers + the auto-snapshot user_id; CI watched upstream). B1: `team_composition_v3` / `role_v3` (ProjectService) and `regenerate_challenge` (RoleService) `get_by_id` first → foreign / missing id = 404 before the AI call (small behavior change: a random project id used to reach Team Builder; FE only calls them on existing entities); case-study isolation test now counts snapshots (the old tenant filter could not fail). B2 tests found a REAL BUG: FE `useTechEditing.ts` re-ids `/regenerate_assessment` questions (`id: uuidv4()`), so those snapshots never resolved → `skill_questions` snapshots match by normalized text (`question_text:` items); limit: reworded vs removed both `questions_edited`, an all-reworded batch stays open (SQL known limit added). Auto snapshots (enhancement JD + MI, standalone-create JD) → `requested_by_id=None`, no generated event; JD history row keeps the user. Tests: role 22→28, isolation 4→7; each new guard / the text match verified to fail without its fix; targeted 83 passed. PR body updated.
- 2026-10-28: **Leo r1** ([comment 6472070231](https://github.com/taller-projects/echo-backend/pull/2475#issuecomment-6472070231), CHANGES REQUESTED on `a03e9684`: B1 change-only rule redefines metric 3 (`kept` 5th bucket, no `accepted` for applied kinds, per-tenant, latest vs all), B2 rollback-together on 2 of ~9 hooks, B3 no table-level isolation test; 9 nits) → fixes **`90d3e908`** pushed (user asked; worktree `.claude/worktrees/25639-ai-suggestion-leo-r1`, branch `25639/ai-suggestion-snapshots-leo-r1` → `origin 25639/ai-suggestion-snapshots`; the merge-dev worktree is owned by another session). B1 decided by the user (PRD owner): keep change-only resolution, SQL folds kept → derived `accepted` (ignored when the role / card is deleted), auto on own rows (`requested`), every query per tenant, run as postgres; PRD rev 77 + US 25639 updated. B2: rollback tests for role PATCH, auto MI, POST / PATCH / update_and_sync assessment, generate_solution_v3, card edit / regenerate / find similar. B3: repo-level isolation (tenant-B row on the same entity id) + `tests/unit/test_ai_suggestion_rls_policies.py` (rls_probe; foreign insert → RowLevelSecurityError 403 via handle_commit_errors). Nits: `open_for_update` (FOR UPDATE), `comparison.py`, `AssessmentService.record_*_generation`, `new_entity` for new cards, `current=` on update, typing, log `project.role_spec_suggestion_resolve_failed`, status-checked helpers, internal re-wrap test, role_v3 failure test. 12 mutations all caught; SQL checked on a seeded throwaway PG (3a = expected per case); full local unit + multitenancy **6917 passed**. PR body refreshed. Reply to Leo DRAFTED (worktree `.claude/worktrees/tmp/reply_leo_r1.md`), not posted.

## How
- **Migration `bmyaawpi69zn`** (parent `m8qz4tkv2wdc`): new table `ai_suggestion` (PRD columns + `updated_at`, FKs to user SET NULL on `requested_by_id` / `outcome_by_id`), indexes (tenant, kind, created_at) and (tenant, entity_type, entity_id, created_at), RLS = tenant expression (custom_fields form) for ALL, plain builds (new empty table), guarded re-run.
- **Module `app/modules/ai_suggestion/`**: `AiSuggestionService.record_generation` (supersede same target + key as `regenerated`; additive = no key; full assessment supersedes all; trigger manual / regenerate / auto; `tenant_id` override for runs with no request tenant), `supersede` (case study set), `resolve_field_save` (JD, MI, case study card), `resolve_assessment_save` (per-snapshot question items by id + live challenge), `resolve_team_save`, `resolve_role_spec_save`. Never commits; callers commit with their own write. `payload = {target, target_key, content}`. `model` = service (`team_builder` / `vectorizer` / `assessment_creator`), `prompt_version` = endpoint (`job_descriptions_v2`, ...).
- **Events**: `ai_suggestion_generated` / `ai_suggestion_resolved`, entity role / project / `case_study` (new UserEventEntityType), only when a user acted.
- **Hooks**: `RoleService._update_job_description_with_history` (regenerate endpoint + enhancement JD `auto` + standalone-create JD `auto=True`), `_generate_matching_instructions` (auto, `commit=False` + snapshot + commit, rollback in the except), `generate_matching_instructions_draft(role_id, user_id)`, `regenerate_challenge(req, role_id, user_id)`, `resolve_ai_suggestions` called from `ProjectService.update_role` for USER saves before `_update` commits; `ProjectService.create_team_composition_v3` / `generate_role_v3` (moved out of the router), `generate_solution_v3` resolves the team before `repo.update`, `add_role(acting_user_id=)` resolves role_v3 in its own guarded transaction; case study repo writes gained `commit=`; `AssessmentService.record_ai_generation`, `create` / `update(user_id)` / `update_and_sync_interviews(user_id)` resolve.

## Decisions (user, 2026-10-27, all 4 recommendations)
- Applied content (JD, case studies, auto MI) resolves only on a CHANGE; an open applied snapshot = "kept" in the SQL (accepted by inaction). Implemented as one universal rule: every save resolves only when it changes the AI content.
- 2026-10-28 (Leo r1, user = PRD owner): `kept` folded into the PRD's four outcomes — open applied = derived `accepted`, `ignored` once the role / card is deleted; auto generations reported on their own rows; months not final (re-run the series whole); "latest vs all" = one open snapshot per part, so all open = each part's latest.
- Assessments: one row per call + target (assessment / skill / question / skill_questions / live_challenge); save resolves each open snapshot by its own items; supersede only same target + key; a full generation supersedes all.
- `model` = service name, `prompt_version` = endpoint version (AI services return no model).
- Scope = FE-used endpoints + role_v3; dead legacy endpoints out (regenerate_interview, regenerate_virtual_interview, v1 generate_solution, /roles/generate, interview / virtual interview updates).

## Gotchas
- FE `RoleOverlayContext.updateRoleData` PATCHes `...role` on assessment saves and `handleGenerateAssessment` auto-saves a full generation → the "only a change resolves" rule; full generations read as accepted (documented limit).
- FE single-question regenerate swaps the text in under the OLD question id → the snapshot's item key is the request's `question_id`.
- Enhancement-pipeline paths can run with no tenant in the request context (tests; `_generate_matching_instructions` direct calls) → `ai_suggestion.tenant_id` NULL → pass the role's tenant explicitly.
- `test_team_builder_industry.py` called the v3 router functions directly → now calls the service methods.
- Test data: a team preview's `role_id` becomes the created role's id → each preview needs fresh ids (module-level constants collided across tests); seniority must be a valid enum value ("Semi Senior", not "Mid Level"); generate_solution_v3 tests need `mocked_role_workflow_steps`.
- `tests/unit/export/test_export_rfq_logic.py` 4 failures are PRE-EXISTING on M2 head `ad72edfe` (verified in a detached baseline worktree; `case_study_instructions` MagicMock; CI ignores tests/unit/export).
- `-p no:logging` turns caplog tests into ERRORs; rerun them without it.
- Repo `save` is wrapped in `handle_commit_errors`: an RLS rejection surfaces as `RowLevelSecurityError` and rolls the WHOLE session back (savepoint gone), so RLS-probe tests assert the exception instead of a savepoint + ProgrammingError.
- FOR UPDATE + EvalPlanQual stops a double resolve, but two FIRST generations of a part at the same instant can both stay open (next save / generation resolves both) — documented limit.
- No pytest-xdist in the venv: full unit + multitenancy runs serially (~19 min).

## Evidence
- New tests: 22 role + 14 project + 4 multitenancy, all green; full local unit + multitenancy 6,792 passed (+ the 11 caplog tests green on rerun).
- Migration smoke (`.claude/worktrees/tmp/migration_smoke_m3.py` in the worktree, PYTHONPATH=<worktree>): create_all + stamp → down → up → down → up → re-run over existing table; 10 names == create_all; RLS on; canonical policy.
- The 5 SQL queries run on seeded data with the expected counts.

## Pending
- [ ] CI on `90d3e908`; Leo re-review (post the drafted reply first); Pedro review; merge.
- [ ] Tell Nico: metric 3 definition (derived accepted / ignored, auto rows, per tenant, run as postgres) + the SQL; series start at the M3 deploy.
- [ ] Answer Leo's out-of-scope: screening questions not in "assessments"? (confirm); ticket for missing `Protected(...)` on `team_composition_v3` / `role_v3` (pre-existing).
- [x] Self-review r1 blockers B1 + B2 + auto-snapshot requester → `a03e9684` (2026-10-28).
- [x] Self-review r1 nits: resolve race (FOR UPDATE) + typing done in `90d3e908`; explicit REGENERATE trigger left as is (trigger derived from prior snapshot).
- [x] PRD changelog rows + US 25639 wording (user asked, 2026-10-28; PRD rev 77, US rev 3).
- [ ] Measure payload size on dev after deploy (PRD risk).
- [ ] Tell Nico (SQL, series start at the M3 deploy) and Flor (full-assessment autosave limit).

## Related
- [[Customer metrics M2 - domain history (US 25638)]] · [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]] · [[Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)]]
