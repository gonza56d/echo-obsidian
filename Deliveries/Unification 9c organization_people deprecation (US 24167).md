---
type: delivery
status: in-review
env: both
delivered:
tags: [chore, kforce, unification, tech-debt, docs]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2027"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24167"
prd: "https://app.notion.com/p/3b2aedca11f081f8a460f1c22f675ba8"
---

# Unification 9c: organization_people deprecation (US 24167)

Step 9c of the [[Kforce-main code unification (PRD 3b2aedca)]] program, with an **inverted premise**: the original plan asked to convert dev's derived `People.contact_id` (`column_property` linkedin-match) into a physical FK to converge with kforce. Pedro's investigation (in the ticket) showed `organization_people` is **legacy in both environments** — replaced by `organization_employees`, zero internal consumers on either branch, FE reads fully migrated — so instead of re-adding a dead column to dev, the step records the divergence as `deuda-cola` **row 11** in `docs/unification-ledger.md` and defers reconciliation to Phase 6 as a **drop of the table in both envs**. Shipped as a docs-only PR to dev.

## Azure / docs
- [US 24167](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24167) — In development; created by Pedro with the full evidence (volume counts dev/prod, consumer analysis). Step 1 (ledger row) = this delivery; step 2 (the drop) = Phase 6 follow-up.
- PRD: [Unificación del código KForce con la branch principal — PRD Técnico](https://app.notion.com/p/3b2aedca11f081f8a460f1c22f675ba8) · ledger: `docs/unification-ledger.md` row 11.

## PRs
- [#2027](https://github.com/taller-projects/echo-backend/pull/2027) → dev — **open, in review** (docs-only, +1 ledger row, squash).

## How
- One `deuda-cola` row (11) following the style of rows 4/7/8: the row IS the spec of the Phase 6 drop — routers unmount (`app/routers.py` both branches), delete `app/modules/people/`, drop migration + dead `view_smart_search_companies_employees` cleanup, coordinated FE PR (`employeeContactService.ts` PATCH + orphan `invalidateQueries(['people'])`), blocking pre-drop traffic check.
- All ticket claims re-verified against `origin/dev` / `origin/kforce-dev` before writing them into the ledger (mounts at dev `routers.py:493/:708`, kforce `:322/:481`; only out-of-module reference = org-merge relink in `organization/repository.py`; internal POST is an upsert `create_or_update` — the possible-ingestion path).

## Decisions
- **Drop over re-add**: re-adding the physical column to dev would be expensive and cross-tenant-risky (coalesce over a table without `tenant_id`) for a table nobody reads. Phase 6 target is `DROP` in both envs.
- Branch named per pr-skill snake_case (`24167/unification_9c_organization_people_ledger`); PR title without conventional prefix (squash-title style).

## Gotchas
- **The ticket's "FE PATCH is a no-op" claim is dev-only.** Dev's `PeopleUpdate` extends plain pydantic `BaseModel` (`extra='ignore'`) → 200 and both fields dropped. But kforce's `PeopleBase` **accepts `contact_id` and persists it** to the physical column — so the pre-drop traffic check matters most on kforce, where the PATCH is half-live.
- `openapi.json` is in the golden-snapshot corpus → unmounting the people routers changes it; baseline must be re-recorded at drop time or the parity gate shows an unexplained mismatch. (No people endpoints in the corpus otherwise.)
- Worktree guard blocks anything non-trivial (pipes, heredocs, long `curl -d`) inside a worktree session — Azure comments / vault writes need `ExitWorktree(keep)` first, then re-enter.
- EnterWorktree branched from local HEAD (the 24155 branch), not `origin/dev` — always verify the base and `git switch -c <branch> origin/dev` before committing.

## Pending
- Merge #2027 (squash → dev), then move US 24167 forward.
- Confirm with Pedro that AC-2 ("plan de drop acordado para Fase 6") is satisfied by the ledger row, or whether the drop gets brought forward (it would be its own delivery: both branches + migration + FE PR + traffic check).
- The drop itself (Phase 6): AC-3/AC-4 (`git grep` clean, FE clean) only apply then.

## Related
- [[Kforce-main code unification (PRD 3b2aedca)]] — the program; this is step 9c after 9a (placement, #1998) and 9b (contact_relationship, #2001).
- [[Map - Kforce]]
