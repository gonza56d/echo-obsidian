# Referral source variant cleanup (Bug 25021)

**Status**: MERGED dev `aff9167e` 2026-09-18 · qa release [#2303](https://github.com/taller-projects/echo-backend/pull/2303) OPEN · **Ticket**: [Bug 25021](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25021) (In revision) · **PR**: https://github.com/taller-projects/echo-backend/pull/2302 (→ dev)

Follow-up to [[Referral Attribution M1 permission+gating (US 24996)]] — reported by Meli (FE) while testing on Taller.

## Problem
`is_referral_source()` / migration `xj4qk9wr2vbn` only match case/accent variants of `Referral`. Legacy prefixed/typo spellings escape every referral rule (validation, conflict, Source=Referral filter, Camino A links):
- **prod**: `Taller - Referral` = de-facto referral source — Taller tenant 1885 talents (1884 with referrer) + 29 apps + 5 vendor links; SKYE TECH 5 talents. **No canonical `Referral` row existed in prod**; xj4qk9wr2vbn was a pure no-op there.
- **dev**: 5 variants (canonical `Referral` 3, `Taller - Referral` 1846, `Taller Referral` 2, `Taller referral` 1, `Taller Referal` 2).

## Fix — migration `wm3rp9kzt2ve` (PR #2302)
Same converge steps as xj4qk9wr2vbn with matcher widened to `btrim(lower(unaccent(source))) ~ '^(taller[[:space:]-]+)?refer+al$'` (anchored; POSIX class so it does not depend on `standard_conforming_strings`; aligned with the ticket regex in review r1). Canonical = exact `Referral` else oldest. Prod degenerates to **rename in place** (no repoints/deletes, same source_id). Dev merges 4 variants → canonical. New final step: idempotent Camino A insert (Referral row × internal vendors, all tenants). Bypasses outbox + change-history on purpose. Inert on KForce. Downgrade = documented no-op.

## Verification
- Real `upgrade()` via `Operations.context` ran 2× against throwaway PG (prod/SKYE/dev/control shapes): converged + idempotent; anchor spares `Client Referral Program`; no orphan FKs; Camino A complete.
- Read-only dry run of the ranked CTE on real dev+prod matched expected blast radius exactly.
- Pre-change CSV snapshots of affected talent_source rows taken 2026-09-18 (prod 2 rows, dev 5) — session scratchpad; re-capture at promo time if needed.
- Automated: `tests/unit/test_fold_referral_source_variants_migration.py` (added `1f49c00e`) runs the real `upgrade()` twice in the unit suite over prod / dev / no-canonical / untouched tenant shapes — rename in place, merge + repoint (talent + application), oldest-wins, anchor misses untouched, vendor links copied before delete, Camino A, 0 orphan FKs, run-2 snapshot identical.

## Review
- **r1 2026-09-18 (`/pr-review`, scoped mode)**: 0 blockers, 5 nits, all fixed in `1f49c00e`: committed migration test; regex `referr?al` → `refer+al` (ticket's) with `[[:space:]-]`; docstring wrongly claimed `talent.source_id` indexed (it is not — the repoint hash-join short-circuits on empty `dups`, measured sub-ms on 300k rows); `-- VendorKind.INTERNAL` breadcrumb on the raw literal. CI green.
- Open from review: "inert on kforce-prod" was inferred, not observed (no local creds; kforce-dev re-verified 0/0 with the exact pattern). Runtime `is_referral_source()` still only matches `referral` — recurrence gap is a recorded decision but has no Azure follow-up ticket.

## Release
- [#2302](https://github.com/taller-projects/echo-backend/pull/2302) squash-merged to dev `aff9167e` 2026-09-18 19:44Z (CI green on `1f49c00e`).
- **qa**: [#2303](https://github.com/taller-projects/echo-backend/pull/2303) dev → qa OPEN 2026-09-18 — rider [#2301](https://github.com/taller-projects/echo-backend/pull/2301) (rocha-p: intake gate on attribution, prod 404 fix; post-prod follow-up = revert BT `Member` `edit_source` unblock). Merge with merge commit. → **CLOSED** 2026-09-18 evening, superseded by [#2306](https://github.com/taller-projects/echo-backend/pull/2306) (dev → qa with #2301 + #2302 + #2304 once Bug 25028 landed). Same migration pre-check (single head `wm3rp9kzt2ve`); Prod: [#2307](https://github.com/taller-projects/echo-backend/pull/2307) → main OPEN (cherry-pick branch `deploy/prod_2026-09-18_referral-fixes`, same 3 commits; merge only after #2306 + QA). Details in [[Role sync overwrites Referral source (Bug 25028)]].
- **main**: convention is qa → main (user closed dev→main #2297 this morning; rocha-p shipped #2299 qa→main). qa == main tree at 2026-09-18 evening, so the qa→main PR can only be opened after #2303 merges; body drafted (prod effect table, snapshot revert plan, approvals note).
- Pre-release checks: simulated `git merge-tree qa dev` → `alembic heads` single head `wm3rp9kzt2ve`; tree(main) == tree(qa). qa real data = merge path (Referral 44 + Taller Referral 661 + Taller referral 1 → 706 talents, 12 internal vendors linked); prod = 2 renames + 1 link (Lagom, inactive). Prod Taller row already carries 5 links: 4 internal vendors named "Taller" (cross-tenant, pre-existing quirk) + external "Taller Recruitment".
- Gotcha: qa's tree has 6 old migration files with different `down_revision` than dev (re-chained by cherry-pick releases into qa, e.g. #2266); each branch is a valid single chain and dev never touches those files, so merges keep qa's versions. Always simulate the chain before a release.

## Decisions / nuances
- Meli's "dos Taller referral en prod" = same name in 2 tenants (Taller + SKYE TECH) — multitenancy, not dupes.
- Her custom-field claim didn't hold in DB: prod definition `talent_str_referral_9186` **disabled + 0 values** (nothing to backfill); dev `talent_str_referal_ca3c` has exactly **1** value. Referrer data already lives in `talent.referral` (2680 prod rows) and `/talents/referrers` reads that column source-agnostically.
- No data was lost by the prod deploy: xj4qk9wr2vbn matched 0 prod rows. No DB backup needed (Supabase PITR + tiny blast radius + snapshots).
- Test gotchas: pydantic `EmailStr` rejects the reserved `.test` TLD (seed talents with `@fold.echo`); conftest creates an internal vendor inside `mocked_tenant`, so Camino A assertions on that tenant must query `vendor.kind='internal'` instead of hard-coding a set.

## Pending
- [x] PR #2302 review r1 (self, `/pr-review`) — nits fixed `1f49c00e`
- [x] PR #2302 merged to dev `aff9167e`
- [ ] Verify dev DB converged (expect 1 `Referral` row, 1852 talents)
- [ ] Merge #2303 (dev → qa, merge commit); verify qa: 1 `Referral` row / 706 talents; `POST /talents` source=LinkedIn no-permission → 201
- [ ] Open qa → main after #2303 merges (body drafted); prod approvals; post-deploy: filter returns 1885, revert BT unblock (#2301)
- [ ] Confirm kforce-prod has 0 variant rows (Supabase `hslptkvpsrawnrouwkhc`) or drop the claim
- [ ] File Azure follow-up for the runtime recurrence gap (write-time guard / widened `normalize_source_name`)
- [ ] 1 prod talent ends Referral + empty referrer → flag to recruiting
- [ ] Dev one-off: port the 1 CF value → `talent.referral`, disable `talent_str_referal_ca3c`
- [ ] Ask Meli where she saw CF data (QA? FE field ≠ column?)
- [ ] Recurrence: nothing blocks a future prefixed variant; monitor, no write-time guard for now
