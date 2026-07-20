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

Bring Companies → Open Jobs → "Get Candidates" from the old raw-% cosine display to the same 1-5 LLM scoring that Roles→Candidates uses ("battle tested" matching). Keeps the `matched_talents` JSONB on `organization_job` (extended; schema unchanged, but a **data-only migration wipes legacy entries at rollout** — see 2026-07-20 follow-up); a NEW **synchronous** Data-service endpoint scores 5 candidates per call. "Get More Candidates" +5 per click, hard cap 30. Taller only (Kforce has no Open Jobs UI). Status: **M1 (backend) implemented + review rounds 1 (`614aa7ab`) & 2 (`e2171b0e`, + CI-red fix `6e7de88b`) fixed + round-2 follow-up (`be34ce85` stranded tests + `678b8225` legacy-wipe migration) — PR [#1854](https://github.com/taller-projects/echo-backend/pull/1854) open → `dev` (merge gated on Data endpoint US 23610); M2 (FE) in progress.**

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
- Request: `{ organization_job_id (tracking), open_job:{id,title,description,location,work_model,employment_type,posted_at,is_tech,top_tech,url,apply_url,source}, talents:[{talent_id,first_name,last_name,title,summary,seniority,country_code,core_skills[],additional_skills[],experiences[{title,company,description,start_date,end_date}]}], tenant_id?, industry?, instructions? }`. (`core_skills`/`additional_skills` were split from a single merged `skills` list in review round 1 — see below.)
- Talents = **curated matching fields** (chosen over full TalentResponse) → no email/phone/rates/ATS ids to Data. Built from the cosine-selected `Talent` ORM; repo `match_talents` now `joinedload(experiences).joinedload(organization)` to get company without N+1.
- **Notes added (3rd commit `b7b9b6ef`):** each talent also carries `notes` (internal Echo recruiter notes: `content`, `created_at`) and `ats_notes` (`content`, `category` NOTE|STATE_CHANGE, `commented_at`, `commenter_name`) — data Data would otherwise fetch from Echo. `notes` eager-loaded via `selectinload(Talent.notes)` (selectin, NOT joined — a 2nd one-to-many joined onto experiences = cartesian). `ats_notes` fetched in **1 batched query via injected `ATSNoteService.get_all(ATSNoteFilter(talent_id__in=...))`** (layering-clean; never queries the foreign `ATSNote` model directly), grouped by talent_id. New schemas `OpenJobMatchNote`/`OpenJobMatchAtsNote`. Weight OK: bounded to 5 talents/click.
- **Email added (4th commit `0d7a2f15`):** talent `email` now in the payload — **reverses the earlier "no email/PII" stance** (per explicit request); phone/rates/ATS ids still excluded. Direct `Talent.email` column, no extra load.
- New schemas in job `schemas.py`: `OpenJobMatchExperience`, `OpenJobMatchTalent`, `OpenJobMatchJobPayload` (OrmBaseModel, `model_validate(job)`). Service builds them → `model_dump(mode="json")` → passes dicts to `VectorizerService.evaluate_open_job_match(organization_job_id, open_job, talents, tenant_id, industry, instructions)` (vectorizer stays decoupled from job schemas).
- Response gained `error_message` (per-talent; backend logs only, FE never shows). Data status codes: 200 (ok, incl. per-talent errors) / 422 (validation) / **503** systemic (OpenAI down) → Echo maps to **502** + toast / timeout → **504**.

## As built (M1, PR #1854)

- Settings in `CommonSettings` (next to Roles `MATCH_*`): `OPEN_JOB_MATCH_BATCH_SIZE=5`, `OPEN_JOB_MATCH_MAX_CANDIDATES=30`, `OPEN_JOB_MATCH_READ_TIMEOUT=60` (placeholder, align w/ Data P95), `OPEN_JOB_MATCH_ENDPOINT="/candidate_matching/evaluate_open_job_match"`.
- `ExternalApiService.__send_request` gained per-call `read_timeout` + `max_retries` overrides; `requests.Timeout` now maps to **504**. `evaluate_open_job_match` calls with `read_timeout=setting, max_retries=0`.
- `highest_match_score` column_property → `MAX((value->>'matching_score')::int)` **scoped by `current_setting('request.tenant_id', true)`** (+ legacy null-tenant entries). GUC confirmed set per request in `app/database/base.py` after_begin. **Decision confirmed: tenant-aware SQL** (not plain MAX) so the "Highest Match" column AND `order_by` stay tenant-correct.
- Tenant read-filtering done via dedicated **`get_job_for_tenant` / `get_jobs_for_tenant`** service methods. Initially wired to the **public** router only; the deprecated **internal** GET routes were left unfiltered — **corrected in review round 1** (see below): they now filter too. `tenant_id` is stored inside each JSONB entry but is **absent from `MatchedCandidate`** so it never serializes out.
- Concurrency: `repo.get_matched_talents_for_update` (SELECT … FOR UPDATE) + RMW in `_persist_new_matches`; cap-overflow truncation sorts by score first (keeps the best), cap-hit commits to release the lock and returns a no-op.

## Review round 1 fixes — 2026-07-17 (commit `614aa7ab`)

`/pr-review` (3 parallel reviewers: architecture, tests-security, prd) on #1854. PRD compliance 15/16, CI green, no scope creep. Findings addressed in one commit:

- **BLOCKER — internal-route cross-tenant leak (tests-security T6).** The deprecated internal GET routes `/internal/organizations/{org}/jobs` and `/{job_id}` returned `matched_talents` straight from `get_by_id`/`get_all` with **no tenant filter** → an `X-Echo-Api-Key` for tenant A could read tenant B's matches (names, 1-5 scores, LLM justifications) on the shared, tenant-less `organization_job` row. Pre-existing for the old %, but the PR's whole point is isolation and it left the internal surface open (and the new data is richer). **Fix:** both routes now go through `get_jobs_for_tenant`/`get_job_for_tenant` using a new `_api_key_tenant_id` dep = `get_request_context().get_tenant_id(required=False)` (set by `check_api_key_auth`). `None` tenant → legacy-untagged-only, a safe default. Reverses the earlier "internal left unfiltered on purpose" decision. Non-deprecated `get_all_company_jobs` was already safe (returns `IDOrganizationJobResponse`, no `matched_talents`). Create routes return freshly-created jobs (`matched_talents=[]`) → no leak, untouched.
- **NIT — malformed Data 200 body → 500 (tests-security T3/T7).** `OpenJobMatchResponse.model_validate(raw)` was outside the try/except, so a 200 with an off-contract body raised `pydantic.ValidationError` → generic 500. **Fix:** wrapped it; a `ValidationError` now maps to **502** like the other Data failures.
- **NIT — encapsulation (architecture A1/A3).** No-op branch called `self.repo.db_session.commit()` to release the row lock. **Fix:** added `OrganizationJobRepository.commit()`; service calls `self.repo.commit()`.
- **NIT — typing (architecture A14).** Widened `get_job_for_tenant`/`get_jobs_for_tenant`/`_tenant_filtered_response`/`_visible_entries` `tenant_id` to `uuid.UUID | None` (internal path can pass `None`); tightened `talent_by_id: dict[uuid.UUID, tuple]` and `_get_ats_notes_by_talent -> dict[uuid.UUID, list]`.
- **Contract change (user request, coordinated with Data US 23610): split talent `skills`.** The talent payload now sends **separate `core_skills` + `additional_skills` lists** instead of one merged `skills` list. `OpenJobMatchTalent` gains both fields; `_build_talent_payload` sets each from `Talent.core_skills`/`Talent.additional_skills`. **PRD §8 request example + this note (line above) updated to match** so Data implements the split shape.
- Tests: added `test_score_candidates_maps_malformed_response_to_502`; updated skills-split assertions (`core_skills`/`additional_skills`) and `repo.commit` assertion. All 14 open-job matching unit tests pass; lint clean. The ~10 `assert 404` TestClient failures are the known local-only issue (verified identical failing set on clean baseline — no regressions).
- **Deferred to round 2 (all now DONE in `e2171b0e`):** the PRD §5 full-flow system test, the `ExternalApiService` DEBUG-log PII leak, plus the round-2 blockers below. The smart-search view `smart_search_companies_open_jobs.sql` `matched_talents` exposure stays untouched (still no downstream consumer).

## Review round 2 fixes — 2026-07-17 (commit `e2171b0e`)

Pedro's review (CHANGES REQUESTED: 4 blockers + nits + 4 questions). All blockers + nits in one commit `e2171b0e`. Verified: 16 new tests green + all pre-existing service-level unit tests green; **4/4 system tests green vs real Postgres**; lint clean.

**Blockers**

- **B1 — vectorize leg violated the error contract + timeout.** The lazy `if job.vector is None` re-vectorize ran with the shared 300s×3 default and its `ExternalApiException` escaped the 502/504 normalization (raw 500/503 to the client — exactly what Task 23641 was meant to prevent). Extracted `OrganizationJobService._ensure_vectorized(job, industry)`: calls `vectorize_job_description(..., read_timeout=OPEN_JOB_MATCH_READ_TIMEOUT, max_retries=0)` inside try/except → shared `_external_error(exc)` helper (504 on timeout, else 502). Threaded `read_timeout`/`max_retries` passthrough into `VectorizerService.vectorize_job_description` (+ the mock) — background ingest callers keep the 300s default (params default `None`). **422 decision: implemented, not declared vestigial** — new `OpenJobNotVectorizableError` (group 1, 422) when a job has neither title nor description (the only genuinely non-vectorizable case; title is normally non-null so it's rare, but it gives the documented contract a real code path).
- **B2 — Data-response validation.** (a) intra-batch dedup by `talent_id` when building `ok_results` (a repeated `ok` would double-append + double-consume the per-tenant cap; `_persist_new_matches` only dedups vs *stored*). (b) `OpenJobMatchResult` `model_validator` rejects `ok` with a null score → `OpenJobMatchResponse.model_validate` raises → existing malformed-200→502 path. Chose Pedro's "whole batch → 502" over partial-trust (a contract-violating body isn't partially trusted).
- **B3 — PII in DEBUG logs.** `ExternalApiService.__send_request` gained a per-call `log_body: bool = True` guarding both the request- and response-body `logger.debug`; `evaluate_open_job_match` sends `log_body=False`. Default behavior unchanged for every other consumer.
- **B4 — full-flow system test.** Added match → 5 scored (1-5) → Get More → grow to cap → idempotent no-op, + not-found. **Driven through the service, NOT the HTTP client:** the local TestClient 404s all `/company/jobs/*` success paths (documented quirk — green in CI) AND system tests never run in CI, so a `client`-based test would be red locally and unverifiable anywhere. Service-level exercises the real gap the round-1 note flagged (real cosine selection, `SELECT … FOR UPDATE` row-locked RMW, per-tenant cap, JSONB tenant tagging) against real Postgres. Small batch(5)/cap(6) + 8 seeded matchable talents avoid seeding 30.

**Nits**

- `OrganizationJobResponse.highest_match_score` `float`→`int` (matches `Mapped[int|None]`; aligns before FE M2 consumes it — was serializing `5.0`).
- `matched_talents` moved OUT of `OrganizationJobBase` INTO `OrganizationJobResponse` only → the create/update **write** schemas no longer accept it (closes the "internal caller overwrites/injects tagged entries on the shared row" hole; verified no code/test writes it via the schemas — ingest uses a raw dict). Read shape unchanged.
- Type hints on `_ensure_vectorized`/`_score_candidates`/`_build_talent_payload`/`_persist_new_matches`/`_tenant_filtered_response` (foreign ORM objects typed `Any` to avoid importing `Talent`/`ATSNote` into the service). Stale "no email" docstring (`OpenJobMatchTalent`) + `test_build_talent_payload` comment corrected.
- Extra unit coverage: new `tests/unit/test_external_api_service.py` (Timeout→504, `max_retries=0` = one attempt, `read_timeout` override reaches `requests`, `log_body` suppresses/logs bodies); Page-branch of `get_jobs_for_tenant`; unknown-`talent_id` drop.

**Questions (Q1/Q2 answers below were SUPERSEDED on 2026-07-20 — see next section)**

1. ~~Legacy entries consuming a tenant's cap-30 — intended per PRD §7~~ → **superseded: legacy entries are wiped at rollout** (migration `ehjnwsqitqve`), dissolving the starvation edge entirely.
2. Smart-search view exposing raw `matched_talents` — pre-existing, no consumer in echo-backend; **Data team being notified** (they query the view directly) — see next section.
3. `Timeout`→504 global to every consumer — **yes** (added in the original PR, not round 2); additive. Data 422 (= an Echo bug) → generic 502 toast is intended.
4. Repo `Talent`/`Experience` coupling — the match query is the **sanctioned exception** (vector-distance JOIN + payload build).

**Gotchas**

- Adding `read_timeout`/`max_retries` to `vectorize_job_description` broke `test_vectorize_job_description_cache_does_not_collide_across_industries` (its `fake_post(endpoint, json)` mock) → added `**kwargs`. Two `fake_post` defs in that file; only the job_description one needed it (`vectorize_text` unchanged).
- **CI RED after `e2171b0e` — fixed in `6e7de88b` (`default=list`).** I initially (wrongly) called the 3 `test_get_organization_jobs` errors "pre-existing" because models.py was untouched and the Response fields existed at HEAD. **That was wrong — it was a round-2 regression**, and the *local* TestClient-404 quirk masked it (the route 404s before the query runs), so locally it looked like the same 404 family. CI (routes resolve) exposed the truth: **8 failed + 3 errors, all in `test_organization_jobs`, all `DataError: cannot extract elements from a scalar` / `ResponseValidationError`**. Root cause: stripping `matched_talents` from the write schemas (nit 4) meant `OrganizationJobCreate` no longer carries it, so `create_entity` **and the real `create()` path** fall back to the model column default — which was the **string** `default="[]"`, JSON-serialized to a JSONB *scalar string* `"[]"`, breaking `jsonb_array_elements` in `highest_match_score` (would have 500'd every job read/list in prod, not just tests). **Fix:** `matched_talents` model default `"[]"` → `list` (proper JSONB array `[]`) + a service-level regression guard (`test_job_with_default_matched_talents_is_readable`) that reproduces the read path locally (TestClient tests can't — they 404). `top_tech` has the identical latent `default="[]"` but is still on the write schema so it's always provided — left as-is (unexercised); worth fixing if it's ever stripped.
- **Lesson:** "CI green before, red after my push" is the authoritative baseline — never label a failure pre-existing off local results when a known local quirk (TestClient-404) can mask the real CI error. Verify the actual code path (here: service-level read) locally, not the TestClient result.

## Round 2 follow-up — 2026-07-20 (commits `be34ce85`, `678b8225`)

Session verified round 2 against the actual PR head (not the commit messages) and found one claim false + settled Pedro's Q1/Q2:

- **Stranded test file (gotcha!):** `tests/unit/test_external_api_service.py` (5 transport tests: Timeout→504, `max_retries=0` = one attempt, `read_timeout` override, `log_body` on/off) was **claimed in `e2171b0e`'s message but left untracked** — never committed, never pushed. Committed now as `be34ce85`. **Lesson: after committing, check `git status` for strays — commit-message claims ≠ repo state.**
- **Q1 decision change — wipe legacy entries (migration `ehjnwsqitqve`, commit `678b8225`).** The starvation edge (a job with ≥30 legacy untagged entries consumes every tenant's cap forever) is **new to this PR** (pre-PR there was no cap at all — clicks appended forever). Product decision: wipe legacy at rollout; lists rebuild in the new format on next click. Data-only migration `2026_07_20_1200-ehjnwsqitqve_wipe_legacy_matched_talents.py` (revises `51r81g9s8arp`): normalizes non-array values, then strips only entries **without** a `tenant_id` key → **idempotent, can never touch tagged entries**, safe to re-run by hand to mop up strays from the migration→rollout window (pipeline runs `apply_migrations.sh` in `RunScripts` BEFORE the ArgoCD stage, so old pods serve for a few minutes post-wipe). Downgrade = documented no-op. **Supersedes PRD "no migration" scope note + "legacy keeps current behavior" decision.** Verified read-only vs dev DB: 288k jobs, 0 non-array rows, only 100 jobs with entries, 0 with ≥30 legacy; post-wipe expression returns `[]` for legacy-only rows.
- **Q2 — Data-team notification.** The view `view_smart_search_companies_open_jobs` exposes raw `matched_talents` (now with `tenant_id` tags + LLM justifications) and is consumed by the Data side directly in Postgres. Spanish notification message drafted for gonza to send: new entry shape, legacy wipe at deploy, tenant-filter warning for any tenant-facing surface, and 2 questions (do they use `open_job_matched_talents`? if not → follow-up to drop it from the view; careful: view column drops need `DROP VIEW`+`CREATE`, see the `_view_is_repo_shaped` incident).
- **Q4 — layering exception DISSOLVED, not consecrated (commit `4b9ea905`).** Key insight: `OrganizationJobRepository.match_talents` joined `organization_job` **solely to reference `job.vector`**, but the service already holds the job row (`get_by_id` + `_ensure_vectorized` guarantee a vector) — so passing the vector *value* kills the entire cross-module coupling. Query moved to `TalentRepository.get_top_matches(target_vector, tenant_id, exclude_talent_ids, limit)` + `TalentService.get_top_matches` façade; job repo dropped `_talent_model`/`_experience_model` lazy-import properties and the `Experience` import. Same SQL semantics (percentage label, `is_available_for_matching`, exclusion, joined experiences→organization + selectin notes). Verified: baseline-diff clean (identical 10 local TestClient-404 failures on unmodified head), 5/5 system tests green vs real Postgres (also proves the new `Inject[TalentService]` DI wiring). **Note:** `ApplicationRepository` (Roles matching) still has the same `_talent_model` pattern — candidate for the same treatment as a follow-up, out of scope here.
- **Q3 — audited, confirmed intended.** Nothing in the app branches on 500 vs 504: only status conditionals anywhere are `!= 404` (trackers/contact), `== 400` (vault), `== 504` (new job code). Response body unchanged (`retryable=False` is a class attr, FE reads `detail` only). The 504 is strictly more accurate for triage. One external caveat: any Grafana alert keyed to exactly `status=500` (not 5xx) would stop seeing timeouts — flagged in the PR reply for a quick dashboard eyeball.

## Pending

- [x] M1 BE implementation (tasks 23641/42/43) → single PR **[#1854](https://github.com/taller-projects/echo-backend/pull/1854)** → `dev` (open).
- [ ] Data endpoint (US [#23610](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23610)): final path + staging availability; then validate real contract end-to-end (PRD "Verificación" §4) + set `OPEN_JOB_MATCH_ENDPOINT`/`READ_TIMEOUT`.
- [ ] Latency target (P95) to agree with Data → drives the timeout setting value.
- [ ] Merge #1854 (blocked on US 23610).
- [ ] M2 FE (US 23644) — frontend milestone, needs FE owner (**not backend scope**); PR should note M1 #1854 must merge first.
- [ ] QA gating on full feature (M1+M2), 4-6h per PRD.
- [x] Tenant-isolation decision (per-entry tag + tenant-aware SQL) — Pedro reviewed rounds 1+2 with no objection to the core approach (his round-2 questions were about the legacy-cap edge + the consumer-less smart-search view exposure, not the isolation mechanism).
- [x] PRD §5 full-flow system test + PII-log fix — done in round 2 (`e2171b0e`).
- [x] Legacy-wipe migration (`ehjnwsqitqve`) + stranded `test_external_api_service.py` — pushed 2026-07-20.
- [x] Q4 refactor: cosine selection moved to `TalentService.get_top_matches` (commit `4b9ea905`) — layering exception dissolved.
- [ ] Reply to Pedro's review comment on #1854 (blockers fixed in `e2171b0e`; Q1 → wipe migration, Q2 → Data notified, Q3 → audited/intended + Grafana caveat, Q4 → dissolved via `4b9ea905`).
- [ ] Possible follow-up: apply the same vector-value treatment to `ApplicationRepository`'s `_talent_model` coupling (Roles matching) — same pattern, out of scope for #1854.
- [ ] gonza sends the Spanish notification to the Data team re: `view_smart_search_companies_open_jobs`; their answer decides the follow-up (drop `matched_talents` from the view if unused).
- [ ] PRD amendment: "no migration" scope note + §7 "legacy keeps current behavior" → superseded by the wipe (session was updating Notion + Azure tickets right after this vault update).

## Related

- [[Industry-agnostic Echo (PRD 398aedca)]] — same `candidate_matching` external service; industry param plumbing.
- Battle Tested rollout epic context: see memory note `project_battle_tested_client`.
