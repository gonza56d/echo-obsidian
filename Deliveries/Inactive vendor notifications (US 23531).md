---
type: delivery
status: merged
env: taller
delivered: 2026-07-10
tags: [bugfix, notifications, vendors]
prs: [1802]
tickets: [23531, 23293]
---

# Exclude users of inactive vendors from all notifications (US 23531)

Deactivating a vendor sets `vendor.is_active=False` but not its users' `user.is_active`, and recipient queries filtered on raw `user.is_active` → inactive-vendor users kept receiving notifications. Harmless while notification emails are off by default, but a real leak the moment they're enabled. Detected during QA of [#23293](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23293).

## PRs
- [#1802](https://github.com/taller-projects/echo-backend/pull/1802) → dev — merged 2026-07-10 (+ review follow-up commit `ad7dc557`)

## How
- `UserFilterBase.enabled` filter mirrors `User.enabled()` at query level (`is_active AND (vendor IS NULL OR vendor.is_active)`); plus `email__in`.
- **Central gate** in `NotificationService`: `bulk_create` drops non-enabled recipients (covers every notification kind, current and future); `_filter_enabled_emails` gates commitment + 3 interview email paths; digest skips disabled users but leaves rows unsent (delivered if vendor reactivates).
- Recipient builders fixed at source (`_get_taller_recruiters`, `_get_partner_recruiters`, `_get_users_by_access_role_names`, `_get_special_notification_users`, commitment publishers).
- Scheduler excludes disabled users' rows at query level (`NotificationFilter(user_enabled=True)`); send-time gate stays as safety net.
- `enabled`/`email__in` became additive optional query params on `GET /users` — intentional, non-breaking.

## Open questions (never closed)
- `interviewer_email` exact-match semantics.
- Whether the **welcome email** should also be gated.

## Related
- [[Pending interview notifications (US 23321)]] · [[Map - Observability & Reliability]]
