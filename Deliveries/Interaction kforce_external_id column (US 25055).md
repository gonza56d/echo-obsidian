---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, kforce, contacts, interaction, migration, internal-api]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2326"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25055"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
prd: "https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg"
---

# Interaction kforce_external_id column (US 25055)

Fase 2 / F1 of Emiliano's Kforce-push PRD. `Interaction` was the only contact-owned entity with no external-identity column — its siblings already have one (`Relationship.kforce_relationship_id`, `ContactActivity.kforce_external_id`). Without it the push has no **adoption key** (Echo can't recognise interactions the old pipeline already wrote) and no **idempotency anchor** (every run would recreate them). Shipped ahead of the rest of Fase 2 because it's a migration — cheap now, expensive to retrofit once the table is large. **Column + index only**; write-path wiring waits on Kforce's Silver-layer interaction shape.

## Azure / docs
- Parent: [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972) "Kforce - New Integration pipelines structure"
- [US 25055](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25055) — this PR (PRD F1) — In development → In revision
- PRD: [Pedidos a echo-backend para el push de Kforce](https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg) (Claude Doc, Emiliano) — section "Fase 2 → F1"

## PRs
- [#2326](https://github.com/taller-projects/echo-backend/pull/2326) → dev — open 2026-09-22. Branch `25055/interaction-kforce-external-id`.
  - Reviewed via `/pr-review` 2026-09-22 (3 parallel reviewers): 0 blockers, verdict READY WITH NITS. Nits fixed `77892481` (empty-string guard + pinned predicate). Round-2 external review nits fixed `2fe0e51f`.

## How
- `Interaction.kforce_external_id: str | None` + partial unique index `uq_contact_interaction_kforce_external_id` on `(tenant_id, kforce_external_id) WHERE kforce_external_id IS NOT NULL` (`app/modules/contact/interaction/models.py`).
- Migration `p8w3knf2v6qd` (down_revision `c7k2npq4x8ra`): `ADD COLUMN` (metadata-only, instant) + `CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS` inside `op.get_context().autocommit_block()` with `SET statement_timeout = 0`. Byte-for-byte the shape of the merged, prod-run `ioa7qbx7e9xj` (relationship kforce id) migration.
- Tests `tests/unit/test_interaction_kforce_external_id.py`: model spec + DB-level guard (same-tenant dup collides incl. across contacts, two NULLs coexist, same id across tenants coexists).

## Decisions
- **Tenant-scoped, not global.** `(tenant_id, kforce_external_id)`, explicitly NOT the single-column global unique used on `Contact.kforce_external_id` / `Organization.kforce_external_id` / `ContactActivity` (the "mine" the PRD flags): a second Dynamics-ingesting tenant must not collide. Matches the PRD's explicit recommendation for this column.
- **`contact_id` deliberately out of the key** (unlike `Relationship`, which needed it for company↔contact mapping ambiguity): a source external id identifies one interaction *within a tenant*, regardless of contact — so the same id on two contacts of one tenant is correctly a duplicate.
- **Column + index only** (per Gonzalo): no `InteractionBase`/`BulkInteractionCreate` field and no `bulk_create` ON CONFLICT target yet — the exact write shape waits on Kforce's Silver layer. Keeps the migration (the expensive-to-retrofit part) landed now.
- **`CREATE INDEX CONCURRENTLY`**: `contact_interaction` is ~2.69M rows on kforce-dev (~567k on dev). A plain in-transaction `CREATE INDEX` would hold ACCESS EXCLUSIVE through the full-heap scan and risk the 25s timeout; concurrent is safe because the brand-new column is all-NULL so no row qualifies for the partial predicate.

## Review (2026-09-22)
- `/pr-review` scoped mode, 3 reviewers. Architecture 8 PASS/0 FAIL; Tests&Security 11 PASS/0 FAIL; PRD 4/7 implemented, 1 partial (AC#3), 2 out-of-scope-by-decision, 0 scope creep. **0 blockers.**
- Two nits, both fixed (commit `77892481`): (1) empty-string vs NULL — `""` is NOT NULL so it falls under the partial predicate and two empty ids in one tenant collide; added `test_empty_string_external_ids_collide` + a note that the future write path must map a missing source id to NULL, never `""`. (2) pinned the index WHERE-clause text (`kforce_external_id IS NOT NULL`) in the model-spec test. Interaction kforce-id suite now 6 pass.
- **Ticket action (not code):** US 25055 AC#3 as written enumerates the write-path exposure that this PR descopes. Amend/split AC#3 — (i) tenant-isolation of the column [met here], (ii) bulk create/update accept-and-echo [move to the deferred write-path ticket with F1.2/F1.3/F1.4] — before closing 25055.

## Round-2 review (external, 2026-09-22)
One reviewer flagged a "blocker" (ticket AC not ratified) + 4 nits. Resolution:
- **Migration `op.add_column` not idempotent** → fixed (`2fe0e51f`): `ALTER TABLE ... ADD COLUMN IF NOT EXISTS kforce_external_id VARCHAR` so the upgrade is re-runnable if the CONCURRENTLY build fails after the column commits in its own autocommit block. (Dropped the now-unused `import sqlalchemy as sa`.)
- **"RLS test mislabeled as isolation evidence"** → the reviewer assumed a tenant-scoping RLS policy. `contact_interaction`'s RLS is `using=true` ("Backend full access", kept only for PostgREST default-deny); interaction tenant isolation is app/repo-layer, and testcontainers runs as superuser so RLS is bypassed regardless. Fixed (`2fe0e51f`): the cross-tenant test is now explicitly documented as proving the **unique index** is tenant-scoped (not RLS row-hiding), and the model spec asserts the RLS policy **survived** the column add — the achievable RLS coverage for a column-only change.
- **Empty-string→NULL contract is test-only** → acknowledged; carried into the deferred write-path PR (the ingest must map a missing source id to NULL, never `""`).
- **No measured CONCURRENTLY build time** → reviewer said not required; not fabricating a number (build qualifies zero rows since the column is all-NULL).
- **"Blocker": ticket AC not ratified.** AC#6 (RLS/tenant-isolation coverage) is now met in-PR (index-scope test + RLS-policy survival guard). AC#4 (expose field on `BulkInteractionCreate`/`InteractionUpdate`/`InteractionResponse`) genuinely depends on Kforce's undefined Silver-layer interaction shape → **split to a follow-up task, mirroring the F3→Task 25056 precedent**, and amend US 25055's AC. **PENDING Gonzalo's go-ahead to create that task + post the AC amendment on 25055.**

## Gotchas
- The repo test suites build schema via `create_all`, **not** the alembic chain, and the full chain can't run on a vanilla Postgres (a Supabase migration needs `auth.users`). So the migration DDL was exercised by hand on a throwaway `pgvector/pgvector:pg16` container: upgrade + downgrade both idempotent (`IF NOT EXISTS`/`IF EXISTS`), clean final state. Behavioural uniqueness is covered by the unit tests on real PG.
- Worktree guard refuses `source`, `zsh -ic`, and shell heredocs into files; used `/…/.venv/bin/python -m pytest` directly and python3 heredocs for vault writes.

## Pending
- CI green + merge; then US 25055 → Closed, dev deploy.
- **Split AC#4 (write-path exposure) to a follow-up task + amend US 25055 AC** (like F3→25056) before closing — awaiting go-ahead.
- Write-path wiring (schema field + `bulk_create` idempotency via ON CONFLICT) when Kforce's interaction Silver shape is defined — the reason this is column-only.
- qa/main promotion after dev QA.

## Related
- [[Map - Kforce]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Audit log on internal via IntegrationAuditMiddleware (Task 25058)]]
