---
type: delivery
status: merged
env: taller
delivered: 2026-08-04
tags: [bugfix, applications, pipeline-buckets, jazz]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1973"
  - "https://github.com/taller-projects/echo-backend/pull/1976"
  - "https://github.com/taller-projects/echo-backend/pull/1977"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24010"
prd: ""
---

# On Hold candidates invisible in pipeline buckets (Bug 24010)

Candidates with status **"On Hold"** appeared in NO bucket of Roles → Candidates: the FE queries `/applications` with `category=active|matched|hired|inactive` and never asks for `other`, and the status-fallback of `Application.category` (used when `workflow_step_id IS NULL`, the Taller/Jazz flow) had title-case `On Hold` in no list → `else_` → `other` → invisible. Shipped: both On Hold variants categorize as **active** (In Process), plus normalization of Jazz's `"ON HOLD"` into canonical `"On Hold"` (write-path validator + data migration). Backend-only; FE self-heals per Meli's analysis.

## Azure / docs
- [Bug 24010](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24010) — comment 28531666 (Meli) has the definitive analysis; comment 28531468 (Paloma) the evidence (role 102651: 23 apps in `other` = 20 "On Hold" + 3 "1st Client Interview Done")
- Related: [US 11885](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/11885) (original buckets), [Bug 20819](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/20819)

