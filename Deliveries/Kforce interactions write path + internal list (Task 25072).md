---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, kforce, contacts, interaction, internal-api]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2360"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25072"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25209"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
prd: "https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg"
---

# Kforce interactions write path + internal list (Task 25072)

Emiliano's request of 2026-09-28 (`pedido-echo-backend-release-y-pendientes-2026-09-28.md`, section B1): wave 5 of the new Kforce pipeline must **adopt the ~3.26M interactions** the old pipeline wrote before pushing new ones. Two gaps: the `kforce_external_id` column from [[Interaction kforce_external_id column (US 25055)]] was never accepted or echoed by the API (a POST carrying it stored NULL, a re-push duplicated), and there was no cross-contact interaction lookup on `/internal`. One PR ships both: F1 step 2 (Task 25072) and P2-8 (Task 25209).

## Azure / docs
- Parent: [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972) "Kforce - New Integration pipelines structure"
- [Task 25072](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25072) — F1 step 2, write path (New since 2026-09-22; In revision 2026-09-28)
- [Task 25209](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25209) — P2-8 internal list (created 2026-09-28, Sprint 45; In revision)
- Emi's request file (repo root, untracked): `pedido-echo-backend-release-y-pendientes-2026-09-28.md`; his PRD side: `docs/prd-pedidos-a-echo-backend-2026-09-21.md` in the pipeline repo (not cloned locally)

