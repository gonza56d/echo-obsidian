---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, internal-api, kforce, data-team, background-job]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2491"
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
- [Feature 25728](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728) → [US 25729](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25729) (M1, **In revision**, PR linked) · M2-M5 = US 25730-25733 · [Task 25734](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25734) API keys per tenant
- Request doc (the contract): [echo-backend: endpoints commercial-signals](https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C) (Juani, 2026-10-29, forwarded by Pedro)
- Repo note: `docs/commercial-signals.md`

## PRs
- [#2491](https://github.com/taller-projects/echo-backend/pull/2491) → dev — **OPEN** 2026-10-30, commit `a01d2687`, branch `25729/commercial_signals_activities`

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
- `Row.count` is the tuple method: read aggregate rows through `row._mapping["count"]`.
- ORM bulk `insert(Model)` drops None keys and splits the batch, so the rollup uses `insert(Model.__table__)`.
- The main `.venv` lacked `nh3` (from #2489), so I ran `uv sync --frozen` to build a worktree-local venv.
- Throwaway alembic check needs `DB_ADMIN_ROLE=<db user>` (env.py does `SET LOCAL ROLE`); full-chain `alembic check` fails on Supabase auth functions, unrelated.
- The kforce-dev timings (worst statement 3.5 s, slices 66 s from a laptop, names 3.8 s) are in the PR body.

## Pending
- The full local unit + multitenancy suite was still running when the PR was opened; confirm it and CI.
- Tests predate the team testing practice CLAUDE.md section added 2026-10-30 (names `test_<entry>_<outcome>_when_<condition>`, Given/When/Then, entry points rather than direct service calls). Align them if reviewers ask.
- Review + squash-merge; then close US 25729.
- Worker must run with `ENHANCEMENT_WORKER_ENABLED` per env (check prod / kforce-prod).
- Task 25734: issue one internal API key per tenant and env; consumer smoke on kforce-dev with Juani.
- Answer Juani's checklist in the doc (owner/ETA, rollup mechanism, org list decision); stage mapping is M3.
- M2-M5 (US 25730-25733).

## Related
- [[Map - Kforce]]
