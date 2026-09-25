---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, feature, kforce, contacts, activities, internal-api]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2349"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25154"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25155"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
prd: ""
---

# Kforce activities bulk on_conflict + internal list (Bug 25154)

Round 3 of Emiliano's Kforce push PRD (wave 2: activities `job_order`), asked on 2026-09-25 after #2344 was verified in DEV. **P2-4 (blocking):** `POST /internal/contacts/{cid}/relationships/{rid}/activities/bulk` inserted without `on_conflict`, so one item whose `(kforce_external_id, kind)` already existed (Echo holds ~745K old-pipeline `job_order` activities) failed the whole batch with a 400; the activities push was switched off until fixed. **P2-5 (optimization):** no way to look activities up by external id, so seeding the pipeline's id map meant ~150K no-op POSTs (~19 h) and the Echo `id` of existing activities (needed to PATCH dates when a placement completes) was unreachable. Both shipped in one PR: `ON CONFLICT DO NOTHING` + RETURNING on the bulk POST, and `GET /internal/contacts/activities?kind=&kforce_external_id__in=` (≤100 ids).

## Azure / docs
- [Bug 25154](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25154) (P2-4) + [Task 25155](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25155) (P2-5), parent [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972), Sprint 45 — both In revision with the PR linked.
- Previous rounds: [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Kforce contacts kforce_external_id__in item cap (Bug 25111)]] · [[Kforce org updated_at filter for merges (Task 25112)]]
- PRD source: Emiliano's `docs/prd-pedidos-a-echo-backend-2026-09-21.md` in `taller_kforce_integration_api` (untracked copy at `echo-backend/prd-pedidos.md`, does not yet contain P2-4/P2-5 — they came by message).

## PRs
- [#2349](https://github.com/taller-projects/echo-backend/pull/2349) → dev — open 2026-09-25, branch `25154/activities-bulk-on-conflict-internal-list`, commit `63c46f90`. Full unit + multitenancy suite green locally (5628 passed, 1 xfailed).

## How
- **P2-4** `ActivityService.bulk_create` → `repo.bulk_create(entities, on_conflict=do_nothing_on_conflict)`; the contact refresh runs only when rows were inserted. Relationship/interaction services already did this since `7efdaa85` (#2314 only added RETURNING to their responses).
- **P2-5** `list_router` in `activity/internal_routers.py`, included in `app/routers.py` **before** `internal_contact_router` at `/contacts/activities`. `ActivityInternalFilter(ActivityFilter)` in `activity/filters.py`: `kforce_external_id__in` capped at 100 items by `field_validator` (reuses `KFORCE_EXTERNAL_ID_BATCH_MAX` from `contact/filters.py`), plus a fail-closed tenant semi-join `Activity.contact_id IN (SELECT contact.id WHERE tenant_id = :t)` via `get_request_context().get_tenant_id(required=True)`. `ActivityService.list_internal` → `repo.get_all(..., response_model=ActivityInternalResponse)` (id, kforce_external_id, kind, contact_id, relationship_id, start_date, end_date, timestamps).
- `InternalParams` / `InternalPage` (size ≤ 30000) moved from `organization/internal_routers.py` to `app/core/pagination.py`; both internal lists import from there.
- No migration: `uq_contact_activity_kforce_external_id_kind` `(kforce_external_id, kind)` serves the lookup.
- Tests: `tests/unit/test_activity_bulk_create_internal.py` (6) + `tests/unit/test_activity_internal_list.py` (9).

## Decisions
- **One PR for both requests** (Gonzalo, 2026-09-25) even though P2-4 is blocking and P2-5 is not; two tickets keep Emi's P-numbering traceable.
- **Filter internal-only** (`ActivityInternalFilter` subclass), not on the shared `ActivityFilter`: the public `/contact-activities` route and its golden snapshots stay untouched, and the tenant semi-join belongs only where the path contact does not gate the query.
- **Tenant isolation lives in the filter, fail-closed**: `contact_activity` has no `tenant_id`, no RLS policies (kf9cnv1tnt01 drops them), and `/internal` runs under `DisableRLS`; the only prior cross-contact internal path (`bulk_update`) documents the same reasoning.
- **Skip the refresh on an all-duplicate batch**: DO NOTHING means nothing changed; on ~150K near-all-no-op POSTs that is 4 recomputations saved per call. Did **not** add a `refresh_contacts` Query param to the activities POST (F3 territory, not asked).
- **`InternalParams` reused via `app/core/pagination.py`** instead of the public `Params` (≤100): a 100-id batch without `kind` can return one row per kind, and the #2314 gotcha was exactly a page spilling unnoticed.
- Caveat stated in the PR: DO NOTHING has no target, so any unique violation is skipped — including a collision with another tenant's row (global unique, Task 25057).

## Gotchas
- `GET /internal/contacts/{contact_id}` is declared in `internal_contact_router`; Starlette matches in include order, so a `/contacts/activities` router included after it answers 422 (`activities` is not a uuid). Pinned by `test_path_is_not_captured_by_the_contact_id_route_and_pages_wide`.
- Compiling ORM SQL outside the app needs `import app.main` first (the `Tenant` mapper references `Subscription`, which is only registered once every module is imported).
- Worktree-guard refuses `zsh -ic`, `timeout` with a shell variable, and python heredocs that call `subprocess`; write the script to the scratchpad first and run `python3 <file>` as a plain command.
- kforce-dev facts (2026-09-25): tenant id `018a3ca4-a8de-41fd-9e49-73b1b47fed9c` (same uuid as its org), 1,636,903 contacts, activities: 691,536 `job_order` / 407,859 `placement` / 403,328 `send_out` / 7 `client_visit`.
- kforce-dev `EXPLAIN (ANALYZE, BUFFERS)` of the route's query with 100 real ids: Index Scan `uq_contact_activity_kforce_external_id_kind` → Nested Loop → Index Only Scan `uq_contact_id_tenant_id` (20 heap fetches). Cold 164 ms, warm 3.8 ms, count 1.5 ms.

## Pending
- PR review + merge → Bug 25154 / Task 25155 → Closed; dev deploy; tell Emi (P2-4 in DEV unblocks the activities push; P2-5 route + caveat).
- Bug 25111 and Task 25112 were still **In revision** on 2026-09-25 although #2344 / #2345 merged → close them.
- qa/main promotion.
- Still open from the PRD (not asked this round): F1 remainder (interaction `kforce_external_id` in schema + `__in`), F4 (`kforce_relationship_id__in` + Client backfill owner), F3 open question, P2-2 Q2.

## Related
- [[Map - Kforce]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Kforce contacts kforce_external_id__in item cap (Bug 25111)]] · [[Kforce org updated_at filter for merges (Task 25112)]] · [[Audit log on internal via IntegrationAuditMiddleware (Task 25058)]]
