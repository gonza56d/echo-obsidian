# Referral source variant cleanup (Bug 25021)

**Status**: PR open · **Ticket**: [Bug 25021](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25021) (In revision) · **PR**: https://github.com/taller-projects/echo-backend/pull/2302 (→ dev)

Follow-up to [[Referral Attribution M1 permission+gating (US 24996)]] — reported by Meli (FE) while testing on Taller.

## Problem
`is_referral_source()` / migration `xj4qk9wr2vbn` only match case/accent variants of `Referral`. Legacy prefixed/typo spellings escape every referral rule (validation, conflict, Source=Referral filter, Camino A links):
- **prod**: `Taller - Referral` = de-facto referral source — Taller tenant 1885 talents (1884 with referrer) + 29 apps + 5 vendor links; SKYE TECH 5 talents. **No canonical `Referral` row existed in prod**; xj4qk9wr2vbn was a pure no-op there.
- **dev**: 5 variants (canonical `Referral` 3, `Taller - Referral` 1846, `Taller Referral` 2, `Taller referral` 1, `Taller Referal` 2).

## Fix — migration `wm3rp9kzt2ve` (PR #2302)
Same converge steps as xj4qk9wr2vbn with matcher widened to `btrim(lower(unaccent(source))) ~ '^(taller[\s-]+)?referr?al$'` (anchored). Canonical = exact `Referral` else oldest. Prod degenerates to **rename in place** (no repoints/deletes, same source_id). Dev merges 4 variants → canonical. New final step: idempotent Camino A insert (Referral row × internal vendors, all tenants). Bypasses outbox + change-history on purpose. Inert on KForce. Downgrade = documented no-op.

## Verification
- Real `upgrade()` via `Operations.context` ran 2× against throwaway PG (prod/SKYE/dev/control shapes): converged + idempotent; anchor spares `Client Referral Program`; no orphan FKs; Camino A complete.
- Read-only dry run of the ranked CTE on real dev+prod matched expected blast radius exactly.
- Pre-change CSV snapshots of affected talent_source rows taken 2026-09-18 (prod 2 rows, dev 5) — session scratchpad; re-capture at promo time if needed.

## Decisions / nuances
- Meli's "dos Taller referral en prod" = same name in 2 tenants (Taller + SKYE TECH) — multitenancy, not dupes.
- Her custom-field claim didn't hold in DB: prod definition `talent_str_referral_9186` **disabled + 0 values** (nothing to backfill); dev `talent_str_referal_ca3c` has exactly **1** value. Referrer data already lives in `talent.referral` (2680 prod rows) and `/talents/referrers` reads that column source-agnostically.
- No data was lost by the prod deploy: xj4qk9wr2vbn matched 0 prod rows. No DB backup needed (Supabase PITR + tiny blast radius + snapshots).

## Pending
- [ ] PR #2302 review + merge to dev; verify dev DB converged (expect 1 `Referral` row, 1852 talents)
- [ ] Ride qa/main promo (feature already in prod ignoring the 1885 until this lands)
- [ ] 1 prod talent ends Referral + empty referrer → flag to recruiting
- [ ] Dev one-off: port the 1 CF value → `talent.referral`, disable `talent_str_referal_ca3c`
- [ ] Ask Meli where she saw CF data (QA? FE field ≠ column?)
- [ ] Recurrence: nothing blocks a future prefixed variant; monitor, no write-time guard for now
