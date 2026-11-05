---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, internal-api, navitec, data-team, background-job]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2520"
  - "https://github.com/taller-projects/echo-backend/pull/2519"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25732"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728"
prd: "https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C"
---

# Commercial signals M4 - interactions aggregates for the commercial profile API (US 25732)

Fourth signal of the data team contract: `GET /internal/commercial-signals/interactions` serves the tenant's interactions as `totals` (interaction type x period) and `by_group` (industry x interaction type x period: interactions, contacts, organizations), plus the complete `organizations` list. Navitec is the consumer; KForce is opted out. Same snapshot / refresh as [[Commercial signals M3 - deals aggregates for the commercial profile API (US 25731)]]. No FE involvement.

## PRs
- [#2520](https://github.com/taller-projects/echo-backend/pull/2520) -> dev, **OPEN**, opened 2026-11-04 at `de296910e` (branch `25732/commercial_signals_interactions`, worktree `.claude/worktrees/25732-cs-interactions`). Migration `l4rpbl15ac7b` after `1yw2kc2or920`. US 25732 In revision.
- **Review round 1** (Gise, review 5775341261, 2026-11-04, COMMENTED, no blockers, 6 nits + 3 questions): fixed in `830ba7da` 2026-11-05 from a second worktree `.claude/worktrees/25732-cs-interactions-r1` (branch `25732/commercial_signals_interactions_r1`, off the PR branch, pushed `HEAD:25732/commercial_signals_interactions` over HTTPS askpass). `origin/dev` merged first (merge commit `65f10883`, heads = 1). Replies: inline 4481443964 / 4481444486 + [comment 6660080959](https://github.com/taller-projects/echo-backend/pull/2520#issuecomment-6660080959); PR body refreshed (prod measurements, "Review round 1" section, the kforce-dev "almost never" claim corrected). US 25732 rev 4 (description + AC rewritten to the as-built contract) + comment 29270884.
- Hotfix [#2519](https://github.com/taller-projects/echo-backend/pull/2519) -> dev **MERGED** `c731b673` 2026-11-05 (alembic merge revision `1yw2kc2or920` for the #2509 / #2514 heads).
- Local: full unit + multitenancy 7,398 passed on `de296910e`; commercial-signals suites 125 passed on `830ba7da`; 7 mutation probes caught; migration up / down / up on throwaway pg16.

## Decisions (user, 2026-11-04)
- No since / until (told Juan 2026-11-02, thread 33691): whole history, `period` by `date` (never null, no undated). Future-dated follow-ups read recent.
- Company chain: related_company_id -> most recent relationship WITH a company by `relationship_recency_order`, ANY type -> current open contact_job (newest start). Unresolved still counted (industry null, no org). Resolved to the tenant's own org -> dropped (same rule as every signal). Gise asked whether the own org should stop the chain: measured on prod, Navitec 1 contact / 5 interactions, Taller 7 / 78, KForce 123 / 1,052 -> rule kept.
- KForce gate: opt-out `TenantFeature.DISABLE_COMMERCIAL_SIGNALS_INTERACTIONS` (empty snapshot, no reads, logs `commercial_signals_interactions_disabled`, tick sees it fresh). Migration sets it on tenants with an enabled `kforce` integration (precedent `c8n2vr5tqk7d`); seed_kforce_tenant.py carries it. No API/admin route for available_features, hence the migration.
- Slice count stays global (64, calibrated on KForce's 3.3M rows). Protection for a tenant that outgrows it = statement timeout fails only the interactions signal + one attempt a day after the job dies (docs say when to set the flag; clearing it on KForce means re-measuring a slice).
- `interaction_type` raw; contacts distinct per (type, company, period) summed over the group (M2 approximation).

## How
- `InteractionSQLRepository.aggregate_by_company`: CTE `per_contact` (contact, type, related_company, period) -> fallback company once per contact without related company (two correlated LIMIT 1 subqueries, both tenant-scoped since r1) -> group by (type, company, period); own org filtered with `IS DISTINCT FROM` so NULL survives. Reads contact_relationship + contact_job (M2 precedent).
- Rollup reuses `type` + `contacts`; `organization_id` nullable (migration). Reads NULL-safe: `_exclusion` = `org IS NULL OR org NOT IN (...)`; `organization_ids` skips NULL.
- Parked #2509 follow-ups done here: `ActivityPeriod` -> `SignalPeriod` in import-free `app/modules/commercial_signals/period.py`; "mapping table" docstrings; per-row unmapped-stage assertion; `_recent_since()` reads settings; midnight tests freeze noon with `clock`; hash-invariant test; relationships/deals failure tests use `db_faults`.

## Numbers (all in docs/commercial-signals.md)
- kforce-dev 2026-11-04: 3,049,169 interactions, 33% with related company, 684k contacts. 1/32 slice 11.5-13.6 s cold; 1/64 slice 4.3-10.8 s cold, ~0.2 s warm.
- kforce-prod 2026-11-05 (user, Supabase SQL editor): 3,300,265 interactions, 38.8% related company, 726k contacts, 200k recent; heaviest 1/64 slice 54k rows; slice 1 (49.8k) 0.58 s warm (contact_id range index + tenant filter; relationship probe on `ix_contact_relationship_contact_id_company_id`). Fallback IS useful there (kforce-dev said "almost never"): of 508k contacts without related company, relationship 106k, job 66k, unresolved 336k (1.03M interactions, 31%). Types: 7 client-visit kinds, plain "Client Visit" 1.94M with 0 recent.
- echo-prod 2026-11-05 (me, read-only psql via `PGSERVICE=echo-prod`; the direct `db.<ref>.supabase.co` host times out): 676,941 interactions / 4.8 GB. Navitec 564,127 (96.9% related company, 47k contacts, 111k recent); Taller 112,611 (0.1%); Battle Tested 203. Slice 1/64: Navitec contact_id range + tenant filter, 66 ms first / 28 ms warm, ~9k blocks (heaviest slice 10.2k rows, +19%); Taller BitmapAnd with `ix_contact_interaction_tenant_id`, 29 / 16 ms; Battle Tested 2 ms -> each tenant pays about its own share. Cache was warm on every run. Navitec resolution: 4,950 contacts without related company (17k, 3%) -> relationship 4,072, job 128, unresolved 749 (7.6k, 1.3%). Taller: 18,741 -> relationship 422, job 5,947, unresolved 12,363 (66k, 59%). Navitec types: 19 incl. `[[namingevent]]` 7k rows; Taller 7.
- echo-prod has two hand-made indexes absent from code and kforce-prod: `contact_relationship_active_idx (contact_id, (end_date IS NULL), end_date, start_date)` and `contact_relationship_active_latest_idx (contact_id, end_date DESC, start_date DESC)`. Worth a ticket.

## How I measured (reusable)
- Compile the ORM statement with literal binds: instantiate `InteractionSQLRepository.__new__`, set `db_session` to a fake whose `execute` raises with the statement, call `aggregate_by_company` for `id_slices(64)[1]`, then `stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})` (import `app.main.create_app` first so every mapper is configured).
- Heaviest slice: `('x' || substr(contact_id::text, 1, 2))::bit(8)::int / 4 AS slice` grouped per tenant.
- Own-org stop: per contact without related company, the two correlated subqueries (relationship by `relationship_recency_order`, open job by start_date) and `count(*) FILTER (WHERE rel_company_id = own_org)` / `... AND job_company_id <> own_org`.

## Gotchas
- polyfactory can't build under a frozen `clock` (FakeDatetime -> "Unsupported type datetime"): build rows first, then `clock.set(...)`.
- `Row.count` is the tuple method: `row._mapping["count"]`; sum() over bigint comes back Decimal -> int().
- `db_faults.fail_next(statement_containing=...)` is a plain substring: "per_contact" (interactions), "FROM organization_deal" (deals), "%(contact_ids)s" (relationships aggregate).
- Worktree guard refuses `source`, `export X=$(...)`, computed paths in sed/find and heredocs that mention the VCS; put gh / curl batches in a dotfile script inside the worktree and run it by path. The original worktree belongs to the opening session: continue a PR from a NEW worktree off the PR branch.
- `docs/` is gitignored: `git add -f docs/commercial-signals.md` or the docs change silently stays out of the commit.
- After deploy every tenant reads stale once (no interactions snapshot) -> one full refresh per tenant on the first tick.

## Pending
- Gise re-review of `830ba7da` -> squash-merge -> close US 25732.
- kforce-prod Q5: confirm the `kforce` row in `tenant_integrations` is enabled, else the migration will not flag KForce (user to run; Q0 there showed `opted_out = false`, expected pre-migration).
- Tell Juani: raw `interaction_type` (Navitec's `[[namingevent]]`, KForce's client-visit kinds) and deal `type` vs Feature 25728's "no free text"; Navitec 1.3% unresolved, Taller 59%; KForce opted out.
- Ticket for the two echo-prod-only contact_relationship indexes.
- Feature-level: Task 25734 API keys, M5 only if needed, qa/main promotion of M2-M4.

## Related
- [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]]
- [[Commercial signals M2 - relationships aggregates for the commercial profile API (US 25730)]]
- [[Commercial signals M3 - deals aggregates for the commercial profile API (US 25731)]]
