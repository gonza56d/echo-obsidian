---
type: delivery
status: in-review
env: infra
delivered:
tags: [chore, tooling, pr-review, claude]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2332"
  - "https://github.com/taller-projects/echo-backend/pull/2339"
  - "https://github.com/taller-projects/echo-backend/pull/2340"
fe_prs: []
tickets: []
prd: ""
---

# Require an explicit PR id for /pr-review (PR 2332)

Running the `/pr-review` (or `/review-pr`) review workflow with **no argument** silently reviewed the wrong PR: with no explicit number, the `gh pr view/diff/checks` calls resolve to the currently checked-out branch's PR, so the review ran against a "random" PR instead of stopping and asking. Fix makes the PR identifier mandatory — a missing id is now an abort, not a current-branch fallback. Non-ticketed tooling chore.

## Azure / docs
- No ticket (Claude Code tooling chore).

## PRs
- [#2332](https://github.com/taller-projects/echo-backend/pull/2332) → `dev` — **in review** (opened 2026-09-23)
- [#2339](https://github.com/taller-projects/echo-backend/pull/2339) — release `dev` → `qa` MERGED 2026-09-23 (`26e57503`; 31 commits, 7 migrations, single head `zolvj810zl6j`).
- [#2340](https://github.com/taller-projects/echo-backend/pull/2340) — release `qa` → `main` OPEN 2026-09-23 (prod + kforce-prod behind Azure approvals).

## How
- `.claude/skills/pr-review/SKILL.md` — new **"Precondition: a PR identifier is MANDATORY"** section at the top: abort and ask when no id is given; never infer from the current branch / latest PR / a default; never run `gh pr *` without an explicit `<num>`. "Inputs required" also marks the PR id REQUIRED.
- `.claude/commands/review-pr.md` — mirrors the same precondition and marks the PR-identifier input required.
- No behavior change when a PR id is supplied.

## Decisions
- **Root cause is the current-branch fallback**, not just a missing prompt. `gh pr *` with no `<num>` resolves to the checked-out branch's PR, so the guard forbids running those commands without an explicit number rather than merely reminding the reviewer to ask.
- Fix landed on its own branch `chore/pr-review-require-id` off `origin/dev` (dedicated worktree) rather than riding the unrelated placement-status feature branch it was discovered from.

## Gotchas
- The skill (`/pr-review`) and the command (`/review-pr`) are **two separate entry points** to the same review flow — both needed the guard, or the hole persists via whichever the user invokes.

## Pending
- Merge [#2332](https://github.com/taller-projects/echo-backend/pull/2332) to `dev`.

## Related
- (standalone tooling chore)
