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
- Self-review 2026-10-29 (pr-review skill, full mode): **READY WITH NITS**, 0 blockers. Arch 16 PASS, PRD 19/20 (the extra `(tenant_id, project_id, version)` index is correctly omitted — the unique key serves it), tests 14 PASS. Confirmed: `projects.view` gate via router mount, DI auto-bind (no registry entry, `ai_suggestion` precedent), RLS `FOR ALL USING` covers INSERT/RETURNING, atomic rollback, header-merge order safe.
- Review round 2 2026-10-29 (pr-review skill on `6892e27c`, not posted): **READY WITH NITS**, 0 blockers, 7 nits. All fixed + pushed `91c626b4` (branch `25640/proposal-entity-r2-nits` → `origin/25640/proposal-entity`; user: fix all nits, push without waiting for local tests): `next_version` filters by the request tenant itself; the GET's 404 gate moved into `ProjectService.get_proposals` (router no longer injects `ProposalService`); renames `ProposalExportRecord` / `RenderedProposal`; new tests: `projects.view` gate via `tests/act_as.py` (200 / 404), page 2, failed commit stores nothing and frees the version, `Content-Disposition` survives the header merge, CORS exposes `X-Echo-Proposal-Id` (`tests/unit/test_cors.py`), policy pin checks `FOR ALL` / no `WITH CHECK`; the concurrency test waits on `pg_locks` (ungranted advisory lock of the second session's pid) instead of `join(0.5)`. Ruff clean, imports + collection OK; the targeted tests were not run locally. PR body refreshed.
- CI on `ec90cd59` and `6892e27c` failed with 2 failures in `tests/multitenancy/test_user_events_isolation.py`. Those tests are from M1 and fail on every branch: a fixed `occurred_at` is past the 7-day window. Fixed in [#2481](https://github.com/taller-projects/echo-backend/pull/2481), squash-merged dev `428b6b19` 2026-10-29. CI on `91c626b4` still red (branch predates the fix) → user: fix it in the same PR → merged origin/dev into the branch, pushed `3d2e0161` (2 tests green locally; CI re-running).
- Nits fixed + pushed `6892e27c` 2026-10-29 (branch `25640/proposal-entity-nits` → `origin/25640/proposal-entity`): 2 edge-case tests (empty GET list, empty-team `roles_count=0`) + comments on `next_version`/lock `project_id`-only scoping and why the list skips the `response_model=` planner. ruff clean; both new tests green locally.

## How
- `app/modules/project/proposal/` (models, schemas, repository, service). Migration `p9sz72wa88h5` (parent `r68n8jlvbspz` since `3704680c`; was `bmyaawpi69zn`): composite FK `(project_id, tenant_id)` CASCADE, `UNIQUE (project_id, version)`, tenant RLS `FOR ALL` like `ai_suggestion`, `exported_by_id` SET NULL, TimestampMixin (`created_at` = API `exported_at`).
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
- 19 new tests (versions, event, RFQ, rate card, failed render, rollback-together, list, empty list, 404, empty-team `roles_count=0`, real two-session lock, lock order; rls_probe; multitenancy + policy pin). Mutations caught: lock, GET project check, tenant filter, commit.
- Migration smoke (throwaway Postgres): upgrade / downgrade / upgrade, create_all names == migration names, re-run over existing objects. Metric 6 SQL runs on a create_all schema.
- `tests/unit/export` with `-o addopts=""`: 365 passed. Full unit + multitenancy run was in progress at PR time.

## Pending
- [x] Self-review done (READY WITH NITS, nits fixed in `6892e27c`).
- [x] Review round 2 nits fixed + pushed `91c626b4`.
- [x] [#2481](https://github.com/taller-projects/echo-backend/pull/2481) merged on dev; dev merged into #2480 (`3d2e0161`).
- [x] #2480 CI green on `3d2e0161` (6959 passed).
- [x] Chain fix: Leo's #2483 (`r68n8jlvbspz`, PSA welcome form) merged on the same parent `bmyaawpi69zn` → two heads. Dev merged in (`25e3e43e`), `p9sz72wa88h5` now Revises `r68n8jlvbspz`, pushed `3704680c` (single head; throwaway PG: downgrade ×2 + upgrade head OK; proposal migration tests 7 passed). PR body updated. CI re-running.
- [ ] Reviews (Leo / Pedro / Gise); merge.
- [ ] US 25640 description rev 2 (`roles_count`, rate card definition).
- [ ] Tell Nico: the SQL, series start at the M4 deploy date.
- [ ] qa / main promotion after merge.

## Related
- [[Customer metrics M3 - AI suggestion snapshots (US 25639)]] · [[Customer metrics M2 - domain history (US 25638)]] · [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]] · [[Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)]]
