---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, security, talent, access-control, vendor, visibility]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2414"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25504"
prd: ""
---

# External vendors see all LinkedIn candidates via auto-linked channel source (Bug 25504)

Taller prod: the external vendors **TeamUp** (12 users) and **WES** (13 users) could see the 65 LinkedIn-sourced candidates of the org, almost all sourced by Taller recruiters (reported by Belen Alday / TeamUp to Paloma, CSR, 2026-10-13). Root cause: vendor-scope visibility is source-based (RLS on `talent` + `application`: "the talent's source is linked to my vendor in `vendor_sources`"), `LinkedIn` is one shared channel row per tenant, and the `Talent` `before_insert` hook `set_source` auto-links the creator's vendor to whatever source the talent carries. The Chrome extension stamps `source="LinkedIn"` on every import, so one import by a TeamUp recruiter (1 talent) and three by WES linked `(vendor, LinkedIn)` and exposed the whole channel. Fixed by never auto-linking a channel source to an external vendor; data fix pending on prod.

## Azure / docs
- [Bug 25504](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25504) — Sev 2, Sprint 45, tag CSR. Ticket carries vendor config (`GET /vendors`), counts (`GET /talents`) and Paloma's suggested data fix.
- No PRD (bugfix).

## PRs
- [#2414](https://github.com/taller-projects/echo-backend/pull/2414) → dev — **OPEN** 2026-10-13, branch `25504/linkedin_source_external_vendor_visibility`, commit `93669f35`.
- No FE change (visibility is RLS-only; FE just lists what the API returns).

## How
- `app/modules/talent/models.py::set_source` (before_insert): resolves the creator's vendor **id + kind** in one join; when `kind == external` and `is_channel_source(target._source)` (`CHANNEL_SOURCES` = LinkedIn / Referral / Self-applied, case/accent-insensitive) it returns before the `vendor_sources` insert. The talent still gets the channel `source_id`; internal vendors and non-channel sources (a partner's own name) link exactly as before.
- Tests: `tests/system/test_talent_set_source.py` (parametrized external+channel → no link; internal+LinkedIn → link; external+own source → link) and a route-level case in `tests/unit/test_referral_source_validation.py` (`POST /talents` as agency recruiter with `source=LinkedIn` → 201, keeps LinkedIn, no link) so CI (unit-only) covers it.
- Local run 2026-10-13: 12 system + 37 unit + 168 related (user-bound keys, referral isolation/conflicts, application RLS/ownership/recruiter override, fold-referral migration) all green.

## Decisions
- **Talent only** (Gonzalo): no contacts / other entities. Applications follow automatically because their RLS joins the talent's source.
- **LinkedIn stays visible to the internal vendor only.** Only Taller recruiters use the extension today, so `source=LinkedIn` ≡ "added by Taller from the extension". The alternative (re-attribute external recruiters' LinkedIn imports to their own vendor source, like user-bound API keys do in `public_api/talent_write_service._resolve_source`) was proposed and deliberately deferred: "if other vendors start using the extension we tweak it when it becomes a problem".
- **Admin validation left out**: `PATCH /vendors` still lets an admin link a channel source to an external vendor by hand. Explicit admin action, auditable; not blocked in this PR.
- The exposure itself is a bug (nobody decided external vendors see the LinkedIn channel; Leandro's auto-link commit `202559fe` 2026-03-10 meant "a vendor sees what it creates"); only the remedy involved product choices.

## Gotchas
- Vendor-scope visibility cannot express "candidates my vendor loaded": it is purely `talent.source_id ∈ my vendor's sources`. Any shared source linked to an external vendor leaks the whole source. The hook is the silent path; `PATCH /vendors` the manual one.
- Prod psql reads from a Claude session were blocked by the auto-mode classifier ("Production Reads") — counts/config in this note come from the ticket (Paloma verified via API as super admin).
- `tests/system/test_talent_set_source.py` is in the **system** suite (CI runs unit only) — hence the extra route-level unit test.

## Pending
- [ ] Review + merge #2414 → dev, then qa / main promotion.
- [ ] **Data fix on prod Taller, once the PR is approved and before merge** (Gonzalo): re-source the 4 LinkedIn talents created/owned by TeamUp (1) / WES (3) to their vendor's own source with `talent_change_history` rows, then delete the two `(vendor, LinkedIn)` `vendor_sources` rows. Audit + transactional SQL prepared in the worktree at `docs/bug_25504_prod_taller_data_fix.sql` (gitignored). Audit query A1 also lists every external vendor linked to a channel source across tenants — run it on prod + kforce-prod.
- [ ] Follow-up only if an external vendor starts importing from the extension: attribute their LinkedIn imports to the vendor's own source (intake rewrite in `TalentService.create_talent`) or add an owner-vendor RLS branch.
- [ ] Optional: reject channel sources for `kind=external` in `VendorService.create/update`.

## Related
- [[Referral Attribution M1 permission+gating (US 24996)]] — introduced `CHANNEL_SOURCES`, `is_external_source_name`, the own-vendor exemption and the user-bound-key source fix this bug mirrors.
- [[Role sync overwrites Referral source (Bug 25028)]] — channel-vs-attribution rule on the application-source snapshot.
