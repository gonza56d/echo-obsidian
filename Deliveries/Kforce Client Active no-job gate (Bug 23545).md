---
type: delivery
status: merged
env: kforce
delivered: 2026-07-10
tags: [bugfix, kforce, contact, relationships]
prs: [1811]
tickets: [23545]
---

# Kforce: relax Client Active account gate for unscraped contacts (Bug 23545)

kforce.echoai.us (prod): untracked/unscraped Client contacts (zero `contact_job` rows) read **Past** despite interactions 7–30 days old. Kforce's `_relationship_is_active_expr` still had the original 2-branch account gate — it never received the Taller [[Client Active gate relaxation (PR 1745)]] nor the [[Moved-away Client contacts Past (Bug 23519)]] guard.

## PRs
- [#1811](https://github.com/taller-projects/echo-backend/pull/1811) → kforce-dev — merged 2026-07-10

## How
- Expanded the Client `account_gate` 2 → 4 branches mirroring current Taller: `~has_any_job` (fixes the report), `recent_interaction_same_company`, minus `has_moved_to_another_company` override.
- **Copy + adapt port**, on-read only → no migration; prod re-derives on deploy.
- One pre-existing test legitimately flips under `~has_any_job` → repurposed into a *left-account* variant + a companion for no-job→Active.

## Related
- [[Map - Kforce]] · [[Map - Contact Relationships]]
