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
- `InterviewFilter.hide_out_of_step_pending` (opt-in) appends
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
  now no-ops via `InterviewService.has_active_interview`; a cancelled one is
  still reactivated by `create` (the #2312 terminal detour).

## Azure
- [US 25462](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25462) — Leandro's spec (very detailed: prod numbers, rule, safeguard, dev test roles); In revision, GitHub PR link added.
- Origin [#23225](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23225).

## PRs
- [#2402](https://github.com/taller-projects/echo-backend/pull/2402) → dev — OPEN 2026-10-08 (`eb392c98`); branch `25462/pending_scheduling_step_filter`, worktree `.claude/worktrees/25462-pending-scheduling-step-filter`.

## How
- `app/modules/assessment/interview/filters.py`: `filter()` override — strips
  the non-column field via `model_copy(update=...)` and `super(InterviewFilter, copy).filter()`
  (same pattern as `ApplicationFilter.recruiter_id__in`), then two correlated
  `EXISTS` helpers. `Application.tenant_id == Interview.tenant_id` is what lets
  the planner use `uq_application_tenant_role_talent`.
- `routers.py`: `interview_filter.hide_out_of_step_pending = True` (pydantic
  setattr marks the field set; `filter()` reads the attribute directly anyway).
- Tests `tests/unit/test_interview_pending_step_filter.py` (17): reuse the
  #2312 fixture helpers; a `Pipeline` helper builds before/ready/after/terminal
  steps on one role.

## Decisions
- Safeguard anchored on the **role's** workflow (not the application's) so an
  orphan Pending interview on a flagged workflow is hidden while roles without
  workflow (legacy status-driven) or without a flagged step behave as today.
- Router-level, not filter default: the internal API and service callers must
  keep the raw Pending set (Slack notice logic).
- Field exposed as a query param (`hide_out_of_step_pending`) — harmless, and
  gives the internal API an opt-in.

## Gotchas
- RLS edge: the `EXISTS` on `application` runs under the application policy; a
  `talents`-permissioned user with `user`/`vendor` scope would also lose Pending
  rows for applications they cannot see. ACs are global-scope; noted in the PR.
- `WorkflowStepFactory` randomizes `creates_interview` / `cancels_interview`
  — pin both in tests or a random True cancels/duplicates mid-test.
- Dev check (psql `echo-dev`, Taller): NK Sr FE Job6777 17 → 10, ME C#/.Net
  Job2924 10 → 8, Node/Python B 3 → 2, tenant-wide 127 → 109. EXPLAIN: both
  subplans index-only lookups.

## Pending
- Review + squash-merge #2402 to dev; dev smoke on the three roles; qa / main.
- Close US 25462 after merge; tell Leandro / Palo.
- Separate tickets (per the US, unfiled): prod backfill of #2312's stranded
  terminal interviews (`scripts/cancel_pending_interviews_terminal_steps.sql`,
  coordinate with Pedro); Slack "Interview needed" firing for candidates no
  longer in step 5.

## Related
- [[Map - JazzHR integration]] (interview creation path) · #2312 (no note; Pedro's).
