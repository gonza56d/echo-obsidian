---
type: delivery
status: in-progress
env: taller
delivered:
tags: [feature, matching, open-jobs, battle-tested]
prs: ["https://github.com/taller-projects/echo-backend/pull/1854"]
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23494"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23640"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23641"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23642"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23643"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23644"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23610"
prd: "https://app.notion.com/p/39eaedca11f081ff95f4c0b20b6b3aab"
---

# Open Jobs 1-5 matching (US 23640)

Bring Companies → Open Jobs → "Get Candidates" from the old raw-% cosine display to the same 1-5 LLM scoring that Roles→Candidates uses ("battle tested" matching). Keeps the `matched_talents` JSONB on `organization_job` (extended, **no migration**); a NEW **synchronous** Data-service endpoint scores 5 candidates per call. "Get More Candidates" +5 per click, hard cap 30. Taller only (Kforce has no Open Jobs UI). Status: **M1 (backend) implemented — PR [#1854](https://github.com/taller-projects/echo-backend/pull/1854) open → `dev` (merge gated on Data endpoint US 23610); M2 (FE) in progress.**

## Azure / docs

- Epic [#23300](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23300) "Battle Tested - Rollout" → Feature [#23494](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23494) (Sprint 41, assigned gonza)
- **US BE [#23640](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23640)** (gonza) → Tasks:
  - [#23641](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23641) M1.1 — `VectorizerService` sync client + mock + per-call timeout setting
  - [#23642](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23642) M1.2 — `match_talents` re-implementation + schema + `highest_match_score` 1-5 + tenant tagging
  - [#23643](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23643) M1.3 — error mapping, structured logs, unit + system tests
- **US FE [#23644](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23644)** (unassigned; echo-frontend; contract impact in its description)
- **US Data [#23610](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23610)** (rodrigo.ferrer, pre-existing) — the sync endpoint itself: receives open-job id + 5 talent ids, returns all 5 scored results in one JSON. **External blocker for merge; BE dev starts against the mock.**
- PRD: [Open Jobs Get Candidates — New Matching (1-5) — PRD Técnico](https://app.notion.com/p/39eaedca11f081ff95f4c0b20b6b3aab) — has "7. Plan de ejecución (2026-07-17)" with the decisions below; milestone sections carry these ticket links.

## PRs

- **BE M1**: [#1854](https://github.com/taller-projects/echo-backend/pull/1854) — branch `23640/open-jobs-matching-1-5` → `dev` (OPEN). Covers tasks 23641/23642/23643 in one PR. Developed vs the mock; **merge gated on Data endpoint US 23610**.
- FE M2 (US 23644): **frontend milestone — not backend scope**, needs an FE owner. Its PR must note BE M1 #1854 merges first.

## How (the shape of the implementation)

All in echo-backend, Taller (`dev`), no migration:

- `app/services/vectorizer_service.py` — `VectorizerService` is already the HTTP client to the Data service (`X-Echo-internal` auth, `/candidate_matching/*` endpoints used by Roles). Add a **sync** method (e.g. `evaluate_open_job_match(organization_job_id, talent_ids, tenant_id, industry, instructions?)`) → `{results: [{talent_id, matching_score 1-5, matching_status ok|error, matching_justification}]}`. Mirror it in `MockedVectorizerService` (test seam, registered in test DI).
- `app/services/external_api_service.py` — `READ_TIMEOUT=300` + retries on 502/503/504/408/429 is hardcoded in `post()`; unacceptable for a user-facing sync call. Allow per-call timeout override + new setting in `app/core/config.py` (align value with the P95 Data commits to).
- `app/modules/organization/job/service.py::match_talents` — keep: lazy vectorize + `repo.match_talents` cosine top-5 (already filters `Talent.tenant_id` + `is_available_for_matching`, excludes already-matched ids). Replace the `MatchingDiffService` skills-diff block with: sync Data call → append only `matching_status=ok` entries (each tagged with `tenant_id`, keeping `percentage`) → sort `matching_score` desc, `percentage` tiebreak, legacy score-less entries last (sort must handle `None`) → per-tenant cap 30 → persist under row lock.
- `app/modules/organization/job/schemas.py::MatchedCandidate` — add optional `matching_score` (int 1-5), `matching_status`, `matching_justification`; keep `percentage` + legacy `match_description`.
- `app/modules/organization/job/models.py:84` — `highest_match_score` column_property: `MAX((value->>'percentage')::float)` → `MAX((value->>'matching_score')::int)`. `filters.py` already does nulls-last on it.
- `app/modules/organization/job/routers.py::match_talents` — return the updated `OrganizationJobResponse` (today `-> None`); map external failure/timeout to 502/504 with `{detail}` shape.
- Logs: `open_job_match` (job_id, new, total, remaining-to-30) + `open_job_match_external_call` (latency, ok/error counts).
- Tests: unit (selection/append/cap/sort/parsing/tenant filter) + system testcontainers with mocked Data endpoint (match → 5 scored → Get More → cap 30 → partial failure → timeout). Reference enum: `MatchingResultStatus` in `app/modules/application/models.py:71` (ok/error — same values; define locally in job module rather than cross-module import).

## Decisions

- **Keep JSONB, no new entity** — agreed with Data 2026-07-15: sync endpoint returning everything at once removes the need for row-based entities/callbacks (PRD v1 alternative discarded).
- **Tenant isolation** (risk CONFIRMED in code 2026-07-17): `organization`/`organization_job` have NO `tenant_id` — global shared catalog (unique `linkedin_url`). Cross-tenant visibility of matches is pre-existing with the old %. Chosen fix: per-entry `tenant_id` tag + service-level read filtering + per-tenant cap/exclusion. Legacy untagged entries keep current behavior (no conversion, no backfill).
- Response shape: return updated job (sync flow, saves FE refetch). Cap reached → idempotent 200 no-op.
- Batching 5/+5/cap-30 (deliberately NOT aligned with Roles' 30/+10/100).
- Failed evaluations are NOT appended → naturally re-selectable by cosine on next "Get More" (retry for free).
- Feature is **not tenant-gated** — replaces the old % flow for all Taller tenants; Battle Tested is just the driving epic.

## Gotchas

- `matched_talents` mixes old-shape entries (`percentage` + `match_description`, no score) with new — sorting with `None` scores crashes naive `sorted(key=x["matching_score"])`; handle explicitly. FE also needs to render legacy entries sanely (flagged in US FE).
- `ExternalApiService` retries 502/503/504 — with a sync LLM call, retries × long timeout could hang the user's request for minutes; tighten both.
- Old flow's `MatchingDiffService.get_technologies` in `create()` stays (top_tech column is used elsewhere) — only the per-match skills-diff dies.
- Azure REST from non-interactive shells: org is `TallerInternTools`, project `Echo Core`; use the **already-exported** `$AZURE_DEVOPS_EXT_PAT` env var (the `sed` extraction from `~/.zshrc` grabbed 2 extra chars → 302/redirect; the env var, 84 chars, auth'd fine). `base64` on macOS wraps — pipe through `tr -d '\n'`.
- Local test gotcha: the TestClient success-path tests in `test_organization_jobs.py` (get list/single, bulk-patch, cluster-vector) **404 locally** — pre-existing (verified: identical failing set on clean `origin/dev` baseline), green in CI. Do NOT read them as an M1 regression. M1 logic is unit-tested via `_build_service` (MagicMock, no TestClient) + system tests (real Postgres, no TestClient).
- **CI break + fix (commit `6c6b2fcc`):** adding `ats_note_service` to `OrganizationJobService.__init__` broke `test_matching_diff_industry.py::test_job_create_resolves_industry_once_for_both_calls`, which *also* constructs the service directly (missed it — only checked `test_organization_jobs.py::_build_service`). Lesson: `rg "OrganizationJobService\("  tests/` (there are **2** call sites) before changing the ctor. CI (tests/unit) had **only that 1 failure**; the ~30 local `assert 404==200` failures (application_comments/owner_snapshot/process_status_filter) are the known local-only TestClient issue → green in CI.
- M1 unit tests reused the existing `_build_service` helper (constructor DI, not `__new__`), so no `__new__`-fixture breakage. `match_talents` now returns `OrganizationJobResponse` → the pre-existing `test_match_talents_vectorizes_with_tenant_industry` needed a complete job stub (switched to `_job_ns`).

## Contract update — 2026-07-17 (2nd commit on PR #1854)

Team decision: **send the full open job + curated talent data inline** to Data (not just `organization_job_id` + `talent_ids`), so Data **never calls back to Echo** (no ping-pong: no JD lookup, no `GET /talents`). See PRD **section 8** for the full request/response.

- Path finalized: `OPEN_JOB_MATCH_ENDPOINT = /candidate_matching/evaluate_open_job_match` (was placeholder `/candidate_matching/evaluate_open_job`).
- Request: `{ organization_job_id (tracking), open_job:{id,title,description,location,work_model,employment_type,posted_at,is_tech,top_tech,url,apply_url,source}, talents:[{talent_id,first_name,last_name,title,summary,seniority,country_code,skills[core+additional],experiences[{title,company,description,start_date,end_date}]}], tenant_id?, industry?, instructions? }`.
- Talents = **curated matching fields** (chosen over full TalentResponse) → no email/phone/rates/ATS ids to Data. Built from the cosine-selected `Talent` ORM; repo `match_talents` now `joinedload(experiences).joinedload(organization)` to get company without N+1.
- **Notes added (3rd commit `b7b9b6ef`):** each talent also carries `notes` (internal Echo recruiter notes: `content`, `created_at`) and `ats_notes` (`content`, `category` NOTE|STATE_CHANGE, `commented_at`, `commenter_name`) — data Data would otherwise fetch from Echo. `notes` eager-loaded via `selectinload(Talent.notes)` (selectin, NOT joined — a 2nd one-to-many joined onto experiences = cartesian). `ats_notes` fetched in **1 batched query via injected `ATSNoteService.get_all(ATSNoteFilter(talent_id__in=...))`** (layering-clean; never queries the foreign `ATSNote` model directly), grouped by talent_id. New schemas `OpenJobMatchNote`/`OpenJobMatchAtsNote`. Weight OK: bounded to 5 talents/click.
- **Email added (4th commit `0d7a2f15`):** talent `email` now in the payload — **reverses the earlier "no email/PII" stance** (per explicit request); phone/rates/ATS ids still excluded. Direct `Talent.email` column, no extra load.
- New schemas in job `schemas.py`: `OpenJobMatchExperience`, `OpenJobMatchTalent`, `OpenJobMatchJobPayload` (OrmBaseModel, `model_validate(job)`). Service builds them → `model_dump(mode="json")` → passes dicts to `VectorizerService.evaluate_open_job_match(organization_job_id, open_job, talents, tenant_id, industry, instructions)` (vectorizer stays decoupled from job schemas).
- Response gained `error_message` (per-talent; backend logs only, FE never shows). Data status codes: 200 (ok, incl. per-talent errors) / 422 (validation) / **503** systemic (OpenAI down) → Echo maps to **502** + toast / timeout → **504**.

## As built (M1, PR #1854)

- Settings in `CommonSettings` (next to Roles `MATCH_*`): `OPEN_JOB_MATCH_BATCH_SIZE=5`, `OPEN_JOB_MATCH_MAX_CANDIDATES=30`, `OPEN_JOB_MATCH_READ_TIMEOUT=60` (placeholder, align w/ Data P95), `OPEN_JOB_MATCH_ENDPOINT="/candidate_matching/evaluate_open_job_match"`.
- `ExternalApiService.__send_request` gained per-call `read_timeout` + `max_retries` overrides; `requests.Timeout` now maps to **504**. `evaluate_open_job_match` calls with `read_timeout=setting, max_retries=0`.
- `highest_match_score` column_property → `MAX((value->>'matching_score')::int)` **scoped by `current_setting('request.tenant_id', true)`** (+ legacy null-tenant entries). GUC confirmed set per request in `app/database/base.py` after_begin. **Decision confirmed: tenant-aware SQL** (not plain MAX) so the "Highest Match" column AND `order_by` stay tenant-correct.
- Tenant read-filtering done via dedicated **`get_job_for_tenant` / `get_jobs_for_tenant`** service methods used only by the **public** router; internal routers (`internal_routers.py`, API-key, may lack tenant ctx) left unfiltered on purpose. `tenant_id` is stored inside each JSONB entry but is **absent from `MatchedCandidate`** so it never serializes out.
- Concurrency: `repo.get_matched_talents_for_update` (SELECT … FOR UPDATE) + RMW in `_persist_new_matches`; cap-overflow truncation sorts by score first (keeps the best), cap-hit commits to release the lock and returns a no-op.

## Pending

- [x] M1 BE implementation (tasks 23641/42/43) → single PR **[#1854](https://github.com/taller-projects/echo-backend/pull/1854)** → `dev` (open).
- [ ] Data endpoint (US [#23610](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23610)): final path + staging availability; then validate real contract end-to-end (PRD "Verificación" §4) + set `OPEN_JOB_MATCH_ENDPOINT`/`READ_TIMEOUT`.
- [ ] Latency target (P95) to agree with Data → drives the timeout setting value.
- [ ] Merge #1854 (blocked on US 23610).
- [ ] M2 FE (US 23644) — frontend milestone, needs FE owner (**not backend scope**); PR should note M1 #1854 must merge first.
- [ ] QA gating on full feature (M1+M2), 4-6h per PRD.
- [ ] Tenant-isolation decision (per-entry tag + tenant-aware SQL) — confirm with Pedro at review time.

## Related

- [[Industry-agnostic Echo (PRD 398aedca)]] — same `candidate_matching` external service; industry param plumbing.
- Battle Tested rollout epic context: see memory note `project_battle_tested_client`.
