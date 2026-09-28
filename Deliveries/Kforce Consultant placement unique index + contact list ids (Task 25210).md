---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, kforce, contacts, relationship, migration, internal-api]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2361"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25210"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25211"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
prd: "https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg"
---

# Kforce Consultant placement unique index + contact list ids (Task 25210)

Emiliano's request of 2026-09-28, section B2 (wave 4, ~458k Consultant relationships): P2-6 a unique partial index on `(tenant_id, contact_id, kforce_placement_id)` so a retried bulk POST no longer duplicates the Consultant row (the POST uses `ON CONFLICT DO NOTHING`, which only helps where a unique index exists), and P2-7 both KForce ids on the relationships nested in `GET /contacts` (the pipeline's only per-contact lookup). One PR, two tasks.

## Azure / docs
- Parent: [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972)
- [Task 25210](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25210) — P2-6 unique index (In revision 2026-09-28; carries the prod cleanup proposal)
- [Task 25211](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25211) — P2-7 ids on the contacts-list relationships (In revision)

## PRs
- [#2361](https://github.com/taller-projects/echo-backend/pull/2361) → dev — OPEN 2026-09-28 (branch `25210/relationship-kforce-placement-id-unique`, commit `07c889fd`; review round 1 fixes `e5e7b04b`, pushed from worktree `25210-review-nits`)
- Twin: [#2246](https://github.com/taller-projects/echo-backend/pull/2246) `uq_contact_relationship_kforce_relationship_id`

- Merge of `origin/dev` after #2360 landed: `3508216a` (waivers.toml conflict, both sides kept; never rebased)

## How
- `Relationship.__table_args__` + migration `n4yq7zr2wk9e` (revises `v3kq8dn2mr7p`): `CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_contact_relationship_kforce_placement_id ON contact_relationship (tenant_id, contact_id, kforce_placement_id) WHERE kforce_placement_id IS NOT NULL` in an autocommit block, timeout cleared. The single-column `contact_relationship_kforce_placement_id_idx` stays.
- **Precheck**: the upgrade counts duplicate groups and raises with the count before building; drops an INVALID leftover first. Verified on a throwaway `pgvector/pgvector:pg16`: CONCURRENTLY on duplicates fails and leaves `indisvalid = false`, and a re-run's `IF NOT EXISTS` keeps that INVALID index (NOTICE "already exists, skipping") — hence the precheck + drop.
- `ContactListRelationshipResponse.kforce_placement_id` / `.kforce_relationship_id`: schema-only; the planner adds the columns; `RelationshipService.list_for_contacts` (group children) reuses the schema.
- Golden waivers for the 12 `contacts_list_*` + `contacts_dashboard_list` + `contacts_flat_relationships` snapshots carry both relationship keys **and** `last_interaction.kforce_external_id` from [[Kforce interactions write path + internal list (Task 25072)]] (TOML forbids a second table per snapshot, so both live here).

## Review round 1 (2026-09-28) — CHANGES REQUESTED → fixed in `e5e7b04b`
- **B1**: the duplicate count ran inside the migration transaction under env.py's 25 s `statement_timeout`. Measured on kforce-dev: **53.0 s** (`EXPLAIN ANALYZE`: ordered Index Scan on `contact_relationship_kforce_placement_id_idx` + Incremental Sort, ~461k buffers; 1,327,274 rows / 713 MB heap). The migration would have died with `QueryCanceled`, not the count. A synthetic 1.5M-row local copy took 0.46 s (bitmap + hash plan) — misleading; measure on real data.
- **B2**: `lock_timeout=20s` (env.py connection option) still applied to CONCURRENTLY's waits for older snapshots → INVALID index after 20 s behind any long transaction (reproduced). Precedent `oemp7cidx3vk` clears it.
- **Fix**: count + INVALID drop + build all run inside the autocommit block, with `statement_timeout` **and** `lock_timeout` cleared and restored after (`SHOW` + `set_config`, the `j03pxu12yitx` pattern); a valid index skips everything. Side effect: the block commits the run's earlier revisions first, so a count failure leaves them applied (alembic_version = the previous revision).
- **B3 (merge gate, no code)**: #2359 (dev→qa) has live `dev` as head → merge #2361 only after #2359 merges. kforce-prod: `MigrateKforceProd` raises on the 34 pairs and `DeployArgoCDKforceProd` depends on it. The PR body now opens with this gate.
- Nits fixed: session `SET statement_timeout = 0` no longer leaks to later revisions; comments (SHARE lock, not ACCESS EXCLUSIVE; no unmeasured row counts; "fork's list responses never exposed them"); PR body names `GET /internal/contacts` as the pipeline's route (no group fold there); +7 tests (intra-batch dup, per-contact POST/PATCH dup → 400 `duplicate_item`, exact bulk PATCH detail, NULL rows stored, ids on `/internal/contacts` + `/contacts/relationships` + `/contacts/dashboard`, statement count 1 vs 4 contacts — a lazy-load mutation turns it red 23 vs 29), group test asserts folded values; waivers add `last_relationship.*`, `internal_contacts_list`, `w_contacts_bulk_create_readback`, `openapi` `ContactRelationship.properties.kforce_*`, drop the empty `contacts_dashboard_list`.
- Migration re-exercised on throwaway PG16 through an env.py-shaped harness (connection timeouts, one outer txn, prior revision, probe): clean → VALID + next revision sees 25s/20s; re-run no-op; downgrade ×2; 34 dups → RuntimeError, prior revision committed; INVALID leftover + dups → stops on count, after cleanup → rebuilt VALID; 30 s REPEATABLE READ holder → build waits and finishes VALID.

## Decisions
- **Migration fails loudly on duplicates rather than deduping** (Gonzalo's call pending; my default): a data delete on prod belongs to an agreed cleanup, not a release pipeline step. Consequence: the release carrying `n4yq7zr2wk9e` will stop on kforce-prod until the 34 rows are gone.
- Prod duplicates (read-only, 2026-09-28): kforce-prod 458,160 rows with a placement id, **34 duplicate pairs**; all: same placement pushed again 2026-08-24 against org `7d82f097` "CIENA CORPORATION" (`merged_into_id` = `34f2e7c2` "Ciena"), original rows 2026-05..07 on Ciena; 0 activities, no `kforce_relationship_id`, no `application_id`/`role_placement_id`, all closed. kforce-dev: 457,192 rows, 0 duplicates. Proposed cleanup SQL is on Task 25210 (delete the 34 newer rows on the merged-away company).
- Kept the single-column index: the new one is prefixed by tenant + contact and does not serve lookups by placement id alone.

## Gotchas
- `/contacts/dashboard` only lists tracked contacts whose **latest job has a `change_kind`** (LATERAL inner join in `ContactDashboardFilter.filter`) — a test needs a `ContactTracker` **and** a `Job(change_kind=...)`.
- Worktree-isolated sessions refuse heredocs and multi-line `python3 -` scripts: write a dot-file in the worktree with the Write tool, run it, delete it.
- The `worktree-owner` hook pins every checkout to its branch: a second ticket needs `git worktree add -b <branch> <dir> origin/dev` (run from inside the current worktree, without `-C`) and then `EnterWorktree(path=<dir>)`. Helper dot-files (apply script, PR body) copied between worktrees with absolute paths.
- `ruff format` on a test file that CI never formats reflows unrelated hunks — `git restore` and re-apply only the intended hunk.
- kforce-prod has no `~/.pg_service.conf` entry; the direct `db.hslptkvpsrawnrouwkhc.supabase.co:5432` URL with `SET default_transaction_read_only = on` works (collation-mismatch WARNING on every connect is harmless).

## kforce-prod cleanup (2026-09-28, done)
- Gonzalo ran the guarded script from the main checkout (`psql <url> -X -f cleanup.sql`): `\copy` backup of the 34 rows to `duplicate_consultant_relationships_2026-09-28.jsonl` (in the echo-backend main checkout dir, untracked), then `DELETE … USING` on the rows pointing at CIENA CORPORATION `7d82f097` whose keeper on Ciena `34f2e7c2` exists, with `kforce_relationship_id`/`application_id`/`role_placement_id` NULL and no activities; `COMMIT` only if `deleted_count=34 AND groups_after=0` (psql `\gset` + `\if`). Output: `COPY 34`, `deleted_count=34 groups_after=0`, `COMMITTED`.
- Verified read-only afterwards: duplicate groups 0, rows with placement id 458,126, rows on the merged company 0, Ciena keepers 41. Comment left on Task 25210 and on release PR [#2365](https://github.com/taller-projects/echo-backend/pull/2365) (Pedro's qa → main, 17 commits, carries `n4yq7zr2wk9e`).
- The auto-mode permission layer refused to let the session write/run the delete against prod ("Modify Shared Resources"); read-only checks were fine. Hand the script to the user for prod writes.

## Pending
- ~~Decide the 34 kforce-prod rows~~ done 2026-09-28 (see above). Still owed to Emi: confirm the old pipeline will not re-push placements against the merged-away company id; re-run the duplicate count right before approving `echo-backend-kforce-prod` on #2365.
- CI on `e5e7b04b`; full local unit suite was still running at push time. **Merge only after #2359 merges** (then squash-merge #2361); Tasks 25210 / 25211 → Closed; dev deploy; tell Emi (`201 []` on a re-pushed placement; ids on `GET /contacts` relationships).
- qa/main promotion.

## Related
- [[Map - Kforce]] · [[Kforce interactions write path + internal list (Task 25072)]] · [[Kforce Contact Relationships]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]]