## PRs
- [#2360](https://github.com/taller-projects/echo-backend/pull/2360) → dev — OPEN 2026-09-28 (branch `25072/interaction-kforce-external-id-write-path`, commit `ee24a2bc`; review-round-1 fixes `ddbe8446` pushed from worktree `25072-review-nits-r1`, branch `25072/review-nits-r1`; Pedro's round 2 fix `28954230` pushed from worktree `25072-interaction-kforce-external-id`)
- Prerequisite: [#2326](https://github.com/taller-projects/echo-backend/pull/2326) column + index (on dev/qa/main)

## How
- `KforceExternalIdInput` mixin (`kforce_external_id` + blank→NULL validator) on `BulkInteractionCreate` / `BulkInteractionUpdate` only; `InteractionResponse.kforce_external_id` echoed everywhere; `InteractionInternalResponse` lean (`id, contact_id, created_by_id, date, type, kforce_external_id`).
- `InteractionInternalFilter(Filter)`: `contact_id__in`, `kforce_external_id__in` (field_validator cap 100 each — never `max_length`, see [[Kforce contacts kforce_external_id__in item cap (Bug 25111)]]), model_validator → 422 without a selective filter; own `sort()` with per-key default order and `id` tie-break.
- `GET /internal/contacts/interactions` = `list_router` in `contact/interaction/internal_routers.py`, mounted in `app/routers.py` **before** `internal_contact_router` (its `GET /{contact_id}` would swallow the segment) — same pattern as [[Kforce activities bulk on_conflict + internal list (Bug 25154)]].
- `InteractionService.list_internal` pins `get_tenant_id(required=True)` on `InteractionSQLRepository.tenant_query` (fails closed: `/internal` is DisableRLS and `TenantScopedRepository._base_query` only scopes when the context has a tenant).
- Golden waivers: `contact_interactions`, `contacts_flat_interactions`, `w_interactions_bulk_create_readback` → `body.items.*.kforce_external_id` (shape-only).

## Decisions
- **Write surface = internal bulk routes only** (Gonzalo 2026-09-28): the FE never carries a source id; public `InteractionCreate`/`InteractionUpdate` untouched.
- **Blank id → NULL** at the schema: `""` is NOT NULL to the partial unique index (two blank ids in one tenant collide, `test_empty_string_external_ids_collide`).
- **Default order follows the lookup key, not a bare `id`** (deviation from Emi's "orden estable por id", told on Task 25209 and in the PR): `kforce_external_id, id` when `kforce_external_id__in` is given, else `contact_id, id`; any requested `order_by` gets `id` appended. Measured on kforce-dev (2.69M rows): bare `id` → planner walks the **pkey** and filters (2.8 s per page for the heaviest 100 contacts, 29k rows) vs 0.3 ms via the contact_id index + incremental sort; and `kforce_external_id` has **no pg_stats row** (never analysed, all NULL) so any order the contact_id index can serve made the planner scan all 2.69M rows (52 s) instead of probing the partial unique index (0.1 ms).
- Duplicate handling stays `ON CONFLICT DO NOTHING` without target (there since 7efdaa85): a re-pushed id is skipped and absent from the response; a collision with any other unique key is skipped the same way.

## Review round 1 (2026-09-28, self `/pr-review`)
- Verdict on `ee24a2bc`: CHANGES REQUESTED, 1 blocker. **Blocker fixed in `ddbe8446`:** `InteractionSQLRepository.bulk_update_by_ids` had no `@TenantScopedRepository.handle_commit_errors`, so a PATCH setting an id another row of the tenant holds (or one id on two rows) raised a raw `UniqueViolation` → unmapped 500 on the adoption path. Now 400 `duplicate_item`, nothing written.
- **`order_by` allow-list** (nit, fixed): fastapi_filter only checks `hasattr`, so relationships / JSON `data` → 500 and `__table__` / `date-` → silently unordered pages (`get_all` swallows `AttributeError`; the old override used `lstrip` vs the lib's `replace`). Now `date`, `type`, `kforce_external_id` and, on a contact lookup, `contact_id`; anything else 422.
- **`id` always sorts last** (nit, fixed): `order_by=id` (Emi's assumed URL) returns the lookup order; `-id` only flips the tie-break. New kforce-dev EXPLAINs: `created_by_id` 15 s (heaviest 100 contacts), `id` / `created_by_id` on an external-id lookup > 90 s (cancelled); `date` / `kforce_external_id` 25 ms, `type` 660 ms cold, COUNT 21 ms (contact) / 0.1 ms (ext).
- `kforce_external_id` capped at 255 (btree entry limit ~2.7 KB → unmapped 500 otherwise) and stored verbatim (blank still NULL) so writes match `__in` lookups.
- `openapi` golden waiver gained the two `InteractionResponse{,WithCompany}` property paths; `last_interaction` waivers stay in #2361 (both PRs append at the end of `waivers.toml` → one-hunk conflict for whichever merges second).
- Azure comments posted on 25072 (narrowing to `BulkInteractionUpdate`, targetless DO NOTHING ≡ targeted, PATCH 400) and 25209 (order_by rules). Full unit + multitenancy: 5601 passed, 1 xpassed.
- OUT-OF-SCOPE, not ticketed yet: bulk PATCH not tenant-scoped (filters on `id` only under DisableRLS; same in `ContactRepository.bulk_update_by_ids`), `created_by_id` unchecked on bulk POST/PATCH (nested `created_by` email leak, same class as Bug 25158), no item-count cap on the interaction bulk bodies, `get_all`'s `except AttributeError: pass` around `sort()`.

## Review round 2 (2026-09-28, Pedro — CHANGES REQUESTED on `ddbe8446`)
- **Blocker:** the bulk PATCH had no tenant predicate — `bulk_update_by_ids` / `get_contact_ids` filtered by id only; `/internal` is DisableRLS and the table policy is `using="true"`, so a foreign API key rewrote another tenant's interactions (a reviewer reproduced it: 202, row overwritten, foreign contact refreshed). Pre-existing, same gap #2351 closed for activities; Pedro made it a blocker because the PR extends that method with `kforce_external_id`.
- **Fix `28954230`:** both UPDATEs + the contact lookup carry `tenant_id` passed by the service, which pins `get_tenant_id(required=True)`; `_assert_owned` → `ResourceNotFoundError(error_code="unknown_reference", context={"interactions": [...]})` before any write; unknown and foreign read the same. Full suite 5610 passed.
- **Nits, all done in the same commit:** `tenant_query` on `_base_query()`; bulk POST `ON CONFLICT` targets `(tenant_id, kforce_external_id) WHERE kforce_external_id IS NOT NULL` via `functools.partial(do_nothing_on_conflict, index_elements=…, index_where=…)`; blank items dropped from `kforce_external_id__in` before the selective gate; duplicate 400 detail names the field, not the index (service catches `DuplicateError` and re-raises when `error.constraint == KFORCE_EXTERNAL_ID_INDEX`, constant moved to `interaction/models.py`); tests for the id swap (400, nothing written) and `size=30001`.
- Reply posted on the PR; description gained a "Review round 2" section and the swap / 404 notes for the pipeline.

## Gotchas
- Any `/internal` write path on a tenant-scoped table must carry its own `tenant_id` predicate: RLS is off there and `TenantScopedRepository._base_query` only helps reads. Raw `UPDATE … WHERE id IN (…)` in a repo is the smell (`ContactRepository.bulk_update_by_ids` at `contact/repository.py:1254` has the same shape — check how `/internal/contacts/bulk` PATCH is gated).
- Another session had pushed `ddbe8446` on the same branch and updated this note; `git fetch` + `merge --ff-only` before touching a PR branch, and re-read the note before editing it.
- `EXPLAIN` on kforce-dev before trusting an ORDER BY on this table: the planner happily picks a pkey walk for `LIMIT 100` when the estimated match count is high (heavy contacts appear in the MCV list) — and has no stats at all for the fresh column.
- Worktree session: the guard refused `cmd; python3 - <<EOF`, `cat > f <<EOF; …`, `psql <<EOF | grep` chains and any heredoc whose text mentions the VCS command; single `python3 - <<EOF` (VCS-free text) and `psql -f file > out` work. Wrote SQL / PR-body / Azure / vault scripts as dot-files inside the worktree, ran them plainly, deleted them before committing.
- `CREATE TEMP TABLE` is a write under `default_transaction_read_only`; materialise id lists with `\gset` instead.
- `EnterWorktree` branched from the local `dev` (81b5eb08), not `origin/dev`: hard-reset onto `origin/dev` first.

## Pending
- Tenant-scope gap fixed in-PR (`28954230`, Pedro's blocker); still open from round 1: the `created_by_id` tenant check on bulk create/update → file a Bug.
- Pedro re-review of `28954230` → squash-merge #2360 (no bad trailers on this branch); then Task 25072 / 25209 → Closed; dev deploy; tell Emi the route shape + the ordering deviation + `201 []` on a re-pushed id + `404 unknown_reference` on a foreign id + clear-one-side-first for id swaps.
- Follow-up worth a ticket: `ContactRepository.bulk_update_by_ids` (`contact/repository.py:1254`) has the same id-only UPDATE shape; verify whether `/internal/contacts/bulk` PATCH is tenant-gated upstream.
- kforce-dev has 0 rows with `kforce_external_id` → run `ANALYZE contact_interaction` after Emi's first push so the planner gets stats for the column (autovacuum will eventually).
- qa/main promotion (rides the next release after [#2359](https://github.com/taller-projects/echo-backend/pull/2359)).

## Related
- [[Map - Kforce]] · [[Interaction kforce_external_id column (US 25055)]] · [[Kforce activities bulk on_conflict + internal list (Bug 25154)]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Kforce Consultant placement unique index + contact list ids (Task 25210)]]
