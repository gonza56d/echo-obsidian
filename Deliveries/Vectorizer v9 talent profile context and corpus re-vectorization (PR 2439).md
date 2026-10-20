---
type: delivery
status: in-review
env: taller
delivered: 2026-10-20
tags: [feature, matching, vectorizer, navitec, script]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2439"
fe_prs: []
tickets: []
prd: "https://claude.ai/artifact/DEqpgKApmv5nmPZNR51zrH"
---

# Vectorizer v9 talent profile context and corpus re-vectorization (PR 2439)

Data (Nico Lizondo) moves the five matching-products vectorizers from the gpt-4 family (being deprecated) to `gpt-6-luna` with a new normalization, v9. Their request to backend (2026-10-20, [Pedido Vectorizadores v9](https://claude.ai/artifact/DEqpgKApmv5nmPZNR51zrH)): send three more talent fields when vectorizing (`summary`, `academic_history`, `certifications`, the domain line of the embedded text: an insurance data architect ranks ~8,000th without the summary and ~500th with it), and re-vectorize every stored talent and role vector once after their deploy because v8 and v9 vectors are not comparable (cosine 0.93 on the same talent, 8% below 0.90). My backend evaluation for Pedro: [Vectorizador v9 en echo-backend](https://claude.ai/artifact/7HUHfmS8ra3HpNvuBwgfgR). Pedro picked option B (script to the DB); the PR implements point 01 plus the B' variant (our script, vectors from Data's endpoint).

## Azure / docs
- No Azure ticket yet (asked nothing of the user; create one if Pedro wants it tracked).
- Data's request: [Pedido Vectorizadores v9](https://claude.ai/artifact/DEqpgKApmv5nmPZNR51zrH) (Nico, 2026-10-20). Matching-products branch `feature/vectorizer-gpt6-luna`, PR against their dev.
- My evaluation (Spanish, for Pedro): [Vectorizador v9 en echo-backend](https://claude.ai/artifact/7HUHfmS8ra3HpNvuBwgfgR) — verdict per option, code verification table, checklist for direct DB writes, mixed-corpus window, questions.

## PRs
- [#2439](https://github.com/taller-projects/echo-backend/pull/2439) → dev: OPEN 2026-10-20 (head `56ed9542`, branch `vectorizer_v9_talent_fields`, 2 commits: `2f4bfaef` feature, `56ed9542` script). Assignee gonza-taller.
- FE: no contract change (no route, response, permission or schema change).

## How
- `VectorizerService.vectorize_talent` gains optional `summary`, `academic_history: List[EducationItem]`, `certifications: List[CertificationItem]` (`OrmBaseModel`, so `@validate_call` accepts both the Pydantic `Education`/`Certification` objects of the create path and the raw JSON/JSONB dicts of the ORM). `talent_profile_context()` trims entries to `{title|name, entity}`, treats `[Degree Name]` / `[Institution Name]` as empty, drops entries without a label, omits an empty entity, and adds a key only when it has content → the byte-identical test for talents without those fields is untouched. Same signature on the mock.
- Call sites: `TalentService.create_talent` (service.py ~637) and `update_talent_vector_by_id` (~1014) forward the three fields.
- `TalentUpdate.touches_vector_input` (property; `VECTOR_INPUT_FIELDS = summary, job_history, academic_history, certifications`) replaces the inline `summary or job_history` check in `PATCH /talents/{id}` and `PATCH /internal/talents/{id}`.
- `scripts/revectorize_corpus.py` (psycopg2 + `VectorizerService`): plan mode (counts + ETA per tenant), `--probe N --concurrency C` (no writes, p50/p95/throughput, extrapolated corpus time), `--apply --confirm-db <host-substring>`. Roles first (`enables_matching` step ahead) with `vector_generated_at = now()`, then talents per tenant largest last, keyset pagination, `execute_values` batches with rowcount check (aborts on RLS / missing rows), checkpoint file `.revectorize_checkpoint.txt`, abort after 25 consecutive vectorizer failures, `--refresh-percentages` with the `100 * (1 - (role.vector <=> talent.profile_vector))` expression. DB URL defaults to the `.env`'s `DB_URL`; loguru set to WARNING to keep the request logs out of the progress output.
- Tests: `test_vectorizer_service.py` (+4), `test_talent_vector_input.py` (both call sites, the property, router trigger on/off), `test_revectorize_corpus_script.py` (pure helpers); `test_industry_propagation.py` SimpleNamespace gained the three attrs (the `__new__` fixture trap).

## Decisions
- **Endpoints of Echo are not a re-vectorization path.** None only re-vectorizes: `PATCH /talents/{id}` (grammar check, custom fields, outbox `talent.updated` → TrackerRMS, 29k events for Navitec), experiences endpoints (+ red-flags AI call), `PUT roles` (change history, outbox), `rematch` (paid evaluations). And all run the vectorization as a Starlette `BackgroundTask` (no record, no retry, lost on deploy). A new internal endpoint = option A's work with the loop outside.
- **Option A (worker job) rejected for now:** infra exists but prod worker is 1 replica × `BACKGROUND_WORKER_CONCURRENCY=3` (Vault, deliberate enhancement ceiling) → ~36 h; 4 h needs a temporary bump to 32 + DB pool. 1.5–2 days of dev. Keep only if the run will repeat per model change.
- **B' over B:** our script, vectors from the deployed endpoint → no prod write credential for Data, body parity with runtime via `VectorizerService`. Cost: ½–1 day script (done) and the endpoint's capacity is unmeasured (Data's 4 h / 32 parallel was with their script calling OpenAI directly, bypassing the matching-products pods: prod HPA 2–5).
- **Trimming interpretation:** title/name required (a placeholder title drops the entry even with a real entity); entity optional. Flagged to Data in the PR as open.
- Trigger extended to education/certifications edits (recommended in the report; cheap).
- Script defaults `--database-url` to `settings.DB_URL` (the .env), consistent with `VECTORIZER_API_URL` / `ECHO_INTERNAL_API_KEY` coming from the same .env; `--confirm-db` guards `--apply`.

## Gotchas
- `lru_cache` on `vectorize_job_description` AND `vectorize_text` (per process, 1000 entries, key = title/desc/industry): after the matching-products deploy a warm pod can regenerate a role with the cached v8 vector and stamp it fresh; semantic search queries cached in v8 compare against v9 talents. Mitigation: rolling restart of API + worker after their deploy and after the run. The role enhancement pipeline vectorizes JDs in the worker, so a worker-side job would need `cache_clear()`.
- Two partial HNSW indexes on `talent.profile_vector` (Taller, Navitec; `ix_talent_pv_hnsw_<tenant>`) bloat with 50k updates → `REINDEX INDEX CONCURRENTLY` + `VACUUM ANALYZE talent, role` after the run (table owner). `role.vector` has no index.
- `talent` and `application` have RLS; the script's rowcount check turns a non-bypassing role into a hard abort instead of silent zero-row updates.
- `vectorize_talent` wraps errors in `TalentVectorizerException` (400), not `ExternalApiException`, so `update_talent_vector_by_id`'s except does not catch it (BackgroundTask just logs). Irrelevant for the script (catches `Exception` per item).
- `refresh_match_percentages` formula is `100 * (1 - distance)`, not `Talent.similarity`'s `((1-d)+1)/2`.
- Worktree session: the isolation hook refuses `source …/activate` → call `.venv/bin/python` / `.venv/bin/ruff` by absolute path. `./scripts/lint.sh` creates a `.venv` inside the worktree (uv), gitignored.
- SSH to github still times out → push with `GIT_ASKPASS` + gonza-taller token over HTTPS (`HEAD:<branch>`); `gh pr create` with `GH_TOKEN=$(gh auth token --user gonza-taller)` worked from inside the worktree.
- Dev plan run: 31,573 vectors across 15 tenants (Navitec 19,880 talents / 959 roles; Taller 7,453 / 2,558). Probe `--probe 3 --concurrency 3` against `matching-products-api-dev`: 3/3 OK, p50 3.9 s → the current (v8) service ignores the new keys, so the backend can deploy before Data.

## Pending
- Review + squash-merge [#2439](https://github.com/taller-projects/echo-backend/pull/2439) to dev; qa/main promotion.
- Pedro's call (meeting 2026-10-21): B' (our script, no credential for Data) vs B (Data's script with a prod write credential); window (off-hours, ~4 h, roles first); rollback net (copy of old vectors) or accept a second run; who runs REINDEX/VACUUM.
- Nico: does `revectorize_corpus.py` on their side already send the 3 fields (moot if we run B'); is the service async / how many in-flight requests per pod; do endpoint and script share the OpenAI key with live matching; confirm the trimming interpretation; confirm `--refresh-percentages` formula.
- Capacity probe in dev at 8/16/32 (`--probe 100 --concurrency N`) once matching-products dev runs v9; then the full dev run (`--apply --confirm-db`), verification by md5 snapshot (SQL in the evaluation), REINDEX/VACUUM, pod restart.
- Prod run after Data's deploy; warn Navitec/Taller/EQT about rankings moving that day.
- Optional: Azure ticket if Pedro wants it tracked.

## Related
- [[Industry-agnostic Echo (PRD 398aedca)]] — byte-identical request guarantee this PR preserves.
- [[Evaluate batch scoped to new candidates (PR 2334)]] · [[Matching batch status proxy (US 24774)]] — sibling matching-products integrations.
- [[Open Jobs 1-5 matching (US 23640)]] — `VectorizerService` sync client + timeouts.
- [[Map - Observability & Reliability]]
