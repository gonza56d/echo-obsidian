---
type: map
tags: [map, kforce]
---

# Map — Kforce

Kforce is a **parallel fork**, not a config flavor: `kforce-dev`/`kforce-master` diverged from `dev` on 2026-01-09; hundreds of commits of drift. Single-tenant (no `tenant_id`, no RLS tenant filtering, `user_id` is `str`), `X-Echo-internal` auth, no `/admin` mount. Full rules in echo-backend `CLAUDE.md`.

## Backport doctrine (the thing to re-read before any "port X to kforce" task)
1. **Targeted cherry-pick** — only for small, dependency-free changes. Rarer than it looks.
2. **Copy + adapt** (most common) — reimplement against the structure kforce actually has.
3. **Scheduled batch backport** — dedicated PRD, weeks of work.

Never `git merge dev → kforce-dev`. Always verify claims against `origin/kforce-dev` (`git show origin/kforce-dev:<path>`).

## Drift bites from this window (cautionary tales)
- [[Kforce Last Contacted By filter (PR 1846)]] — dev fix `00fdc79e` never ported; resurfaced as a 500 a month later.
- [[Kforce Client Active no-job gate (Bug 23545)]] — Taller gate fixes [#1745](https://github.com/taller-projects/echo-backend/pull/1745)/[#1793](https://github.com/taller-projects/echo-backend/pull/1793) never ported; wrong states in kforce prod.
- [[Kforce contacts custom sorts (23546)]] — kforce lacks dev's `validate_order_by` override.
- [[Deep pagination selectin fix (23553)]] — planner is a separate copy; needed its own PR ([#1820](https://github.com/taller-projects/echo-backend/pull/1820)).

## Kforce-native deliveries
- [[Kforce multilevel groups (US 23339)]] — group hierarchy for Echo Usage
- [[Kforce Contact Relationships port (US 23370)]] + [[Kforce relationship aggregates M6 (US 23424)]]
- [[Client Active significant activity (US 23536)]] — kforce was the SOURCE, Taller the port (rich activity data lives there)

## Env facts
- kforce-dev Supabase: conn ref `dlacftfazmdbmreqpfth`; kforce-prod: `hslptkvpsrawnrouwkhc`.
- Kforce uses `app/migrations/versions/` (not `alembic/versions/`).
- Deploy artifacts: Helm `values-kforce-{dev,prod}.yaml`, Vault `secret-echo-backend-kforce-*`, ArgoCD `kforce-{dev,prod}` — all separate from the echo-* ones.

## Standing kforce debt
- [Task 23375](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23375) — gated physical `last_relationship_type` column DROP (owner must recreate views inline per env first).
- Group-hierarchy seed: 3 latent bugs + prod seed pending.
- M5 FE for contact relationships (Alumni flip, dashboard key rename).
