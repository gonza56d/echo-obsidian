---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, kforce, contacts, internal-api, pagination]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2314"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25054"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25055"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25056"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25057"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25058"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25059"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
prd: "https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg"
---

# Kforce push — echo-backend requests: kforce_external_id__in filter (US 25054)

Emiliano Kokic's new Kforce pipeline (Bronze/Silver/Gold built) is about to push ~1.98M contacts through `/internal`, TrackerRMS/HubSpot-style. 99.8% of them (1,976,237) already exist in Echo with `kforce_external_id`, so the cutover is an **adoption** job (external id ↔ Echo id map) and 359k contacts without email or LinkedIn would become silent duplicates if adoption missed them. His PRD listed 7 requests to echo-backend; I verified every claim against `dev` (2026-09-21), found one already satisfied (P1-2: `GET /internal/organizations?kforce_external_id__in=` exists), ticketed the rest under Nicolás's Feature 24972, and shipped the only blocker plus two one-liners in one PR.

## Azure / docs
- Parent: [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972) "Kforce - New Integration pipelines structure" (Nicolás, Sprint 45)
- [US 25054](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25054) — this PR (P0-1 filter + P1-0 tie-break + P2-1 bulk ids) — In development → In revision
- [US 25055](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25055) — phase 2: `contact_interaction.kforce_external_id` + partial unique `(tenant_id, kforce_external_id)` (PRD F1)
- [Task 25056](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25056) — bulk POST `refresh_contacts` → BackgroundTasks parity + push refresh policy (F3)
- [Task 25057](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25057) — tech debt: `kforce_external_id` unique is global, not per tenant (contact / organization / activity)
- [Task 25058](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25058) — `IntegrationAuditMiddleware` on `internal_app` (P2-3)
- [Task 25059](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25059) — agree push concurrency/RPS; `rate_limit_rpm` is stored but never enforced (P2-2)
- PRD: [Pedidos a echo-backend para el push de Kforce](https://claude.ai/artifact/Ce8YpGSFnkqdYPNtomNMuC?sk=W9zUtnMU6qCcOgoVLxriMg) (Claude Doc, Emiliano, 2026-09-21; raw survey lives in the pipeline repo `docs/echo-backend-relevamiento-2026-09-21.md`)

## PRs
- [#2314](https://github.com/taller-projects/echo-backend/pull/2314) → dev — open 2026-09-21. Branch `25054/kforce-external-id-filter`.
- Review 2026-09-21 (`/pr-review`, 3 parallel reviewers): READY WITH NITS — 3/3 requirements, 0 scope creep, 0 blockers. Addressed nit inline: commit `22fecaa9` caps `kforce_external_id__in` at `max_length=100` (aligned to the ≤100-id push batch / `/internal/contacts` page cap) + 2 tests. Sibling `id__in` stays uncapped (predates this work). Second nit (EXPLAIN on a non-default sort key) is verification-only, not a code change — assessed negligible (id is the PK, cheap terminal tie-break).

## How
- `ContactFilter.kforce_external_id__in: List[str]` next to `id__in` (`app/modules/contact/filters.py`). No migration: `Contact.kforce_external_id` is `unique=True, index=True` (`models.py:712`). Public `/contacts` gets it too (shared filter).
- `ContactFilter.sort()` now appends `Contact.id` after every requested key whenever there is an `order_by`; the `_ACTIVITY_SORT_PARAMS` gate (only activity sorts got the tie-break) was removed as dead code.
- `POST /internal/contacts/relationships/bulk` and `.../interactions/bulk` return `List[RelationshipResponse]` / `List[InteractionResponse]` (the service already computed them; router declared `-> None`). Golden snapshot `w_interactions_bulk_create` waived in `tests/golden_snapshots/waivers.toml` (body class change; status/content-type still under test).
- Tests: `tests/unit/test_contact_kforce_external_id_filter.py` (filter SQL, internal route incl. cross-tenant invisibility, tie-break SQL, real paged `created_at` tie via `size=1`, both bulk bodies vs DB); `test_non_activity_sort_has_no_id_tiebreaker` flipped.

## Decisions
- **Bundle the three one-liners in one PR**, defer P1-1 (upsert by `kforce_external_id` in `bulk_create`): Postgres allows one `ON CONFLICT` target per statement, so "a second target" is not implementable as asked; the PRD itself says to drop P1-1 first. Alternative offered to Emiliano: resolve ids via the new filter, then `PATCH /internal/contacts/bulk` for the 1.976M adoptees + `POST /internal/contacts/bulk` for the ~2k new ones (~4k requests instead of 1.98M).
- **Cap `kforce_external_id__in` at 100, not `id__in`**: the push has a documented ≤100-id batch and `/internal/contacts` pages at size≤100, so a larger IN has no legitimate caller; `id__in` is left uncapped because it predates this work and changing it is out of scope.
- **Tie-break only when there is an `order_by`**: a caller that explicitly clears ordering keeps an unordered query (no hidden ORDER BY on programmatic paths).
- **Global unique on `kforce_external_id` is inherited, not a decision**: migration `492db619e39d` (2025-03-05, single-tenant fork). Answer to the PRD's alert: not on purpose; fixing it = rebuild a unique index on ~2M rows under the 25s timeout → Task 25057, direction for a second Dynamics tenant is `entity_external_links`.
- **No openapi waiver**: additive params on `/contacts` have not been waived since the cutover (contact groups #2269 added several) — consistent with current practice.
- Ticketed under Feature 24972 (not a new Feature): the PRD is the echo-backend side of that pipeline structure. Re-parent if Nicolás disagrees.

## Gotchas
- `GET /internal/contacts` uses fastapi-pagination `Params` (size ≤ 100), unlike `GET /internal/organizations` (`InternalParams`, ≤ 30000). With `kforce_external_id__in` batches of ≤100 ids that is one page per call (~19.8k calls for 1.98M). Raising it is an optional follow-up, not done.
- `ContactFilter()` built without `order_by` in a test carries the FastAPI `Query` default object → `sort()` explodes; always pass `order_by=[...]` when compiling SQL in tests (precedent: `test_contact_started_tracking_sort.py`).
- kforce-dev `EXPLAIN ANALYZE` (1.64M contacts, 1,636,527 with kforce id): default first page 0.07 ms → 0.13 ms with the tie-break (Incremental Sort, presorted `contact_created_at_idx`); 100-id `IN` lookup 20 ms via `contact_kforce_external_id_idx`; OFFSET 500000 is 16 s regardless — the offset itself, which is exactly why P0-1 matters.
- Worktree guard refuses `source`, `zsh -ic`, and `cat > file <<EOF` in Bash; python heredocs and direct `/…/.venv/bin/python -m pytest` work.
- The PRD link is a Claude Doc, not an HTML artifact: read it with the Claude Docs MCP `read` (project → node, `kind: view`), and the 68 kB result must be parsed from the saved tool-result file.

## Pending
- PR review + merge; then US 25054 → Closed, dev deploy, tell Emiliano (Slack) + reply to the PRD's questions (`kforce` is the agreed platform value; global unique inherited; `rate_limit_rpm` not enforced; Loki already logs `/internal`).
- US 25055 (interaction column) when phase 2 approaches — cheap now, expensive later.
- Tasks 25056–25059 (low priority) — 25059 needs infra numbers (ingress/pooler) before answering.
- qa/main promotion after dev QA.

## Related
- [[Map - Kforce]] · [[Kforce-main code unification (PRD 3b2aedca)]] · [[CRM organization on contact read models (Feature 24038)]] · [[Kforce Contact Relationships port (US 23370)]]
