---
type: delivery
status: merged
env: taller
delivered: 2026-06-29
tags: [feature, notifications, interviews, talent]
prs: [1637, 1671]
fe_prs: [2850]
tickets: [23180, 23321, 23224]
prd: "Notion 389aedca11f081c3802decf0b16ea601 — Manual re-send of pending interview Slack notifications"
---

# Pending interview notifications (23180 → US 23321)

Two-step arc around "Interview Needed" Slack notifications for candidates without loaded availability.

**Step 1 — bug + manual re-send (#1637, ticket 23180).** Creating an interview for a candidate with no availability correctly deferred the Slack notification, but loading availability later never sent it: `_get_talent_pending_interviews` filtered `start_at__gte=tomorrow` and unscheduled interviews have `start_at IS NULL`. Fix: filter `status__in=["Pending"]`. Then, to avoid re-sending on every availability edit: auto-notify **only on the first availability load** (no→yes transition), plus a new manual endpoint `POST /talents/{talent_id}/pending-interview-notifications` → `202 {"notified_interviews": n}` with **no availability guard** (user-driven re-send).

**Step 2 — FE signals (#1671, US 23321).** The FE button (US 23224 / FE PR #2850) had no data to decide presentation. Backend now exposes **data only, FE owns the policy** (PRD reverses the earlier "don't track notification state" decision):
- `Interview.interviewer_notified_at` — nullable timestamp stamped on every dispatch path (creation-with-availability, first-availability auto-send, manual re-send), via `InterviewService.mark_interviewer_notified` (no foreign-model writes). Migration `kq3n7vb2xr9d`, additive; historical rows stay NULL = "never/unknown".
- `TalentResponse.pending_interview_count` + `last_pending_interview_notified_at` (MAX over pending interviews) — button visibility (count > 0) + soft "recently notified" warning. Attached via `Talent.__declare_last__` (cross-module computed column pattern, avoids the Interview↔Talent circular import).

## PRs
- [#1637](https://github.com/taller-projects/echo-backend/pull/1637) → dev — merged 2026-06-24
- [#1671](https://github.com/taller-projects/echo-backend/pull/1671) → dev — merged 2026-06-29

## Decisions
- **No server-side cooldown, no new permission** — re-sends always allowed (PRD AC4); FE gates softly.
- FE contract PRD: Notion `38eaedca…` (FE contract addendum).

## Related
- [[Inactive vendor notifications (US 23531)]] — the notification-recipient gating that followed
