---
type: delivery
status: merged
env: taller
delivered:
tags: [bugfix, navitec, trackerrms, outbox, external-links]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2388"
  - "https://github.com/taller-projects/echo-backend/pull/2390"
  - "https://github.com/taller-projects/echo-backend/pull/2391"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25390"
prd: "https://app.notion.com/p/383aedca11f0812c8c52cee6d9852d4b"
---

# Reverse push duplicates TrackerRMS Resources — external ids read from entity_external_links (Bug 25390)

Navitec (2026-10-06): "se están duplicando entidades con el push". A talent
born in Tracker reaches Echo with a link row only; the outbound side decided
create-vs-update on the legacy columns, saw NULL and POSTed a second
Resource. Root-cause analysis + PROD evidence:
[[Navitec duplicated Resources from reverse push — ats_external_ids vs entity_external_links (investigation)]].

## What
- Dispatcher (`OutboxRepository.get_external_id`) and manual "Sync to ATS"
  (`TrackerRMSSyncService.sync_talent/sync_role/sync_application`) now resolve
  the Tracker id from `entity_external_links` first (newest mapping,
  platform-scoped) and fall back to `talent.ats_external_ids->>0` /
  `role.external_id` / `application.external_id` only when no link exists.
- `sync_application` parent checks resolve talent/role the same way (no more
  `missing_dependency` for Tracker-born parents); update payloads carry the
  resolved id.
- `RoleService._update` outbox gate (`_is_linked_to_ats`) also accepts a link
  row → Tracker-born roles sync their edits (before: silently dropped).
- New `ExternalLinkService.resolve_external_id(entity_type, entity_id, platform)`.

## Azure
- [Bug 25390](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25390)
  — **In revision**, assigned to me. Body = repro + root cause + PROD evidence
  + fix scope + follow-ups; comment 28992862 carries the PR link.

