---
type: delivery
status: merged
env: taller
delivered: 2026-10-13
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
- [#2414](https://github.com/taller-projects/echo-backend/pull/2414) → dev — **MERGED** 2026-10-13 20:00 UTC as squash `c5c544a2` (branch `25504/linkedin_source_external_vendor_visibility`, commits `93669f35` fix + `0aa9b899` review r1). Leo r1 CHANGES REQUESTED (review 5508502577) → addressed same day → approved. Pipeline build 31033 (20261013.4): BuildAndPush / Test / ReleaseDev / ReleaseKforceDev all succeeded; GH Actions test run 38459432591 green. Bug 25504 → Closed with the deploy comment.
- Follow-up [Task 25510](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25510) (child of the Bug): guard channel sources on `PATCH /vendors` + resolve the own source before the INSERT on `/sync` cold-start.
- No FE change (visibility is RLS-only; FE just lists what the API returns).

## How
- `app/modules/talent/models.py::set_source` (before_insert): resolves the creator's vendor **id + kind** in one join; when `kind == external` and `is_channel_source(target._source)` (`CHANNEL_SOURCES` = LinkedIn / Referral / Self-applied, case/accent-insensitive) it returns before the `vendor_sources` insert. The talent still gets the channel `source_id`; internal vendors and non-channel sources (a partner's own name) link exactly as before.
- Tests: `tests/unit/test_talent_rls_policies.py` (new, CI) installs the **real** talent policy via `tests/rls_probe` and flushes as the RLS-bound role — external vendor-scope + LinkedIn → RLS denial, internal + LinkedIn → inserted, external + own source → inserted. `tests/system/test_talent_set_source.py` (parametrized external+channel → no link; internal+LinkedIn → link; external+own source → link). Route-level case in `tests/unit/test_referral_source_validation.py` proves only the missing link (its 201 is a no-RLS artifact, docstring says so).
- `logger.info("set_source: channel source not linked to external vendor")` with `talent_id`/`vendor_id`/`source` on the skip branch (Leo's nit) — grep it in Loki to confirm the rule fires in prod.
- Local run 2026-10-13 (r1): 221 tests green across the hook, RLS probe, referral validation, user-bound keys, referral isolation/conflicts, application RLS/ownership/recruiter override, RLS denial translation.

## Decisions
- **Talent only** (Gonzalo): no contacts / other entities. Applications follow automatically because their RLS joins the talent's source.
- **LinkedIn stays visible to the internal vendor only.** Only Taller recruiters use the extension today, so `source=LinkedIn` ≡ "added by Taller from the extension". The alternative (re-attribute external recruiters' LinkedIn imports to their own vendor source, like user-bound API keys do in `public_api/talent_write_service._resolve_source`) was proposed and deliberately deferred: "if other vendors start using the extension we tweak it when it becomes a problem".
- **Accepted 403 (Leo's blocker, r1).** The `talent` policy is `FOR ALL` with `USING` only (`RLSPolicySpec` default: no `with_check`), so Postgres applies `USING` to the INSERT. Before, the hook's link made a vendor-scope INSERT pass; now an external **vendor-scope** recruiter importing a channel source (LinkedIn from the extension, Referral) gets `RowLevelSecurityError` → 403 "You do not have permission to make this change" (generic FE toast). Option A (re-attribute to the vendor's own source at intake) was the alternative; B (accept the 403, document it) was chosen because LinkedIn is Taller-only by decision. Pinned by the RLS test.
- **Admin validation left out**: `PATCH /vendors` still lets an admin link a channel source to an external vendor by hand. Explicit admin action, auditable; moved to Task 25510.
- The exposure itself is a bug (nobody decided external vendors see the LinkedIn channel; Leandro's auto-link commit `202559fe` 2026-03-10 meant "a vendor sees what it creates"); only the remedy involved product choices.

## Gotchas
- Vendor-scope visibility cannot express "candidates my vendor loaded": it is purely `talent.source_id ∈ my vendor's sources`. Any shared source linked to an external vendor leaks the whole source. The hook is the silent path; `PATCH /vendors` the manual one.
- Prod psql reads from a Claude session were blocked by the auto-mode classifier ("Production Reads") — counts/config in this note come from the ticket (Paloma verified via API as super admin).
- `tests/system/test_talent_set_source.py` is in the **system** suite (CI runs unit only) — hence the extra route-level unit test and the probe-based RLS test in `tests/unit`.
- `tests/rls_probe.py` is the way to test a real policy in the unit suite (installs `auth.jwt()` / `authorize()` / `user_vendor()` + the model's `rls_policies` verbatim, switches to a non-superuser role; everything rolls back). Use `begin_nested()` around the flush so the denial can be caught and the session reused.
- Prod facts from Leo's review: vendor `Taller Recruitment ` (trailing space) is `kind=external` with 6 active **global**-scope users, has LinkedIn + Referral linked and created 52 of the 70 LinkedIn talents. Untouched by the PR and by the data fix, but it contradicts "LinkedIn = internal vendor" — decide its kind before any `(external, channel)` cleanup.
- App Comm ownership (`application/ownership.py::application_content_allowed`) keys on the application **snapshot** `source_id` when there is no owner — dropping a vendor↔source link without moving the snapshots would deny the vendor its own App Comm. Hence step F1b in the SQL.

## Pending
- [ ] qa / main promotion of `c5c544a2` (next release).
- [x] **Data fix on prod Taller — DONE 2026-10-13 20:37 UTC** (Gonzalo ran audit → dry-run → commit from the terminal; 4 talents re-sourced, 2 links dropped, verified; result posted on Bug 25504; nothing gates the prod release). Original plan, kept for the record: `bug_25504_audit.sql` (read-only; D1/D2 exact names, A1 external vendors on channel sources across tenants, A3 the 4 TeamUp/WES LinkedIn talents) then `bug_25504_prod_taller_data_fix_v2.sql` (guarded: aborts unless exactly 1 tenant + 2 vendors with own source; re-source + history rows + application snapshots + delete 2 links; idempotent). Both attached to Bug 25504 and in the worktree `docs/` (gitignored). Validated 2026-10-13 on a seeded test schema via a throwaway pytest + `psql -f` (TeamUp, `WES ` with trailing space, internal Taller vendor, creator- and owner-based talents, LinkedIn app snapshot). Claude sessions cannot run prod psql (classifier) → run it from the terminal: `PGSERVICE=echo-prod psql -f <file>` (no `-X`, the FIX block flips read-only off itself). Until it runs, TeamUp/WES still see the org's LinkedIn candidates.
- [x] **`Taller Recruitment` stays external — decided 2026-10-14** (talent-channel PRD review): an application worked by one of its recruiters on a candidate of another source must be credited to it, and `_resolve_snapshot_source` only does that for external vendors. The `(Taller Recruitment, LinkedIn)` link stays (6 global-scope users → no practical widening); the 52 historical LinkedIn talents are NOT re-credited in that release. Closing the 25504 invariant for this vendor = separate ticket (re-credit + drop the link together).
- [ ] **Accreditation to `Taller Recruitment` broken since 2026-09-21** (found in the same review): the vendor name carries a trailing space, the source row does not, and `canonical_source_id_for_vendor` (#2313) compares `lower(unaccent())` without trim → `None` → the partner branch never runs (0 automatic snapshots since 09-21, 5 manual `PATCH /applications/{id}/source`, 58 TR-owned applications kept the prior source). Fix planned as M0 of the talent-channel PRD: `btrim` in `canonical_source_id_for_vendor`, the `set_source` hook lookup and `TalentSourceRepository.get_by_name`; `str_strip_whitespace=True` on `VendorCreate`/`VendorUpdate`; `UPDATE vendor SET name = btrim(name)` in prod.
- [ ] [Task 25510](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25510): channel-source guard in `VendorService.create/update` + `/sync` cold-start own-source link.
- [ ] Extension imports re-credited to the creator's vendor at intake (`channel=linkedin` + `source=<vendor>`) → talent-channel PRD (Claude Doc, 2026-10-14, backend-only, no extension release): https://claude.ai/code/artifact/34631c54-12ea-4b80-8690-6db066703db9

## Related
- [[Referral Attribution M1 permission+gating (US 24996)]] — introduced `CHANNEL_SOURCES`, `is_external_source_name`, the own-vendor exemption and the user-bound-key source fix this bug mirrors.
- [[Role sync overwrites Referral source (Bug 25028)]] — channel-vs-attribution rule on the application-source snapshot.
