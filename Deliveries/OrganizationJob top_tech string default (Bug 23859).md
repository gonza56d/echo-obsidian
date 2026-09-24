---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, organization-job, jsonb, open-jobs]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2347"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23859"
prd: ""
---

# OrganizationJob top_tech string default (Bug 23859)

`OrganizationJob.top_tech` (JSONB) was declared `default="[]"` — a Python **string**. The JSONB bind processor JSON-serializes it, so an ORM insert that omits `top_tech` stores the JSONB scalar `"[]"`: `OrganizationJobResponse` then fails (`top_tech: Input should be a valid list`) and `top_tech_sort` (`jsonb_array_elements_text`) raises `cannot extract elements from a scalar`. Fixed by `default=list`. Latent: no poisoned rows exist anywhere measured.

## Azure / docs
- [Bug 23859](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23859) — filed by me 2026-07-29 as a follow-up of [[Create Role from Open Job (US 23849)]]. State → In revision 2026-09-24 (PR hyperlink + measurement comment added).

## PRs
- [#2347](https://github.com/taller-projects/echo-backend/pull/2347) → dev — OPEN 2026-09-24 (branch `23859/org-job-top-tech-default`, worktree `.claude/worktrees/23859-top-tech-default`).

## How
- `app/modules/organization/job/models.py`: `top_tech` `default="[]"` → `default=list` (Python-side ORM default only — **no DDL / no migration**). `skills` comment re-pointed (it referenced "the top_tech gotcha").
- Regression test `tests/unit/test_organization_jobs.py::test_orm_insert_without_top_tech_stores_a_jsonb_array` — ORM insert without `top_tech` → `jsonb_typeof='array'`, `top_tech_sort` is NULL (not an error), `GET /company/jobs/{id}` 200 with `[]`. **Fails on origin/dev** with `cannot extract elements from a scalar` (verified by swapping the old model in).
- Removed the `top_tech=[]` workaround (+ its "filed as follow-up" comments) from the 3 US 23849 fixtures: unit `test_role_from_open_job.py`, multitenancy `test_role_from_open_job_isolation.py`, system `test_role_from_open_job.py`.

## Decisions
- **No backfill migration.** Measured 2026-09-24, `jsonb_typeof(top_tech)` over every row: dev 290,862 / qa 9,217 / prod 3,211,336 / kforce-dev 50,807 → **0 non-array** everywhere. Matches the code: every prod insert path writes `top_tech` explicitly (`OrganizationJobService.create` via `get_technologies`; `bulk_create` via full `model_dump()` of `OrganizationJobCreate` whose field defaults to `[]`; scraped ingest `upsert_scraped` inserts `payload.top_tech or []`). The string default was only reachable from direct ORM inserts (fixtures/scripts/future code). A guarded UPDATE would be a full scan (~1.1M kforce / 3.2M prod rows) inside the 25s migration timeout for a no-op.
- The ticket's premise "ingest rows without enrichment fall into the default" was wrong: only the ON CONFLICT **update** set is enrichment-conditional; the insert always carries `top_tech`.
- Did **not** add a `server_default` (like `skills` has) — out of the ticket's scope and would need a migration; column is `NOT NULL` with no DB default, so a raw-SQL insert omitting it fails loudly (NOT NULL violation) rather than poisoning.
- Repo sweep: `top_tech` was the only JSONB column with a Python-string `default=`; every other `"[]"`/`"{}"` is a `server_default` (SQL literal — fine).

## Gotchas
- `ruff format` on test files reformats unrelated lines (tests are not formatted in CI — [[reference_lint_only_lints_app]]); I reverted those hunks to keep the diff to the fix.
- Running pytest with `-p no:logging` removes `caplog` → `test_bulk_update_by_ids_drops_unknown_fields_with_warning` ERRORs. Not a real failure.

## Pending
- [ ] CI green on #2347 (user watching upstream; my local full unit+mt run was still in progress when the PR opened).
- [ ] kforce-prod count not measured (no credentials): `SELECT count(*) FROM organization_job WHERE jsonb_typeof(top_tech) <> 'array';` — expected 0.
- [ ] Merge → Bug 23859 → Closed; rides the next dev→qa→main promo.

## Related
- [[Create Role from Open Job (US 23849)]] (origin) · [[Open Jobs 1-5 matching (US 23640)]] (same bug fixed for `matched_talents`) · [[GET roles 500 virtual_interview default drift (Bug 24988)]] (same class: JSONB default vs list type)
