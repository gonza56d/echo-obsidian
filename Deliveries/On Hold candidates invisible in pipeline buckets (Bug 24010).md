---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, applications, pipeline-buckets, jazz]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1973"
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
- [#1973](https://github.com/taller-projects/echo-backend/pull/1973) → dev — **open, in review** (branch `24010/fix-on-hold-category`)

## How
- `app/modules/application/schemas.py`: `ON_HOLD` + `ON_HOLD_JAZZ` appended to `ACTIVE_STATES`; `ON_HOLD_JAZZ` removed from `INACTIVE_STATES`; `field_validator("status")` on `ApplicationCreate` maps `"ON HOLD"` → `"On Hold"` — ALL write schemas inherit it (Create/Update, public/internal, incl. `partial_model` ones, since `partial_model` uses `__base__=model`).
- Migration `1u4ash4rwbxj`: `UPDATE application SET status='On Hold' WHERE status='ON HOLD'`. Enum value stays (PG can't drop enum values); downgrade = documented no-op (pre-existing title-case rows indistinguishable).
- `app/modules/role/service.py` pipeline-health `excluded_statuses`: added `ON_HOLD` next to `ON_HOLD_JAZZ` (behavior preserved post-normalization).
- Tests `tests/unit/test_application_on_hold_category.py`: list guards, validator (create + partial update), query-level `category == active` for both variants (factory writes raw status → also covers pre-migration rows).

## Decisions
- **Scope narrowed by Gonzalo: On Hold ONLY.** Meli found 8 statuses falling to `other`; the other 7 were deliberately left out (see Pending).
- **Both variants → In Process** (product semantics: On Hold = pause within the process, not an exit). Moves existing Jazz "ON HOLD" rows from Inactive → In Process visibly.
- **Normalize to a single canonical value** ("On Hold") per Meli's suggestion — validator at the schema layer (not in services), one-shot data migration for existing rows.
- No bucket-change migration needed: `category` is a query-time `column_property`, list changes apply on deploy.

## Gotchas
- `ApplicationStatus` has **73 members** and the category fallback only covers what the two lists enumerate — anything new falls silently to `other` and disappears from the UI. No exhaustiveness guard exists (deliberately not added: out of the narrowed scope).
- The 8 orphans found: On Hold, Technical/1st/2nd/3rd Client Interview **Done**, Candidate Pre-Selected by Client (opt), **Position Canceled** (single-L typo twin of the double-L entry in INACTIVE), **Full Time**. The 4 "Done" states are the worst: candidate finishes an interview → vanishes until manually moved to Passed.
- `Offer Accepted` sits in BOTH `ACTIVE_STATES` and `INACTIVE_STATES` (ACTIVE wins by case order). Left as-is.
- Pre-existing local failures (also on clean `origin/dev`): `test_source_pipeline_health.py` 4 failures standalone; `test_application_process_status_filter.py` fails only in combination with other files. Not caused by this change — verified against baseline.

## Pending
- PR [#1973](https://github.com/taller-projects/echo-backend/pull/1973) review + merge → then move Bug 24010 to Ready to Test.
- **Follow-up ticket NOT filed yet**: the remaining 7 `other`-orphan statuses + `Offer Accepted` dup + `Full Time` bucket decision (needs Product; check row counts in prod first).
- Consider an exhaustiveness test (no enum member falls to `other`) when the orphans are resolved.

## Related
- [[Map - TrackerRMS integration]] (Jazz sync is the "ON HOLD" writer)
