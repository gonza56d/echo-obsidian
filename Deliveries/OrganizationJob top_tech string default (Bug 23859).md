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
- `app/modules/organization/job/models.py`: `top_tech` `default="[]"` → `default=list`. `skills` comment re-pointed (it referenced "the top_tech gotcha").
- **Added after Pedro's review (`5ecf19f6`)**: `server_default '[]'::jsonb` on `top_tech`, like `skills`, plus migration `ufqnmj4llnke` (`ALTER COLUMN top_tech SET DEFAULT '[]'::jsonb`, down_revision `j03pxu12yitx`). This is metadata-only and safe to re-run. Measured 2026-09-25: none of dev/qa/prod/kforce-dev had a DB default on `top_tech`, while `skills` had `'[]'::jsonb`. New test `test_sql_insert_without_top_tech_takes_the_db_default` does a raw `INSERT` without `top_tech` and gets `[]`. Without the server_default it fails with `NotNullViolation` (verified). Its raw INSERT must also pass `matched_talents`, which has no DB default either.
- Regression test `tests/unit/test_organization_jobs.py::test_orm_insert_without_top_tech_stores_a_jsonb_array` — ORM insert without `top_tech` → `jsonb_typeof='array'`, `top_tech_sort` is NULL (not an error), `GET /company/jobs/{id}` 200 with `[]`. **Fails on origin/dev** with `cannot extract elements from a scalar` (verified by swapping the old model in). Commit `2ea872e3` (review nit) added the FE's list sort: `GET /company/jobs?organization_id=…&id__in=<job>&order_by=top_tech_sort` → 200 + the row. Checked in isolation against the old str default: fails on its own.
- Removed the `top_tech=[]` workaround (+ its "filed as follow-up" comments) from the 3 US 23849 fixtures: unit `test_role_from_open_job.py`, multitenancy `test_role_from_open_job_isolation.py`, system `test_role_from_open_job.py`. **Cleanup only, not coverage**: those tests never read `top_tech` (`create_role_from_job` projects through `OrganizationJobRoleSeed`), so they pass on the old default too (18 passed). The workaround was never load-bearing.

## Decisions
- **No backfill migration.** Measured 2026-09-24, `jsonb_typeof(top_tech)` over every row: dev 290,862 / qa 9,217 / prod 3,211,336 / kforce-dev 50,807 → **0 non-array** everywhere. Matches the code: every prod insert path writes `top_tech` explicitly (`OrganizationJobService.create` via `get_technologies`; `bulk_create` via full `model_dump()` of `OrganizationJobCreate` whose field defaults to `[]`; scraped ingest `upsert_scraped` inserts `payload.top_tech or []`). The string default was only reachable from direct ORM inserts (fixtures/scripts/future code). The justification is the zero counts (nothing to fix), **not** migration cost — the "25s timeout" argument was never measured and the first PR body wrongly cited ~1.1M rows (largest table is Taller prod, 3.2M); reworded in the PR body after self-review.
- The ticket's premise "ingest rows without enrichment fall into the default" was wrong: only the ON CONFLICT **update** set is enrichment-conditional; the insert always carries `top_tech`.
- ~~Did not add a `server_default`~~ (r1 decision, reversed): Pedro's review listed it as an optional nit and the user asked to address the nits, so it was added in `5ecf19f6` with migration `ufqnmj4llnke`. I left `matched_talents` without a DB default: out of scope.
- The migration was verified on its own against a throwaway pgvector Postgres; the full chain can't run locally because it needs Supabase `auth.users`. Upgrade sets `'[]'::jsonb`, and re-running it is harmless. Existing rows are unchanged, and an insert without the column gets `[]`. Downgrade drops the default, after which such an insert fails the NOT NULL again.
- Repo sweep: `top_tech` was the only JSONB column with a Python-string `default=`; every other `"[]"`/`"{}"` is a `server_default` (SQL literal — fine).

## Gotchas
- `ruff format` on test files reformats unrelated lines (tests are not formatted in CI — [[reference_lint_only_lints_app]]); I reverted those hunks to keep the diff to the fix.
- Running pytest with `-p no:logging` removes `caplog` → `test_bulk_update_by_ids_drops_unknown_fields_with_warning` ERRORs. Not a real failure.

## Pending
- [ ] CI green on the `5ecf19f6` push, then merge (this session is watching CI and merges when it goes green).
- [ ] kforce-prod count not measured (no credentials): `SELECT count(*) FROM organization_job WHERE jsonb_typeof(top_tech) <> 'array';` — expected 0. **Gates closing the ticket, not the merge.** If non-zero → guarded data migration modeled on `NORMALIZE_NON_ARRAYS_SQL` in `ehjnwsqitqve` (matched_talents precedent) + `ANALYZE`.
- [ ] Merge → Bug 23859 → Closed; rides the next dev→qa→main promo.

## Self-review (2026-09-24, /pr-review r1: READY WITH NITS)
- 0 blockers. 3 nits, all addressed in `2ea872e3` + PR body PATCH: list-sort test, fixture-cleanup wording, backfill rationale wording.
- Out-of-scope follow-ups (unticketed):
  - Explicit `"top_tech": null` on the internal PATCH / bulk update (`partial_model` + `exclude_unset`) probably stores JSON `null` → same breakage. 0 rows today.
  - `tests/system/test_scraped_job_ingest.py::test_unique_source_source_id_is_enforced` passes for the wrong reason: raw INSERT hits `NotNullViolation` on `url` before the unique constraint.
  - ~~Optional hardening: `server_default '[]'::jsonb` on `top_tech`~~ → done in `5ecf19f6`.

## Related
- [[Create Role from Open Job (US 23849)]] (origin) · [[Open Jobs 1-5 matching (US 23640)]] (same bug fixed for `matched_talents`) · [[GET roles 500 virtual_interview default drift (Bug 24988)]] (same class: JSONB default vs list type)

## Pedro's review (2026-09-24, APPROVED, READY WITH NITS)
- Addressed 2026-09-25 in `5ecf19f6` with a PR comment and an updated PR body:
  1. Test isolation: the tests use `mocked_organization_factory()` and filter on their own `org.id`.
  2. `server_default` added (see How).
  3. kforce-prod count: still unmeasured (no creds). It blocks closing the ticket, not the merge.
- He flagged as out of scope: `MatchingDiffService.get_technologies` (`app/services/matching_diff_service.py:89-104`) doesn't validate the response, so an upstream `null` would be stored as JSONB `null`. Not ticketed; 0 rows today.
