---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, talents, placements, filters]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2022"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24155"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24156"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24157"
prd: ""
---

# Not Eligible for Rehire talent filter (US 24155)

Recruiters can now filter the talent search by rehire eligibility. A talent is **Not Eligible for Rehire** when ANY of its placements has `placement.eligible_for_rehire = false` (ATS-fed, read-only in Echo). Backend adds `not_eligible_for_rehire` to `TalentFilter`; the FE task adds the control and fixes the overlay badge (today it checks only the FIRST placement) to the same ANY semantics so badge and filter never disagree. Tech spec came fully written from Gonzalo; tickets created 2026-08-07.

## Azure / docs
- [US 24155](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24155) — parent (Active); decisions recorded in the description
- [Task 24156](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24156) — [BE] filter (mine, In development)
- [Task 24157](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24157) — [FE] control + overlay badge ANY fix (unassigned, FE team; keeps the misspelled `notElegibleForRehire` prop name)

## PRs
- [#2022](https://github.com/taller-projects/echo-backend/pull/2022) → dev — **open, in review** (branch `24155/not-eligible-for-rehire-filter`, commit `620c0c35`)

## How
- `TalentFilter.not_eligible_for_rehire: bool | None` (`app/modules/talent/filters.py`) via `_apply_rehire_filter`, mirroring `_apply_applications_exists`: correlated EXISTS over `placement` on `(talent_id, tenant_id)` (composite FK), field consumed (set to `None`) before `super().filter()` so the generic loop doesn't try `Talent.not_eligible_for_rehire`.
- `true` → EXISTS non-eligible placement; `false` → NOT EXISTS (all eligible **or no placements**); absent → no-op. No migration, no new column.
- `Placement` imported at module top level (no cycle: placement/models imports only database base/mixins) — spec suggested a function-local import, unnecessary.
- Tests: `tests/unit/test_not_eligible_for_rehire_filter.py` — 5 route-level tests incl. the two-placement mixed case (locks ANY) and `id__in` + pagination composition.

## Decisions
- **No backend tenant gate** (Gonzalo confirmed via the spec's open question): mirrors the `process_status__in` Status filter precedent — FE gates visibility per tenant (Kforce/Taller); non-ATS tenants' placements default to eligible so a hand-crafted param is harmless. NOTE: the spec mentioned an `enabled_process_status` feature flag — **it doesn't exist**; the Status filter has no backend gate either.
- Not added to `PlacementFilter` — the filter belongs to the talent listing.
- Ticket shape: US + 2 child tasks (BE mine / FE unassigned).

## Gotchas
- **Import-time `ENABLE_ACCESS_CONTROL` capture in older test modules is order-fragile**: modules like `test_multiple_active_applications.py` do `_original = settings.ENABLE_ACCESS_CONTROL; settings.ENABLE_ACCESS_CONTROL = False` at module import — the captured "original" is whatever the previously *imported* module left, and the module-teardown restore then breaks whoever *runs* after. Reproduced both directions locally; in CI's alphabetical order it would have failed MY file. Fix: my module toggles the flag in a module-scoped autouse fixture at run time (flag is read per-request, so this works). Consider migrating the older modules someday.
- `tests/unit/test_talents.py` (29) and `test_future_interaction.py` (50) fail locally even alone and with pristine dev `filters.py` (proved by swapping the file) — pre-existing local breakage, CI green on dev.
- Azure PAT in `~/.zshrc` is wrapped in SINGLE quotes — the azure-devops skill's `cut -d'"' -f2` extraction silently returns the whole line and every API call 302s to MS login. Extract with `cut -d"'" -f2`.
- Task work items here don't have an "Active" state — flow is `New → In development → …` (US does have Active).

## Pending
- PR [#2022](https://github.com/taller-projects/echo-backend/pull/2022): CI + review + merge → then US/Task states → Ready to Test.
- FE Task 24157: filter control (`useFilterConfig.tsx`, `onlyVisibleForTenants: [KFORCE, TALLER]`), `src/types/talent.ts` type, overlay badge `.some(...)` fix (`TalentOverlay.tsx`).
- Kforce port: not evaluated — `TalentFilter` diverged on kforce-dev; if wanted, copy + adapt (no tenant_id correlate there).

## Related
- [[Kforce-main code unification (PRD 3b2aedca)]] — placement ATS columns / bulk sync came from that program's Phase 1/3.
