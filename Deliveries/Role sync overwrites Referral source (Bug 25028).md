---
type: delivery
status: merged
env: taller
delivered:
tags: [bugfix, talent, referral-attribution, jazzhr]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2304"
  - "https://github.com/taller-projects/echo-backend/pull/2306"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25028"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24999"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25021"
prd: "https://app.notion.com/p/3deaedca11f081b39e81c49c7ffb2ce3"
---

# Role sync overwrites Referral source (Bug 25028)

**Status**: PR [#2304](https://github.com/taller-projects/echo-backend/pull/2304) → dev MERGED `98ce1715` 2026-09-18 (squash, by Gonzalo); release [#2306](https://github.com/taller-projects/echo-backend/pull/2306) dev → qa OPEN · **Ticket**: [Bug 25028](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25028) (In revision)

Follow-up to [[Referral Attribution M1 permission+gating (US 24996)]], sibling of [[Referral source variant cleanup (Bug 25021)]]. Reported by Meli (FE) 2026-09-18 while testing on Taller: adding a candidate **with a role** ("Role Applying For") goes to `POST /talents/{role_id}/sync` (FE routes there when `!isMultiTenant`), and that path stamped the uploader's vendor over the freshly written `Referral` source, recording the change as **System**. Without a role (`POST /talents`) it worked, so it looked fine at first.

## Azure / docs
- [Bug 25028](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25028) — this fix. Related: [US 24999](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24999) (M2 intake), [Bug 25021](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25021).
- PRD: [PRD Técnico — Referral Attribution](https://app.notion.com/p/3deaedca11f081b39e81c49c7ffb2ce3) — explicitly left integration paths untouched ("Jazz sync ... no cambian"); **open question 5** (manual attribution wins, sync doesn't revert) never resolved → this is the PRD gap. Changelog row still to add.

## PRs
- [#2304](https://github.com/taller-projects/echo-backend/pull/2304) → dev — MERGED 2026-09-18 `98ce1715` (branch `25028/sync-preserves-referral-attribution`, commits `47c33c2c` + review follow-up `34cc5f35`).
- Release [#2306](https://github.com/taller-projects/echo-backend/pull/2306) dev → qa — OPEN 2026-09-18 evening, reviewer rocha-p (Slack DM sent). Carries #2301 + #2302 + #2304 (= all of `qa..dev`). Replaces the closed [#2303](https://github.com/taller-projects/echo-backend/pull/2303). Pre-check: `git merge-tree --write-tree origin/qa origin/dev` clean + ScriptDirectory heads on the merged tree = single `wm3rp9kzt2ve`. qa == main today → prod release = qa → main PR AFTER #2306 merges (convention: user closed dev→main #2297; rocha-p did #2299 qa→main).
- Review r1 (pr-review skill, 2026-09-18): architecture 13/0, ticket 10/10 reqs, tests-security 1 FAIL (T2: the fixed flow was asserted only against `__new__` fakes / MagicMock `update`) + 5 nits. Fixed in `34cc5f35`: route-level 201 test (`/sync` + Referral + `edit_source` → Referral row in DB), two DB-backed native-apply tests (existing Referral kept + no history; channel talent → vendor + history `changed_by_id` = uploader), 4th native matrix case, 255-cap tests; `writes_attribution` evaluated once per request (router → `keeps_attribution` kwarg), `_require_edit_source` helper for the 3 router gates, stale comments + `/sync` OpenAPI summary reworded.

## How
- Root cause: `create_and_sync_talent` → `create_talent` (attribution applied correctly) → `sync_talent_with_jazz_and_vendor` → `update_data["source"] = vendor_name` → public `update()` with no `changed_by`. Same in `_apply_talent_to_role_natively`, the re-upload branch and `POST /talents/{id}/apply/{role}` (strips Referral from an already-referred candidate). Legacy Jazz-flow default (Bugs 22384/24264/24239).
- Fix: `TalentService._apply_sync_source(update_data, talent, vendor_name, keeps_attribution)` — payload writes attribution (`writes_attribution`, same rule as #2301) → keep payload source; talent already `Referral` → never downgrade; else vendor. `create_and_sync_talent` computes `keeps_attribution` once and passes it to both paths. Both paths pass `changed_by=created_by_id`.
- Jazz payload unchanged: `sync_overrides["source"] = vendor_name` stays (avoids ER `_process_source` clearing `recruiterId` → 422).
- Router `sync_talent`: `writes_attribution` 404 gate (mirror of `POST /talents`), evaluated once and passed down as `keeps_attribution` (`create_and_sync_talent(keeps_attribution: bool | None = None)` falls back to the rule for direct callers). `_require_edit_source(user)` is the shared 404 raise for create / sync / generic PATCH. `TalentSyncCreate` now extends `TalentCreateRequest` → 422 for Referral without referrer at request time, 255 caps inherited.
- Tests: new `tests/unit/test_talent_sync_attribution.py` (Jazz + native matrix, schema), two router tests in `test_referral_source_validation.py`; existing `__new__` fakes updated.

## Decisions
- Attribution-scoped rule (Meli's proposal), not "sync never touches source": channel intakes keep the vendor default so legacy behaviour is unchanged.
- Existing `Referral` protected on `/apply` too (user approved as recommended).
- Jazz keeps receiving the vendor name for now; sending "Referral" needs data-team confirmation of `_process_source` (profiles_api local clone from 2026-08-20 doesn't contain it).
- Review question left as-is: a talent whose CURRENT source is an external vendor (not Referral) applied via `/apply` or re-uploaded with the legacy vendor echo IS downgraded to the uploader's vendor — matches the ticket's literal "already Referral" rule, asymmetric with `writes_attribution` (external source counts as attribution at intake). Product call; one-line change at the `is_referral_source(talent.source)` check if they want "Referral or external".

## Gotchas
- `__new__`-style fakes broke on the new collaborator/keyword: needed `vendor_service` stub, `talent.source` attribute, `**_kwargs` on fake `update` (`changed_by`). 422 body `detail` is a pydantic list → assert on `error.message`.
- Worktree-guard inside a worktree blocks `awk -v`, `source scripts/venv.sh`, long multi-heredoc `&&` chains and Write outside the worktree → `uv run` directly, temp files inside the worktree.
- Re-upload with owner reassignment still goes through `TalentUpdateInternal` → no history row, referrer invariant skipped, `_canonical_referrer` skipped, no explicit Camino A `link_source_to_internal_vendors` (pre-existing; 422 now caught at schema level). Now that this path can persist `source=Referral`, it is an attribution write with no audit row.
- `/apply` (`POST /talents/{id}/apply/{role}`) has NO native branch — always calls the ER→Jazz sync regardless of the `jazz_hr` flag (pre-existing). Route-level test impossible without an ER mock in the test container (none exists; only `__new__` fakes).
- `create_entity(db, TalentFactory, Talent, source="Referral", referral=...)` works: the `source` setter fills `_source` and the `before_insert` hook get-or-creates the row. Read `talent.source` back through `svc.get_by_id` (joined `source_obj`), not on the detached factory instance.

## Pending
- [x] PR #2304 reviewed (r1) + merged to dev `98ce1715`
- [ ] Verify on dev: add candidate with role + Referral → source stays Referral, history author = recruiter
- [ ] Release [#2306](https://github.com/taller-projects/echo-backend/pull/2306) dev → qa: Pedro review + merge (merge commit) → then open qa → main → prod approvals
- [ ] Tech PRD changelog: resolve open question 5 (attribution wins over sync) + amend "Jazz sync no cambia" (local write changed, outbound payload did not) + add `POST /talents/{role_id}/sync` next to `POST /talents` in Autorización/Validación criteria
- [ ] Tech PRD: record the re-upload-with-owner-reassignment path (`TalentUpdateInternal`) as the declared exception to "every source change writes one history row" and to "no write path touches owner_id" — or open a follow-up ticket
- [ ] Product: should an existing EXTERNAL-vendor source also be protected on `/apply` / legacy re-upload (see Decisions)?
- [ ] Data team: what does ER `_process_source` do with source "Referral"? (decides whether Jazz should receive Referral)
- [ ] Reply to Meli (draft handed to Gonzalo)

## Related
- [[Map - JazzHR integration]] · [[Referral Attribution M1 permission+gating (US 24996)]] · [[Referral source variant cleanup (Bug 25021)]] · [[Candidate sync JazzHR duplicates fix (Bug 24264)]]
