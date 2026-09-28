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
- [#2361](https://github.com/taller-projects/echo-backend/pull/2361) → dev — OPEN 2026-09-28 (branch `25210/relationship-kforce-placement-id-unique`, commit `07c889fd`)
- Twin: [#2246](https://github.com/taller-projects/echo-backend/pull/2246) `uq_contact_relationship_kforce_relationship_id`

## How
- `Relationship.__table_args__` + migration `n4yq7zr2wk9e` (revises `v3kq8dn2mr7p`): `CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_contact_relationship_kforce_placement_id ON contact_relationship (tenant_id, contact_id, kforce_placement_id) WHERE kforce_placement_id IS NOT NULL` in an autocommit block, timeout cleared. The single-column `contact_relationship_kforce_placement_id_idx` stays.
- **Precheck**: the upgrade counts duplicate groups and raises with the count before building; drops an INVALID leftover first. Verified on a throwaway `pgvector/pgvector:pg16`: CONCURRENTLY on duplicates fails and leaves `indisvalid = false`, and a re-run's `IF NOT EXISTS` keeps that INVALID index (NOTICE "already exists, skipping") — hence the precheck + drop.
- `ContactListRelationshipResponse.kforce_placement_id` / `.kforce_relationship_id`: schema-only; the planner adds the columns; `RelationshipService.list_for_contacts` (group children) reuses the schema.
- Golden waivers for the 12 `contacts_list_*` + `contacts_dashboard_list` + `contacts_flat_relationships` snapshots carry both relationship keys **and** `last_interaction.kforce_external_id` from [[Kforce interactions write path + internal list (Task 25072)]] (TOML forbids a second table per snapshot, so both live here).

## Decisions
- **Migration fails loudly on duplicates rather than deduping** (Gonzalo's call pending; my default): a data delete on prod belongs to an agreed cleanup, not a release pipeline step. Consequence: the release carrying `n4yq7zr2wk9e` will stop on kforce-prod until the 34 rows are gone.
- Prod duplicates (read-only, 2026-09-28): kforce-prod 458,160 rows with a placement id, **34 duplicate pairs**; all: same placement pushed again 2026-08-24 against org `7d82f097` "CIENA CORPORATION" (`merged_into_id` = `34f2e7c2` "Ciena"), original rows 2026-05..07 on Ciena; 0 activities, no `kforce_relationship_id`, no `application_id`/`role_placement_id`, all closed. kforce-dev: 457,192 rows, 0 duplicates. Proposed cleanup SQL is on Task 25210 (delete the 34 newer rows on the merged-away company).
- Kept the single-column index: the new one is prefixed by tenant + contact and does not serve lookups by placement id alone.

## Gotchas
- The `worktree-owner` hook pins every checkout to its branch: a second ticket needs `git worktree add -b <branch> <dir> origin/dev` (run from inside the current worktree, without `-C`) and then `EnterWorktree(path=<dir>)`. Helper dot-files (apply script, PR body) copied between worktrees with absolute paths.
- `ruff format` on a test file that CI never formats reflows unrelated hunks — `git restore` and re-apply only the intended hunk.
- kforce-prod has no `~/.pg_service.conf` entry; the direct `db.hslptkvpsrawnrouwkhc.supabase.co:5432` URL with `SET default_transaction_read_only = on` works (collation-mismatch WARNING on every connect is harmless).

## Pending
- **Decide the 34 kforce-prod rows** with Emi (delete via the SQL on Task 25210, or the pipeline re-points them) **before** the release that carries `n4yq7zr2wk9e`, or the kforce-prod migration step fails by design.
- Review + squash-merge #2361; Tasks 25210 / 25211 → Closed; dev deploy; tell Emi (`201 []` on a re-pushed placement; ids on `GET /contacts` relationships).
- qa/main promotion.

## Related
- [[Map - Kforce]] · [[Kforce interactions write path + internal list (Task 25072)]] · [[Kforce Contact Relationships]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]]
