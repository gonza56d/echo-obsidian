---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, export, rfq, flaky-test]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2647"
fe_prs: []
tickets: []
prd: ""
---

# Proposal export team order flake (PR 2647)

`test_export_proposal_rfq_prints_every_section_of_the_generic_template[no_template]` failed on the dev pipeline ([build 33290](https://dev.azure.com/TallerInternTools/Snapshot%20Exploration/_build/results?buildId=33290), commit `7781510c` / #2640, which does not touch export). The RFQ cover printed the team reversed (`NLP / ML Engineer + AI Solution Architect`). Root cause: `build_proposal_request` built the Team Builder team from `project.roles`, a relationship with no `ORDER BY`. Fix: sort the roles by `(created_at, id)`.

## Azure / docs
- No ticket (`fix/` branch).

## PRs
- [#2647](https://github.com/taller-projects/echo-backend/pull/2647) → dev, opened 2026-11-13. Branch `fix/proposal_export_team_order`, commit `47546e2d`. Reviewers Leo, Pedro, Gisel.

## How
- `app/modules/project/proposal_builder.py`: `team=[_build_team_member(r) for r in sorted(project.roles, key=lambda r: (r.created_at, r.id))]`.
- The same payload feeds the proposal export (PDF/PPTX/RFQ) and the case-study generation, so all of them now send roles in creation order.
- No test change. A mutation check reversed the loaded roles: without the sort, all 3 parametrizations of the RFQ test fail; with it, they pass. `test_proposal_export.py` and `test_case_studies.py` pass (160).

## Decisions
- Sorted in the payload builder, not with `order_by` on `Project.roles`. The relationship change would reorder every load of a project's roles, so the fix stays on the export path.
- `created_at` is a Python-side default evaluated per row, so roles inserted in one commit still get distinct, ordered timestamps. `id` only breaks exact ties.

## Gotchas
- The test harness resets modules with `DELETE`, not `TRUNCATE` (`tests/db_harness.py`). After autovacuum, new rows reuse freed heap slots, so an unordered `SELECT` can return rows in any order, even rows inserted in one commit. Any test that reads an unordered relationship can flake this way.
- In production, updating a role row can change the heap order in the same way.
- The Test stage of build 33290 was re-run (attempt 2) by someone else before the fix.

## Pending
- Review + merge #2647.

## Related
- [[RFQ proposal export (Feature 23298)]] · [[Testing practice - Given-When-Then tests through real entry points (Feature 25717)]]
