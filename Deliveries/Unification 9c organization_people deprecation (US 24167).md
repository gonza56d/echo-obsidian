---
type: delivery
status: in-review
env: both
delivered:
tags: [chore, kforce, unification, tech-debt, docs]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2027"
  - "https://github.com/taller-projects/echo-backend/pull/2051"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24167"
prd: "https://app.notion.com/p/3b2aedca11f081f8a460f1c22f675ba8"
---

# Unification 9c: organization_people deprecation (US 24167)

Step 9c of the [[Kforce-main code unification (PRD 3b2aedca)]] program, with an **inverted premise**: the original plan asked to convert dev's derived `People.contact_id` (`column_property` linkedin-match) into a physical FK to converge with kforce. Pedro's investigation (in the ticket) showed `organization_people` is **legacy in both environments** — replaced by `organization_employees` — so the step became: ledger **row 11** (`deuda-cola`) + **drop of the table in both envs**. The dev-side drop was **brought forward from Phase 6 and executed in PR #2027** (per Gonzalo's direct call, after freshness evidence reclassified the traffic-check findings from blocker to courtesy heads-up): routers unmounted, `app/modules/people/` deleted, org-merge relink cleaned, migration `mq7xw2vk4dpe` (DROP VIEW + TABLE + TYPE, all IF EXISTS ⇒ kforce-replay-safe). kforce twin + FE cleanup are follow-ups.

