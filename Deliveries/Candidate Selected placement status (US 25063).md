---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, placement, roles]
prs: ["https://github.com/taller-projects/echo-backend/pull/2330"]
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

## How
- Enum: `CANDIDATE_SELECTED = "Candidate Selected"` added to `RolePlacementStatus` and to `NON_TERMINAL_PLACEMENT_STATUSES` (`app/modules/role/placement/schemas.py`).
- Migration `q7fkc2npl8rs` (`...add_candidate_selected_placement_status.py`): `op.sync_enum_values` **appends** the value to `role_placement_status_enum`. `existing_server_default` is `'Draft'` (set by `change_role_placement_status_default_to_draft`, NOT the `'Open'` the older `add_placement_draft` migration used). Mirrors the `add_placement_draft` pattern.
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
- Enum migration `existing_server_default` is `'Draft'` today, not `'Open'` — always re-check the real current default before copying an older enum migration.

## Review (2026-09-23)
Ran the full pr-review skill (3 parallel reviewers). Verdict: **CHANGES REQUESTED** — 2 blockers, 2 nits. PRD compliance 7/7; every count/reporting bucket independently verified in code.
- **Nits fixed** in commit `826a9735` (pushed to #2330):
  - Parametrized `test_patch_rejects_talent_linked_to_another_non_terminal_placement` over `[Open, Candidate Selected]` (occupancy rejection on the PATCH branch now covers the new status).
  - Migration docstring: documented the `sync_enum_values` full-type-swap rewrite cost + KForce budget + no view dependency on `role_placement.status`.
- **Blockers still open (not addressed — left for author decision):**
  1. `refresh_placement_denormalized_fields` widening (`repository.py:325`) has no test exercising a `CANDIDATE_SELECTED` placement — the PR's central repo change is uncovered. Add `test_candidate_selected_placement_used_for_denormalization`.
  2. Migration `downgrade()` removes the enum value with no guarded `UPDATE` first → hard-fails if any row is in `'Candidate Selected'` (violates the CLAUDE.md enum-downgrade rule; same flaw as precedent `add_placement_draft`). Fix: `UPDATE role_placement SET status='Open' WHERE status='Candidate Selected'` before the sync, or document downgrade unsupported.
- **Question raised:** paired echo-frontend PR/ticket for the `"Candidate Selected"` string (FE hardcodes the status set; must NOT add it to FE `FULFILLED_STATUSES`).

## Pending
- Review + merge to dev.
- qa/main promotion.
- FE must reproduce the exact `"Candidate Selected"` casing.
- Feature QA.

## Related
- Placement `Draft` status + default change (`add_placement_draft`, `change_role_placement_status_default_to_draft`) — same enum, prior work.
