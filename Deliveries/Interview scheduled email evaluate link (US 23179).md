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
- [#1865](https://github.com/taller-projects/echo-backend/pull/1865) — branch `23179/interview-scheduled-evaluate-link` → `dev` (OPEN). Four commits:
  - `578a106d` — feature: `evaluate_link` + jinja button + render test.
  - `9191872e` — `/pr-review` nit fixes (DRY mixin refactor + direct scheduled-path render test); see Decisions.
  - `3aa501ed` — external-review nit: regression test locking that the Slack-only `InterviewEventPayload` has no `evaluate_link`.
  - `266264d7` — Pedro-review nits: payload-base naming (`*PayloadBase`) + docstrings; test module renamed to `test_interview_scheduled_email.py` + rescoped docstring.

## How
- `app/modules/assessment/event_handlers.py` — the `/evaluate` deep link. Interviewer-facing link building is now factored into two mixins (post-refactor):
  - `InterviewLinkMixin` — owns `interview_id` + the `link` `@computed_field` → `/interviews/interviewer-slots/{id}` (the cancel/reschedule "Manage Interview" target). Shared by all payloads that expose `link`.
  - `InterviewEmailLinksMixin(InterviewLinkMixin)` — adds the `evaluate_link` `@computed_field` → `f"{settings.FRONTEND_URL}/interviews/assessment/{self.interview_id}/evaluate"`. Applied to **both** `InterviewScheduledPayload` and `InterviewerChangedPayload` (the scheduled-email payloads). `InterviewEventPayload` (Slack-only) stays on `InterviewLinkMixin` → gets `link` but deliberately **not** `evaluate_link`.
- `app/modules/notification/service.py::_send_interview_scheduled_email` — passes `evaluate_link=payload.evaluate_link` into the template render. This single method serves both events.
- `app/modules/notification/mail_templates/interview_scheduled_email.jinja` — new "Evaluate Candidate" button reusing the existing `.btn` class + parallel copy, placed above the existing "Manage Interview" link.

## Decisions
- **Both dispatch paths get the link**: `interview.scheduled` and `interviewer.changed` share `_send_interview_scheduled_email` + the same template and both go to the interviewer, so both payloads carry `evaluate_link`.
- **DRY refactor (review nit, commit `9191872e`)**: the `link`/`evaluate_link` computed fields were duplicated verbatim across payloads. Collapsed into the two-tier mixin above — `link` now has a single definition (was triplicated) and `evaluate_link` a single definition (was duplicated). Two mixins (not one) because the Slack `InterviewEventPayload` needs `link` but must **not** gain `evaluate_link`. All construction sites use kwargs, so field ordering under inheritance is a non-issue.
- **Style aligned to current**: reused `.btn` (same blue) and the "…please use the link below:" copy structure rather than introducing a new button style (per gonza's request).
- **No FE change**: `/interviews/assessment/{id}/evaluate` is an existing echo-frontend route (confirmed: `src/pages/interviews/assessment/[id]/evaluate.tsx`, also referenced in `ScheduledCard.tsx`, `interviewsTableColumns.tsx`); `{id}` is the interview id, already present in the payload.

## Review
- **External review on #1865** ([comment](https://github.com/taller-projects/echo-backend/pull/1865#issuecomment-5023841905), leoassontaller, scoped) — ✅ **READY WITH NITS**, 0 blockers, CI green, ticket 4/4.
  - **Nit 1 (fixed, `3aa501ed`)** — nothing locked the deliberate Slack exclusion. Added `test_slack_only_payload_does_not_expose_evaluate_link`: asserts `not hasattr(InterviewEventPayload(...), "evaluate_link")` + `"evaluate_link" not in model_dump()`, and that the shared interviewer-slots `link` is still present.
  - **Nit 2 (no action)** — the `__new__`-based fixture was flagged for awareness only; mirrors the existing accepted pattern in the same file.
  - **PII logging** in `_send_interview_notification` (logs the full payload incl. `interviewer_email`/`talent_name`) — pre-existing in `dev`, out of scope; folds into the hardening follow-up below.
- **Second review on #1865** ([review](https://github.com/taller-projects/echo-backend/pull/1865#pullrequestreview-4736269251), rocha-p / Pedro) — ✅ **APPROVED**, ticket fully satisfied, CI green, no blockers. Verified the FE route expects exactly the interview id the backend passes. Two non-blocking nits, both fixed in `266264d7`:
  - **Nit 1 — test module scope**: `test_interviewer_changed_email.py` held `TestNotificationServiceInterviewScheduledHandler` + `TestEvaluateLink` beyond its docstring scope. Renamed → `test_interview_scheduled_email.py` (`git mv`, history preserved) + rewrote docstring (both handlers render the one template).
  - **Nit 2 — naming**: the two "mixins" declare `interview_id`, so they're payload bases, not pure mixins. Renamed `InterviewLinkMixin`→`InterviewLinkPayloadBase`, `InterviewEmailLinksMixin`→`InterviewEmailLinksPayloadBase` + docstrings.
  - **Informational**: on `interviewer.changed`, a late email can land on the read-only "already submitted" evaluate view — confirmed intended (matches in-app). The `autoescape=False` XSS surface is the pre-existing hardening follow-up below.

## Gotchas
- Worktree based off `origin/dev` (reset from HEAD) because the launch checkout sat on the concurrent `23640/open-jobs-matching-1-5` branch (another agent) — avoids dragging unrelated open-jobs work into this PR.
- Tests render the **real** jinja template via `NotificationService.__new__` + a real `jinja2.Environment` (no HTTP client; render assertions need no DB). New in `9191872e`: `TestNotificationServiceInterviewScheduledHandler` drives `interview_scheduled(event)` end-to-end (mocks `_resolve_interview_cancel_request`, `recruiter_id=None` to skip `bulk_create`) and asserts the button + `evaluate_link` + manage `link` in the rendered email — previously only covered transitively via the `interviewer.changed` test. `TestEvaluateLink` still asserts the computed-field URL for both payloads.
- `ruff` flags `C408` (`dict()` → literal) on the original `TestEvaluateLink._kwargs`, but CI lints **only `app/`**, never `tests/` — left as-is per repo convention (don't rewrite pre-existing test lines). `app/` is lint-clean.
- Verified locally (main `.venv`, Docker up): `test_interviewer_changed_email` + `test_notification_service` + `test_inactive_vendor_notifications` = 64 passed; `test_interviews` (exercises the re-based `InterviewEventPayload`) = 25 passed.

## Pending
- [ ] Merge #1865 → `dev` (in review).
- [ ] qa/main promotion cherry-picks after dev.
- [ ] Feature QA: interviewer receives the email, "Evaluate Candidate" lands on the correct candidate's evaluation page.
- [ ] Out-of-scope hardening (separate ticket, not this PR): jinja `Environment` has autoescape off + `talent_name`/`role_title` render unescaped (pre-existing XSS surface); and `_send_interview_notification` logs the full payload incl. `interviewer_email`/`talent_name` (PII).

## Related
- [[Pending interview notifications (US 23321)]] — same interviewer-notification surface (Slack + scheduled-interview email).
- [[Interview assessment change history (US 22248)]] — the assessment `/evaluate` page this link targets.
