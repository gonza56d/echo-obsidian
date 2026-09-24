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
- [#2345](https://github.com/taller-projects/echo-backend/pull/2345) → dev — open 2026-09-24, branch `25112/org-updated-at-filter-merge-bump`, commit `d201d1e4`

## How
- `OrganizationInternalFilter.updated_at__gte` (existing `organization_updated_at_idx`, no migration). Super-admin org list shares the filter.
- `OrganizationRepository.touch_updated_at(ids)`: `UPDATE organization SET updated_at = now(py)` in the caller's transaction, no commit. Called for loser + keeper in `_link_organizations` and `_merge_into`, right before `_persist_merge_manifest`.
- `UndoService` injects `OrganizationService`; `revert` calls `touch_updated_at([loser, keeper])` for `organization_merge` ops before its commit (conflict → rollback → nothing touched).
- `OrganizationInternalResponse(OrganizationResponse)` + `merged_into_id`, return type of the internal list only.
- Tests: `test_organization_updated_at_sync.py` (new), pins in `test_organization_dedup.py`, `test_undo_service.py`, e2e `test_unmerge_endpoint.py` with real orgs. Mutation-checked. 5241 passed.
- kforce-dev EXPLAIN: `updated_at >= now()-1d` → index scan, 2,884 rows, ~300 ms.

## Decisions
- `updated_at__gte` + explicit bumps over a new `merged_at` column (user choice 2026-09-24): no migration on ~473k prod rows, and it also surfaces unmerges.
- `merged_into_id` on an **internal-only** response subclass, not the shared `OrganizationResponse`: keeps the FE contract and the golden `organizations_list` snapshot untouched. (Ticket text originally said OrganizationResponse; comment added.)
- Undo bump inside `revert` (atomic with the undo) rather than in the super-admin router (second transaction).
- Python `datetime.now(UTC)` for the bump, same clock as `TimestampMixin`.

## Gotchas
- **Joined inheritance + `onupdate`:** an ORM edit that only changes `organization_insight` columns (`industry`, `kforce_external_id`, `echo_id`, …) emits no UPDATE on `organization`, so `updated_at` does NOT move (verified with a probe test). Only `organization` columns (`name`, `linkedin_url`, `logo`, …) bump it. So `updated_at__gte` is a merge/unmerge cursor, not a general change cursor. Documented on the field + PR body.
- Merge clears the loser's `kforce_external_id` / `echo_id`; the pipeline must re-point by the loser's Echo id → `merged_into_id`.
- Watermark: `updated_at` is stamped at write time, not commit time → the pipeline should overlap its cursor by a few minutes.
- `UndoService(...)` built directly in 2 tests → needed the new collaborator (`MagicMock()`).

## Pending
- Review + merge #2345 → Task 25112 Closed, dev deploy.
- Ask the user whether to also bump `updated_at` on insight-only ORM edits (mapper `before_update` listener on `OrganizationInsight`), as a follow-up.
- Reply to Emiliano (cursor overlap, merges only, keep a periodic `--full` for insight-only edits / external-link re-points).
- qa/main promotion.

## Related
- [[Map - Kforce]] · [[Kforce contacts kforce_external_id__in item cap (Bug 25111)]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]]