## Azure / docs
- [US 24167](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24167) — In development; created by Pedro with the full evidence (volume counts dev/prod, consumer analysis). Step 1 (ledger row) = this delivery; step 2 (the drop) = Phase 6 follow-up.
- PRD: [Unificación del código KForce con la branch principal — PRD Técnico](https://app.notion.com/p/3b2aedca11f081f8a460f1c22f675ba8) · ledger: `docs/unification-ledger.md` row 11.

## PRs
- [#2027](https://github.com/taller-projects/echo-backend/pull/2027) → dev — **open; review r1 (Pedro, 2026-08-10) addressed in `c74f8c9c`, merge gated on the heads-up blocker**. Scope grew from docs-only to the full dev-side drop. r1 verdict: code clean; 1 process blocker (courtesy heads-up to prod reader `607b7da5-…` not done — it's the compensating control the blocker→heads-up downgrade depends on); nits: migration cycle test (done, see How), `checkfirst=True` on downgrade enum create (done), openapi baseline refs (waiver added, re-record tied to kforce twin); questions: pg_dump backup as prod-promotion precondition (added to row 11), program-owner ack of the reclassification on the ticket (asked of Pedro), waivers.toml (done).
- [#2051](https://github.com/taller-projects/echo-backend/pull/2051) → **kforce-dev** (2026-08-12) — the kforce twin. **Copy+adapt, not a cherry-pick**: #2027's migration is parented on a dev-only rev and kforce's table shape diverges (still has the physical `contact_id` col + FK; dev dropped it in `g9keztwnnspn`, never migrated to kforce). Migration `z8kqr3nw2p6t` off the verified kforce head `og0kr2s2znyu`; upgrade DROP VIEW→TABLE→TYPE (all IF EXISTS); **downgrade recreates the kforce shape WITH `contact_id`** + the 3 indexes + the view from the kept `.sql` — the recreate-with-contact_id is *required* because the smart-search view SELECTs `contact_id`. Module deleted, both mounts + org-merge relink removed, migration-cycle test asserts the recreate keeps `contact_id`. `people_position_level_enum` verified kforce-only-used by `organization_people` (`organization_employees` moved to `employee_position_level_enum` in `qrxoxk4cexrt`) ⇒ DROP TYPE clean. No `waivers.toml`/openapi baseline on kforce ⇒ that #2027 step drops out. Lint clean, 12 tests green, single alembic head, `app.routers` imports. Reviewer: **Pedro (rocha-p)** (reviewed #2027).

## How
- One `deuda-cola` row (11) following the style of rows 4/7/8: the row IS the spec of the drop, updated in-place as the check ran and the drop executed.
- All ticket claims re-verified against `origin/dev` / `origin/kforce-dev` before writing them into the ledger (mounts at dev `routers.py:493/:708`, kforce `:322/:481`; only out-of-module reference = org-merge relink in `organization/repository.py`; internal POST is an upsert `create_or_update` — the possible-ingestion path).
- **The evidence chain that unblocked the drop** (the method matters — reusable for future "is X dead?" calls): traffic check found callers (would-be blocker) → freshness check showed the table frozen (dev `max(created_at/updated_at)` = 2026-02-04; prod = 0 internal write-path calls across the whole 28d Loki retention) → runtime view check via the `Smart query:` log line (83 real LLM-generated queries in prod, 0 reference the view/table — the external SQL builder doesn't know them) → live-DB `pg_depend` check (only the known view depends on the table; no inbound FKs, no RLS). Conclusion: the "reader" consumes a frozen snapshot → heads-up, not blocker.
- Drop implementation (dev, commit `375bbdca`): unmount public+internal routers; `git rm -r app/modules/people`; remove the `organization_people` dedup+`fk_reassign` block from `migrate_organization_references` (+ its comment and test docstring); migration `mq7xw2vk4dpe` off head `91eebppm0zva` — upgrade = `DROP VIEW IF EXISTS` → `DROP TABLE IF EXISTS` → `DROP TYPE IF EXISTS people_position_level_enum` (view first: it selects FROM the table); downgrade recreates the empty final dev shape (9-value enum incl. `Owner/founder` — the DB enum has one more value than the model's `PositionLevel`!) + the 4 indexes + the view from the kept `.sql`.
- Suite: full unit + multitenancy green, **3701 passed, 1 xpassed** (the 5 flaky adoption tests didn't fire this run). **NOT via alembic** — see Gotchas.
- Review r1 fixes (`c74f8c9c`): permanent migration-cycle test `tests/unit/test_drop_organization_people_migration.py` (imports the real migration module via `importlib`, binds `alembic.op` to the testcontainer connection — the `mx7qkw9n2r4v` pattern): upgrade replay no-op → downgrade recreates enum+table+view (asserts no `contact_id`, view queryable) → upgrade real-drops; `checkfirst=True` on the downgrade enum create; `[openapi]` waiver in `waivers.toml` (2 routes + `Page_PeopleResponse_`/`PeopleResponse`/`PeopleUpdate`, deliberately NOT `PeopleInvolved` = contact module).

## Decisions
- **Drop over re-add**: re-adding the physical column to dev would be expensive and cross-tenant-risky (coalesce over a table without `tenant_id`) for a table nobody reads. Target is `DROP` in both envs; dev executed in this PR.
- **Prod traffic ≠ automatic blocker**: Gonzalo challenged the initial "parked" call; the freshness+runtime evidence showed the observed reader consumes dead data, so the gate's *intent* (don't silently break consumers) is satisfied by a courtesy heads-up. Recorded in row 11 as the reclassification.
- **Keep `smart_search_companies_employees.sql`** (deliberate deviation from the ticket's "limpieza del path muerto"): 3 historical migrations `open()` it during upgrade — deleting it breaks `alembic upgrade head` on fresh DBs. The DB **view** is what gets dropped.
- Branch named per pr-skill snake_case (`24167/unification_9c_organization_people_ledger`); PR title without conventional prefix (squash-title style).

## Gotchas
- **The unit suite does NOT run alembic.** `tests/conftest.py` builds the schema via `create_database()` (`create_all` from models) — a green suite proves the app works, not that any migration executes. I wrongly claimed the opposite in the PR body (caught while addressing Pedro's downgrade nit; corrected). Migrations only run under test when a test binds `alembic.op` to the container connection and calls upgrade()/downgrade() explicitly — the `mx7qkw9n2r4v` / `mq7xw2vk4dpe` test pattern.
- **The pre-drop traffic check FAILED (2026-08-10, Loki 7d)** — the ticket's "cero consumidores" evidence covered *code*, not *traffic*. Taller prod has a live reader: 12 GET 200 via script (`python-requests/2.33.1`), always user `607b7da5-7e10-4ea7-96b8-155d34b6041a`, across multiple orgs — plus 8 vestigial PATCH 404 from the same user's browser. kforce-dev showed an internal POST 201 + DELETE 204 pair (2026-08-04, create+delete in 1 s — probably a synthetic probe, but the internal ingestion path is proven alive). kforce-prod: 5 PATCH 404 from 4 distinct browser users, latest 2026-08-10. All PATCHes 404 everywhere (FE sends `organization_employees` ids) — pure FE cleanup. **Step 2's code was therefore NOT written**: unmounting the routers would break the prod reader on promotion.
- Prod-DB lookup of the caller was permission-blocked in-session; run manually: `PGSERVICE=echo-prod psql -c "SELECT id, email FROM \"user\" WHERE id = '607b7da5-7e10-4ea7-96b8-155d34b6041a'"`.
- **The ticket's "FE PATCH is a no-op" claim is dev-only.** Dev's `PeopleUpdate` extends plain pydantic `BaseModel` (`extra='ignore'`) → 200 and both fields dropped. But kforce's `PeopleBase` **accepts `contact_id` and persists it** to the physical column — so the pre-drop traffic check matters most on kforce, where the PATCH is half-live.
- `openapi.json` is in the golden-snapshot corpus → unmounting the people routers changes it; baseline must be re-recorded at drop time or the parity gate shows an unexplained mismatch. (No people endpoints in the corpus otherwise.)
- Worktree guard blocks anything non-trivial (pipes, heredocs, long `curl -d`) inside a worktree session — Azure comments / vault writes need `ExitWorktree(keep)` first, then re-enter.
- EnterWorktree branched from local HEAD (the 24155 branch), not `origin/dev` — always verify the base and `git switch -c <branch> origin/dev` before committing.

## Pending
- Merge #2027 (squash → dev), then move US 24167 forward.
- **MERGE BLOCKER (review r1)**: identify the Taller prod reader script owner (user id + psql query in Gotchas; the lookup was classifier-blocked in-session) and notify/get ack — Pedro flagged it as the compensating control the blocker→heads-up reclassification depends on.
- **Prod-promotion preconditions**: one-time `pg_dump -t organization_people` attached to AB#24167 (~56k rows; downgrade recreates empty structure) + the `pg_depend` dependent-objects query against prod (dev verified clean; query saved in the PR body).
- **Program-owner ack** of the reclassification on AB#24167 (asked of Pedro in the review reply — sets the precedent consciously before the kforce twin, where the PATCH persists).
- **kforce-dev twin PR — DONE: [#2051](https://github.com/taller-projects/echo-backend/pull/2051) → kforce-dev (2026-08-12)** (branch `24167/unification_9c_organization_people_kforce`). **Merge-gated on** identifying the live **internal** POST/DELETE caller (probe pair 2026-08-04 — the genuine open risk; the public FE PATCH 404s in practice) + the FE cleanup below. Backend authors of the kforce people/employees module for context: **agusmdev**, **Gattas Agustín**.
- **FE cleanup PR — owner Melina Cantamutto** (authored `employeeContactService.ts` + the /people→/organization-employees backwards-compat fallback, FE US 22264 #2559): remove the `updateEmployeeContactId` PATCH to `/organizations/{id}/people/{id}` (called via `bulkLinkEmployeesToContacts` in `ContactMatchReviewForm.tsx`) + orphan `invalidateQueries(['people'])`. In practice these PATCH 404 (FE sends `organization_employees` ids) ⇒ pure cleanup, but coordinate with Melina before the kforce drop promotes.
- Golden-snapshot `openapi.json` baseline re-record (routers removed ⇒ expected mismatch until re-recorded; noted in row 11).

## Related
- [[Kforce-main code unification (PRD 3b2aedca)]] — the program; this is step 9c after 9a (placement, #1998) and 9b (contact_relationship, #2001).
- [[Map - Kforce]]