## PRs
- [#1973](https://github.com/taller-projects/echo-backend/pull/1973) → dev — **MERGED 2026-08-04** (`68e1a085`, merge commit; another agent re-chained the migration onto `tp7dq2mk9v4x` + added a pipeline-health exclusion test pre-merge). **Dev e2e verified 2026-08-04**: staged both variants on a QA role → both returned by `category=active`, `category=other` empty; migration ran on deploy (alembic at `1u4ash4rwbxj`, 3 legacy ON HOLD rows collapsed); staged data restored to NULL.; /pr-review round 1 done 2026-08-04, blocker + nit fixed in `346b8225`

- Cherry-picks: [#1976](https://github.com/taller-projects/echo-backend/pull/1976) → qa + [#1977](https://github.com/taller-projects/echo-backend/pull/1977) → main — **open 2026-08-04** (branches `24010/fix-on-hold-category-qa|-main`). Full pick of `68e1a085` incl. the migration, **re-chained onto `n8vc3kq7wx2m`** per Gonzalo's explicit call (heads confirmed by him; my code-only recommendation was overridden). `alembic heads` single-head + lint + 10/10 tests verified on both branches. Merge with MERGE COMMITS, never squash.

## How
- `app/modules/application/schemas.py`: `ON_HOLD` + `ON_HOLD_JAZZ` appended to `ACTIVE_STATES`; `ON_HOLD_JAZZ` removed from `INACTIVE_STATES`; `field_validator("status")` on `ApplicationCreate` maps `"ON HOLD"` → `"On Hold"` — ALL write schemas inherit it (Create/Update, public/internal, incl. `partial_model` ones, since `partial_model` uses `__base__=model`).
- Migration `1u4ash4rwbxj`: `UPDATE application SET status='On Hold' WHERE status='ON HOLD'`. Enum value stays (PG can't drop enum values); downgrade = documented no-op (pre-existing title-case rows indistinguishable).
- `app/modules/role/service.py` pipeline-health `excluded_statuses`: added `ON_HOLD` next to `ON_HOLD_JAZZ` (behavior preserved post-normalization).
- Tests `tests/unit/test_application_on_hold_category.py`: list guards, validator (create + partial update), query-level `category == active` for both variants (factory writes raw status → also covers pre-migration rows).

## Review round 1 (2026-08-04, own /pr-review — 3 reviewers)
- Ticket compliance 7/7, architecture 13 PASS / 0 FAIL, tests-security 9 PASS / 2 FAIL → **CHANGES REQUESTED** on one mechanical blocker.
- **BLOCKER (fixed)**: alembic fork — dev merged `tp7dq2mk9v4x` (reminder stamps) after this branch was cut, also revising `tpls3jaidxpa` → two heads on merge. Fix in `346b8225`: merged origin/dev into the branch + re-chained `down_revision` → `tp7dq2mk9v4x`; `alembic heads` = single head `1u4ash4rwbxj`. CI was green because the branch predated the fork — CI green ≠ merged-chain valid.
- **NIT (fixed)**: `get_pipeline_health` ON_HOLD exclusion had zero coverage → added `test_get_pipeline_health_excludes_both_on_hold_variants` (`RoleService.__new__` + mocked repo, pins the excluded list the service passes to the repository). 10/10 file tests green.
- **Questions left open (answer on PR body/ticket before merge)**:
  - **ACTIVE_STATES ripple**: the list change also flips `Talent.has_active_applications` (`talent/models.py:715`), `Role.active_candidates_count` (`role/models.py:345`) and the talent source-change gate (`talent/service.py:687` — On Hold now hard-blocks as `active_application`; before, "On Hold" fell through both lists and "ON HOLD" hit the softer 2-business-day inactive rule). Consistent with "pause, not exit" but unstated in PR body.
  - `application_status_history` keeps legacy "ON HOLD" literals (migration only touches `application`) — inert for this bug.
  - Pre-existing title-case "On Hold" rows previously COUNTED in pipeline-health metrics; now excluded — QA heads-up needed at close-out.

## Decisions
- **Scope narrowed by Gonzalo: On Hold ONLY.** Meli found 8 statuses falling to `other`; the other 7 were deliberately left out (see Pending).
- **Both variants → In Process** (product semantics: On Hold = pause within the process, not an exit). Moves existing Jazz "ON HOLD" rows from Inactive → In Process visibly.
- **Normalize to a single canonical value** ("On Hold") per Meli's suggestion — validator at the schema layer (not in services), one-shot data migration for existing rows.
- No bucket-change migration needed: `category` is a query-time `column_property`, list changes apply on deploy.

## Gotchas
- **`ApplicationResponse` inherits `ApplicationCreate`** → the normalization validator also applies on READ: un-migrated `'ON HOLD'` rows display as "On Hold" in API responses while the raw DB value stays "ON HOLD". Defense-in-depth, but remember it when comparing API output vs raw SQL.
- `ApplicationStatus` has **73 members** and the category fallback only covers what the two lists enumerate — anything new falls silently to `other` and disappears from the UI. No exhaustiveness guard exists (deliberately not added: out of the narrowed scope).
- The 8 orphans found: On Hold, Technical/1st/2nd/3rd Client Interview **Done**, Candidate Pre-Selected by Client (opt), **Position Canceled** (single-L typo twin of the double-L entry in INACTIVE), **Full Time**. The 4 "Done" states are the worst: candidate finishes an interview → vanishes until manually moved to Passed.
- `Offer Accepted` sits in BOTH `ACTIVE_STATES` and `INACTIVE_STATES` (ACTIVE wins by case order). Left as-is.
- Pre-existing local failures (also on clean `origin/dev`): `test_source_pipeline_health.py` 4 failures standalone; `test_application_process_status_filter.py` fails only in combination with other files. Not caused by this change — verified against baseline.

## Pending
- PR [#1973](https://github.com/taller-projects/echo-backend/pull/1973) team review + merge → then move Bug 24010 to Ready to Test.
- Answer the 3 review questions on the PR body/ticket (ACTIVE_STATES ripple, history literals, pipeline-health metric shift) — doubles as the QA heads-up.
- **Follow-up ticket NOT filed yet**: the remaining 7 `other`-orphan statuses + `Offer Accepted` dup + `Full Time` bucket decision (needs Product; check row counts in prod first).
- Consider an exhaustiveness test (no enum member falls to `other`) when the orphans are resolved.

## Related
- [[Map - TrackerRMS integration]] (Jazz sync is the "ON HOLD" writer)
