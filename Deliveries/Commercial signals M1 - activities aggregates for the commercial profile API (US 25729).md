---
type: delivery
status: shipped-prod
env: both
delivered: 2026-11-02
tags: [feature, internal-api, kforce, data-team, background-job]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2491"
  - "https://github.com/taller-projects/echo-backend/pull/2496"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25729"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25734"
prd: "https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C"
---

# Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)

Juani's (data team) `tenant_commercial_profile_api` v1.1 needs per-tenant aggregates instead of rows. M1 adds `GET /internal/commercial-signals/activities`, which serves job orders, send-outs, placements and client visits grouped by kind × line of business × job function × assignment type × industry × period, plus buyer titles and the complete organizations list. A daily snapshot refreshed on the worker backs it, because a live aggregate over KForce's ~1.5M activities outlives the 20 s statement timeout. No FE involvement (internal surface).

## Azure / docs
- [Feature 25728](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728) → [US 25729](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25729) (M1, **Closed** 2026-11-02 on merge, PR linked; merge comment 29240911) · M2-M5 = US 25730-25733 · [Task 25734](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25734) API keys per tenant
- Request doc (the contract): [echo-backend: endpoints commercial-signals](https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C) (Juani, 2026-10-29, forwarded by Pedro)
- Repo note: `docs/commercial-signals.md`

