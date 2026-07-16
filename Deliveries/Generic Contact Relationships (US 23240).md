---
type: delivery
status: merged
env: taller
delivered: 2026-06-30
tags: [feature, contact, relationships]
prs: [1648, 1657, 1669, 1670, 1680]
tickets: [23240, 23241, 23242, 23243, 23264, 23292]
prd: "Tech PRD Notion 38aaedca (Tier A) · Business PRD 387aedca · FE US 23259"
---

# Generic Contact Relationships (US 23240) — Taller

The foundational refactor of the whole [[Map - Contact Relationships]] saga: relationship = **label** (Client/Consultant) ⟂ **state** (Active/Past), all computed **on-read** (nothing derived is persisted — kills the trigger-staleness bug). Contact rollup: any Active → Active; all Past → Past; no relationships → Prospect. "Alumni" ≡ Past Consultant.

## PRs / milestones
- [#1648](https://github.com/taller-projects/echo-backend/pull/1648) **M1** (Task 23241, 2026-06-25) — `last_relationship_type`/`current_relationship`/`previous_relationship` become on-read `column_property`; behavior-preserving (expr reproduces the trigger exactly, incl. "Alumni"). Physical column+trigger **retained** (smart-search matview read it — Leo blocked the original drop).
- [#1657](https://github.com/taller-projects/echo-backend/pull/1657) **M2+M3-additive** (23242/23243, 2026-06-26) — label-aware `_relationship_is_active_expr` (Client rule: interaction ≤12mo OR live end_date, AND account gate); per-rel `state` + contact `relationship_state` exposed; `relationship_state__in` filter.
- [#1669](https://github.com/taller-projects/echo-backend/pull/1669) review nits (Task 23292, 2026-06-29) — internal get-by-id projection parity; CI-runnable unit tests (CI = unit only!).
- [#1670](https://github.com/taller-projects/echo-backend/pull/1670) **column DROP** (Task 23264, 2026-06-29) — migration `mx7qkw9n2r4v` drops column+trigger+function; real migration round-trip test **caught a deploy-breaking bug** (view column type text vs varchar → `CAST(... AS VARCHAR)`).
- [#1680](https://github.com/taller-projects/echo-backend/pull/1680) hotfix (2026-06-30) — `mx7qkw9n2r4v` broke the dev pipeline: `_view_is_repo_shaped` guard added.

## Key decisions
- **Nothing derived is persisted** (user decision "B") — display via Python, filter/sort/aggregate via `column_property`.
- Client Active = (interaction ≤12mo OR live end_date) AND account gate — later amended by [[Client Active gate relaxation (PR 1745)]], [[Moved-away Client contacts Past (Bug 23519)]], [[Client Active significant activity (US 23536)]].

## Gotchas (reusable)
- `view_smart_search_contacts_info` + `mv_smart_search_*` are **owner-managed out-of-band** (ticket 19757): deployed = 40 cols, repo SQL = 12 cols. Any `CREATE OR REPLACE VIEW` on them fails "cannot drop columns from view" → always guard with a shape check (`_view_is_repo_shaped`).
- `CREATE OR REPLACE VIEW` can only append columns and can't change a column's type — cast to match the deployed type.
- CI runs **unit tests only** — features tested solely in `tests/system/` have no CI gate.

## Pending
- **QA/PROD still gated**: out-of-band matviews must be recreated to compute the value inline BEFORE `mx7qkw9n2r4v` runs there (dev done; coordinate with view owner, ref 19757).
- Dashboard counts reshape (#4) + `alumni_*` naming removal (#5, FE US 23259) + M3 perf measurement — still open under US 23240.

## Related
- [[Kforce Contact Relationships port (US 23370)]] — the Kforce copy+adapt
- [[Alumni label removal (PR 1742)]] · [[Map - Contact Relationships]]
