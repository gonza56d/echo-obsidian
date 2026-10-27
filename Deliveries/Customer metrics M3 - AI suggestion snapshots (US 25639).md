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

Customer metrics M3 (metric 3, "AI leverage"). Every AI generation for the five kinds (job description, matching instructions, assessment, team composition, case study) leaves an `ai_suggestion` snapshot of what the generator returned; a user's save that CHANGES the content resolves it (`accepted` / `edited` + `changed_fields`), a new generation of the same part resolves the previous one as `regenerated`. STACKED on [[Customer metrics M2 - domain history (US 25638)]].

## Azure / docs
- [US 25639](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25639) (In revision since 2026-10-27, PR linked as GitHub Pull Request). Parent [Feature 25635](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635); business contract [CR 25592](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592).
- Tech PRD: [Customer Metrics Event History](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj), section 6 Milestone 3, section 7 metric 3; rev 73 at the time (no M3 changelog rows yet).
- Nico's SQL: `docs/customer_metrics_m3_ai_suggestions.sql` (3a-3e; `-f`, docs/ is ignored).

## PRs
- [#2475](https://github.com/taller-projects/echo-backend/pull/2475) → `25638/domain-history` (STACKED on [#2469](https://github.com/taller-projects/echo-backend/pull/2469)), OPEN 2026-10-27, `9dddc18c` (branch `25639/ai-suggestion-snapshots` off `ad72edfe`, worktree `.claude/worktrees/25639-ai-suggestion`, upstream unset before the first push so a bare push could not land on M2). Retarget to dev after #2469 merges. Body draft in the worktree's `.claude/worktrees/tmp/pr_m3_body.md`.

## How
- **Migration `bmyaawpi69zn`** (parent `m8qz4tkv2wdc`): new table `ai_suggestion` (PRD columns + `updated_at`, FKs to user SET NULL on `requested_by_id` / `outcome_by_id`), indexes (tenant, kind, created_at) and (tenant, entity_type, entity_id, created_at), RLS = tenant expression (custom_fields form) for ALL, plain builds (new empty table), guarded re-run.
- **Module `app/modules/ai_suggestion/`**: `AiSuggestionService.record_generation` (supersede same target + key as `regenerated`; additive = no key; full assessment supersedes all; trigger manual / regenerate / auto; `tenant_id` override for runs with no request tenant), `supersede` (case study set), `resolve_field_save` (JD, MI, case study card), `resolve_assessment_save` (per-snapshot question items by id + live challenge), `resolve_team_save`, `resolve_role_spec_save`. Never commits; callers commit with their own write. `payload = {target, target_key, content}`. `model` = service (`team_builder` / `vectorizer` / `assessment_creator`), `prompt_version` = endpoint (`job_descriptions_v2`, ...).
- **Events**: `ai_suggestion_generated` / `ai_suggestion_resolved`, entity role / project / `case_study` (new UserEventEntityType), only when a user acted.
- **Hooks**: `RoleService._update_job_description_with_history` (regenerate endpoint + enhancement JD `auto` + standalone-create JD `auto=True`), `_generate_matching_instructions` (auto, `commit=False` + snapshot + commit, rollback in the except), `generate_matching_instructions_draft(role_id, user_id)`, `regenerate_challenge(req, role_id, user_id)`, `resolve_ai_suggestions` called from `ProjectService.update_role` for USER saves before `_update` commits; `ProjectService.create_team_composition_v3` / `generate_role_v3` (moved out of the router), `generate_solution_v3` resolves the team before `repo.update`, `add_role(acting_user_id=)` resolves role_v3 in its own guarded transaction; case study repo writes gained `commit=`; `AssessmentService.record_ai_generation`, `create` / `update(user_id)` / `update_and_sync_interviews(user_id)` resolve.

## Decisions (user, 2026-10-27, all 4 recommendations)
- Applied content (JD, case studies, auto MI) resolves only on a CHANGE; an open applied snapshot = "kept" in the SQL (accepted by inaction). Implemented as one universal rule: every save resolves only when it changes the AI content.
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

## Evidence
- New tests: 22 role + 14 project + 4 multitenancy, all green; full local unit + multitenancy 6,792 passed (+ the 11 caplog tests green on rerun).
- Migration smoke (`.claude/worktrees/tmp/migration_smoke_m3.py` in the worktree, PYTHONPATH=<worktree>): create_all + stamp → down → up → down → up → re-run over existing table; 10 names == create_all; RLS on; canonical policy.
- The 5 SQL queries run on seeded data with the expected counts.

## Pending
- [ ] CI on `9dddc18c`; Leo / Pedro review; merge after #2469, retarget to dev.
- [ ] PRD changelog rows (change-only resolution / kept vs ignored, assessment targets, payload shape, model / prompt_version meaning, role_v3 in scope, legacy out) — ask the user before editing the PRD.
- [ ] Measure payload size on dev after deploy (PRD risk).
- [ ] Tell Nico (SQL, series start at the M3 deploy) and Flor (full-assessment autosave limit).
- [ ] US 25639 description wording (decisions above).

## Related
- [[Customer metrics M2 - domain history (US 25638)]] · [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]] · [[Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)]]
