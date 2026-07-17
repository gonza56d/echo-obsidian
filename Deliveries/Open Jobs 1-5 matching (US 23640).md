---
type: delivery
status: in-progress
env: taller
delivered:
tags: [feature, matching, open-jobs, battle-tested]
prs: []
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

Bring Companies → Open Jobs → "Get Candidates" from the old raw-% cosine display to the same 1-5 LLM scoring that Roles→Candidates uses ("battle tested" matching). Keeps the `matched_talents` JSONB on `organization_job` (extended, **no migration**); a NEW **synchronous** Data-service endpoint scores 5 candidates per call. "Get More Candidates" +5 per click, hard cap 30. Taller only (Kforce has no Open Jobs UI). Status: **planned, tickets created, no code yet** — everything below is the handoff to execute.

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

- (none yet) BE: one PR from branch `23640/open-jobs-matching-1-5` → `dev`.

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
- Azure REST from non-interactive shells: org is `TallerInternTools`, project `Echo Core`; PAT via `sed -n 's/^export AZURE_DEVOPS_EXT_PAT=//p' ~/.zshrc` (plain `source ~/.zshrc` doesn't work in Claude's bash).

## Pending

- [ ] Data endpoint (US [#23610](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23610)): final path + staging availability; then validate real contract end-to-end (PRD "Verificación" §4).
- [ ] Latency target (P95) to agree with Data → drives the timeout setting value.
- [ ] M1 BE implementation (tasks 23641/42/43) → single PR → `dev`.
- [ ] M2 FE (US 23644) — needs an owner; blocked on M1 contract.
- [ ] QA gating on full feature (M1+M2), 4-6h per PRD.
- [ ] Tenant-isolation decision (per-entry tag) taken by gonza 2026-07-17 — confirm with Pedro at review time.

## Related

- [[Industry-agnostic Echo (PRD 398aedca)]] — same `candidate_matching` external service; industry param plumbing.
- Battle Tested rollout epic context: see memory note `project_battle_tested_client`.
