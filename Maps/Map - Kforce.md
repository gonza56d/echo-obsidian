---
type: map
tags: [map, kforce]
---

# Map — Kforce

Kforce is a **parallel fork**, not a config flavor: `kforce-dev`/`kforce-master` diverged from `dev` on 2026-01-09; hundreds of commits of drift. Single-tenant (no `tenant_id`, no RLS tenant filtering, `user_id` is `str`), `X-Echo-internal` auth, no `/admin` mount. Full rules in echo-backend `CLAUDE.md`.

## ⚠️ The fork is being retired — [[Kforce-main code unification (PRD 3b2aedca)]]
Pedro's Tier-C program (**Draft**, 2026-08-04) collapses both codebases into **one** (base = `dev`) where **Kforce becomes a tenant** on its own dedicated infra/DB. When it ships, everything below — the backport doctrine and every "drift bite" — stops being a recurring tax: Kforce differences become additive, feature-gated PRs on `dev`, and `kforce-dev` is archived. Until then this map still governs; treat every port you do now as a future ledger entry the program will absorb. Read that note before any large Kforce decision.


## Backport doctrine (until unification lands — the thing to re-read before any "port X to kforce" task)
1. **Targeted cherry-pick** — only for small, dependency-free changes. Rarer than it looks.
2. **Copy + adapt** (most common) — reimplement against the structure kforce actually has.
3. **Scheduled batch backport** — dedicated PRD, weeks of work.

Never `git merge dev → kforce-dev`. Always verify claims against `origin/kforce-dev` (`git show origin/kforce-dev:<path>`).

## Drift bites from this window (cautionary tales)
- [[Kforce Last Contacted By filter (PR 1846)]] — dev fix `00fdc79e` never ported; resurfaced as a 500 a month later.
- [[Kforce Client Active no-job gate (Bug 23545)]] — Taller gate fixes [#1745](https://github.com/taller-projects/echo-backend/pull/1745)/[#1793](https://github.com/taller-projects/echo-backend/pull/1793) never ported; wrong states in kforce prod.
- [[Kforce contacts custom sorts (23546)]] — kforce lacks dev's `validate_order_by` override.
- [[Deep pagination selectin fix (23553)]] — planner is a separate copy; needed its own PR ([#1820](https://github.com/taller-projects/echo-backend/pull/1820)).

## Kforce push pipeline (2026-09, post-unification)
Emiliano's new pipeline (Bronze/Silver/Gold → push through `/internal`, TrackerRMS/HubSpot-style) replaces the old contact ingestion. Its echo-backend requests live under [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972). PRD = [Pedidos a echo-backend para el push de Kforce](https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg) (Claude Doc — read via Claude Docs MCP `read`, project → node `kind: view`).

**Deliveries**
- [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] — PRD triage + the blocker PR ([#2314](https://github.com/taller-projects/echo-backend/pull/2314), merged dev): P0-1 contact `kforce_external_id__in`, P0-2/P1-0 stable `Contact.id` tie-break, P2-1 bulk POSTs return ids.
- [[Audit log on internal via IntegrationAuditMiddleware (Task 25058)]] — P2-3 ([#2323](https://github.com/taller-projects/echo-backend/pull/2323), merged dev): `IntegrationAuditMiddleware` on `internal_app`.
- [[Interaction kforce_external_id column (US 25055)]] — Fase 2 / F1 ([#2326](https://github.com/taller-projects/echo-backend/pull/2326), open dev): `Interaction.kforce_external_id` + tenant-scoped partial unique index (column + index only).
- [[Kforce contacts kforce_external_id__in item cap (Bug 25111)]] — P0-1 follow-up ([#2344](https://github.com/taller-projects/echo-backend/pull/2344), open dev): the 100 cap counted characters (2 GUIDs); now counts ids.
- [[Kforce org updated_at filter for merges (Task 25112)]] — P1-3 ([#2345](https://github.com/taller-projects/echo-backend/pull/2345), open dev): `updated_at__gte` + merge/unmerge bumps + `merged_into_id` on internal org list.

**PRD request status (where the next agent picks up)**
- ✅ **P0-1** contact filter — #2314 (dev).
- ✅ **P0-2 / P1-0** stable tie-break on `/internal/contacts` — #2314 (dev). Pipeline no longer needs the `order_by=created_at,id` workaround.
- ✅ **P1-2** org lookup by external id — already existed (`OrganizationInternalFilter.kforce_external_id__in`); no work. Option 2 (ContactBase resolving `crm_organization_kforce_external_id`) is convenience-only scope creep — skip.
- ✅ **P2-1** bulk POSTs return ids — #2314 (dev).
- ✅ **P2-3** audit on `/internal` — #2323 (dev).
- ⏸️ **P1-1** upsert / actionable `bulk_create` — **DEFERRED**. Decision: if ever built use **option 2 (per-item results)**, NOT "second ON CONFLICT target" (Postgres = one conflict target; `contact` has 5 unique keys). Build only if Emiliano says the per-row POST/PATCH dispatcher (0 collisions) is too slow at 1.98M rows.
- 📋 **P2-2** push concurrency / `rate_limit_rpm` ([Task 25059](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25059)) — mostly an **agreement with Emiliano** (RPS + whether to enforce the stored-but-inert `rate_limit_rpm`); needs infra numbers (ingress/pooler) before answering.
- ✅ **Fase 2 / F1** interaction `kforce_external_id` column — [US 25055](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25055), [#2326](https://github.com/taller-projects/echo-backend/pull/2326) (open dev). **Tenant-scoped** partial unique `(tenant_id, kforce_external_id)` (NOT global; `contact_id` out of the key); migration `p8w3knf2v6qd` builds the index `CONCURRENTLY` on the `contact_interaction` table (**2.69M rows on kforce-dev**, ~567k on dev — not ~9M; that was contact_relationship). Column + index only — write-path wiring deferred until Kforce's Silver interaction shape exists. F2 (interaction bulk POST ids) already shipped in #2314.
- 📋 **Fase 2 / F3** bulk POST `refresh_contacts` sync policy ([Task 25056](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25056)) — agreement + BackgroundTasks parity; not started.
- 📋 **Task 25057** tech debt: `kforce_external_id` unique is **global**, not per-tenant (inherited from migration `492db619e39d`) — rebuild as partial `(tenant_id, kforce_external_id)` unique; ~2M-row index rebuild under timeout.

**Still-open cross-cutting items**
- Reply to Emiliano on Slack (owed answers: `kforce` is the agreed platform value; global-unique is inherited; `rate_limit_rpm` stored not enforced; Loki already logs `/internal`).
- qa/main promotion of #2314, #2323 and #2326 after dev QA.

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
