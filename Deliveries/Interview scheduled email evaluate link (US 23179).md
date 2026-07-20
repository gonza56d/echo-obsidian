---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, notifications, interviews]
prs: ["https://github.com/taller-projects/echo-backend/pull/1865"]
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23179"
prd:
---

# Interview scheduled email evaluate link (US 23179)

Add a direct link to the candidate's `/evaluate` page in the "Interview Scheduled" email so the interviewer can jump straight to submitting their evaluation instead of navigating the app. Backend-only (Taller); the FE evaluation page already exists.

## Azure
- **US [#23179](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23179)** (gonza) — "Agregar link a /evaluate en el email de scheduled interview". No dedicated PRD (small US in the interviews area).

## PRs
- [#1865](https://github.com/taller-projects/echo-backend/pull/1865) — branch `23179/interview-scheduled-evaluate-link` → `dev` (OPEN). Single commit.

## How
- `app/modules/assessment/event_handlers.py` — new `evaluate_link` `@computed_field` on **both** `InterviewScheduledPayload` and `InterviewerChangedPayload` → `f"{settings.FRONTEND_URL}/interviews/assessment/{self.interview_id}/evaluate"`. Mirrors the pre-existing `link` field, which points at `/interviews/interviewer-slots/{id}` (the cancel/reschedule "Manage Interview" target).
- `app/modules/notification/service.py::_send_interview_scheduled_email` — passes `evaluate_link=payload.evaluate_link` into the template render. This single method serves both events.
- `app/modules/notification/mail_templates/interview_scheduled_email.jinja` — new "Evaluate Candidate" button reusing the existing `.btn` class + parallel copy, placed above the existing "Manage Interview" link.

## Decisions
- **Both dispatch paths get the link**: `interview.scheduled` and `interviewer.changed` share `_send_interview_scheduled_email` + the same template and both go to the interviewer, so both payloads carry `evaluate_link`.
- **Style aligned to current**: reused `.btn` (same blue) and the "…please use the link below:" copy structure rather than introducing a new button style (per gonza's request).
- **No FE change**: `/interviews/assessment/{id}/evaluate` is an existing echo-frontend route (confirmed in `ScheduledCard.tsx`, `interviewsTableColumns.tsx`); `{id}` is the interview id, already present in the payload.

## Gotchas
- Worktree based off `origin/dev` (reset from HEAD) because the launch checkout sat on the concurrent `23640/open-jobs-matching-1-5` branch (another agent) — avoids dragging unrelated open-jobs work into this PR.
- Tests render the **real** jinja template via `NotificationService.__new__` + a real `jinja2.Environment` (no HTTP client, no DB needed for the render assertions) — the pattern already in `test_interviewer_changed_email.py`. New `TestEvaluateLink` asserts the computed-field URL for both payloads.

## Pending
- [ ] Merge #1865 → `dev` (in review).
- [ ] qa/main promotion cherry-picks after dev.
- [ ] Feature QA: interviewer receives the email, "Evaluate Candidate" lands on the correct candidate's evaluation page.

## Related
- [[Pending interview notifications (US 23321)]] — same interviewer-notification surface (Slack + scheduled-interview email).
- [[Interview assessment change history (US 22248)]] — the assessment `/evaluate` page this link targets.
