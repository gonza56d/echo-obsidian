---
type: delivery
status: in-progress          # PRD is Draft; no code/tickets yet — this is the planning reference note
env: both                    # base=dev (Taller preserved byte-identical); Kforce converges to a tenant. Backend + DB + infra
delivered:
tags: [program, kforce, migration, db, backend, planning]
prs: []
fe_prs: []
tickets: []
prd: "https://app.notion.com/p/3b2aedca11f081f8a460f1c22f675ba8"
---

# Kforce↔main code unification (PRD 3b2aedca)

The program that **retires the Kforce fork**. Today echo-backend is two parallel codebases that diverged 2026-01-09 (merge-base `339992ab`) and drift hard (as of 2026-08-04: `dev` has **1 495** commits kforce lacks, kforce has **438** of its own, **1 044** files differ, migrations **429** dev vs **278** kforce). Dual maintenance is unsustainable and Kforce now needs dev-only modules (Sourcing, Solutioning). **Decided end state: a single codebase (base = `dev`) where Kforce is just another tenant** running on its own dedicated infra + DB. The Kforce DB converges to `tenant_id` + RLS with exactly one tenant row; Kforce's functional differences move behind the existing per-tenant config (`TenantFeature` / `TenantModule` / `tenant_integrations`). **Infra and databases stay separate — no data migration between environments, only structural convergence.** Owner **Pedro Rocha**, Tier C, **Draft** (2026-08-04). Engineering-initiated: no Capa 1 business PRD, no Azure work items yet. This note is the map for everything that will link off it.

> Why this note reframes the whole Kforce saga: once this ships, the [[Map - Kforce]] **backport doctrine** (cherry-pick / copy+adapt / never `git merge dev→kforce-dev`) is what gets *retired* — every "port X to kforce" bite in that map becomes an additive gated PR in `dev` instead. The fork's whole reason to exist goes away.

