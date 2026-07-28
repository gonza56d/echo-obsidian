---
type: delivery
status: in-progress
env: taller
delivered:
tags: [reliability, roles, background-tasks, queue, outbox, prd, planning]
prs: []
fe_prs: []
tickets: []
prd: "https://app.notion.com/p/3abaedca11f081ba904afd1f73277444"
---

# Enhancement queue v2 Postgres-backed (PRD 7444)

Move the role **AI enhancement pipeline** (2-5 min per role) out of FastAPI `BackgroundTasks` into a **persistent job queue in Postgres**, drained by a **dedicated worker pod** that clones the operational skeleton of the already-in-prod outbox dispatcher (`FOR UPDATE SKIP LOCKED` claim, lease + expiry, backoff retries, dead-letter, Prometheus metrics, Vault flag, same image / own entrypoint, own Helm+ArgoCD block). This is the **v2 iteration of Pedro's May PRD** and its one substantive revision is the **broker decision**: Dramatiq + managed Redis → **Postgres queue, outbox-style**. **PRD Draft as of 2026-07-28: no code, no Azure tickets.**

## Azure / docs

- PRD v2 (Tier C, Draft, owner Gonzalo): [Cola off-request para enhancements — v2 (Postgres-backed) — PRD Técnico](https://app.notion.com/p/3abaedca11f081ba904afd1f73277444)
- PRD v1 (Pedro Rocha, 2026-05-11, Draft): [Cola de tareas off-request para enhancements de larga duración](https://app.notion.com/p/35daedca11f081d988fbeefa56bb11b6) — lives in the "Echo roadmap (test)" DB. **v2 inherits its diagnosis, prod evidence, technical criteria and milestone shape and does not re-argue them.**
- Sibling PRD: [[Create Role from Open Job (PRD 887e)]] — new creation path feeding the same enhancement; absorbed at cutover, no contract change.
- Business PRD: N/A (pure engineering — reliability/scalability).

## The argument (why Postgres, not Redis)

**Inherited from v1**: `BackgroundTasks` is awaited inside the request task, so a uvicorn worker is tied up 2-5 min per enhancement; under ~50 req/min bursts in-flight concurrency explodes (~250) and saturates the threadpool (40) + pooler. Prod evidence 2026-05-11: 297 `POST /internal/roles`, 100% >30s, max 5m09s, 8-9 5xx/min.

**What changed since May** (the three facts that flip the decision):
1. **The outbox + dispatcher pattern now exists and runs in prod** (since July): separate pod `python -m app.dispatcher`, claim with `FOR UPDATE SKIP LOCKED`, lease TTL + expired-lease release, exponential backoff + jitter, dead-letter, Prometheus, Sentry `component=dispatcher`, Vault flag, own Helm/ArgoCD block. In May "custom PG queue" was dismissed as "reinventing Procrastinate" — it has since been invented, operated and runbooked here.
2. **Same incident class recurred**: [[Role enhance pool timeout unhandled (Bug 23808)]] — the enhancement background task died on a `QueuePool` checkout timeout (30s, pool 20+10) during prod pool-exhaustion windows, roles stuck `PENDING`. Contained, but proof the current mechanism won't survive growth (projection: 5k users, 100-500 concurrent creations).
3. **Durability became an explicit requirement**: no pending enhancement may be lost across deploys/downtime.

**Core argument**: the enqueue INSERT rides **the same transaction that commits the role**, so a role can never be committed without its job — crash, deploy or broker outage. Persisted Redis (Azure Cache Premium RDB/AOF or Azure Managed Redis) protects the *broker* but does **not** close the dual-write window between commit and enqueue; closing it needs an outbox in Postgres anyway — and if the outbox is needed regardless, the PG queue is already paid for. Verified: **zero Redis anywhere in echo-backend's repo or charts today** (Airflow/anvil have their own).

**Three sub-decisions answered**: new jobs table (**not** `integration_outbox` — different semantics: work queue vs integration events; sharing couples retention/metrics/purge and drags the TrackerRMS dispatcher into a foreign domain); **new worker** (the dispatcher is sequential-per-batch and runs as a fixed `BYPASSRLS` role — the worker needs bounded concurrency and per-job multi-tenant context reconstruction); **Redis discarded for v1**.

**Re-evaluation trigger toward Redis** (a commitment, not a wish): sustained `oldest_pending_age > 10 min` for >30 min with the worker pool at the max agreed with infra, or the poll/claim showing up in PG's top load → v3 with Dramatiq + Redis **using this same table as the enqueue outbox** (nothing built is thrown away). Procrastinate: dropped in v2 (its marginal value collapsed once the in-house pattern shipped). Azure Service Bus / Storage Queues: same dual-write problem. No-queue mitigations (in-flight cap + 503 + `Retry-After`, v1's M6): parachute only.

**Capacity math**: enqueue is a trivial INSERT; drainage with `C` concurrent jobs/pod at 2-5 min ⇒ ~`C × 12-30` jobs/h/pod (2 pods × 8 ⇒ ~190-480/h), horizontally linear. The real ceiling becomes the AI providers' rate limits — which is exactly why worker concurrency must be **bounded and configurable** (today concurrency = incoming traffic, unbounded).

## Scope + schema

**IN**: new jobs table + migration; new worker deployment (`echo-backend-worker` [tentative], same image, Vault flag); migrate role enhancement on **`POST /roles`, `POST /internal/roles`, `POST /projects/{id}/roles` (public + internal), `POST /roles/{id}/retry-enhancement`**; move the standalone-without-JD **synchronous** JD generation into the job; tenant context serialized in the job and rebuilt in the worker (RLS intact); idempotency by role state + retries + dead-letter + alert; queue metrics/logs/dashboard/alerts; flag `USE_QUEUE_FOR_ENHANCEMENT` [tentative, inherited name] with runtime rollback to `BackgroundTasks`; final sweep of heavy `background_tasks.add_task` sites.

**OUT**: optimizing the pipeline's internals; fanning the internal `WorkerGroup` out into separate jobs (worker v2); replacing EventBus; touching `integration_outbox`/the dispatcher; client-driven idempotency keys; small (<10s) background tasks; existing schedulers (the stale-role cleanup stays as a backstop); **Kforce** (the outbox pattern doesn't exist on `kforce-dev` → copy+adapt with its own PRD).

