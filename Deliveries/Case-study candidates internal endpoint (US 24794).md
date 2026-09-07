---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, internal-api, talent, matching, team-builder, case-studies]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2231"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24794"
prd: ""
---

# Case-study candidates internal endpoint (US 24794)

Team Builder's Inspired case-study source read echo-backend's Postgres directly (3 SQL queries in its `project_export/echo_backend_db.py`): 5 prod DB secrets in its Vault, RLS bypassed with manual `tenant_id` filters, and ~150-line CTEs duplicating application/workflow/experience semantics. Shipped `POST /internal/talents/case-study-candidates` (X-Echo-Api-Key, tenant from key) with three modes replacing those queries one-to-one; Team Builder switches transport, not algorithm. Proposal + agreed answers live in the shared artifact (claude.ai/code/artifact/df45ea55-889c-440c-afc9-77f171b3c2f3, updated 2026-09-07 with echo-backend's responses).

## Azure / docs
- [US 24794](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24794) — Active, PR linked in comment.
- Proposal doc: Team Builder technical proposal (artifact above; Estado "Acordado · en implementación").

## PRs
- [#2231](https://github.com/taller-projects/echo-backend/pull/2231) → dev — OPEN 2026-09-07.

## How
- Single endpoint, `mode` as Pydantic **discriminated union** (`application` / `vector` / `similar`), all request models `extra="forbid"` → foreign-mode field or unknown rule key = 422.
- `application`: `ApplicationRepository.get_case_study_candidate_rows` — pool = applications with `matching_score` set + `matching_status='ok'` on the project's roles; ROW_NUMBER per role ordered by priority rules → score → `advancement_rank` (WorkflowStepStage weight ×1000 + step `order`; NotHired 0, no step 1, Intake 2 … Final 6) → primary-exp-described → `last_status_update`; cut `per_role_cap` (1–50, default 3); global order repeats the keys.
- `vector` / `similar`: `TalentRepository.get_case_study_candidates_by_vector` — cosine over `profile_vector`, EXISTS-gate to talents with an application on the project, `tid_literal` bindparam kept for partial HNSW indexes; `similar` uses the anchor's vector (anchor excluded; missing/unvectorized → 200 empty). Vectorization backend-side via `VectorizerService` + tenant industry (503 on failure).
- Rules reuse `MatchFilterRule`/`MatchSortRule` grammar (`app/modules/match/config.py`); new `build_sort_rank_case`/`build_priority_rank_case` expose the CASE for the projected `priority_rank`. STRICT — no `parse_matching_config` fallback.
- Experiences: 3 batch queries in `TalentRepository` (primary DISTINCT ON, described ≤30, eligible ≤10 within 2y — application mode only); `organization_insight.industry` LEFT JOINed via the **bare table** (`OrganizationInsight.__table__`) — joining the polymorphic entity collides with the base `Organization` join.
- Orchestration in `TalentService.get_case_study_candidates`; `ApplicationService` fetched via `self.inject.get(...)` (constructor DI circular). Response carries **no talent PII**.
- Tests: `tests/unit/test_case_study_candidates.py` (17). Full unit+multitenancy suite green locally (4542 passed).

## Decisions
- Route under `/internal/talents/` (resource returned is talents; application ranking is an implementation detail).
- One endpoint + mode union over three routes: one response contract AND strict per-mode bodies.
- 2-year window, 10/30 caps stay backend constants (`TalentService.CASE_STUDY_*`); no raw `vector` in body — both additive later.
- **Accepted semantic change**: vector/similar order `priority_rank` BEFORE distance; identical to TB's current behavior when `rules` absent.
- Navitec's "tag A first" moves from TB config to per-request `rules` — new tenants with own rules = TB yaml change, no backend deploy.

## Gotchas
- `parse_matching_config` silently degrades bad configs — this endpoint must NOT (caller is a service): strict subclasses `CaseStudyFilterRule`/`CaseStudySortRule`/`CaseStudyCandidateRules` with `extra="forbid"`.
- `ExternalApiException` takes kwargs only (`status_code=`, `detail=`) — positional arg TypeErrors.
- `/internal` runs with `DisableRLS` → every WHERE carries tenant_id explicitly (isolation pinned by test).
- KForce scale: N/A-ish — queries are project-gated over talent/application/experience, none of the contact-scale tables.

## Pending
- PR [#2231](https://github.com/taller-projects/echo-backend/pull/2231) review + merge to dev (deploys dev + kforce-dev).
- Changelog entry in the Case Studies technical PRD (this reverts its "talent queries stay direct-DB" decision).
- Team Builder side (their repo): HTTP client, Navitec yaml `candidate_rules`, N-tier `_select_application`, delete `echo_backend_db.py` + 5 `ECHO_POSTGRES_DB_*` Vault secrets — gated on their dev validation (3 Navitec projects, endpoint rows vs old queries).
- qa/main promotion after dev validation.

## Related
- [[Matching batch status proxy (US 24774)]] · [[Tenant list search param ignored (Bug 24696)]]
