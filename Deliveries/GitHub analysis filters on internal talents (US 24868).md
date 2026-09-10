---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, talent, internal-api, github-analyzer]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2247"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24868"
prd: ""
---

# GitHub analysis filters on internal talents (US 24868)

The github-candidate-analyzer reads echo-backend's Postgres directly (5 DB secrets in its Vault, RLS bypass, JSONB-shape coupling) to find talents stuck in `pending` GitHub analysis every 5 min. This delivery adds `has_github` / `github_analysis_status` / `github_analysis_status__in` to `TalentFilter` so the discovery goes through `GET /internal/talents` with the per-tenant `X-Echo-Api-Key`, and the analyzer can drop the credentials. Proposal came as a Claude artifact PRD from the analyzer side (same playbook as the Team Builder case-study endpoint, [[Case-study candidates internal endpoint (US 24794)]]).

## Azure / docs
- [US 24868](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24868) (created this session; Active, assigned to me)
- PRD: analyzer-side artifact "Análisis de GitHub pendientes por API" (claude.ai artifact a3a0b733-8a25-4c8c-b6da-fd0613fde687, 2026-09-10)

## PRs
- [#2247](https://github.com/taller-projects/echo-backend/pull/2247) → dev — OPEN 2026-09-10; Leo **APPROVED** 2026-09-10 (review 5169451906), nits addressed `79cbeeea` (other session: enum at the pending writer, empty-`__in` + whitespace-URL tests, multitenancy isolation cases) + `547b01ae` (combined eq+`__in` test, class-level consume-and-skip note)
  - `44a7d9b2` original feature
  - `79cbeeea` (2026-09-10) review-nit follow-up (self /pr-review, below)

## How
- `GithubAnalysisStatus` StrEnum (pending/completed/failed) in `app/modules/talent/schemas.py` — the values written into `talent.github_analysis_result["status"]` (writer: `TalentService.enqueue_github_analysis` + analyzer PATCH).
- Three filter fields on `TalentFilter`, applied manually in `_apply_github_filters` with the consume-and-skip pattern (`_apply_rehire_filter` style): `status` lives inside JSONB (`github_analysis_result["status"].astext`), the generic AdvancedFilter loop can't resolve it via `getattr(Talent, name)`.
- `has_github=true` → `github_url IS NOT NULL AND != ''`; `false` → explicit `or_(IS NULL, = '')` (avoids 3-valued-logic NOT). `{}` result matches no status value.
- No new route / response schema / migration / index. All tenants (plain filter params on internal endpoint).
- Tests `tests/unit/test_talent_github_filters.py`: 8 query-level + 4 endpoint-level via `X-Echo-Api-Key` TestClient (tenant isolation incl. second-tenant pending talent, `__in`, 422 on bad enum, empty-page shape).

## Decisions
- Filters on the existing listing instead of a dedicated light endpoint (PRD open question): smallest change; a `GET /internal/talents/github-analysis` endpoint stays additive if payload weight ever matters.
- The `pending` writer in `service.py` (`enqueue_github_analysis`) originally kept the magic string; the self-review flagged it and `79cbeeea` switched it to `GithubAnalysisStatus.PENDING.value` so write and read share one source of truth (value-identical, no behaviour change).
- `has_linkedin` mirrors this need but is a `@property` resolved by the generic loop — the PRD warned it's a trap; github filters never depend on it.

## Gotchas
- polyfactory randomizes `github_url` AND `github_analysis_result` (random dict!) on TalentFactory — every test create pins both or assertions go vacuous.
- worktree-guard now also blocks Bash commands with `export VAR=$(...)` or computed sed args (too-complex-to-verify heuristic) — Azure API calls from a worktree go via python3 heredoc, not curl+export.

## Pending
- Self /pr-review done + nits landed (`79cbeeea`). Pending: team review + merge of [#2247](https://github.com/taller-projects/echo-backend/pull/2247); dev + kforce-dev deploy.
- Analyzer side (their repo): `EchoApiClient.list_pending_github_talents`, transport switch in `fetch_pending_talents`, delete `echo_supabase_reader.py` + 5 Vault secrets. Rollout comparison needs manually-marked pendings (prod has 0 today).
- Out of scope but noted: 1,275 talents with URL and no analysis (`has_github=true` + no status finds them); conversation pending on enqueueing them.

## Review (self /pr-review, 2026-09-10)
Full-mode 3-agent review (architecture / prd / tests-security). **Verdict: READY WITH NITS, 0 blockers.** PRD compliance 12/13 (only "multitenancy tests" wording partial). Nits addressed in `79cbeeea`:
- Use `GithubAnalysisStatus.PENDING` at the `enqueue_github_analysis` writer (single source of truth).
- Unit: empty `github_analysis_status__in=[]` matches no rows; `has_github` treats only NULL/`''` as absent (whitespace URL counts as present).
- Multitenancy: dedicated `tests/multitenancy/test_talent_isolation.py::TestTalentGithubFilterIsolation` — the pending-github discovery filter never surfaces another tenant's talent (satisfies the acceptance wording literally).

Not actioned (deliberate): rename `has_github`→`has_github_url` (ticket names the param `has_github` verbatim; it's the analyzer contract); JSONB status index (talent is not a KForce-hot table, scan is tenant-bounded — declined, EXPLAIN-if-poller-budget-bites left as an open QUESTION). 21 tests green locally; lint clean.

## Related
- [[Case-study candidates internal endpoint (US 24794)]] — same "kill direct-DB access from a sibling service" pattern.