**Table** [tentative name `background_job`]: `id`, `kind` (e.g. `role_enhancement`), `payload` JSONB (ids + serialized context), `tenant_id`, `status` (`pending`/`running`/`completed`/`failed`/`dead`), `attempts`, `last_error`, `available_at`, `locked_at`, `locked_by`, `completed_at`, timestamps; partial dispatch index on pending by `available_at` (mirroring `ix_outbox_dispatch`); optional dedup by `(kind, entity)` while active [dev's call in M1]. `integration_outbox*` untouched. One alembic revision, starts empty, rollback = drop table (runtime rollback = flag).

## Criteria (v1's, kept as contract, + new durability ones)

- `201 < 500ms p95` on the three creation endpoints under 100 req/min × 5 min (k6).
- **Zero jobs lost** on deploy or crash: `kill -9` mid-job → re-executed after the lease expires; rollout with N queued → queue drains fully on return. Both are chaos-test criteria.
- Zero `SSL connection has been closed unexpectedly` from role/project service during burst; ≥99% enhancements `ENHANCED` in <10 min.
- Retries 3× with backoff [tentative 30s / 2min / 10min] → `FAILED` + alert. **At-least-once**, idempotent by terminal role state (stages are overwrite-safe).
- A dead worker releases its jobs within the lease TTL; a live job never loses its lease (renewable lease or TTL > p99 — **the dispatcher's 60s TTL explicitly does NOT apply** to 2-5 min jobs).
- Logs per stage (`enhance.start` … `enhance.complete`/`failed`) with `role_id`/`tenant_id`/`job_id`/`attempt`/`stage_duration_ms`; Prometheus queue depth, `oldest_pending_age`, in-flight, error rate, p50/95/99 per stage; Grafana panel beside the dispatcher's.

**Estimate**: 8-13 dev days + 8-12 h QA + ~1 DevOps day (v1 was 9-15 + 1-2 infra days — the broker provisioning that blocked v1's M0 disappears). Milestones: **M0** table + worker skeleton (1-2 d, *no longer infra-blocked*) → **M1** roles through the queue (2-3 d) → **M2** worker DB hygiene + lease calibration (1 d) → **M3** observability (1 d) → **M4** cutover dev→qa(24h)→prod behind the flag (0.5-1 d) → **M5** sweep of heavy background tasks (3-5 d).

## Code-verified facts (checked on `dev` @ `b9465656`, 2026-07-28)

- Dispatcher config to mirror (and the numbers **not** to copy) — `app/core/config.py:255-270`: `OUTBOX_DISPATCHER_ENABLED=False`, `POLL_SECONDS=2`, `BATCH_SIZE=50`, **`LEASE_TTL_SECONDS=60`**, `DB_ROLE="echo_dispatcher"`, `DELIVERY_TIMEOUT=30`/`CONNECT_TIMEOUT=10`, `MAX_ATTEMPTS_5XX=10`, `MAX_ATTEMPTS_409=20`, `SKIP_WRITEBACK=True`, `OUTBOX_RETENTION_DAYS=7`, `RETENTION_PURGE_INTERVAL_SECONDS=3600`, `OUTBOX_METRICS_PORT=8001`. The PRD's "7-day retention, same mechanism as the dispatcher" and "60s TTL does not apply" both trace to real values here. Entry point: `app/dispatcher.py` + `app/modules/outbox/dispatcher.py`.
- **Zero Redis** in `app/` or `pyproject.toml` (only false positives in bundled font licenses) — the "first Redis piece in the stack" cost is real.
- The 5 enhancement call sites: public `POST /projects/{id}/roles` `app/modules/role/routers.py:91` (also enqueues `_reload_solution_with_context`), internal twin `internal_routers.py:38`, public standalone `POST /roles` `routers.py:355`, internal standalone `internal_routers.py:170`, retry `routers.py:276` — all going through `_enhance_role_with_context` → `enhance_role(role_id)`.
- In-request **synchronous** JD generation confirmed: `ProjectService.create_role_with_placeholder_project` calls `regenerate_job_description` inline when the payload has no JD — `app/modules/project/service.py:747-748`. This is the one externally visible change and the Changelog entry the PRD promises.
- `RoleService.enhance_role` (`app/modules/role/service.py:449`) is already **never-raises** with best-effort `FAILED` marking (from [[Role enhance pool timeout unhandled (Bug 23808)]]), and `RoleCleanupSchedulerService` sweeps stale `pending`/`enhancing` at 15 min → the double safety net the PRD keeps during the transition.
- M2's "sessions released around external calls (today partial)" = the two explicit `self.repo.db_session.close()` calls at `service.py:485` and `:501`, before the JD call and before the parallel `WorkerGroup`.
- M5 sweep candidates, confirmed in code: `role_service.update_vector` (`role/routers.py:272`, `role/internal_routers.py:114` and `:225`), `talent_service.update_talent_vector_by_id` (`talent/routers.py`, `talent/internal_routers.py`, 3 sites in `talent/experience/routers.py`), `wg.compute_vector` in `organization/job/service.py`, and solution regeneration (`_reload_solution_with_context`, `project/service.py`'s `generate_solution` path).

## Pedro's review — 9 gaps, now a section inside the PRD (2026-07-28)

Signed review against `dev` `b9465656`. **He endorses the approach** ("bien sostenido") and explicitly verified OK: the outbox/dispatcher pattern as described, zero Redis, the sequential+`BYPASSRLS` dispatcher argument for a separate worker, and the in-request sync JD generation. Bonus: **the FE risk can be closed now, not in M1** — `useRoleEnhancementPolling` polls every 60s with no timeout while the stage is `pending|enhancing`, and `shouldShowEnhancementLoader` covers "no JD yet", so deferring the standalone JD to the worker is FE-safe. Everything below I re-verified in the repo — **all of it holds**.

**Blockers**

1. **The cleanup scheduler kills queued jobs → enhancements lost in silence.** `role_cleanup_scheduler_service.py:88-99` runs every 5 min and blind-`UPDATE`s `role SET enhancement_stage='failed' WHERE stage IN ('pending','enhancing') AND updated_at < now() - 15 min`. A job that waits >15 min in queue — exactly what a queue *does* under burst — leaves `updated_at` frozen, gets swept to `failed`, and then the PRD's own idempotency rule ("terminal → skip + ack") makes the worker discard it. No error anywhere. It also races the lease: with a TTL "> p99" (~8-10 min) a post-kill re-execution starts near the sweeper's threshold. The "double safety net" framing in the Anexo is wrong — it's an active conflict. Also: skip-on-terminal must distinguish swept-`failed` from retries-exhausted-`failed`.
2. **`≥99% ENHANCED < 10 min` is arithmetically incompatible with this PRD's own capacity math.** The committed load test (100 req/min × 5 min = 500 jobs) against the proposed sizing (2 pods × 8 = 16 in-flight, 2-5 min/job ⇒ ~4.5 jobs/min) drains in **~110 min**, p99 ≈ 108. Hitting 99% <10 min would need ~150-175 concurrent jobs — past the AI providers' rate limit the PRD itself names as the ceiling. The criterion was inherited from v1, where concurrency *was* incoming traffic; v2 deliberately trades queue latency for stability and must say so. Split the SLO into (a) 201 p95 <500ms, (b) time-to-start in steady state, (c) "the queue drains in X" under burst. **Corollary: open question 3 (sizing) can't be answered before this — sizing is a consequence of the SLO.**
3. **"Serialize the context" is not enough — `is_internal` is a correctness guard, not tenancy metadata.** `outbox/writer.py:25-35` never emits when `is_internal`, precisely to avoid a TrackerRMS sync loop, and both internal creation endpoints set it via `mark_sync_context` (`role/internal_routers.py:131`). If the job doesn't persist and restore `is_internal`/`is_sync_operation`/`authenticated`, an enhancement originating in `/internal/roles` **will emit outbox from the worker** — the exact loop of [[Outbox skips internal-originated emits (Bug 23656)]]. Worse, RLS reads `auth.jwt() ->> 'sub'` and sessions are built from `req_ctx.jwt` via `set_config('request.jwt.claims', …)` (`database/base.py:348-364`), so "rebuild the context" means **storing JWT claims in the jobs table**: PII/quasi-credential material in `payload` JSONB with 7-day retention, plus expiry (a 10-min retry runs on a dead JWT; a deactivated user keeps "acting"). Precedent for the alternative exists: `candidate_email_worker_service.py:299-302` synthesizes `RequestContext(authenticated=False)` + explicit tenant scoping. **Decision: (A) impersonate the creator vs (B) synthetic context — he recommends B**, and asks the PRD to enumerate the context fields verbatim instead of saying "multi-tenant context".

**Important**

4. **Zero multi-tenant fairness.** FIFO on `available_at` + bounded concurrency ⇒ one tenant importing 300 roles parks every other tenant's single manual role behind them. Needs a `priority` column, round-robin claim by tenant, or "global FIFO accepted" as a conscious decision. This — not aggregate throughput — is what users perceive (ties into #2).
5. **Dedup can't stay "optional".** With at-least-once + leases on 2-5 min jobs, *concurrent* double execution of the same role is expected. "Stages are overwrite-safe" (inherited from v1) is a property of *sequential* re-execution: `create_match_applications` is an upsert and tolerates overlap, but `evaluate_application_batch` and `update_screening_questions` re-run whole → double AI spend and results stomping each other. Commit to a partial unique index on active jobs by `(kind, entity_id)`, and define `retry-enhancement`'s semantics (409 if a job is active, or enqueue anyway?).
6. **Connection budget unquantified.** The pipeline doesn't use one connection per job: `enhance_role` spawns a `WorkerGroup` and each thread gets its own `DatabaseResource` ⇒ ~3 connections/job ⇒ ~24/pod ⇒ ~48 new Supavisor clients at 2 pods. With `DB_USE_NULLPOOL` (prod via pooler 6543) worker concurrency **is** the connection limit — a DevOps sizing item missing from dependencies. Minor: the PRD quotes prod pool as 20+10; repo defaults are 30+100 (`core/config.py:53-54`) — say those are Vault values.
7. **No deploy shutdown policy, only a chaos test.** With 2-5 min jobs and the default `terminationGracePeriodSeconds` (30s), **every deploy kills all in-flight jobs**, which then wait out the lease TTL. The dispatcher can cut between events; this worker can't. Commit to grace ≥ p99 + a preStop that stops claiming and drains, or accept re-execution per deploy — in which case #5 becomes critical.
8. **It's 5 enqueue sites, not 4 — plus a sixth path M4 doesn't cover.** Real sites: `role/routers.py:112`, `:290`, `:374`, `role/internal_routers.py:55`, `:181`. The missing amplifier is `project/service.py:491`: `generate_team` fans `enhance_role` out over every role of the project in a `WorkerGroup(max_threads=5)` **and joins in-request**. The PRD pushes it to M5, but M4's "Done" declares §3's criteria met in prod — with that path still in-request, "zero SSL-closed" isn't covered for `POST /projects`. Structural point: today the enhance decision lives in the **router** (`add_task`) while `_create(enhance_role=False)` disables it in the service; a transactional enqueue must live in the service (like `write_outbox`) → the PRD should mandate **one single decision point**, or the flag ends up split across two owners.
9. **Flag rollback strands queued jobs.** If the flag also stops the worker (as `OUTBOX_DISPATCHER_ENABLED` stops the dispatcher, `app/dispatcher.py:28-30`), queued jobs sit there and the sweeper marks their roles `failed`. Needs two flags or drain-then-disable: the flag cuts *enqueue*, the worker keeps draining.

**Minor**: a **third queue pattern already exists** in the repo and the PRD doesn't mention it — `CandidateEmailWorkerService` (APScheduler inside the web pods, advisory lock, atomic claim, stale reaper); it's the precedent for both the synthetic context and the reaper, and today it's hidden under "OUT: migrate existing schedulers" — say whether it converges into `background_job`. • `OUTBOX_METRICS_PORT=8001` is taken — the worker needs its own port + ServiceMonitor. • The metric that governs the *user-visible* SLO is missing: **queue wait / time-to-start** (`oldest_pending_age` alone can't tell "long job" from "clogged queue"); add an `attempts` histogram too. • Schema needs `updated_at`/heartbeat if the lease is renewable (only `locked_at` today), and must state whether `payload` holds JWT claims (changes the table's data classification and retention). • `tests/system/test_outbox_atomicity.py` already exists as the template for M1's atomicity test.

## Gotchas

- The worker **cannot** reuse the dispatcher's `BYPASSRLS` role posture: enhancement runs tenant-scoped code, so the job must carry the serialized `RequestContext` and the worker must `SET LOCAL request.tenant_id` per job. This is the PRD's risk #1 and the one an implementer is most likely to get subtly wrong — see the `background_request_context` gotcha recorded in [[Outbox skips internal-originated emits (Bug 23656)]] (`TenantScopedRepository` only auto-injects the tenant inside a request context; otherwise INSERTs fall back to the hardcoded Taller `server_default`).
- Chaos criteria (`kill -9`, rollout with a loaded queue) live in `tests/system` — **CI runs `tests/unit` only**, so they will never gate a PR. Plan them as manual/scripted verification.
- The alembic revision must use a real random id, and heads must be checked with `alembic heads` (not regex) — repo rules.

## Pending

- **Close Pedro's 3 blockers first** (sweeper-vs-queue authority, SLO redefinition, context strategy A-vs-B) — the SLO one gates open question 3, so sizing can't be answered before it.
- Then the 6 important ones (fairness, committed dedup index + retry semantics, connection budget, shutdown/drain policy, single enqueue decision point + `generate_team`, split enqueue/worker flags) and the 5 minors (CandidateEmailWorker precedent, metrics port, time-to-start metric, heartbeat column + JWT-in-payload classification, reuse `test_outbox_atomicity.py`).
- Then Azure Feature/US + milestone tasks (nothing created yet).
- Remaining inherited open questions: failed-enhancement UX (product/FE), client-side idempotency keys (whoever runs migrations), completed-job retention [7 d], `oldest_pending_age` thresholds for the alert **and** the Redis re-evaluation trigger, Kforce backport modality.
- Scope amendment owed to the sibling PRD: M1 must list **5** creation/retry endpoints + `POST /company/jobs/{job_id}/roles` if [[Create Role from Open Job (PRD 887e)]] ships first.
- FE risk can be closed now (polling verified unbounded) instead of waiting for M1.
- DevOps dependency: new worker Deployment in Helm/ArgoCD + per-env Vault flag/secrets. **No new data infra** — the difference that unblocks v1's M0.
- Confirm with the FE that `useRoleEnhancementPolling` needs no change (expected: none; validate in M1).

## Related

- [[Create Role from Open Job (PRD 887e)]] · [[Role enhance pool timeout unhandled (Bug 23808)]] · [[Outbox poll backoff (Bug 23522)]] · [[Outbox skips internal-originated emits (Bug 23656)]] · [[Sentry observability rollout (US 22295)]] · [[similar_role null-vector 500 (Bug 23362)]] · [[Map - Observability & Reliability]] · [[Map - TrackerRMS integration]]
