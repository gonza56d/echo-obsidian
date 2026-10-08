---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, interviews, assessment, workflow, pending-scheduling]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2402"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25462"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23225"
prd: ""
---

# Pending Scheduling lists only candidates in the interview step (US 25462)

Palo (product) reported via [#23225](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23225)
that "Pending Scheduling" (role Interviews tab + `/interviews` page) shows
candidates with nothing to schedule: the interview is created when the
application enters the `creates_interview` step (step 5 on Taller) and its
status is derived only from the interview's own dates, so when the application
moves to a **non-terminal** step (forward or back) the row stays Pending.
[#2312](https://github.com/taller-projects/echo-backend/pull/2312) (Pedro, 2026-09-21)
only covers terminal steps (`cancels_interview`). Prod 2026-10-08: ~422 Pending,
128 actually in step 5. Product decision: hide, never cancel; reappears when the
candidate returns to the step; orphans (no application on the role) hidden too.

## What
- `InterviewFilter._hide_out_of_step_pending` (private switch, same shape as
  `ContactFilter._hide_group_children`) appends
  `status != 'Pending' OR EXISTS(application in a creates_interview step for the
  talent on the assessment's role) OR NOT EXISTS(creates_interview step on the
  role's workflow)`. Reuses the `Interview.status` column_property CASE as the
  "is Pending" test so it cannot drift.
- `GET /assessments/interviews` sets the flag unconditionally — both FE screens
  and the "Pending Scheduling (N)" counter come from that query → **no FE PR**.
  Internal list and `TalentService._get_talent_pending_interviews` (Slack
  "Interview needed") untouched.
- **Bonus fix found by the tests**: since #1115, re-entering the
  `creates_interview` step with a live interview raised 400
  "An interview already exists" and aborted the step move — the AC "back to 5 →
  reappears" was impossible. `AssessmentService.create_interview_from_application`
  now no-ops via `InterviewService.create_if_absent` (one lookup: keep live /
  reactivate cancelled / insert); the public `create` keeps its 400.

## Azure
- [US 25462](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25462) — Leandro's spec (very detailed: prod numbers, rule, safeguard, dev test roles); In revision, GitHub PR link added.
- Origin [#23225](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23225).

## PRs
- [#2402](https://github.com/taller-projects/echo-backend/pull/2402) → dev — OPEN 2026-10-08 (`eb392c98`); branch `25462/pending_scheduling_step_filter`, worktree `.claude/worktrees/25462-pending-scheduling-step-filter`.
- Self `/pr-review` r1 2026-10-08 (full, 3 agents): **READY WITH NITS, 0 blockers, CI green**. Nits fixed in `83bcd651` (pushed from worktree `.claude/worktrees/25462-review-nits`, branch `25462/pending_scheduling_step_filter_r1`): PrivateAttr switch, `create_if_absent`, `tenant_id` on every EXISTS join, annotations, +2 tests (first step entry creates, No Show), `enabled_for_interviews` pinned. PR body refreshed; implementation notes posted on US 25462 (comment 29016752).

## How
- `app/modules/assessment/interview/filters.py`: `_hide_out_of_step_pending`
  is a pydantic `PrivateAttr` (not a query param on either app, nothing for the
  generic field loop to walk); `filter()` calls `super().filter()` then appends
  the two correlated `EXISTS` helpers, every join matching `tenant_id`. `Application.tenant_id == Interview.tenant_id` is what lets
  the planner use `uq_application_tenant_role_talent`.
- `routers.py`: `interview_filter._hide_out_of_step_pending = True` (same as
  `contact/routers.py` with `_hide_group_children`). Tests set it the same way
  through the `_listed_ids` helper.
- Tests `tests/unit/test_interview_pending_step_filter.py` (20): reuse the
  #2312 fixture helpers; a `Pipeline` helper builds before/ready/after/terminal
  steps on one role.

## Decisions
- Safeguard anchored on the **role's** workflow (not the application's) so an
  orphan Pending interview on a flagged workflow is hidden while roles without
  workflow (legacy status-driven) or without a flagged step behave as today.
- Router-level, not filter default: the internal API and service callers must
  keep the raw Pending set (Slack notice logic).
- Review nit: the first cut exposed the switch as a query param (documented
  but ignored on the public route, undocumented opt-in on internal). Replaced by
  the PrivateAttr; the internal API has no opt-in now, by design.

## Gotchas
- RLS edge: the `EXISTS` on `application` runs under the application policy; a
  `talents`-permissioned user with `user`/`vendor` scope would also lose Pending
  rows for applications they cannot see. ACs are global-scope; noted in the PR.
- `WorkflowStepFactory` randomizes `creates_interview` / `cancels_interview`
  — pin both in tests or a random True cancels/duplicates mid-test. Same for
  `AssessmentFactory.enabled_for_interviews`: a random False silently skips
  the step-entry interview creation (the first cut passed by luck).
- Known edge (no code change, asked product on the ticket): `talents`-permission
  users with `user`/`vendor` data scope lose Pending rows for applications RLS
  hides from them; the role-workflow safeguard cannot rescue those. ACs are
  global-scope.
- Dev check (psql `echo-dev`, Taller): NK Sr FE Job6777 17 → 10, ME C#/.Net
  Job2924 10 → 8, Node/Python B 3 → 2, tenant-wide 127 → 109. EXPLAIN: both
  subplans index-only lookups.

## Pending
- Team review + squash-merge #2402 to dev (strip Co-Authored-By if any); dev smoke on the three roles; qa / main.
- Product answer on the user/vendor data-scope edge (asked on US 25462).
- Close US 25462 after merge; tell Leandro / Palo.
- Separate tickets (per the US, unfiled): prod backfill of #2312's stranded
  terminal interviews (`scripts/cancel_pending_interviews_terminal_steps.sql`,
  coordinate with Pedro); Slack "Interview needed" firing for candidates no
  longer in step 5.

## Related
- [[Map - JazzHR integration]] (interview creation path) · #2312 (no note; Pedro's).
