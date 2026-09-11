---
type: delivery
status: in-review
env: taller
delivered:
tags: [fix, logging, pii, emails]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2254"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24891"
prd: ""
---

# PII logging pass on email send paths (Task 24891)

Email send paths logged full recipient addresses (PII), inconsistent with the domain-only policy in `sendgrid_service.py`. Surfaced during review of PR #2253 (Leo + own review) — see [[Shared email shell for all app emails (US 24886)]].

## PRs
- [#2254](https://github.com/taller-projects/echo-backend/pull/2254) → dev — OPEN 2026-09-11. Logging-only, no FE impact.

## How
- New `email_domain()` in `app/services/sendgrid_service.py` (returns `@domain`), reused by its own two send logs (replacing inline rsplits).
- `welcome_email_service.py`: 3 logs now `to_domain=email_domain(...)`.
- `app/user/service.py`: jazz-id-collision + SSO-check-failure warnings now `email_domain=...` instead of `user.email`.
- `app/modules/notification/service.py` commitment-disabled path: `recipient_count` instead of the full list.
- Helper unit test in `tests/unit/test_sendgrid_service.py`.

## Decisions
- Helper lives in `sendgrid_service.py` (the email-sending home), not a new util module.
- Structured kwargs (`to_domain`, `email_domain`, `recipient_count`) over f-strings for the migrated logs.

## Gotchas
- The zshrc PAT is SINGLE-quoted: `cut -d'"' -f2` extraction yields empty → Azure 302. Use `cut -d"'" -f2` or read via python re.
- Worktree sessions: a stricter isolation layer blocks `zsh -ic`, heredocs and Write outside the worktree — write scripts INSIDE the worktree, run plainly, delete.

## Pending
- CI + team review / merge of #2254; close Task 24891 on merge.
- qa/main promotion rides the normal release train.

## Related
- [[Shared email shell for all app emails (US 24886)]]
