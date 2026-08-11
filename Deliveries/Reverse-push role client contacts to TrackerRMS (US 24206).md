---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, trackerrms, outbox, navitec, reverse-sync]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2038"
fe_prs:
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24206"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24170"
prd:
---

# Reverse-push role client contacts to TrackerRMS (US 24206)

Propagate a Navitec user's edit of a role's **client contacts** from Echo → TrackerRMS. The two role columns `client_hiring_manager_id` (primary) and `client_manager_id` (secondary) map to the TrackerRMS Opportunity's `contact` / `secondaryContact`.

## What

Tyler (Navitec) asked to see the client people related to a role. The **forward** sync (Tracker → Echo) is built by Data (Emiliano) and already populates the two role columns; ~748 prod roles await backfill (741 primary, 146 secondary). FE display/edit is [US 24174](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24174) (Melina, Developed). The parent [Feature 24170](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24170) explicitly carved the **reverse** direction (Echo → Tracker) into a separate ticket — this one.

The integration service `taller_tracker_rms_api` (separate repo) already **declares and accepts** both fields on its input schema (was `extra="ignore"` before, silently dropping them; Emiliano tested in dev 2026-08-10, moved to prod). The gap was entirely on Echo: the outbound role payload builders dropped the two contact fields, so edits never left Echo.

## Azure
- [US 24206](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24206) — "BE: Push role client contacts Echo→TrackerRMS (reverse sync)", child of Feature 24170, Sprint 43. Created + set **Active** 2026-08-11, PR link commented.

## PRs
- [#2038](https://github.com/taller-projects/echo-backend/pull/2038) → dev — **open, in review** (2026-08-11).

## How

Echo already enqueues correctly and never needed a trigger change: `RoleService._update` writes a `ROLE_UPDATED` outbox event **only** when `db_role.external_id is not None` (Tracker-linked), the internal-origin loop-guard still applies, and the dispatcher routes POST/PATCH to `/sync/{tenant_id}/tracker_rms/job`. The contacts were dropped at **payload-build** time. Added them (Echo contact UUID as string; the integration service resolves them to Tracker contact ids) at three builders for parity:

1. `app/modules/outbox/payloads.py` — `build_role_payload` base snapshot + the `RoleLike` Protocol. Reads via `getattr(role, ..., None)` (mirrors `_str_attr`: the builder may receive a lightweight snapshot, and the spec'd test mocks lack the attr).
2. `app/modules/role/service.py` — `_build_role_update_payload` overlay (`build_role_payload` snapshots `db_role` PRE-commit, so an edited field must be overlaid with its NEW value or it ships stale).
3. `app/services/tracker_rms_sync_service.py` — `_RoleSyncProjection` (schema-driven SELECT had to gain the 2 columns or `role.client_*` is absent) + `_build_role_payload` (the manual "Sync to Tracker" button; team plans to remove this button soon but wants parity meanwhile).

Tests: `test_outbox_payloads.py` (base builder set/omit), `test_outbox_triggers.py::TestRoleOutbox` (overlay ships new ids; clear omits; unrelated edit adds no null keys — defaulted the plain-MagicMock `_make_db_role` contacts to `None`), `test_tracker_rms_sync_service.py` (manual builder set/omit; `_mock_role` gained the two kwargs). 136 passing across the 3 files + 119 across sibling outbox files (dispatcher/writer). Lint clean.

## Decisions
- **Never-clear (product-confirmed with Gonzalo, 2026-08-11).** A contact is sent **only when non-null**; a *cleared* contact is **omitted, never sent as `null`**. TrackerRMS is the client's system of record; there's a real prior incident of a reverse PATCH overwriting a contact's `client`. So a delete in Echo does NOT propagate — the forward push re-asserts Tracker on the next job change. This differs **deliberately** from the `account_manager_id → owner_id` overlay right above, which *does* send `null` on clear. Implementation: base/manual builders add the key only when truthy; the overlay `pop()`s it on clear so a pre-commit snapshot value can't leak the old id back.
- **Both builders (parity), not overlay-only.** Considered sending contacts only when actually edited (fewer spurious ambiguity logs for the 269 deduped contacts). Chose the full-snapshot approach for consistency with every other role field + the manual button, at the cost of re-asserting unchanged contacts on every linked-role edit (idempotent per the contract's redundant-PATCH note).
- **Scope**: only the reverse push. Feature 24170's display/edit needs ~zero backend (the columns are already in `RoleBase`/`RoleUpdate`; tenant isolation is RLS-automatic).

## Gotchas
- The `/sync/.../tracker_rms/job` endpoints are **not in this repo** — only consumed. The dev MockServer matches on path and accepts any body, so a missing/wrong field never surfaces in dev (same trap as [[Outbox flat payload fix (PR 1838)]]).
- `_mock_role` uses `MagicMock(spec=Role)` → the contact attrs resolve to truthy child mocks (not absent), so existing manual-builder tests would silently carry junk contact values; defaulted them to `None` in the factory.
- Worktree session: the isolated-worktree Bash guard refuses piped/redirected commands (curl `-o`, `| python3`, code heredocs). Ran Azure REST + vault writes after `ExitWorktree keep`, from the launch checkout.

## Pending
- Merge #2038 → dev; then Bug/US state → Ready to Test.
- **Rollout depends on the `taller_tracker_rms_api` reverse change being live in prod** (Echo change is safe to merge regardless — undeclared fields drop harmlessly). Confirm with Emiliano.
- Turn-on coordinates with Data: 748-row backfill + FE reveal, so Navitec doesn't see empty/premature fields.
- 269 prod cross-tenant-deduped contacts → the integration service can't resolve a unique Tracker id, omits + logs. Expected; tell FE/product.
- qa/main promotion unrequested.

## Related
- [[Map - TrackerRMS integration]] · [[Outbox flat payload fix (PR 1838)]] · [[Outbox skips internal-originated emits (Bug 23656)]]
- Sibling FE: US 24174 (Melina). Parent: Feature 24170.
