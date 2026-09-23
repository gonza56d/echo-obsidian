---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, placement, roles]
prs: ["https://github.com/taller-projects/echo-backend/pull/2330", "https://github.com/taller-projects/echo-backend/pull/2339"]
fe_prs: []
tickets: ["https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25063"]
prd: ""
---

# Candidate Selected placement status (US 25063)

Backend part of adding a `Candidate Selected` status to `RolePlacement`: a **non-terminal step before `Filled`** — a candidate has been picked but the placement is not yet confirmed. The candidate is occupied (cannot hold another non-terminal placement on the same role), but it must **not** count as a hire. String value (FE↔BE contract): exactly `"Candidate Selected"`.

## Azure / docs
- [US 25063](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25063) (BE part; has a parent US for full context) — state set to In revision on PR open.

## PRs
- [#2330](https://github.com/taller-projects/echo-backend/pull/2330) → dev — in review
- [#2339](https://github.com/taller-projects/echo-backend/pull/2339) — release `dev` → `qa` OPEN 2026-09-23 (31 commits, 7 migrations, single head `zolvj810zl6j`); `qa` → `main` opens after it merges (qa == main until then).

## How
- Enum: `CANDIDATE_SELECTED = "Candidate Selected"` added to `RolePlacementStatus` and to `NON_TERMINAL_PLACEMENT_STATUSES` (`app/modules/role/placement/schemas.py`).
- Migration `q7fkc2npl8rs` (`...add_candidate_selected_placement_status.py`): `op.sync_enum_values` **appends** the value to `role_placement_status_enum`. Column passed as a `("role_placement", "status")` **tuple** (r2 fix, `cfe1a728`): the library reads each DB's LIVE default via `get_column_default` and restores it after the retype — no hardcoded `existing_server_default`.
- `refresh_placement_denormalized_fields` (`app/modules/role/repository.py:293`): the denormalized Role fields (`target_fill_date`/`start_date`/`rate`/`max_rate`) now come from `status IN (Open, Candidate Selected)` instead of `== Open`, so the Role keeps its dates after a candidate is picked. Docstring updated.

## Decisions
- **Count buckets need no code change.** `openings_count`/`filled` in `role/models.py` (~717-745) and `role/schemas.py` (~362-388) are **exclusion-based** ({Closed, Cancelled, On Hold, Backfilled, Draft}), so Candidate Selected auto-counts as an active opening but not a filled/hire. Verified, not edited.
- **Reporting needs no code change.** Hires key strictly on `→ Filled` change-history transitions / `status == Filled` (`reporting_dashboard/repository.py`). Adding to `NON_TERMINAL` makes `Filled → Candidate Selected` land in the `reopened` (fill-undo) bucket, never `terminal` (churn) — so it is never counted as a hire. Confirmed per the user's explicit ask.
- `_stamps_a_status_change` already stamps everything except Draft → Candidate Selected stamps `status_change_at` like any real transition. No change.
- **repository.py:324 decision** (include Candidate Selected in denormalized-dates filter) was the user's call via AskUserQuestion.
- Factory left unchanged: `RolePlacementFactory` already randomizes `status`; the new value falls in the same non-terminal bucket as `Open` (already in the pool), so no new flakiness category.

## Gotchas
- `ApplicationStatus.CANDIDATE_SELECTED_BY_CLIENT` (application enum) is a **different** thing from this `RolePlacementStatus.CANDIDATE_SELECTED` — do not conflate.
- Suite builds schema with `create_all`, NOT alembic, so tests don't exercise the migration. Verified upgrade/downgrade against a throwaway pgvector Postgres in isolation (rows preserved, `'Draft'` default intact).
- **`role_placement.status` default has DRIFTED between envs** (checked live 2026-09-23): `'Open'` on dev / prod / kforce-dev, `'Draft'` on qa (playground `'Draft'` per Pedro; kforce-prod unchecked — no local pg service). A clean alembic chain ends in `'Draft'` (`role_placement_status_default`), so a throwaway Postgres can't reveal it. For any `sync_enum_values` on this enum, pass the column as a tuple (reads the live default) — never hardcode `existing_server_default`. Converging the drift is unticketed.

## Review (2026-09-23)
Ran the full pr-review skill (3 parallel reviewers). Verdict: **CHANGES REQUESTED** — 2 blockers, 2 nits. PRD compliance 7/7; every count/reporting bucket independently verified in code.
- **Nits fixed** in commit `826a9735` (pushed to #2330):
  - Parametrized `test_patch_rejects_talent_linked_to_another_non_terminal_placement` over `[Open, Candidate Selected]` (occupancy rejection on the PATCH branch now covers the new status).
  - Migration docstring: documented the `sync_enum_values` full-type-swap rewrite cost + KForce budget + no view dependency on `role_placement.status`.
- **Blockers fixed** in commit `584b45a3` (pushed to #2330):
  1. Added `test_candidate_selected_placement_used_for_denormalization` (`test_role_placements.py`) — a role keeps its denormalized target/start/rate fields after a placement moves OPEN→CANDIDATE_SELECTED (covers the `repository.py:325` widening).
  2. Migration `downgrade()` now runs `UPDATE role_placement SET status='Open' WHERE status='Candidate Selected'` before `sync_enum_values`, so rollback cannot fail on a live row. **Verified against a throwaway Postgres**: unguarded swap fails with `invalid input value for enum "Candidate Selected"`; guarded swap moves the row to Open and commits clean.
- **Question raised:** paired echo-frontend PR/ticket for the `"Candidate Selected"` string (FE hardcodes the status set; must NOT add it to FE `FULFILLED_STATUSES`).

## Review r2 — Pedro (2026-09-23, CHANGES REQUESTED)
[Review](https://github.com/taller-projects/echo-backend/pull/2330#pullrequestreview-5292726167). 1 blocker + 7 nits, all addressed and pushed:
- **Blocker** (`cfe1a728`): hardcoded `existing_server_default='Draft'` would silently flip dev/prod/kforce-dev from `'Open'` → `'Draft'` (and downgrade wouldn't restore). Fix = option (a), tuple form. Verified on a throwaway Postgres seeded once with `'Open'` and once with `'Draft'`: default unchanged through upgrade AND downgrade, rows preserved. Docstring documents the drift.
- **Nits** (`1fc530d8`):
  - Reporting tests (Nov-2025 window, `candidate_selected_scenario`): Draft→CS never a hire; Filled→CS excluded from Total/Active Hires; CS→Filled = active hire; breakdowns sum to 1.
  - Pinned: `get_dropouts_count` counts Filled→CS as a dropout (same as Filled→Open) — PR body "never a churn" wording corrected.
  - Positive PATCH test `{status: CS, talent_id: eligible}` → 202 + linked.
  - Guard test: TERMINAL ∪ NON_TERMINAL test lists == `set(RolePlacementStatus)`, disjoint, and == `NON_TERMINAL_PLACEMENT_STATUSES`.
  - Docstrings: reporting `:299` + `:642` list CS among non-terminal; `role/repository.py` first line + duplicated "When no open placement exists" line fixed.
  - Migration docstring: downgrade's UPDATE writes no change history → after code rollback a Filled→CS row stops reading as a revert and the fill counts as a hire again.
  - PR body: parent US 25062 + FE US 25064 linked (BE must ship before FE); factories.py-unchanged rationale added.
- Test run: 137 passed across the 5 touched/related test files; lint clean; `alembic heads` = `q7fkc2npl8rs`.
- Worktree: original 25063 worktree was hijacked to `pr2331`; r2 fixes done in `.claude/worktrees/25063-review-r2`.

## Pending
- Pedro re-review (r2 fixes `cfe1a728` + `1fc530d8`) + merge to dev.
- Out-of-scope from r2 (US 25062): `available_openings` (`role/models.py:747`) counts a CS seat as available although its talent is blocked — confirm with product.
- qa/main promotion.
- FE must reproduce the exact `"Candidate Selected"` casing.
- Feature QA.

## Related
- Placement `Draft` status + default change (`add_placement_draft`, `change_role_placement_status_default_to_draft`) — same enum, prior work.
