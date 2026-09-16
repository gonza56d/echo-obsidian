---
type: delivery
status: in-review
env: taller
delivered:
tags: [review, feature, workflow, migration]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2277"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24989"
prd: ""
---

# Workflow display_number review+fix (US 24989 | PR 2277)

Pedro's PR [#2277](https://github.com/taller-projects/echo-backend/pull/2277) (US 24989): new nullable `workflow_step.display_number` (business-facing 1-based number, distinct from 0-based `order`) + Taller-only data migration `gd1j8xrfysnf` seeding 1..30 on the 30 pipeline steps and moving "Candidate Selected by Client" ClientProcess → Offer. I ran the full 3-agent /pr-review, **found + fixed the one real blocker myself** (pushed to his branch), and commented the rest.

## Azure / docs
- [US 24989](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24989) — BE: Taller default workflow must reproduce today's stage UX (display numbers + grouping). Assigned Pedro, state New, **zero comments** (relevant: the On Hold deferral is unrecorded there).

## PRs
- [#2277](https://github.com/taller-projects/echo-backend/pull/2277) → dev OPEN (Pedro). My fix commit `029bc0f9` pushed 2026-09-16; consolidated review comment posted same day.

## How (the fix)
- **Blocker found**: the migration's 4 data statements matched step names **tenant-wide** (`tenant_id IN (… LOWER(name)='taller')`), not per-workflow. Verified against real DBs: dev clean, **QA's Taller tenant has a generic `Default Workflow`** whose `Screening Scheduled` / `Technical Interview Scheduled` / `On Hold` would get display_number 1/8/29. Prod unverifiable (permission classifier blocks prod reads from Claude sessions).
- Fix `029bc0f9`: all 4 statements now scope `workflow_id IN (SELECT w.id FROM workflow w JOIN tenant t … WHERE w.name = 'Taller Pipeline' AND LOWER(t.name) = 'taller')`; system test gained the same-tenant/other-workflow collision case (numbering + stage move). Test passes; new assertions fail on the old SQL.

## Decisions
- Kept the tenant+workflow **name** match (repo precedent `3qf9phxv7xly` reporting_phase seed) rather than ids.
- Review verdict CHANGES REQUESTED → after my fix, remaining blocker is Pedro's: `display_number` on `WorkflowStepBase` is client-writable via step POST/PATCH with no `ge=1` (one-liner `Field(default=None, ge=1)`).
- On Hold (29) / Backup (30) grouping deliberately NOT moved to a BE stage (stage drives `advancement_rank` + `STAGE_ORDER` sorts) — FE will special-case by step name. Legit branch of the ticket's open decision, but unrecorded on the US.

## Gotchas
- The migration freezes the 30-name map inline (drift-proof vs defs) — enum member `SECOND_CLIENT_INTERVIEW_DONE` has no `_OPT` but its VALUE is `"2nd Client Interview Done (opt)"`; both maps verified byte-identical to the ticket.
- Taller legacy pipeline can't collide by construction (34 DEPRECATED_STATES names ∩ 30 numbered names = ∅), and `validate_definitions()` check 7 now enforces legacy None.
- The stage move is NOT display-only: Offer > ClientProcess in both `STAGE_ORDER` (application filters) and `advancement_rank` (TB candidate ranking) — intended per ticket, disclosed in PR body.

## Pending
- Pedro: `ge=1` validation blocker; nits (create_default_workflow drops display_number, migration↔defs parity assert, downgrade-inverse comment); record On Hold/Backup resolution + FE follow-up ticket link on US 24989; confirm manual `alembic upgrade head`/`downgrade -1` run.
- Check **prod** for the Default Workflow collision before merge (query in the PR comment) — I could not read prod.
- CI was pending at review time.

## Related
- [[GET roles 500 virtual_interview default drift (Bug 24988)]] — same workflow/roles neighborhood, migration `wxtz7gwf7wqb` is this PR's parent revision.
