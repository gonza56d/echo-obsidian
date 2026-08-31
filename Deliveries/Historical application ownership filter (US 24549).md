---
type: delivery
status: merged
env: taller
delivered: 2026-08-31
tags: [feature, talents, filters, applications, ownership, jazz-retirement, performance]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2180"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24549"
prd: "https://app.notion.com/p/tallertechnologies/Jazz-ownership-history-migration-3c7aedca11f0817ebb2ce7fee6aac68f"
---

# Historical application ownership filter (US 24549)

New `application_owner_id__in` query param on `GET /talents`: "candidates I
have ever worked with" — talents having ANY application whose sticky
`owner_id` is one of the given members. **Pure application history** by
explicit decision: NULL-owner applications (still in `matching`) never match,
and the talent-level current owner stays `owner_id__in`'s job (the PRD's two
filter modes: current owner = existing filter, owner-at-any-point = this one).

## Azure / docs

- [US 24549](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24549) — mine, In development. Child of Epic 24545 "Remove Jazz". PR linked in comment 28703943.
- Sibling [US 24546](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24546) (Nicolás) = the Phase-1 Jazz data migration that back-fills per-process `application.owner_id` — **this filter only becomes truly useful once that lands**.
- PRD: [Jazz ownership history migration](https://app.notion.com/p/tallertechnologies/Jazz-ownership-history-migration-3c7aedca11f0817ebb2ce7fee6aac68f) (Phase 2).

## PRs

- [#2180](https://github.com/taller-projects/echo-backend/pull/2180) → dev — **MERGED 2026-08-31** (squash `d4d4b957`, Leo approved, CI green). `4c1c5df7` filter + 6 query-level unit tests; `1ecef92a` self-review nit fixes (empty-list = match-nothing, DISTINCT subquery, `status=None` fixture pins, +2 tests); `11e27546` Leo's nits 2+3 (endpoint tests through `GET /talents` + dedup contract test) — 11 tests total. His nit 1 (move to tests/system) declined: CI runs tests/unit only, the file would never execute. Merge noted on the US (comment 28704439); state left In development.

## How

- `TalentFilter.application_owner_id__in: list[uuid.UUID] | None` applied via
  `_apply_application_owner_filter` (consume-then-filter pattern like
  `_apply_rehire_filter`).
- **Query shape: `talent.id = ANY(ARRAY(subquery))`** — the uncorrelated
  subquery becomes an InitPlan (one probe of `ix_application_owner_id`), outer
  scan probes the talent PK, top-N sort. EXPLAIN ANALYZE on dev DB (81k
  talents / 126k apps, busiest recruiter 1,752 apps / 826 talents):
  **13 ms page + 5.5 ms count** vs ~160 ms for correlated EXISTS / IN(subq)
  (planner walks the whole `created_at` index probing per talent under the
  paginated ORDER BY) and 130 ms for a COALESCE variant. No new index needed.
- Tenant scoping: `Application.tenant_id == TenantContext.current_tenant_id()`
  INSIDE the subquery — **must stay uncorrelated** (correlating
  `Talent.tenant_id` degrades the InitPlan to per-row execution).

## Decisions

- **Pure application history** (user-confirmed): no OR with talent-level
  current owner (that hybrid measured ~70 ms and duplicates `owner_id__in`).
- Name `application_owner_id__in` over "historical_owner"/"any point"
  variants — says literally what it matches.
- No ownership-transitions table exists anywhere (checked code + dev DB);
  "history" = the per-application sticky `owner_id`. If the Phase-1 migration
  ever adds transition rows, this filter is unaffected (owner sequence display
  would be a separate feature). Review flagged the flip side: within-app
  transfers (`ApplicationService.transfer_owner`) overwrite `owner_id` in
  place (old owner only in Loki logs) — when Phase 2's sibling US builds the
  transition store, this filter should union over it or a transferred-away
  recruiter loses the candidate again. Noted as PRD/sibling-US follow-up,
  not this PR.
- **Empty list matches nothing** (review nit, `1ecef92a`): `?application_owner_id__in=`
  parses to `[]`; originally consumed as absent → unrestricted, the opposite
  of the generic `__in` contract (`IN ()` → zero rows). Guard is now
  `is None`, `[]` flows into `in_([])` = always-false. Settled pre-FE so the
  wire contract never flips.

## Gotchas

- Local testing detour: `.env`'s `DB_URL` points at the **dev Supabase pooler**
  and overrides `POSTGRES_*` — the docker-compose app serves dev data; the
  local postgres container is stale (June) and unused by the app. A 10 s
  request through the local app = ~20 statements × ~200 ms transatlantic RTT,
  NOT the filter (server-side confirmed 10.2 s cold → 6.5 s warm; filter SQL
  itself 13 ms).
- Docker daemon wedge during this work = Docker VM disk full (25 GB build
  cache). `docker builder prune -af` + container/dangling-image prune freed
  ~27 GB; volumes untouched.
- An `alembic upgrade head` intended for the local container ran against dev
  via that same `DB_URL` — verified no-op (dev already at head
  `lptf6d2fvqo5`), but: **always override DB_URL, not just POSTGRES_HOST**.
- EXPLAIN benchmarks ran as superuser = RLS bypassed; under the app role the
  application policy adds per-row cost. Plan shape keeps it bounded; check
  Grafana after dev deploy.
- Bruno request added: Echo collection (`~/taller/Echo`) → `Talents` →
  "List by application owner (24549)" ({{HOST}}/{{AUTH}}; example uuid is
  dev's busiest recruiter `b5200d9d…`, expected total 826).
- **The local TestClient-404 artifact on talent endpoints is avoidable**: the
  rehire-filter tests' pattern — module fixture toggling
  `settings.ENABLE_ACCESS_CONTROL = False` at fixture run time (not import
  time) — makes `GET /talents` endpoint tests pass locally. Update the old
  "validate at service level" reflex when that toggle applies.
- Two applications for the same talent need distinct roles:
  `uq_application_tenant_role_talent`. `mocked_role_factory` (conftest)
  mints extra roles cheaply.
- A dedup test on the outer results is vacuous: the filter is a WHERE on
  Talent (can't duplicate rows), so locking the subquery `.distinct()`
  requires asserting `SELECT DISTINCT` in the compiled SQL.

## Pending

- qa/main promotion per release flow (merged to dev only so far).
- FE change filed as [Task 24664](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24664)
  (child of US 24549, unassigned — frontend-owned): expose the param as the
  "owner at any point" mode of the recruiter filter (FE
  `recruiterFilterConfig.tsx` currently sends only `owner_id__in`). Linked in
  the PR body.
- Real-data usefulness gated on [US 24546](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24546) (per-process ownership migration from Jazz) — today most historical apps carry the collapsed snapshot owner.
- Kforce sibling: N/A (Remove Jazz epic is Taller-specific).

## Related

- [[Per-application recruiter from Jazz back-sync (Bug 24241)]] — the enablement that made `application.owner_id`/`jazz_owner_id` per-process; this filter reads what that (plus the 24546 migration) writes.
- [[Map - JazzHR integration]]
