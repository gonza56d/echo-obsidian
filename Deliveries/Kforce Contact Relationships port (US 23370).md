---
type: delivery
status: merged
env: kforce
delivered: 2026-07-07
tags: [feature, kforce, contact, relationships]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1700"
  - "https://github.com/taller-projects/echo-backend/pull/1701"
  - "https://github.com/taller-projects/echo-backend/pull/1709"
  - "https://github.com/taller-projects/echo-backend/pull/1710"
  - "https://github.com/taller-projects/echo-backend/pull/1732"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23369"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23370"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23371"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23372"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23373"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23374"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23375"
prd: "Tech PRD Notion 38faedca (mine) · Business PRD 380aedca (Kforce)"
---

# Kforce Contact Relationships port M1–M4 (US 23370)

**Copy + adapt** (never cherry-pick) of [[Generic Contact Relationships (US 23240)]] to kforce-dev, **plus net-new Kforce-only features** the Taller PRD scoped out (Re-Engage, tenure, account-scoped fields, expanded view). Kforce is where the contact domain originated; it sat at the pre-[23240](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23240) baseline (persisted `last_relationship_type` + trigger + `alumni_scheduler`).

## PRs / milestones (all → kforce-dev, merged 2026-07-02 unless noted)
- [#1700](https://github.com/taller-projects/echo-backend/pull/1700) **M1** ([23371](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23371)) — on-read column_property + `RelationshipState` rollup + **Alumni scheduler fully retired** (`alumni_scheduler.py`, `POST /alumni/promote`, `ALUMNI_SCHEDULER_*` — verified disabled in all kforce envs first).
- [#1701](https://github.com/taller-projects/echo-backend/pull/1701) **M2** ([23372](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23372)) — label-aware Client Active/Past rule + per-rel `state` + `relationship_state__in` filter.
- [#1709](https://github.com/taller-projects/echo-backend/pull/1709) **M3** ([23373](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23373)) — net-new account-scoped **Re-Engage filter**: `_reengage_moved_in_expr` (open job at account + arrived-from-elsewhere + not-engaged-here) OR `_reengage_gone_quiet_expr` (last significant activity ≥6mo, `greatest(last_interaction_date, max activity_dates end)`). `reengage: bool` on ContactFilter, requires `company_relationship.company_id` (422 otherwise).
- [#1710](https://github.com/taller-projects/echo-backend/pull/1710) **M4** ([23374](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23374)) — account-scoped on-read fields via **GUC** (`SET LOCAL request.contact_company_id` in `get_all` → column_propertys read `current_setting`): `current_job_tenure`, `previous_company_*`, `reengage_reason` (list-only, intentional); People Involved (`recruiter`+`contacted_by`) on expanded view; **BREAKING dashboard reshape** to label×state buckets (`active_clients_count`, `past_clients_count`, …).
- [#1732](https://github.com/taller-projects/echo-backend/pull/1732) (2026-07-07) — inline smart-search `last_relationship_type` + **guarded, gated column DROP** repo-side ([Task 23375](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23375)) — actual DROP per env still gated on the view owner recreating the deployed views inline first (kforce deployed view is 38-col owner-managed; same `_view_is_repo_shaped` guard as Taller [#1680](https://github.com/taller-projects/echo-backend/pull/1680)).

## Key decisions (PRD #D1–#D6)
- Mirror Taller on-read model; enum stays Consultant|Client, "Alumni" = FE display chrome; dashboard = label×state; **gone-quiet = max(last_interaction, activity_dates ends) in-account, 6-month window**; Re-Engage = filter/flag, not an endpoint; moved-in requires `client_visits_count = 0` exact.
- M4 perf **measured on kforce-prod** (EXPLAIN ANALYZE, ~2.4ms largest account, ~10ms worst case, all index-driven) — no speculative index.

## Gotchas (reusable)
- Nested activity `EXISTS` in `people_involved`-style props needs explicit `.correlate(...)` — auto-correlation leaks other rows' people.
- GUC pattern: read the filter's company_id BEFORE `super().get_all` (filter() nulls it).
- Prospect dashboard bucket must key off the **label**, not the state rollup (Prospect-typed latest relationship derives state=Past → fell through all buckets; only data-luck kept sums correct).
- Kforce uses `app/migrations/versions/`, not `alembic/versions/`.

## Pending
- **[Task 23375](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23375) completion**: per-env owner view recreation → then the guarded migration actually drops the column.
- **M5 FE** (separate ticket): Alumni-label flip + dashboard key rename on the FE.

## Related
- [[Kforce relationship aggregates M6 (US 23424)]] — the follow-up
- [[Map - Contact Relationships]] · [[Map - Kforce]]
