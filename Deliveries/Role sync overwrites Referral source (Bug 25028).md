---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, talent, referral-attribution, jazzhr]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2304"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25028"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24999"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25021"
prd: "https://app.notion.com/p/3deaedca11f081b39e81c49c7ffb2ce3"
---

# Role sync overwrites Referral source (Bug 25028)

**Status**: PR [#2304](https://github.com/taller-projects/echo-backend/pull/2304) → dev OPEN 2026-09-18 · **Ticket**: [Bug 25028](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25028) (In revision)

Follow-up to [[Referral Attribution M1 permission+gating (US 24996)]], sibling of [[Referral source variant cleanup (Bug 25021)]]. Reported by Meli (FE) 2026-09-18 while testing on Taller: adding a candidate **with a role** ("Role Applying For") goes to `POST /talents/{role_id}/sync` (FE routes there when `!isMultiTenant`), and that path stamped the uploader's vendor over the freshly written `Referral` source, recording the change as **System**. Without a role (`POST /talents`) it worked, so it looked fine at first.

## Azure / docs
- [Bug 25028](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25028) — this fix. Related: [US 24999](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24999) (M2 intake), [Bug 25021](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25021).
- PRD: [PRD Técnico — Referral Attribution](https://app.notion.com/p/3deaedca11f081b39e81c49c7ffb2ce3) — explicitly left integration paths untouched ("Jazz sync ... no cambian"); **open question 5** (manual attribution wins, sync doesn't revert) never resolved → this is the PRD gap. Changelog row still to add.

## PRs
- [#2304](https://github.com/taller-projects/echo-backend/pull/2304) → dev — OPEN 2026-09-18 (branch `25028/sync-preserves-referral-attribution`, commit `47c33c2c`). Not in release [#2303](https://github.com/taller-projects/echo-backend/pull/2303); rides the next promo.

## How
- Root cause: `create_and_sync_talent` → `create_talent` (attribution applied correctly) → `sync_talent_with_jazz_and_vendor` → `update_data["source"] = vendor_name` → public `update()` with no `changed_by`. Same in `_apply_talent_to_role_natively`, the re-upload branch and `POST /talents/{id}/apply/{role}` (strips Referral from an already-referred candidate). Legacy Jazz-flow default (Bugs 22384/24264/24239).
- Fix: `TalentService._apply_sync_source(update_data, talent, vendor_name, keeps_attribution)` — payload writes attribution (`writes_attribution`, same rule as #2301) → keep payload source; talent already `Referral` → never downgrade; else vendor. `create_and_sync_talent` computes `keeps_attribution` once and passes it to both paths. Both paths pass `changed_by=created_by_id`.
- Jazz payload unchanged: `sync_overrides["source"] = vendor_name` stays (avoids ER `_process_source` clearing `recruiterId` → 422).
- Router `sync_talent`: `writes_attribution` 404 gate (mirror of `POST /talents`). `TalentSyncCreate` now extends `TalentCreateRequest` → 422 for Referral without referrer at request time.
- Tests: new `tests/unit/test_talent_sync_attribution.py` (Jazz + native matrix, schema), two router tests in `test_referral_source_validation.py`; existing `__new__` fakes updated.

## Decisions
- Attribution-scoped rule (Meli's proposal), not "sync never touches source": channel intakes keep the vendor default so legacy behaviour is unchanged.
- Existing `Referral` protected on `/apply` too (user approved as recommended).
- Jazz keeps receiving the vendor name for now; sending "Referral" needs data-team confirmation of `_process_source` (profiles_api local clone from 2026-08-20 doesn't contain it).

## Gotchas
- `__new__`-style fakes broke on the new collaborator/keyword: needed `vendor_service` stub, `talent.source` attribute, `**_kwargs` on fake `update` (`changed_by`). 422 body `detail` is a pydantic list → assert on `error.message`.
- Worktree-guard inside a worktree blocks `awk -v`, `source scripts/venv.sh`, long multi-heredoc `&&` chains and Write outside the worktree → `uv run` directly, temp files inside the worktree.
- Re-upload with owner reassignment still goes through `TalentUpdateInternal` → no history row, referrer invariant skipped (pre-existing; 422 now caught at schema level).

## Pending
- [ ] PR #2304 review + merge to dev; verify on dev: add candidate with role + Referral → source stays Referral, history author = recruiter
- [ ] Ride next dev → qa → main promo (after [#2303](https://github.com/taller-projects/echo-backend/pull/2303))
- [ ] Tech PRD changelog: resolve open question 5 (attribution wins over sync) + amend "Jazz sync no cambia"
- [ ] Data team: what does ER `_process_source` do with source "Referral"? (decides whether Jazz should receive Referral)
- [ ] Reply to Meli (draft handed to Gonzalo)

## Related
- [[Map - JazzHR integration]] · [[Referral Attribution M1 permission+gating (US 24996)]] · [[Referral source variant cleanup (Bug 25021)]] · [[Candidate sync JazzHR duplicates fix (Bug 24264)]]
