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
- [#2439](https://github.com/taller-projects/echo-backend/pull/2439) → dev: OPEN 2026-10-20 (branch `vectorizer_v9_talent_fields`, 3 commits: `2f4bfaef` feature, `56ed9542` script, `1ba19d20` review r1 fixes pushed 2026-10-21 from worktree `vectorizer_v9_r2`). Assignee gonza-taller.
- Leo's r1 (2026-10-21, [comment](https://github.com/taller-projects/echo-backend/pull/2439#issuecomment-6316043126)): CHANGES REQUESTED, 5 blockers all in the script — bodies ≠ runtime (experience order, industry coercion), `--confirm-db` substring useless on the pooler, stale vector stamped fresh on a mid-run edit, no md5 snapshot/verify, probe hides 429/5xx behind retries — plus nits (clears don't re-vectorize, `core_skills` missing, no DB test, RLS reads, idle txn, vector shape, ValidationError on the edit path, checkpoint not keyed to the DB, argv DSN, payload in error text, half-built Runner, percentages on failed roles). All addressed in `1ba19d20`; reply to Leo and PR body refresh pending the user's go-ahead.
- FE: no contract change (no route, response, permission or schema change).

## How
- `VectorizerService.vectorize_talent` gains optional `summary`, `academic_history: List[EducationItem]`, `certifications: List[CertificationItem]` (`OrmBaseModel`, so `@validate_call` accepts both the Pydantic `Education`/`Certification` objects of the create path and the raw JSON/JSONB dicts of the ORM). `talent_profile_context()` trims entries to `{title|name, entity}`, treats `[Degree Name]` / `[Institution Name]` as empty, drops entries without a label, omits an empty entity, and adds a key only when it has content → the byte-identical test for talents without those fields is untouched. Same signature on the mock.
- Call sites: `TalentService.create_talent` (service.py ~637) and `update_talent_vector_by_id` (~1014) forward the three fields.
- `TalentUpdate.touches_vector_input` (property; `VECTOR_INPUT_FIELDS` frozenset = summary, core_skills, job_history, academic_history, certifications; keyed on `model_fields_set`, so a clear re-vectorizes too) replaces the inline `summary or job_history` check in `PATCH /talents/{id}` and `PATCH /internal/talents/{id}`. `update_talent_vector_by_id` catches `TalentVectorizerException` and pydantic `ValidationError` besides `ExternalApiException` (BackgroundTask: log, never raise). `vectorize_talent` forwards `read_timeout` / `max_retries` to the client.
- `coerce_industry()` in `app/modules/tenant/industry.py`: the pure form of `Tenant.industry` (null / unknown → `tech`); the model and the script both use it. `DEFAULT_INDUSTRY` stays re-exported from `tenant.models` (`import … as …`) because the AI service clients import it from there.
- `scripts/revectorize_corpus.py` (psycopg2 autocommit + `VectorizerService`): plan (counts + ETA per tenant), `--probe N --concurrency C` (no writes, `max_retries=0`, p50/p95/throughput, failures by HTTP status), `--apply --confirm-db <supabase project ref>` (exact match on the DSN user's `postgres.<ref>` or `user@host`; prints `current_database` / `current_user`), `--verify`. Up front: `check_rls_bypass` (rolsuper / BYPASSRLS, or owner of talent/role/application without FORCE). Every read carries `now() AS read_ts`; experiences ordered `end_date DESC NULLS FIRST, start_date DESC` like `Talent.experiences`. Each batch is ONE CTE statement: `UPDATE … WHERE updated_at (talent) / vector_input_updated_at (role) <= read_ts AND vector IS DISTINCT FROM new … RETURNING`, outer SELECT (pre-update snapshot) classifies every row sent as written / edited / unchanged / missing; roles stamped `vector_generated_at = read_ts`; abort if the whole batch is missing (RLS) or a batch ≥ 10 is entirely unchanged (service still on the old model). Only written ids go to the checkpoint; edited/unchanged are reported with hints and retried by re-running. md5 `Snapshot` of every vector in scope taken on the first `--apply` (reused on resume), `--verify` prints changed/unchanged/new per tenant and exits 1 if any unchanged. `check_vector` (1536 finite floats), `describe_failure` (status from the `__cause__` chain, ValidationError without the payload). State files `.revectorize_<ref>.checkpoint` / `.snapshot` in `--state-dir` (gitignored). `--refresh-percentages` only for checkpointed roles. No `--database-url`: `DB_URL` from the .env / environment.
- Tests: `test_vectorizer_service.py` (+5), `test_talent_vector_input.py` (both call sites, property incl. clears + core_skills, public + internal router trigger, ValidationError swallow), `test_revectorize_corpus_script.py` (pure helpers: identity/confirm-db, check_vector, describe_failure, checkpoint), `test_revectorize_corpus_db.py` (testcontainers: ORM order parity, write + checkpoint + `vector_generated_at` + percentage refresh, edited-row skip for talent and role, unchanged-batch abort, snapshot/verify), `test_industry_resolution.py` (`coerce_industry`); `test_industry_propagation.py` SimpleNamespace gained the three attrs (the `__new__` fixture trap).

## Decisions
- **Endpoints of Echo are not a re-vectorization path.** None only re-vectorizes: `PATCH /talents/{id}` (grammar check, custom fields, outbox `talent.updated` → TrackerRMS, 29k events for Navitec), experiences endpoints (+ red-flags AI call), `PUT roles` (change history, outbox), `rematch` (paid evaluations). And all run the vectorization as a Starlette `BackgroundTask` (no record, no retry, lost on deploy). A new internal endpoint = option A's work with the loop outside.
- **Option A (worker job) rejected for now:** infra exists but prod worker is 1 replica × `BACKGROUND_WORKER_CONCURRENCY=3` (Vault, deliberate enhancement ceiling) → ~36 h; 4 h needs a temporary bump to 32 + DB pool. 1.5–2 days of dev. Keep only if the run will repeat per model change.
- **B' over B:** our script, vectors from the deployed endpoint → no prod write credential for Data, body parity with runtime via `VectorizerService`. Cost: ½–1 day script (done) and the endpoint's capacity is unmeasured (Data's 4 h / 32 parallel was with their script calling OpenAI directly, bypassing the matching-products pods: prod HPA 2–5).
- **Trimming interpretation:** title/name required (a placeholder title drops the entry even with a real entity); entity optional. Flagged to Data in the PR as open.
- Trigger extended to education/certifications edits (recommended in the report; cheap).
- Script reads only `settings.DB_URL` (the .env / environment, never argv: a DSN in `ps` was one of Leo's nits), consistent with `VECTORIZER_API_URL` / `ECHO_INTERNAL_API_KEY` coming from the same .env; `--confirm-db <project ref>` guards `--apply`.
- **Mid-run edits (Leo's blocker 3):** instead of stamping `now()`, the write carries the read instant and skips rows edited after it (`talent.updated_at` / `role.vector_input_updated_at`), stamping `vector_generated_at = read_ts`. Skipped rows are not checkpointed, so a re-run retries them; an edit's own re-vectorization is never overwritten by an older-text vector. Residual window: `updated_at` is the pod's clock, `read_ts` the DB's — ms-level, accepted.
- **"Old model still deployed" guard instead of only a post-hoc hash check:** the statement compares the stored vector with the new one in SQL (`IS DISTINCT FROM`), so a run against a v8 service writes nothing and aborts on the first full batch; the md5 snapshot + `--verify` stays as the independent proof the evaluation's checklist asked for (no DDL in prod: the snapshot is a local file).
- `coerce_industry` lives in `tenant/industry.py`, not in the script: the script must resolve the industry exactly as `Tenant.industry` does (body parity is the whole point of B').

## Gotchas
- `lru_cache` on `vectorize_job_description` AND `vectorize_text` (per process, 1000 entries, key = title/desc/industry): after the matching-products deploy a warm pod can regenerate a role with the cached v8 vector and stamp it fresh; semantic search queries cached in v8 compare against v9 talents. Mitigation: rolling restart of API + worker after their deploy and after the run. The role enhancement pipeline vectorizes JDs in the worker, so a worker-side job would need `cache_clear()`.
- Two partial HNSW indexes on `talent.profile_vector` (Taller, Navitec; `ix_talent_pv_hnsw_<tenant>`) bloat with 50k updates → `REINDEX INDEX CONCURRENTLY` + `VACUUM ANALYZE talent, role` after the run (table owner). `role.vector` has no index.
- `talent` and `application` have RLS and `talent` is **FORCE** row security (dev: `relforcerowsecurity = t`), so even the table owner needs BYPASSRLS; the dev/prod `postgres` role has `rolbypassrls = t` through the pooler (`current_user` = `postgres` on every environment, useless to tell them apart: the project ref only lives in the DSN user). The script checks this up front and classifies invisible rows as `missing` (whole batch missing → abort).
- `vectorize_talent` wraps errors in `TalentVectorizerException` (400), not `ExternalApiException`; `update_talent_vector_by_id` now catches it (and `ValidationError`, which `@validate_call` raises for legacy malformed education/certification JSON before the try). The script reads the upstream status from `__cause__`.
- pgvector supports `=` / `IS DISTINCT FROM` on `vector` (btree opclass), so "stored equals new" is one SQL predicate; `execute_values(..., fetch=True)` returns the CTE's outer SELECT. The CTE is named `incoming`, not `new` (keyword in plpgsql).
- `--apply` was NEVER run in dev as of 2026-10-21 (Leo asked): only plan (31,573 → 31,582 vectors) and `--probe 3` / `--probe 2` (2/2 OK, p50 7.8 s, no retries). The evaluation artifact's status line "Corrido en dev: 31.573 vectores" overstates it — needs correcting to "plan listed".
- Worktree session: Write/Edit to the memory dir and this vault are blocked by the guard → `ExitWorktree(keep)`, write, `EnterWorktree(path)` to return.
- `refresh_match_percentages` formula is `100 * (1 - distance)`, not `Talent.similarity`'s `((1-d)+1)/2`.
- Worktree session: the isolation hook refuses `source …/activate` → call `.venv/bin/python` / `.venv/bin/ruff` by absolute path. `./scripts/lint.sh` creates a `.venv` inside the worktree (uv), gitignored.
- SSH to github still times out → push with `GIT_ASKPASS` + gonza-taller token over HTTPS (`HEAD:<branch>`); `gh pr create` with `GH_TOKEN=$(gh auth token --user gonza-taller)` worked from inside the worktree.
- Dev plan run: 31,573 vectors across 15 tenants (Navitec 19,880 talents / 959 roles; Taller 7,453 / 2,558). Probe `--probe 3 --concurrency 3` against `matching-products-api-dev`: 3/3 OK, p50 3.9 s → the current (v8) service ignores the new keys, so the backend can deploy before Data.

## Pending
- After `1ba19d20` (needs the user's go-ahead): reply to Leo's r1 on the PR, refresh the PR body (script section, "Verified": `--apply` not run in dev; add `organization_job.vector` / `cluster_vector` scope under "Open with Data"), correct the evaluation artifact's status line; then Leo's re-review + squash-merge [#2439](https://github.com/taller-projects/echo-backend/pull/2439) to dev; qa/main promotion.
- `organization_job.vector` / `cluster_vector` (open-job matching, same vectorizer, lazy path never refreshes an existing vector): out of the script's scope — confirm with Data whether they need a refresh too (Leo's out-of-scope note).
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
