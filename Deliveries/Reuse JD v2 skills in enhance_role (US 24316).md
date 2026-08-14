---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, roles, enhancement-pipeline, team-builder, performance]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2079"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24316"
prd: ""
---

# Reuse JD v2 skills in enhance_role (US 24316)

Pedro's US: `enhance_role` made **two sequential Team Builder calls** in the critical path — `POST /job_descriptions/job_descriptions_v2` (JD) then `POST /matching_diff/get_technologies` / `/get_skills` (skills) — but the v2 response **already carries the skills** (item-level `required`/`nice_to_have`, top-level `skills_required`/`skills_nice_to_have`), so the second call was redundant. Shipped: `job_description()` returns a new `JobDescriptionResult` model instead of discarding everything but the JD string, the pipeline's *job_description* stage persists JD + skills in its single existing `repo.update`, and `_generate_skills` stays as an untouched idempotent fallback. One fewer external round-trip per role on the enhance latency path.

## Azure / docs

- [US 24316](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24316) — In development, assigned to me; PR linked via comment. The ticket body is effectively a mini-PRD (Pedro verified the TB `JobDescriptionResultV2` field names: `required`/`nice_to_have`/`technologies`, NOT `tech_required`).

## PRs

- [#2079](https://github.com/taller-projects/echo-backend/pull/2079) → dev — **OPEN, in review** (branch `24316/reuse_jd_v2_skills`; `3ed6fe97` feature + `f6d140c8` review-round-1 fixes & tech-only gate, 2026-08-14)

## How

- `app/modules/role/solution_service.py`: new `JobDescriptionResult` (`job_description`, `skills_required`, `skills_nice_to_have`). `ProjectSolutionService.job_description()` prefers item-level `required`/`nice_to_have` from `job_descriptions[0]`, falls back to top-level `skills_required`/`skills_nice_to_have`, defaults to `[]` — so a TB response without skills degrades to the old behavior. `MockedProjectSolutionService.job_description` mirrors the happy path (`["Mocked skill"]`).
- `app/modules/role/service.py` (`run_enhancement_pipeline`): the JD stage writes skills in the same `RoleUpdate` **only for tech tenants** (`industry == DEFAULT_INDUSTRY` gate, from the parity check) **and only when the role has none and v2 brought some**. The never-overwrite guard does a **fresh `get_by_id` AFTER the slow JD call** (not a pipeline-start snapshot), so skills entered mid-call win over v2. New struct event **`enhance.skills_from_jd`** (role_id, tenant_id, required_count, nice_to_have_count) when skills come from v2.
- `_clean_skills()` in `solution_service.py`: malformed TB skill arrays (non-list, non-string items) degrade to `[]` instead of raising — a bad skills payload must never cost the already-generated JD (skills have the `_generate_skills` fallback; the JD does not).
- `_generate_skills` untouched: guard makes it a free no-op when v2 populated; still calls `/get_technologies` / `/get_skills` (industry-routed) when v2 brought nothing. `regenerate_job_description` adapted (`.job_description`, JD-only).
- Tests (+7): pipeline happy path (skills persisted, `get_technologies_input` **never called** — the "una sola llamada" AC), fallback when v2 empty, existing-skills guard, 3 client parsing tests (in `test_solution_service_tb_errors.py`), `enhance.skills_from_jd` log-contract test (in `TestEnhanceLogContract`).

## Dev parity check (2026-08-14 — the merge gate, DONE)

Pre-merge (branch not deployed), so instead of Loki: **replayed 5 dev roles against the real dev TB locally** with the branch's own client code — v2 JD+skills first, then the old extraction fed the *same* v2 JD, industry-routed. Script + full JSON in the session scratchpad; results table in the PR description.

- **Tech (Taller ×3): Jaccard 1.0** — identical skill sets. Reuse safe.
- **Generic (Coca-Cola ×2): Jaccard 0.05 / 0.0** — v2 stays IT-shaped (`Python`, `PostgreSQL`) vs `/get_skills`' industry-agnostic 21/16 skills (`Test Planning`, `Project Coordination`, …). NOT equivalent → applied the ticket's contingency: **reuse gated to tech tenants**, non-tech unchanged.

## Decisions

- **Guarded populate, not unconditional**: v2 skills only land when both `skills_required` and `skills_nice_to_have` are empty — mirrors `_generate_skills`; roles created from team composition already carry skills and must keep them.
- **Skip the write entirely when v2 brings nothing** (instead of writing `[]`): keeps NULL/[] semantics untouched and leaves the fallback guard falsy either way.
- **Item-level fields preferred over top-level**: item is the per-JD extraction; top-level aggregate is the compat fallback. Coalescing is falsy-based (explicit `[]` at item level falls through to top-level) and per-field (mixed provenance possible) — safe because callers always send a single role; pinned with tests + comment.
- **Tech-only reuse gate** (round-1 fix): parity check proved v2 non-equivalent for non-tech; gate lives in the pipeline stage (`industry == DEFAULT_INDUSTRY`), not in the client — `job_description()` stays a faithful parser.
- **Fresh-read guard** (round-1 fix): pipeline-start snapshot would let v2 overwrite skills a user entered during the JD call; on old dev the user won that race (via `_generate_skills`' re-read), so the losing side must not flip. Pinned with `test_enhance_role_respects_skills_entered_during_jd_call`.
- **Kforce: not ported** — ticket is Taller-only; the enhance pipeline diverged heavily (queue v2 is Taller-only).

## Gotchas

- **`_run_enhance_role` (existing test helper in `test_roles.py`) patches WorkerGroup tasks with plain MagicMocks — which silently CRASH the pipeline's `match_and_screening` stage** (`worker_group.py` prints `fn.__name__`; MagicMock raises AttributeError) → role lands `failed`. Existing tests pass only because they never assert the terminal stage. Any test asserting `ENHANCED` must patch with named functions (`new=`), like the pool-timeout probe test warns. My `_run_enhance_role_with_live_skills` does this.
- The probe test (`test_enhance_pipeline_releases_transactions...`) now feeds `JobDescriptionResult` **without** skills deliberately, so its `technologies` probe (the fallback) still fires.
- `TestEnhanceLogContract._pipeline_service`'s SimpleNamespace role needs `skills_required=[]`/`skills_nice_to_have=[]`, and **`get_industry.return_value = "tech"`** — a bare MagicMock industry fails the tech-only gate and silently drops the `enhance.skills_from_jd` event.
- **`mocked_tenant` is module-scoped**: the non-tech gate test mutates `matching_instructions_industry` and must restore it in `finally`, or every later test in `test_roles.py` runs generic.
- `Tenant.industry` coerces unknown/legacy column values to `tech` — polyfactory's random string on `matching_instructions_industry` therefore resolves tech (tests deterministic without pinning).
- Parity script gotcha: run with `PYTHONPATH=<repo>` (script lives in scratchpad → `sys.path[0]` is wrong) and strip the psql `\timing` footer before `json.load`.
- Full-suite verification: 30 local failures on the branch = **byte-identical** to a pristine `origin/dev` clone run (known TestClient-404 local class); baseline via `git clone` of the local repo into scratchpad + checkout `607a61f3` (no git-write on the main repo).

## Pending

- PR #2079 review (Pedro) + merge → dev. Parity gate CLEARED (see section above); round-1 rubric self-review findings all addressed in `f6d140c8`.
- Post-merge sanity in dev: grep `enhance.skills_from_jd` in Loki — should appear for tech tenants only.
- qa/main promotion after dev QA.

## Related

- [[Enhancement queue v2 Postgres-backed (PRD 7444)]] — the pipeline this optimizes
- [[Role enhance pool timeout unhandled (Bug 23808)]] — source of the release-before-external-call pattern and the fn.__name__ probe-test gotcha
- [[Map - Observability & Reliability]]
