---
type: delivery
status: in-review
env: both
delivered:
tags: [chore, tooling, claude-config, azure-devops]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2250"
fe_prs: []
tickets: []
prd: ""
---

# Azure DevOps skill real ticket states (PR 2250)

The `azure-devops` Claude skill (`.claude/skills/azure-devops/SKILL.md`) documented the default Agile states (`New`, `Active`, `Resolved`, `Closed`) instead of Echo Core's real customized state list — agents following it would try to set nonexistent states (e.g. `Active`) and had no rule for which state maps to which point of the dev workflow. Replaced with the real 14-state list plus the workflow mapping.

## Azure / docs
- No ticket — non-ticketed Claude-config chore (branch `chore/azure_devops_skill_statuses`).

## PRs
- [#2250](https://github.com/taller-projects/echo-backend/pull/2250) → dev — OPEN 2026-09-10

## How
- Single-file docs change to `.claude/skills/azure-devops/SKILL.md`:
  - Real states: `New`, `Being defined`, `Ready to develop`, `In development`, `Developed`, `Ready to Test`, `Testing`, `Needs revision`, `In revision`, `Blocked`, `Paused`, `Approved by QA`, `Closed`, `Removed` (source: the state dropdown on an Echo Core work item).
  - Workflow mapping: **In development** = coding starts, **In revision** = PR opened, **Closed** = PR merged.
  - PATCH example now sets `In development` (was the nonexistent `Active`).
- Built on a temp worktree off `origin/dev` so the change didn't ride along in the open [#2248](https://github.com/taller-projects/echo-backend/pull/2248) branch where it was drafted.

## Decisions
- Kept it a docs-only chore, no ticket, per the branch-naming convention for non-ticketed work.

## Gotchas
- The skill file is git-tracked, so every checkout/worktree keeps the stale copy until this merges to dev — sessions started before the merge still read the old state list.

## Pending
- [#2250](https://github.com/taller-projects/echo-backend/pull/2250) review + merge to dev.

## Related
- [[Last Interaction stale for future-dated interactions (Bug 24873)]] (session where the stale list was noticed)