## PRs
- [#2491](https://github.com/taller-projects/echo-backend/pull/2491) → dev — **MERGED** 2026-11-02 (squash `e985f5e8`, Gisel APPROVED on `ee15227b`; opened 2026-10-30 at `a01d2687`), branch `25729/commercial_signals_activities`
  - Review r1 (2026-10-30): Leo CHANGES REQUESTED (2 blockers: no test for 2nd refresh / stale-by-age / missing tenant; tests bypass entry points) + 5 contract questions for Juani + nits; Gisel agreed + 2 questions (kforce-prod EXPLAIN, hourly retry of a failing refresh) + nits.
  - r1 fixes pushed 2026-11-02: dev merged `cc299a71` + `0be83afd` (worktree `.claude/worktrees/25729-commercial-signals-r1`, branch `25729/commercial_signals_review_r1`, pushed to `HEAD:25729/commercial_signals_activities`). Pushed on the user's request before the full local suite finished; targeted tests 22/22 green, commercial_signals module 100% covered.
- [#2496](https://github.com/taller-projects/echo-backend/pull/2496) → dev — **MERGED** 2026-11-03 (squash `48edd22e`; Leo APPROVED 2026-11-02 with 2 non-blocking nits → fixed in `64e48a89`: a test whose min/max date sits in a `limit`-cut row + docs say the dates are on every kind; scope-note comment 29247471 on US 25729 for nit 3; CI green, squash-merged to dev); branch `25729/commercial_signals_totals_dates` (worktrees `25729-totals-dates`, `25729-totals-nits`): `totals` rows carry `first_start_date` / `last_start_date` (min/max over every group of the kind × period, honor `exclude_org_ids`, null for undated). No migration (rollup already has first/last per row). Juan asked for it; his client already reads them. Linked to US 25729 (Closed, not reopened, user's choice). Local: commercial-signals unit + multitenancy 28/28.
- Consumer side (tenant_commercial_profile_api, Juan): [PR 13402](https://dev.azure.com/TallerInternTools/Echo%20Core/_git/tenant_commercial_profile_api/pullrequest/13402) (stop sending recent_since/since + totals) — my review thread 33679 + APPROVED; [PR 13410](https://dev.azure.com/TallerInternTools/Echo%20Core/_git/tenant_commercial_profile_api/pullrequest/13410) (exclude_org_ids repeated keys + omitted when empty, totals only, engagement drops period≠recent, RECENT_WINDOW_MONTHS 24→12, fixtures) — thread 33691 + APPROVED 2026-11-02; still open (master = 13402 merge), on their dev.

## How
- Module `app/modules/commercial_signals/`, mounted at `/internal/commercial-signals`. Tenant comes from `X-Echo-Api-Key`; no module or feature gate.
- Migration `65o0viylh9b3` (after `w3kq8vd2mhtp`):
  - `commercial_signal_snapshot`: one row per (tenant, signal).
  - `commercial_signal_rollup`: rows at dimensions × period × organization grain, with a composite FK `(snapshot_id, tenant_id)` ON DELETE CASCADE.
  - Both tables get a tenant RLS policy.
- Refresh:
  - Hourly `CommercialSignalsRefreshSchedulerService` in the web pods enqueues `JobKind.COMMERCIAL_SIGNALS_REFRESH` (entity = tenant) when a snapshot is missing or older than 23 h. The active-job unique index dedups across pods.
  - The worker handler runs `refresh_activities`: 16 relationship-id slices → Python fold → industries via `OrganizationService.get_names_and_industries` → snapshot swap in one transaction.
  - On demand: `scripts/refresh_commercial_signals.py`.
- Reads go through the owning services: `ActivityService.aggregate_by_company` / `aggregate_titles_by_company` / `tenant_has_activities`, `TenantService.list_ids`.

## Decisions
- `recent_since` is fixed per refresh (today − 365 d), echoed; any other value → 422 `recent_since_unsupported`. The period grain is ~74k rows on kforce-dev; a day grain would be ~701k. (User approved 2026-10-30.)
- `organizations` is always inline and complete (21,296 on kforce-dev). M5 is only needed if the list becomes a problem. (User approved.)
- Undated stays `undated`: 63% of job orders have no start_date, and `created_at` is the ingest date.
- Buyer title = `btrim(relationship.role)`, empty roles excluded. The contact_job fallback was dropped (it fills 37 of 35,175).
- Tenant scope = `relationship.tenant_id`, not the contact semi-join (same isolation, ~6 s cheaper).
- `limit` = top N per kind × period, default 100, max 5000.

## Gotchas
- `Row.count` is the tuple method. Since r1 the cross-module aggregates return NamedTuples (`ActivityCompanyAggregate`, `ActivityTitleAggregate`, `OrganizationNameAndIndustry`), so no `_mapping` lookups remain in the service.
- ORM bulk `insert(Model)` drops None keys and splits the batch, so the rollup uses `insert(Model.__table__)`.
- The main `.venv` lacked `nh3` (from #2489), so I ran `uv sync --frozen` to build a worktree-local venv.
- Throwaway alembic check needs `DB_ADMIN_ROLE=<db user>` (env.py does `SET LOCAL ROLE`); full-chain `alembic check` fails on Supabase auth functions, unrelated.
- The kforce-dev timings (worst statement 3.5 s, slices 66 s from a laptop, names 3.8 s) are in the PR body.

## Review r1 — what changed (`0be83afd`)
- Tests through entry points: refresh via `build_handlers(...)[COMMERCIAL_SIGNALS_REFRESH]`, enqueue via `CommercialSignalsRefreshSchedulerService._enqueue_stale`, other tenants over HTTP with their own API key. New cases: replacement after max age, missing tenant, malformed / entity≠tenant job, recent_since midnight boundary, 401/422 edges, limit on by_group, exclusion lowering the org count.
- `ActivityPeriod` (activity schemas) is the single period enum; `SignalPeriod` removed. Handler rejects `entity_id != tenant_id` (NonRetryable). Script sets tenant + is_internal. `repo.commit()` instead of raw commits. Refresh returns/logs `read_seconds` / `write_seconds`. `tenant_has_activities` uses relationship.tenant_id. `exclude_org_ids` max 100 (query-string length).
- Not changed (reasons drafted for the PR reply): REPEATABLE READ in `get_activities` (isolation can't change after the API-key lookup opened the transaction; untestable without concurrency), per-tenant enqueue commit (savepoint already isolates the unique race), scheduler disabled/rollback tests (need mocking our code), failing-tenant test (job isolation = worker property).

## Juani's answers (2026-11-02) + `91c0f16b`
- `recent_since`: fixed 365-day window confirmed; consumer omits it (their branch `fix/signals-backend-window`) and reads the echoed one. **Merge their branch before #2491 reaches dev** (they sent today − 24 months → 422). No per-tenant / multi-window / free date. relationships + deals: same rule.
- Buyer title as-is (no null bucket); undated OK (no created_at); client_visit not consumed; exclude_org_ids ≤ 100 fine; source_updated_at proposal OK but low priority (they only store it).
- `limit` affected them (they summed by_group) → added `totals` per kind × period (count, distinct orgs), uncut by limit, honoring exclude_org_ids.
- Gisel Q2 done: the tick skips a tenant whose refresh job ended failed/dead within 23 h (`failed_job_entity_ids` in background_job writer).
- Interactions (M4, US 25732): no free since/until; they want the no-param response cut to the snapshot window with effective since/until, or everything with `period` and they filter `period = recent` — we must tell them which.
- Answers posted on the PR: https://github.com/taller-projects/echo-backend/pull/2491#issuecomment-6580767694 ; body refreshed (totals, backoff, merge order).

## `ee15227b` — source_updated_at (user: "en este PR", 2026-11-02)
- Snapshot keeps `content_hash` (sha256 of its rows; column added to the unmerged `65o0viylh9b3`). Rows differ from the previous snapshot → `source_updated_at = computed_at`; same rows → `max(updated_at)` never moving back; first snapshot → plain max.
- Why a hash: `organization_insight` has no updated_at and industry edits don't touch `organization.updated_at` (joined inheritance), so industry can't be tracked by timestamp; deletions leave no timestamp either.
- Caveats in docs: the yearly window shift changes the rows → on KForce it moves on most refreshes; org renames are not covered (names resolved at read time).
- Mutation-checked: dropping the bump fails both "moves" cases.

## M2 research — relationships (US 25730), 2026-11-03
Measured on kforce-dev from a laptop (cold cache, session pooler), before any code:
- `contact_relationship` by type: Client 1,031,470 (1,029,971 **without `start_date`**, 94,046 empty `role`, 890,590 with `activity_dates`, 3 with a future `end_date`), Prospect 12,040 (all undated, no empty role), Consultant 457,209 (candidate side, out of scope). 52,568 Client companies / 476 Prospect; 996k distinct Client contacts. Only **34 of 52,570** counted companies have an `organization_insight.industry` on kforce-dev.
- dev (Taller instance): Navitec Client 558 (364 undated, **all 558 empty role**, 290 recover a title from an open `contact_job` at the company) / Prospect 57 (all undated, 25 recover); Taller Client 212 / Prospect 309, all dated, no empty roles. So the `contact_job` title fallback matters for Taller-shaped tenants (M1 dropped it for activities because it filled 37 of 35k on KForce; here it fills 14 of 94k on KForce but 315 of 615 on Navitec).
- Cost per 1/16 relationship-id slice (65k rows): plain aggregate (type × company × period, distinct contacts, max start_date) 16 s cold / 0.35 s warm (heap I/O); **the `_relationship_is_active_expr` predicate 82-97 s** — the correlated `contact.last_interaction_date` lookup costs ~0.94 ms × 64k rows (random heap reads over a 864 MB table, 2M contacts); a JOIN to contact plans as the same nested loop (74 s). The `contact_job` / `contact_interaction` EXISTS are cheap (~1 s per slice).
- Only **28,304 contacts** on kforce-dev have `last_interaction_date` in the last 12 months (65k of 3M interactions); listing them via `ix_contact_tenant_id_last_interaction_date` takes 20 s cold (heap fetches), so it must itself be sliced (by date window) or served index-only.
- **Industry coverage, kforce-prod (user ran it in the Supabase SQL editor, 2026-11-03, for Juan's question)**: 1,552 of 22,180 companies with activities have an `organization_insight.industry` (~7%), but they are the big clients: 54% of job orders (401,824 / 746,998), 56% of send-outs (332,888 / 591,497), 49% of placements (215,889 / 437,630) carry an industry. No client_visit rows on prod. Other sources barely help: industry comes from the LinkedIn scrape; of the ~20.6k companies without one, only 40 have a `linkedin_url` and `organization_job.industry` fills 10. kforce-dev is far worse (16 of 21,219 companies, ~6% of activities), so never judge KForce industry coverage from dev.
- **kforce-prod (user ran it in the Supabase SQL editor, 2026-11-03)**: Client 1,079,568, **0 Prospect rows**, all with a company, **100% without `start_date`** (so `period` by start date = all `undated`, `last_start_date` always null), 64,680 (6%) with an activity bound in the last 365 days, 0 future `end_date`, 64,070 empty `role` of which **9,581 recover a title from an open `contact_job`** at the company (vs 14 on kforce-dev → keep the fallback). Query 2 (fixed): 52,296 counted companies, **2,063 with an industry (4%)**; 1,078,498 distinct contacts (≈1 relationship per contact); 2,017,732 contacts, **63,329 with an interaction in the last 12 months** (the pre-fetch set for the active predicate); live tuples: contact_relationship 1.53M (CLAUDE.md's 9M is stale), contact_interaction 3.3M, **contact_job 6.6M** (118k on kforce-dev — the contact_job EXISTS probes cost more on prod).
- `_relationship_is_active_expr` has no Prospect arm → every Prospect relationship is Past → `active_relationships` = 0 for Prospect groups under the AC ("matches Relationship.state").

## Pending
- Deploy: run 32370 (`e985f5e8`) FAILED on the test job timeout; dev + kforce-dev got M1 with run 32407 (`71a12c99`, ReleaseDev + ReleaseKforceDev succeeded 2026-11-02 23:06Z). First refresh ran on the worker 2026-11-02 22:12-22:14Z: kforce-dev 294,111 rollup rows in 1 m 45 s (`source_updated_at` 2026-10-08, the last ingest); dev 54 tenants, 0 rows each (no activities). ~~Risk:~~ earlier risk: the Azure "Lint and tests" job has no `timeoutInMinutes` (agent default 60) and since #2490 `scripts/test.sh` runs with `--cov` → job went 31–37 min → 54 min (32319) → canceled at 60.2 min (32356, #2493 never deployed).
- Migration re-verified on `ee15227b` before merge (throwaway pg16: create_all minus the 2 tables + stamp `w3kq8vd2mhtp` → upgrade / downgrade -1 / upgrade OK; `alembic check` fails only on Supabase `handle_new_user` (schema `echo`), env-only).
- ~~`exclude_org_ids` CSV vs list~~ → fixed on the consumer side (PR 13410, repeated keys, omitted when empty); backend keeps `list[UUID]`.
- After deploy: first refresh runs on the worker (`ENHANCEMENT_WORKER_ENABLED` per env), read/write seconds in `commercial_signals_refreshed`.
- Task 25734: one internal API key per tenant and env; consumer smoke on kforce-dev with Juani.
- M4 interactions shape TOLD (13410 thread 33691, 2026-11-02): all history, every row labelled by `period` against the snapshot's `recent_since`, no since/until (same contract as the other endpoints; US 25732's since/until params are dropped). Update US 25732 accordingly when M4 starts.
- ~~#2496 merge~~ done 2026-11-03 (`48edd22e`; scope-note comment 29247471 on US 25729 covers Leo's nit 3; a duplicate comment from a second session was deleted). Consumer nit `row.get("period", "recent")` drops explicit null (we never send null).
- M2 relationships (US 25730): decided + opened as [#2500](https://github.com/taller-projects/echo-backend/pull/2500) 2026-11-03 → [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]].
- M2-M5 (US 25730-25733); qa/main promotion (consumer master must have 13402 before activities reaches main).
- **2026-11-11**: on prod + kforce-prod since 2026-11-05 ([#2530](https://github.com/taller-projects/echo-backend/pull/2530) / [#2531](https://github.com/taller-projects/echo-backend/pull/2531), build 32641). Task 25734 closed without new keys → [[Commercial signals - consumer API keys per tenant (Task 25734)]]. echo-prod refresh verified (67 tenants daily since 11-05, no failures). What is still open lives in [[Map - Commercial signals]].

## Related
- [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]]
- [[Map - Kforce]]
- [[Map - Commercial signals]]
