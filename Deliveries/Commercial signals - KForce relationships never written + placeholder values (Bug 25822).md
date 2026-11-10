---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, internal-api, kforce, data-team, background-job, memory]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2560"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25822"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728"
prd: "https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C"
---

# Commercial signals - KForce relationships never written + placeholder values (Bug 25822)

Juani's dev smoke test on 2026-11-10 (all three tenants: no 422s, totals and dates OK) found two real problems:
- KForce `/relationships` returned empty lists;
- KForce activities counted `"NULL"` / `"NaN"` strings as real values.

His third question (694k vs 747k job orders) was a difference between environments, not a bug. Follow-up of [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]] and [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]]. No FE involvement.

## Azure
- [Bug 25822](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25822): created 2026-11-10, assigned to Gonzalo, child of [Feature 25728](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728), Sprint 45. State **In revision**, PR linked.

## PRs
- [#2560](https://github.com/taller-projects/echo-backend/pull/2560) -> dev, **OPEN** 2026-11-10 at `c93103ef`.
  - Branch `25822/commercial_signals_kforce_relationships`, worktree `.claude/worktrees/25822-cs-kforce-relationships`, with its own `.venv` from `uv sync --frozen` (the main venv has no pytest-xdist).
  - Migration `7zmdcppifnwm` after `vtfza44v14jl`.
  - Reviewers Leo, Pedro, Gisel.
- Local results:
  - full `./scripts/test.sh`: 8,459 passed, 1 skipped, 1 xpassed (3:54);
  - 6 mutation probes, all caught;
  - migration stamp / upgrade / downgrade -1 / upgrade on a throwaway pg16, roles verified.

- **Review round 1 (Pedro, CHANGES REQUESTED, review 5843126072, 2026-11-10)**:
  - **Blocker:** two alembic heads. `fd6hehbo4zn7` (#2554) also revises `vtfza44v14jl`; GitHub showed no conflict.
  - **Fixed in `9387db85`** (pushed), after merging `origin/dev` with merge commit `e6f13f7c` (no rebase):
    - `7zmdcppifnwm` now revises `fd6hehbo4zn7`; `alembic heads` = 1;
    - `PLACEHOLDER_PADDING` (space/tab/CR/LF), the same in Python `strip` and SQL `btrim`;
    - `_id_slice` typed;
    - setting `COMMERCIAL_SIGNALS_WRITE_BATCH` plus a test with batch + 1 titles at `limit=5000` (no monkeypatch allowed, so rows instead of a smaller batch);
    - timeout reset to 25 s after the migration UPDATE, plus a frozen-list comment;
    - PR body: 160 ms is from psql; responses return null too; no filter reads those columns.
  - **Results:** full suite 8,535 passed (dev merged); 9 mutation probes caught; migration re-checked on the new parent.
  - **Posted:**
    - reply [issuecomment-6770108249](https://github.com/taller-projects/echo-backend/pull/2560#issuecomment-6770108249);
    - PR body "Review round 1" section;
    - Bug 25822 Fix section rewritten to as-built, plus decisions comment 29304805 (the 4 out-of-scope items Pedro listed);
    - Pedro re-requested.

## Diagnosis (2026-11-10)
- **kforce-dev:** every daily `commercial_signals_refresh` job since 2026-11-03 (the M2 merge) ended with `lease expired after max attempts` (4 tries). There was never a relationships snapshot. Activities rewrote itself on each attempt; deals and interactions were last written 11-07 with 0 rows.
- **Failure mode 1 (11-05 to 11-07):** a 1/32 contact slice of `aggregate_by_company` timed out at 20 s. The slow statements are the `contact_job` EXISTS legs of the active predicate (18-19 s cold). The error was caught, so deals and interactions still refreshed.
- **Failure mode 2 (11-08, 11-09):** all reads passed. ~4 min in, the worker container restarted silently (same pod, no traceback): out of memory. by_title has 781,332 rows on kforce-dev (408k distinct titles × company). Rebuilding the old path read-only peaked at 1,444 MiB of Python allocations / 2,341 MiB RSS; the new path peaks at 28 MiB.
- **kforce-prod:** the worker logs show the same 4× nightly restart pattern (~01:50-02:30Z), so relationships is probably empty there too (not confirmed: no DB access). Each restart also kills other in-flight jobs on the worker.
- **Tools:** Loki via the Grafana proxy worked. The Prometheus datasource (`bea6nn842sveoc`, kforce-dev) answered 504, so OOMKilled was never confirmed from metrics. The local infra repo clone is stale (August), so the worker memory limit is unknown.
- **Placeholders on kforce-dev:**
  - `contact_activity.job_function_type = 'NULL'`: 408,532 of 438,163 placements;
  - `line_of_business = 'NULL'`: 159,580 placements;
  - `city = 'Null'`: 2,798; `postal_code = 'n/a'`: 10;
  - `contact_relationship.role = 'NaN'`: 3,613, plus `-` ×3 and `N/A` ×1;
  - `contact_job.role`: none.
  - echo-dev has none.

## How
- **by_title** is read in company-id slices (`aggregate_titles_by_company(company_id_range=...)`, through `ix_contact_relationship_company_tenant_contact`, ~160 ms per 1/64 slice). Each slice's rows are final and are written as they are read: a generator is chained after the by_industry rows into `_replace_snapshot`.
- **by_industry** keeps the contact slices and the fold (about 53k groups).
- `_replace_snapshot(rows: Iterable)` writes batches of 5,000 through the repo's `open_snapshot` (delete previous + add + flush) and `insert_rows`, then the service commits. Everything stays in one transaction, so readers see the old snapshot until the commit.
- **`_RowsDigest`**: sum of per-row sha256 mod 2^256, plus the row count. It is order-independent and needs no memory beyond the running total. `_SnapshotState` captures the previous hash and source_updated_at before the delete.
- `COMMERCIAL_SIGNALS_RELATIONSHIP_SLICES` goes from 32 to 64, for both passes.
- **Placeholders:** the set lives in `app/core/missing_values.py` (`""`, `-`, `nan`, `n/a`, `none`, `null`, case-insensitive, trimmed).
  - `OptionalFreeText` (placeholder → None) is used by the activity text fields; `FreeText` (placeholder → "") by the relationship `role`. Both are in `base_schemas.py`. `partial_model` keeps the validator on the Update schemas.
  - `null_if_placeholder` is applied in the activity by_group dimensions, the activity buyer title and the relationship title.
  - Migration `7zmdcppifnwm`: one guarded `UPDATE contact_relationship SET role = ''` under `SET LOCAL statement_timeout = '120s'` (11.9 s on kforce-dev: sequential scan + statement trigger). Downgrade is a no-op.

## Decisions
- **User, 2026-11-10:** "both fixes in one PR". Then, on the measured cost: **normalize in the refresh** instead of backfilling the ~410k activity rows. A cold 1/64 batch took 21 s (non-HOT updates into all 21 contact_activity indexes, 657 MB of indexes), which would mean ~15-20 min of Apply migrations per KForce DB. The role cleanup is cheap, so it stays as a migration.
- **Order-independent digest for every signal**, not only relationships. One code path, and activities stops building ~200 MB of sorted lines. Cost: one source_updated_at bump per snapshot at the first refresh after deploy. Juani only stores that field.

## Gotchas
- The read-side sum hides duplicate title rows. A boundary test (one company exactly on a slice bound, one right below) is what catches an inclusive upper bound.
- `fail_next(statement_containing="INSERT INTO commercial_signal_rollup")` hits the relationships write only because a tenant with no activities issues no rollup INSERT.
- Worktree session: the Bash checker refuses Python heredocs with lambdas or braces inside parentheses, and anything that names git in a compound command. Edit/Write work; scripts go under `vault/tmp/` and run by path.

## Pending
- [ ] Pedro's re-review + CI on `9387db85` → squash-merge → close Bug 25822 (merged to dev = Closed).
- [ ] After the dev deploy: confirm the kforce-dev refresh job `completed` and the relationships snapshot has rows (hourly tick). Then tell Juani to rerun the KForce extract (he asked to be told).
- [ ] kforce-prod: confirm relationships is empty today (user runs the query in the SQL editor), then promote to main.
- [ ] Tell Juani: source_updated_at moves once; NULL/NaN gone from the signals after the next refresh (he keeps filtering, no coordination needed).
- [ ] Juani's two new questions, answered in chat 2026-11-10, user to relay:
  - industry coverage on kforce-dev is 4.7% earlier / 11.6% recent / 6.6% undated (dev copy) vs ~50% on prod (same measure; per-period query handed over);
  - Taller deals have no service-line field (`type` = HubSpot deal type; Navitec loads its service line into `type`).
- [ ] Optional: off-pipeline cleanup of the stored activity placeholders, if the KForce screens show them.

## Related
[[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]] · [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]] · [[Commercial signals M4 - interactions aggregates for the commercial profile API (US 25732)]] · [[Map - Kforce]]
