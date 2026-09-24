---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, kforce, organizations, internal-api, merge]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2345"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25112"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
prd: ""
---

# Kforce org updated_at filter for merges (Task 25112)

Emiliano's Kforce push PRD P1-3 (improvement, not blocking): to learn that Echo merged an organization, the pipeline re-queries all ~44k Kforce companies every night (`--full`, ~25 min on dev). Shipped `updated_at__gte` on `GET /internal/organizations`, made merges and unmerges bump `organization.updated_at` (they didn't: raw SQL on `organization_insight`), and exposed `merged_into_id` on the internal list items.

## Azure / docs
- [Task 25112](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25112) (parent [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972)) — In revision
- Sibling from the same message: [[Kforce contacts kforce_external_id__in item cap (Bug 25111)]]
- PRD source: `docs/prd-pedidos-a-echo-backend-2026-09-21.md` (pipeline repo), section P1-3

## PRs
- [#2345](https://github.com/taller-projects/echo-backend/pull/2345) → dev — open 2026-09-24, branch `25112/org-updated-at-filter-merge-bump`, commits `d201d1e4` + `2f07cf16` (r1 review nits) + `daa5e856` (Pedro's nits: per-type post-revert hooks in `UndoService`, cursor contract documented once on the route, super-admin list cursor tests)

## How
- `OrganizationInternalFilter.updated_at__gte: AwareDatetime` (existing `organization_updated_at_idx`, no migration; naive/invalid → 422). Super-admin org list shares the filter.
- Cursor contract lives in the route's `description=` (OpenAPI): inclusive, offset required (`Z` or URL-encoded `+hh:mm`), stamped at write time → overlap the cursor, merges/unmerges only, use `order_by=updated_at` + one-page `size`.
- `OrganizationRepository.touch_updated_at(ids)`: `UPDATE organization SET updated_at = now(py)` in the caller's transaction, no commit. Called for loser + keeper in `_link_organizations` and `_merge_into`, right before `_persist_merge_manifest`.
- `UndoService` injects `OrganizationService`; `revert` calls `touch_updated_at([loser, keeper])` for `organization_merge` ops before its commit (conflict → rollback → nothing touched).
- `OrganizationInternalResponse(OrganizationResponse)` + `merged_into_id`, return type of the internal list only.
- Tests: `test_organization_updated_at_sync.py` (new; incl. real `_link_organizations` merge, inclusive/offset/order_by cursor, naive+invalid 422), real `_merge_into` merge in `test_c1_jwt_track_dedup.py`, pins in `test_organization_dedup.py`, `test_undo_service.py`, e2e `test_unmerge_endpoint.py`. Mutation-checked (undo bump, both merge bumps, filter field). 5248 passed, 1 xpassed.
- kforce-dev EXPLAIN ANALYZE (125k orgs, 1-day window, the real statements): `count(*)` → `organization_updated_at_idx` scan, 2,884 rows, 338 ms; page with default `ORDER BY created_at LIMIT 100` → `organization_created_at_idx` + filter, 122,553 rows removed, 132 ms; page with `order_by=updated_at` → updated_at index, 0.6 ms.

## Decisions
- `updated_at__gte` + explicit bumps over a new `merged_at` column (user choice 2026-09-24): no migration on ~473k prod rows, and it also surfaces unmerges.
- `merged_into_id` on an **internal-only** response subclass, not the shared `OrganizationResponse`: keeps the FE contract and the golden `organizations_list` snapshot untouched. (Ticket text originally said OrganizationResponse; comment added.)
- Undo bump inside `revert` (atomic with the undo) rather than in the super-admin router (second transaction).
- Python `datetime.now(UTC)` for the bump, same clock as `TimestampMixin`.
- r1 review (`/pr-review` 2026-09-24: READY WITH NITS, 0 blockers) → all 10 nits fixed in `2f07cf16`: `AwareDatetime` cursor, contract on the route description, undo docstring names its org hook, no consumer name in the repo docstring, real-DB merge tests, edge cases, monkeypatched repo session, blank lines, Task retitled ("…merged_into_id on the internal list items"), real-statement EXPLAIN in the PR body.
- Default sort left at `created_at` (changing it would affect every consumer); the docs steer the pipeline to `order_by=updated_at` instead.

## Gotchas
- **Joined inheritance + `onupdate`:** an ORM edit that only changes `organization_insight` columns (`industry`, `kforce_external_id`, `echo_id`, …) emits no UPDATE on `organization`, so `updated_at` does NOT move (verified with a probe test). Only `organization` columns (`name`, `linkedin_url`, `logo`, …) bump it. So `updated_at__gte` is a merge/unmerge cursor, not a general change cursor. Documented on the field + PR body.
- Merge clears the loser's `kforce_external_id` / `echo_id`; the pipeline must re-point by the loser's Echo id → `merged_into_id`.
- Watermark: `updated_at` is stamped at write time, not commit time → the pipeline should overlap its cursor by a few minutes.
- `UndoService(...)` built directly in 2 tests → needed the new collaborator (`MagicMock()`).
- **FilterDepends drops `Field(description=...)`** from OpenAPI (FastAPI reads the generated class signature) → put consumer docs on the route's `description=`.
- `OrganizationInternalFilter` extends plain fastapi-filter `Filter`, not `JoinFilter`: no UTC normalization of datetimes (hence `AwareDatetime`).
- With `ORDER BY created_at LIMIT n` the planner walks `organization_created_at_idx` and filters, ignoring the updated_at index; `order_by=updated_at` keeps it index-driven. Offset paging over `updated_at` can skip a row bumped mid-read → one page per window.

## Pending
- Re-review + merge #2345 → Task 25112 Closed, dev deploy.
- Ask the user whether to also bump `updated_at` on insight-only ORM edits (mapper `before_update` listener on `OrganizationInsight`), as a follow-up.
- ~~Reply to Emiliano~~ DONE 2026-09-24: Emi confirmed list-only `merged_into_id`, merge/unmerge-only cursor + periodic `--full`, contract `order_by=updated_at,id` / 15-min overlap / 30000 page / idempotent. Told him to drop `merged_into_id__isnull=false` (hides unmerges; unmerge restores the loser's `kforce_external_id` + bumps both). Posted as reply to Pedro's BLOCKED ON CLARIFICATION review ([comment](https://github.com/taller-projects/echo-backend/pull/2345#issuecomment-5821394155)) + recorded in Task 25112 description. Pedro's nits fixed in `daa5e856` (default-sort nit answered by Emi's `order_by=updated_at,id`); CI left to the user.
- Out-of-scope follow-ups from the review: pre-existing N+1 on the internal list (3 deferred column_properties per item, `related_contacts_count` over `contact_relationship`); `_link_organizations` per-row `rollback()` may drop earlier uncommitted merges in the batch.
- qa/main promotion.

## Related
- [[Map - Kforce]] · [[Kforce contacts kforce_external_id__in item cap (Bug 25111)]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]]
