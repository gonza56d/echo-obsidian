---
type: delivery
status: shipped
env: taller
delivered: 2026-09-07
tags: [feature, internal-api, talent, matching, team-builder, case-studies]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2231"
  - "https://github.com/taller-projects/echo-backend/pull/2241"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24794"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24857"
prd: ""
---

# Case-study candidates internal endpoint (US 24794)

Team Builder's Inspired case-study source read echo-backend's Postgres directly (3 SQL queries in its `project_export/echo_backend_db.py`): 5 prod DB secrets in its Vault, RLS bypassed with manual `tenant_id` filters, and ~150-line CTEs duplicating application/workflow/experience semantics. Shipped `POST /internal/talents/case-study-candidates` (X-Echo-Api-Key, tenant from key) with three modes replacing those queries one-to-one; Team Builder switches transport, not algorithm. Proposal + agreed answers live in the shared artifact (claude.ai/code/artifact/df45ea55-889c-440c-afc9-77f171b3c2f3, updated 2026-09-07 with echo-backend's responses).

## Azure / docs
- [US 24794](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24794) — **Closed 2026-09-07**; merge + tie-breaker clarification recorded in ticket comments.
- Proposal doc: Team Builder technical proposal (artifact above; Estado "Acordado · en implementación").

## PRs
- [#2231](https://github.com/taller-projects/echo-backend/pull/2231) → dev — **MERGED** (squash `d90aef95`, 2026-09-07; approved by Pedro). Deploys dev + kforce-dev.

## How
- Single endpoint, `mode` as Pydantic **discriminated union** (`application` / `vector` / `similar`), all request models `extra="forbid"` → foreign-mode field or unknown rule key = 422.
- `application`: `ApplicationRepository.get_case_study_candidate_rows` — pool = applications with `matching_score` set + `matching_status='ok'` on the project's roles; ROW_NUMBER per role ordered by priority rules → score → `advancement_rank` (WorkflowStepStage weight ×1000 + step `order`; NotHired 0, no step 1, Intake 2 … Final 6) → primary-exp-described → `last_status_update`; cut `per_role_cap` (1–50, default 3); global order repeats the keys.
- `vector` / `similar`: `TalentRepository.get_case_study_candidates_by_vector` — gated pool (EXISTS on project applications) built in a **MATERIALIZED CTE**, exact top-N distance sort over it; `similar` uses the anchor's vector (anchor excluded; missing/unvectorized → 200 empty). Vectorization backend-side via `VectorizerService` + tenant industry (503 on failure). The original `tid_literal`/HNSW shape was REMOVED after review: EXPLAIN on dev showed the partial HNSW index scan with the project gate as post-filter — with `hnsw.iterative_scan=off` + `ef_search=40` a narrow project silently under-returns. Exact CTE plan: 93ms warm on the worst dev project (3,038-talent pool).
- Rules reuse `MatchFilterRule`/`MatchSortRule` grammar (`app/modules/match/config.py`); new `build_sort_rank_case`/`build_priority_rank_case` expose the CASE for the projected `priority_rank`. STRICT — no `parse_matching_config` fallback.
- Experiences: 3 batch queries in `TalentRepository` (primary DISTINCT ON, described ≤30, eligible ≤10 within 2y — application mode only); `organization_insight.industry` LEFT JOINed via the **bare table** (`OrganizationInsight.__table__`) — joining the polymorphic entity collides with the base `Organization` join.
- Orchestration in `TalentService.get_case_study_candidates`; `ApplicationService` fetched via `self.inject.get(...)` (constructor DI circular). Response carries **no talent PII**.
- Tests: `tests/unit/test_case_study_candidates.py` (20 after review round: + stage-weight ladder, default per_role_cap, eligible cap, limit=51, vector/similar isolation probes).

## Decisions
- Route under `/internal/talents/` (resource returned is talents; application ranking is an implementation detail).
- One endpoint + mode union over three routes: one response contract AND strict per-mode bodies.
- 2-year window, 10/30 caps stay backend constants (`TalentService.CASE_STUDY_*`); no raw `vector` in body — both additive later.
- **Accepted semantic change**: vector/similar order `priority_rank` BEFORE distance; identical to TB's current behavior when `rules` absent.
- Navitec's "tag A first" moves from TB config to per-request `rules` — new tenants with own rules = TB yaml change, no backend deploy.

## Review round 1 (2026-09-07, /pr-review)
- Verdict CHANGES REQUESTED — 1 blocker (AC6 EXPLAIN evidence; EXPLAIN then surfaced the real HNSW recall bug above), 5 nits. All addressed in `bdceffc7`; AC6 plans posted as PR comment (issuecomment-5574956587).
- kforce-dev AC6 evidence: talent=2 / vectorized=0 / application=0 / experience=0 / role=0 — queries touch none of the KForce-scale tables; 0.15ms.
- Nits fixed: legacy `X-Echo-internal` dropped from test fixture; `query_text` max_length=10k; typed returns (`list[Row]`, `List[float] | None`); Spanish docstring aside removed.
- OPEN QUESTIONS from review (not code): (1) tie-breakers `primary_has_description`/`last_status_update` are in code + TB's original SQL but NOT in the US text — ticket needs updating; (2) `priority_rank` projects only `sort[0]` while ordering now uses ALL sort rules (CTE projects `sort_rank_i` per rule — ordering is fully correct, the *projected* field describes rule 0 only); (3) Case Studies PRD changelog entry still pending.

## Review round 2 (2026-09-07, Pedro rocha-p — APPROVED with nits)
- Nits addressed at `c944c879`: typed private helpers (`row: Row`, `*extra_columns: ColumnElement`), tests for 2-year boundary (729/732-day probes — leap-safe), described cap 30, empty project → 200 empty. File suite 23 passed.
- REBUTTED (with reply on PR): test placement — `tests/unit` is DB-backed by design here and CI runs ONLY tests/unit, so moving to tests/system would remove the isolation probes from CI.
- Parity question answered on PR: extra tiebreakers port TB's original SQL; Navitec 3-project validation covers it; US to be updated to record them.

## Follow-up: described-experience tie-breaker (Task 24857, 2026-09-09)
- TB ran rollout step 2 (`tools/compare_case_study_candidates.py` vs the endpoint on dev, 3 Navitec dev projects `448417f6`/`374ca11d`/`6ed61090`): `similar` + `vector` + anchor selection **identical**; `application` ranking differed — always the same 2 talents per project at the `per_role_cap=12` edge.
- Cause: 4th tie-breaker shipped as "most recent experience has description" (scalar subquery, no org join). The retired SQL's `latest_exp` CTE ordered description-present DESC first, so it effectively computed "has ANY described experience with a company" — which is also what TB anchors on (`described_experiences[0]`) and what Navitec prod sees.
- Fix: PR [#2241](https://github.com/taller-projects/echo-backend/pull/2241) → dev **OPEN** ([Task 24857](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24857), In development, Related-linked to the US): scalar subquery → EXISTS over described experiences joined to `organization`; label renamed `has_described_experience`. Contract/shape unchanged; TB untouched.
- Pinned test `test_application_mode_any_described_experience_beats_recency` — **verified it fails on the old implementation** (the never-described talent gets a LATER `last_status_update`, so recency can't mask the key; talent_id tiebreak can't save it either).
- Exit: after dev deploy TB re-runs the comparison on the same 3 projects; identical per role = the gate for their transport merge (rollout step 3). Artifact updated with the full analysis (section "Ajuste tras la comparación en dev").

## Gotchas
- `parse_matching_config` silently degrades bad configs — this endpoint must NOT (caller is a service): strict subclasses `CaseStudyFilterRule`/`CaseStudySortRule`/`CaseStudyCandidateRules` with `extra="forbid"`.
- `ExternalApiException` takes kwargs only (`status_code=`, `detail=`) — positional arg TypeErrors.
- `/internal` runs with `DisableRLS` → every WHERE carries tenant_id explicitly (isolation pinned by test).
- KForce scale: N/A-ish — queries are project-gated over talent/application/experience, none of the contact-scale tables.

## Pending
- PR [#2241](https://github.com/taller-projects/echo-backend/pull/2241) (Task 24857): team review + merge + dev deploy, then TB re-runs the 3-project comparison (identical per role = their transport-merge gate).
- Changelog entry in the Case Studies technical PRD (this reverts its "talent queries stay direct-DB" decision) — pre-cutover gate.
- Team Builder side (their repo): HTTP client, Navitec yaml `candidate_rules`, N-tier `_select_application`, delete `echo_backend_db.py` + 5 `ECHO_POSTGRES_DB_*` Vault secrets — gated on the post-#2241 re-comparison.
- qa/main promotion after dev validation (now includes #2241).
~~Verify dev + kforce-dev deploy of `d90aef95`~~ DONE — deployed 2026-09-08, TB comparison ran 2026-09-09.

## Related
- [[Matching batch status proxy (US 24774)]] · [[Tenant list search param ignored (Bug 24696)]]
