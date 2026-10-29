---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, customer-metrics, migration, rls, proposal]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2480"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25640"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M4 - proposal versions (US 25640)

Customer metrics M4 (metric 6, "Solutioning"). Every proposal export (`POST /projects/{id}/export/proposal`, standard or RFQ, pdf / docx / pptx) stores the project's next version in a new `proposal` table with what the file carried, plus a durable `proposal_exported` event, after the render and in one commit. `GET /projects/{id}/proposals` lists the versions. Builds on [[Customer metrics M3 - AI suggestion snapshots (US 25639)]] (on main since release [#2479](https://github.com/taller-projects/echo-backend/pull/2479), 2026-10-28).

## Azure / docs
- [US 25640](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25640) (In revision since 2026-10-29, PR linked as GitHub Pull Request). Parent [Feature 25635](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635); business contract [CR 25592](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592).
- [Tech PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj) rev 84: M4 checklist, API and schema blocks as built, 3 changelog rows (2026-10-29).
- US 25640 description still says `ai_roles_count` and "project has a Rate Card document" (rev 2): to update.

## PRs
- [#2480](https://github.com/taller-projects/echo-backend/pull/2480) → dev, OPEN 2026-10-29 (`ec90cd59`, branch `25640/proposal-entity`, worktree `.claude/worktrees/25640-proposal-entity`).

## How
- `app/modules/project/proposal/` (models, schemas, repository, service). Migration `p9sz72wa88h5` (parent `bmyaawpi69zn`): composite FK `(project_id, tenant_id)` CASCADE, `UNIQUE (project_id, version)`, tenant RLS `FOR ALL` like `ai_suggestion`, `exported_by_id` SET NULL, TimestampMixin (`created_at` = API `exported_at`).
- `ProjectService.export_proposal(..., *, exported_by_id)` returns `ExportedProposal(content, filename, proposal_id)`; after the render, `ProposalService.record_export` runs `lock_versions` (advisory xact lock) → `next_version` → `save(commit=False)` → `user_event_service.record` → `repo.commit()`.
- Router: `X-Echo-Proposal-Id` header via the new `headers` kwarg on `DownloadableFileResponse`, exposed in CORS (`app/main.py`). GET route checks `project_service.get_by_id` first (404), then the page.
- `docs/customer_metrics_m4_solutioning.sql` (6a started / finished, 6b exports, 6c conversion, 6d minutes from M5 active_time), added with `-f`.

## Decisions (user, 2026-10-29: "go ahead with your recommendations")
- Auth: `projects.view` (router-level `Protected`), same as GET /projects/{id} and the export.
- `rate_card_included` = `get_rate_card(tenant.proposal_template) is not None` (brand page, Navitec only), every format and type; a per-tenant fact.
- `ai_roles_count` → `roles_count` = `len(project.roles)` at export (nothing marks a role as AI-made).
- Concurrency: lock only around the version insert, after Team Builder + render.
- Project delete CASCADEs its proposals: known limit, as in the PRD.

## Gotchas
- `SELECT ... FOR UPDATE` on the project needs its UPDATE policy (`projects.edit`) under RLS; the export only needs `projects.view` → `pg_advisory_xact_lock(hashtextextended('proposal:<id>', 0))` instead.
- `db.session_factory()` is a `scoped_session`: two calls in one thread return the SAME session → for a two-session lock test use `db.session_factory.session_factory()`.
- `tests/unit/export` (ignored by CI): the RFQ service-flow mock lacked `case_study_instructions` → 4 failures already on dev; fixed in the PR.
- `ProposalResponse` already exists (Team Builder content, `role/solution_service.py`) → the API schema is `ProposalExportResponse`.

## Evidence
- 17 new tests (versions, event, RFQ, rate card, failed render, rollback-together, list, 404, real two-session lock, lock order; rls_probe; multitenancy + policy pin). Mutations caught: lock, GET project check, tenant filter, commit.
- Migration smoke (throwaway Postgres): upgrade / downgrade / upgrade, create_all names == migration names, re-run over existing objects. Metric 6 SQL runs on a create_all schema.
- `tests/unit/export` with `-o addopts=""`: 365 passed. Full unit + multitenancy run was in progress at PR time.

## Pending
- [ ] Full local run result + CI on `ec90cd59`; reviews (Leo / Pedro / Gise); merge.
- [ ] US 25640 description rev 2 (`roles_count`, rate card definition).
- [ ] Tell Nico: the SQL, series start at the M4 deploy date.
- [ ] qa / main promotion after merge.

## Related
- [[Customer metrics M3 - AI suggestion snapshots (US 25639)]] · [[Customer metrics M2 - domain history (US 25638)]] · [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]] · [[Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)]]