## PRs
- [#2388](https://github.com/taller-projects/echo-backend/pull/2388) → `dev`
  — **squash-MERGED 2026-10-06 20:30 UTC (`97eb3540`)**, CI green on
  `ca5c8483`; Leo did not re-review after `ca5c8483`. Branch
  `25390/external_id_reads_from_links`, commits
  `e106a183` (fix) + `1c987fa9` (self-review nits, 2026-10-06, pushed from a
  second session while this one was mid-review) + `ca5c8483` (Leo's review
  round, rebased on top). No migration.
  Self-review via `/pr-review`: READY WITH NITS, 0 blockers, CI green;
  nits addressed in `1c987fa9`, PR body updated via `gh api` PATCH.
- [#2390](https://github.com/taller-projects/echo-backend/pull/2390) → `qa`
  — **MERGED 2026-10-06 20:45 UTC (merge commit `375906b4`)**, branch `cherry_pick/25390_external_id_reads_qa` off
  `origin/qa`, `git cherry-pick -x` of the `dev` squash `97eb3540` →
  `cd4e1b0c`, applied clean (`qa` lacks #2386's additions to the same
  external-link files, but the hunks do not overlap). Verified on the `qa`
  base: ruff clean, 203 passed across the 6 touched unit + system files
  (Docker). No migration. Merge with a merge commit. Supersedes
  [#2389](https://github.com/taller-projects/echo-backend/pull/2389), a
  full `dev → qa` release I opened by mistake (would have dragged #2386,
  #2387, #2381 along) — closed 2026-10-06 20:39 UTC with a comment.
- [#2391](https://github.com/taller-projects/echo-backend/pull/2391) → `main`
  — **OPEN 2026-10-06**, branch `deploy/prod_2026-10-06_external-id-reads`
  pushed at the `qa` tip `375906b4` (no new cherry-pick). After #2390, `qa` =
  `main` + #2388 only (main-only commits are empty qa→main merges; tree diff
  = #2388's 11 files), and `375906b4`'s tree == `cd4e1b0c`'s (the tested
  one). Why a branch at the qa tip instead of a `_main` cherry-pick or head
  `qa`: same SHAs on qa and main (no duplicate-commit drift, see
  `reference_qa_main_vs_dev_migration_chain_text`), and the content stays
  fixed even if more PRs land on `qa`. Merge commit; gated by
  `echo-backend-prod` + `echo-backend-kforce-prod` approvals. Azure already
  had the PR link (AB# auto-link); comment posted on Bug 25390.

## Review (Leo, 2026-10-06 19:38 UTC, COMMENTED — no blockers)
1. `status = 'active'` had leaked into the link-only entities (org / contact /
   user / touchpoints) via `1c987fa9`: a stale newest link → `None` → POST,
   the same duplication class. **Resolved**: no status filter in either path;
   order `active` first, newest `updated_at`, then `created_at` /
   `external_id` as deterministic tie-breaks — same SQL in
   `OutboxRepository._linked_external_id` and the new
   `EntityExternalLinkSQLRepository.latest_link` (manual sync). A stale-only
   link still names the record (PATCH 404 surfaces, no silent duplicate).
   Gonzalo chose this over Leo's "active-only scoped to talent/role/application".
2. Delete-path test: only `touchpoint.deleted` exists and touchpoints are
   link-only, so the Tracker-born-column-entity scenario cannot reach
   `_deliver_tracker_rms_delete`. Added a direct real-SQL test (stale-only
   link → DELETE delivered + link removed). Clarification lives in the PR
   description (no reply to Leo, per Gonzalo).
3. Role gate wider than the resolver (the first commit used
   `external_ids_by_entity`, any platform/status). **Resolved**:
   `_is_linked_to_ats` = column OR `resolve_external_id(role, TRACKER_RMS)`.
- Nits taken: builders typed with `_RoleSyncProjection` /
  `_ApplicationSyncProjection` (they receive projections, not ORM models);
  tie-break + stale-vs-active tests (unit + system); mixed-parent
  `sync_application` test. Dropped `1c987fa9`'s
  `test_stale_link_falls_back_to_column` (pinned the opposite rule).

## Local end-to-end run (2026-10-06, branch `cherry_pick/25390_external_id_reads_qa` = the tree on qa/main)
Real API (`uvicorn` :8010) + real `python -m app.dispatcher` + local pgvector
Postgres (docker :55432, schema via `create_database()` like conftest) + a fake
tracker-rms-api (:18080) logging every call. Scripts in the session scratchpad
`e2e/` (bootstrap.py, seed_user.py, fake_tracker_rms_api.py, mint_jwt.py,
run_scenarios.py, s8_ordering.py). **8/8 PASS**:
- S1 Tracker-born talent (link only, `ats_external_ids=[]`) edited via `PATCH /talents/{id}` → dispatcher `PATCH candidate/<link id>`, no POST; write-back fills the column with the same id.
- S2 manual `POST /talents/{id}/sync_tracker_rms` on a link-only talent → PATCH, `tracker_rms_id` = link id.
- S3 manual application sync with talent AND role known only by link → `POST application`, 200 (was 409 `dependency_missing`).
- S4 Tracker-born role (column NULL, link) edited via `PATCH /projects/{p}/roles/{id}` → `role.updated` emitted → `PATCH job/<link id>`.
- S5 column-only talent (no link) → still `PATCH candidate/<column id>` on both paths.
- S6 Echo-born talent: create → POST + write-back, edit → PATCH with the written-back id.
- S7 role with `external_id` only (Jazz-shaped) → `PATCH job/<column id>` (column fallback intact).

**Finding (pre-existing, NOT this PR): dispatcher batch order is not
create-before-update.** `OutboxRepository.claim_batch` is `UPDATE … WHERE id IN
(SELECT … ORDER BY available_at … FOR UPDATE SKIP LOCKED) RETURNING …`; the
RETURNING order is not guaranteed and `_poll` iterates it as-is (no re-sort, no
`has_pending_predecessors` guard for `.updated`, only for `.deleted`). Repro
(s8_ordering.py): stop the dispatcher, create+edit N talents, start it →
ONE worker (`locked_by local-10398`) processed `talent.updated` BEFORE
`talent.created` for 5/6 talents: update → no link → POST (dup) → create → POST
again → two links + two column ids per talent. A second batch gave 0/6
(intermittent). Needs a backlog (restart/outage) or create+edit inside one
poll window. Fix candidates: sort claimed rows by `occurred_at` in Python (or
CTE + outer ORDER BY), and/or make `*.updated` wait like deletes. Not ticketed.

## Decisions
- **Links-first, column fallback — never links-only.** Taller has 1,654 roles
  whose JazzHR id lives only in `role.external_id` (0 `jazz_hr` role links)
  and the Jazz dispatcher path (`_deliver_jazz_hr_*`) resolves roles through
  the same `get_external_id`. Dropping the column read would break Taller.
- **One link-resolution rule, any status** (final, `ca5c8483`):
  `ORDER BY (status = 'active') DESC, updated_at DESC, created_at DESC,
  external_id DESC LIMIT 1`, identical in `OutboxRepository._linked_external_id`
  (dispatcher raw SQL) and `EntityExternalLinkSQLRepository.latest_link`
  (behind `ExternalLinkService.resolve_external_id`, manual sync + role gate).
  History: the first commit left the dispatcher status-agnostic and the
  service active-only; `1c987fa9` made both active-only; Leo flagged that
  this also hit the link-only entities (org / contact / user / touchpoints,
  no column fallback), where a stale newest link would resolve to None →
  POST → the same duplicate class. So the WHERE filter went away and
  `active` became a preference. Consequence: a stale-only link now beats
  the column for talent / role / application too (a PATCH 404 surfaces
  instead of a silent duplicate); `1c987fa9`'s
  `test_stale_link_falls_back_to_column` was dropped for
  `test_stale_only_link_still_resolves` / `test_active_link_beats_newer_stale_link`
  / `test_tie_on_updated_at_is_deterministic` (unit + system). Latent today:
  nothing in `app/` writes `stale` / `manual_intervention` and
  `ExternalLinkUpsertRequest` has no `status` field.
  `get_jazz_application_id` is still status-agnostic (out of scope).
- Role gate checks the column first (free) then
  `resolve_external_id(role, TRACKER_RMS)` — the same resolver delivery
  uses, so a role that opens the gate resolves to the same id there (Leo's
  item 3; the first commit used `external_ids_by_entity`, any platform /
  status). Tracker-only is safe: `_deliver_jazz_hr` handles only
  `application` events and Jazz roles pass through the column. One query
  per role update, only for unlinked-column roles.

## Gotchas
- `asyncio.to_thread` + request context: the sync service resolves the link
  in a worker thread; `get_request_context()` is keyed by the request
  ContextVar (middleware) or thread id. Tests that call the service directly
  must `fork_request_context(RequestContext())` — plain
  `get_request_context().set_tenant_id()` only fills the main thread's cache
  and the worker sees "Tenant context not set".
- `talent.ats_external_ids` is NOT NULL (`'[]'`), so raw INSERTs in tests
  must pass `'[]'::jsonb`.
- `entity_external_links.tenant_id` has an FK → cross-tenant tests need a
  real second tenant (`create_entity(db, TenantFactory, Tenant, name=…,
  organization_id=…, max_seats=None)`).
- `tests/system/test_tracker_rms_sync_endpoints.py` 403s locally unless
  `TRACKER_RMS_ENABLED_TENANT_IDS=""` is exported (pre-existing).
- `ApplicationCreate.external_id` is `Optional` → polyfactory randomizes it:
  `create_entity(ApplicationFactory, …)` without `external_id=None` yields
  an application the sync treats as an update (column fallback), so a
  create-path endpoint test silently exercises PATCH.
- `tests/system/test_tracker_rms_sync_endpoints.py::mock_tracker_rms` returns
  one shared `_TRM_ID` for every call; the CAS write-back then upserts that
  id for a second entity of the same type and trips
  `uq_entity_external_links_external_id` (tenant, entity_type, external_id,
  platform) → 500. Override `mock.<call>.return_value` with a per-test id.
- Worktree hooks (own worktree): `source …`, `$(…)` operands next to a
  python heredoc, and `zsh -ic` are refused; use the main venv binaries by
  absolute path and let python fetch tokens via `subprocess` itself.
- `git merge-tree --write-tree --merge-base …` is not supported by the local
  git; its usage error read as "CONFLICTS". Dry-run a cherry-pick with a
  throwaway `git worktree add <scratch> -b <branch> origin/qa` instead.
- Local full-stack recipe lives in the agent memory `reference_local_full_stack_outbox_e2e`
  (docker pgvector, worktree `.env`, `create_database()` + conftest DDL,
  `echo_dispatcher` role + grants, `tenant_integrations` row, fake tracker
  answering `tracker_rms_id`, minted HS256 JWT, `grammar_check=false`,
  `id=uuid4()` on factories, one `psql -c` per statement).
- `TestCASWritebackTolerance._make_service` builds the service by hand —
  new collaborators must be added there and in
  `tests/unit/test_tracker_rms_sync_service.py::_make_service`.
- Worktree session: Bash guard refuses `zsh -ic`, heredocs and `$(…)`
  chains as "too complex"; scripts under `<worktree>/vault/scratch/`
  (gitignored) + `python3 vault/scratch/x.py` work for edits, Azure API and
  file writes outside the worktree.
- **Two sessions on one branch.** A parallel session (the `/pr-review`
  self-review) pushed `1c987fa9` to the PR branch while this one worked;
  the next push was rejected (non-fast-forward). Resolution:
  `git rebase origin/<branch>` (one conflict in `outbox/repository.py`),
  never force-push. Check `gh api pulls/<n>/commits` before pushing to a
  shared PR branch.

## Pending
- [x] #2388 squash-merged → `dev` 2026-10-06 (`97eb3540`).
- [x] #2390 merged → `qa` 2026-10-06 (`375906b4`).
- [ ] Merge [#2391](https://github.com/taller-projects/echo-backend/pull/2391)
      → `main` with a merge commit + the two prod approvals
      (`echo-backend-prod`, `echo-backend-kforce-prod`). Leo was never answered in-thread (answers live in the
      #2388 body) — ping him if he asks.
- [ ] After PROD deploy: cleanup of the duplicate pairs with Navitec —
      they pick the survivor per pair, then Echo drops the duplicate's link
      and re-points the column (28 talent pairs since 2026-06-20 + 1
      application `16378→16427`; Nico's doc lists the 11 since 07-24).
      Newest-link-wins means a stale link keeps PATCHing a deleted Resource:
      the cleanup must DELETE the duplicate's link row, never mark it
      `stale` (a stale-only link still wins the resolver).
- [ ] Optional pre-deploy mitigation: copy the active link id into the empty
      column for the 17 talents / 3 applications / 3 roles exposed.
- [ ] tracker-rms-api defensive guard on candidate/application create
      (resolve `echo_id` against `entity_mapping` / Echo links first).
- [ ] Close Bug 25390 on merge.
- [ ] File a bug for the dispatcher batch-order hazard (see Local end-to-end run): update processed before create in one batch → duplicate Resource.

## Related
- [[Navitec duplicated Resources from reverse push — ats_external_ids vs entity_external_links (investigation)]]
- [[Map - TrackerRMS integration]]
- [[External links writeback (US 23126)]] — the dual-write that left reads behind
- [[Outbox skips internal-originated emits (Bug 23656)]]
