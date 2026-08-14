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

- [#2079](https://github.com/taller-projects/echo-backend/pull/2079) → dev — **OPEN, in review** (2026-08-14, single commit `3ed6fe97`, branch `24316/reuse_jd_v2_skills`)

## How

- `app/modules/role/solution_service.py`: new `JobDescriptionResult` (`job_description`, `skills_required`, `skills_nice_to_have`). `ProjectSolutionService.job_description()` prefers item-level `required`/`nice_to_have` from `job_descriptions[0]`, falls back to top-level `skills_required`/`skills_nice_to_have`, defaults to `[]` — so a TB response without skills degrades to the old behavior. `MockedProjectSolutionService.job_description` mirrors the happy path (`["Mocked skill"]`).
- `app/modules/role/service.py` (`run_enhancement_pipeline`): `has_skills` captured **before** `release_db_session()` (role is detached after); the JD stage writes skills in the same `RoleUpdate` **only when the role has none and v2 brought some** — the same guard as `_generate_skills`, so team-composition/user-entered skills are never clobbered. New struct event **`enhance.skills_from_jd`** (role_id, tenant_id, required_count, nice_to_have_count) when skills come from v2.
- `_generate_skills` untouched: guard makes it a free no-op when v2 populated; still calls `/get_technologies` / `/get_skills` (industry-routed) when v2 brought nothing. `regenerate_job_description` adapted (`.job_description`, JD-only).
- Tests (+7): pipeline happy path (skills persisted, `get_technologies_input` **never called** — the "una sola llamada" AC), fallback when v2 empty, existing-skills guard, 3 client parsing tests (in `test_solution_service_tb_errors.py`), `enhance.skills_from_jd` log-contract test (in `TestEnhanceLogContract`).

## Decisions

- **Guarded populate, not unconditional**: v2 skills only land when both `skills_required` and `skills_nice_to_have` are empty — mirrors `_generate_skills`; roles created from team composition already carry skills and must keep them.
- **Skip the write entirely when v2 brings nothing** (instead of writing `[]`): keeps NULL/[] semantics untouched and leaves the fallback guard falsy either way.
- **Item-level fields preferred over top-level**: item is the per-JD extraction; top-level aggregate is the compat fallback.
- **Kforce: not ported** — ticket is Taller-only; the enhance pipeline diverged heavily (queue v2 is Taller-only).

## Gotchas

- **`_run_enhance_role` (existing test helper in `test_roles.py`) patches WorkerGroup tasks with plain MagicMocks — which silently CRASH the pipeline's `match_and_screening` stage** (`worker_group.py` prints `fn.__name__`; MagicMock raises AttributeError) → role lands `failed`. Existing tests pass only because they never assert the terminal stage. Any test asserting `ENHANCED` must patch with named functions (`new=`), like the pool-timeout probe test warns. My `_run_enhance_role_with_live_skills` does this.
- The probe test (`test_enhance_pipeline_releases_transactions...`) now feeds `JobDescriptionResult` **without** skills deliberately, so its `technologies` probe (the fallback) still fires.
- `TestEnhanceLogContract._pipeline_service`'s SimpleNamespace role needed `skills_required=[]`/`skills_nice_to_have=[]` — the pipeline now reads them pre-release.
- Full-suite verification: 30 local failures on the branch = **byte-identical** to a pristine `origin/dev` clone run (known TestClient-404 local class); baseline via `git clone` of the local repo into scratchpad + checkout `607a61f3` (no git-write on the main repo).

## Pending

- PR #2079 review + merge → dev.
- **Dev parity check before merge (ticket AC)**: enhance a few roles in dev — ideally one non-tech tenant — and compare v2-sourced skills vs the old extraction; grep `enhance.skills_from_jd` in Grafana/Loki. If non-tech parity is bad, the guard+fallback already degrades gracefully (option: skip v2 skills for non-default industries).
- qa/main promotion after dev QA.

## Related

- [[Enhancement queue v2 Postgres-backed (PRD 7444)]] — the pipeline this optimizes
- [[Role enhance pool timeout unhandled (Bug 23808)]] — source of the release-before-external-call pattern and the fn.__name__ probe-test gotcha
- [[Map - Observability & Reliability]]