## Azure / docs
- No Azure work items yet (estimation is deliberately deferred to per-phase planning). Tickets will be filed phase by phase.
- PRD: [Unificación del código KForce con la branch principal — PRD Técnico](https://app.notion.com/p/3b2aedca11f081f8a460f1c22f675ba8) (parent DB: *Echo Product Roadmap*).
- Child page: [Plan de ejecución — pasos de implementación](https://app.notion.com/p/3b2aedca11f0815a97f2eb4208b5c5b1) (implementation steps).

## How (approach + phases)
**Approach = additive, gated reimplementation — NOT a git merge.** Base is `dev`; every Kforce difference is re-implemented as an additive, feature-gated PR on `dev` following dev conventions (tenant-scoped repos, `SET LOCAL request.tenant_id` GUC, composite FKs, dev's exception hierarchy). `kforce-dev` becomes a **reference spec + behavior-snapshot source** until cutover, then is archived (`kforce-dev-final`). A branch merge was rejected: ~60% of the 1 044-file diff is the mechanical tenancy axis → irresolvable conflicts and loses the "Taller never regresses" guarantee.

**Two cross-cutting artifacts hold the program together:**
- **Unification ledger** — living doc mapping each difference → port PR → gating mechanism → parity evidence. Every merge to `kforce-dev` during the program creates a port-forward obligation in the ledger.
- **Golden snapshots** — ~40 endpoints recorded against `kforce-dev` QA (normalized), replayed in CI against the unified app + converged DB, and against the live env at cutover. Primary net against silent behavior drift. Recorded in Phase 0.

**Migrations are the one deliberate exception to "no git merge":** both histories are retained in one `app/migrations/versions/` tree, joined by an alembic **merge revision** + a **canonicalization queue** — so **zero `alembic_version` stamping**; every DB reaches the single head via `alembic upgrade head`. Kforce's DB gets tenant-ified by **replaying dev's real, prod-tested tenant-ification history** (seed tenant from `organization`, re-point `contact.tenant_id`, `add_tenant_id_to_*` backfills ~48 tables, then composite FKs + policies) — not a parallel script + stamp (rejected: the team already had a stamp-over-unapplied-migrations incident).

**Dual maintenance during the program:** from the start, `kforce-dev` only takes contractual bugfixes/features **with a mirror PR in dev**; from **Phase 3** (inversion point) new Kforce work is built in `dev` first; from **Phase 7** `kforce-dev` is hotfix-only.

**Milestones = phases** (deps: 0 → 1 → {2,3,4}; 5 parallel; 6 continuous; 7 last):
- **Phase 0 — Foundations**: gating table + superset contracts ratified with both FEs; open decisions 1–8 resolved; the only 2 new flags merged (`TenantFeature.LABEL_STATE_DASHBOARD`, `TenantFeature.SSO_TALENT_PROVISIONING`); reproducible Kforce-tenant seed; golden-snapshot corpus recorded; ledger live.
- **Phase 1 — Schema substrate (additive)**: ATS columns (`contact_activity` +9 with partial unique per-kind on `kforce_external_id`, `placement` +9 with composite FK, `contact_relationship` +2); `people.contact_id` physical FK backfilled in dev; `onupdate=CASCADE` on FKs to `user.id`; **`handle_new_user` trigger merged** with tests for every signup path; email uniqueness converged to `(tenant_id, lower(email))` + trigger. Taller suites/snapshots unchanged.
- **Phase 2 — Identity / SSO**: Entra/Teams exchange served by dev, gated by a tenant-scoped `sso_provider` row; `UserRole.TALENT` + provisioning gated by `SSO_TALENT_PROVISIONING`.
- **Phase 3 — Data plane (dual-maintenance inversion point)**: bulk internal endpoints (`PATCH /internal/contacts/relationships/bulk`, activities bulk ≤500/tx, placements internal GET/POST bulk) served by dev; **dual-auth shim merged** (inert without `LEGACY_INTERNAL_TENANT_ID`); api-key provisioning script extended to Kforce Vault; golden snapshots running in CI.
- **Phase 4 — Product features**: Re-Engage, People Involved, Total Placements/Client Visits (always-on, data-driven); label-state dashboard behind `LABEL_STATE_DASHBOARD`; historical drift resolved in dev's favor (incl. `has_echo`, with sign-off); kforce's internal-router hack dies.
- **Phase 5 — group_hierarchy + adoption (parallel)**: `group_hierarchy` rewritten tenant-scoped (tenant_id, composite FKs, RLS) under the existing ADOPTION addon; adoption reconciled (dev's cross-tenant `_resolve_tenant_id` + kforce's group-selection); `/reporting` canonical also serves the deprecated alias `/admin/reports` (needs `/admin` mounted **after** the auth router in `main.py`).
- **Phase 6 — Parity (hard gate, continuous from Phase 1)**: triage the **233 divergent kforce test files** (drop / port tenant-parameterized / rewrite superset); snapshots ≥95% exact-match, rest explained; migration gates green (from-scratch, from-kforce-shape, from-Taller-shape).
- **Phase 7 — Cutover**: 2 consecutive clean rehearsals on a kforce-prod clone (incl. old image booting on the converged schema = the rollback window); kforce-dev migrated + soaked with real pipelines within the error budget; kforce-prod migrated; FE deployed; post-cutover callers migrate to api keys one by one (shim → 0 → removed), alias removed, branches archived, new schedulers enabled one at a time.

**Rollout order:** Taller dev → qa → kforce-dev → same-day fresh rehearsal on a kforce-prod clone → kforce-prod → Taller prod.

## Decisions
- **Kforce = a tenant, not a config flavor.** Structural convergence only; infra/DBs stay dedicated and separate; no cross-env data migration.
- **Additive gated reimplementation over branch merge**; **replay dev's tenant-ification history over parallel-script+stamp** (zero stamping is a structural property of the approach — `alembic_version` can never lie).
- **Taller compatibility is the central invariant:** every unification PR declares "Taller flag-off behavior: unchanged" with byte-identical response snapshots + green unit/system/multitenancy suites; every new dev migration during the program is additive + nullable/defaulted (no mandatory backfill, zero downtime for Taller).
- **Only 2 new feature flags** for the whole program (`LABEL_STATE_DASHBOARD`, `SSO_TALENT_PROVISIONING`).
- **Internal auth end state:** `/internal/*` requires `X-Echo-Api-Key` (per-tenant, resolves tenant + suppresses outbox + DisableRLS). Transition via a **dual-auth shim**: if `X-Echo-Api-Key` is absent, `X-Echo-internal` matches the secret, and `LEGACY_INTERNAL_TENANT_ID` is set (Kforce deployments only; inert in Taller), resolve to that tenant and log a `legacy_internal_auth` metric. Shim removed when the metric hits 0.
- **Open decisions forced in Phase 0** (owners/defaults in the PRD): (1) `role_placement.hire_pay_rate` — dev drops it, kforce reporting uses it → data loss if dev wins; (2) chat RLS — root-cause kforce's `disable_chat_rls` before re-enabling; (3) `tenant.id = organization.id` seed trick (makes the hot `contact` re-point a 0-row UPDATE) vs a batched mass UPDATE; (4) `has_echo` — kforce also requires a logo, converging to dev changes visible Kforce behavior; (5) `talent-echo-creator` (kforce-only outbound dev deleted) — port gated or retire; (6) `ContactDashboardResponse`/label-state superset sign-off from both FE TLs; (7) triage dev-only migrations that mutate data on replay over Kforce; (8) real endpoint inventory of C2/C3/C4 (grep their repos) — a blocking Phase-0 *discovery*.

## Gotchas
- **`disable_chat_rls` (kforce-only migration) replayed on Taller prod would disable chat RLS.** Must be explicitly neutralized in the guards pass; final chat-RLS state decided in the canonicalization queue.
- **Revision-id collision `interaction_subject_note`** exists distinctly in each branch → rename the kforce copy to a fresh random id + fix the one `down_revision` that references it. Pre-flight (blocking): all 5 envs' `alembic_version` must be at their branch's expected head. Also audit the **7 backports** that share a revision id.
- **Guards pass**: 190 dev-only migrations must be made kforce-safe and 39 kforce-only made Taller-safe (`to_regclass`/`IF [NOT] EXISTS`, `ADD VALUE IF NOT EXISTS`, `NOT EXISTS` backfills, `CREATE INDEX CONCURRENTLY IF NOT EXISTS` on hot tables). ~13 duplicate-DDL pairs become idempotent no-ops; different-shape ones (adoption tables, `user_group`) keep the create and get reshaped in the canonicalization queue.
- **Kforce data verification post-upgrade (blocking):** exactly 1 tenant row; `tenant_id IS NULL = 0` across ~48 backfilled tables; orphan probes on every re-pointed FK; RLS smoke (own GUC = rows, foreign GUC = 0).
- **Silent contract drift already exists** in the 1 044-file diff (e.g. `has_echo` differs between branches with no one having decided that) — that's the whole point of golden snapshots; any unexplained mismatch is a cutover blocker.
- **Cutover downtime**: per-env maintenance window with the app scaled to zero (kills the known old-pods + column-drop deadlock vector); single alembic transaction (atomic rollback), fall back to `transaction_per_migration=True` with a resume runbook if rehearsal shows excessive locks.
- **Point of no return** is explicit: first destructive migration (split expand/contract to push it past the soak) or first write by a unified-only feature (new schedulers stay off at cutover).

## Consumers affected (why this touches everything)
FE Kforce (additive PR: tolerate extra fields, ~25 new `Permission` members, read `label_state`, migrate `/admin/reports`→`/reporting`) · **entity-resolution + jazz-client** (401 on `/internal` → dual-auth shim + per-tenant api key, migrate at their own pace) · Kforce pipelines (Azure DevOps) · companies-api · shared outbound (vectorizer, resume parser, team builder) · GoTrue `handle_new_user` trigger · kforce ops scripts · Helm/ArgoCD/Vault (Kforce envs start consuming `dev`/`main` by parameter) · 4 new dev schedulers (off at cutover, enabled one by one).

## Pending (the whole program)
- **Everything** — Draft PRD, no code, no tickets. Phase 0 must resolve open decisions 1–8 and the blocking discoveries (real `/internal` endpoint inventory of the Kforce callers; whether FE Kforce validates schemas strictly with zod).
- **Explicitly OUT of this program** (future/separate): cross-env data migration; enabling **TrackerRMS writeback (outbox) for Kforce** (capacity installed but gated off — see [[Map - TrackerRMS integration]]); functional changes to Sourcing/Solutioning; FE unification; Kforce infra migration.

## Related
- [[Map - Kforce]] · every Kforce delivery in that map is a "port bite" this program is designed to make obsolete.
- [[Map - JazzHR integration]] · [[Map - TrackerRMS integration]] — jazz-client + entity-resolution + the (deferred) Kforce TrackerRMS writeback are all consumers of the `/internal` auth change.
- Kforce-native deliveries that this program absorbs: [[Kforce multilevel groups (US 23339)]] (group_hierarchy → Phase 5), [[Kforce Contact Relationships port (US 23370)]] + [[Kforce relationship aggregates M6 (US 23424)]], [[Kforce Client Active no-job gate (Bug 23545)]], [[Kforce contacts custom sorts (23546)]], [[Kforce Last Contacted By filter (PR 1846)]].
