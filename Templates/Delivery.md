---
type: delivery
status: in-progress   # in-progress | in-review | merged | shipped-prod
env: taller           # taller | kforce | both | infra
delivered:            # date of last merge (YYYY-MM-DD)
tags: []              # feature | bugfix | hotfix | security | chore + domain tags
prs: []               # echo-backend PR numbers
fe_prs: []            # echo-frontend PR numbers, if any
tickets: []           # Azure work item ids (US/Task/Bug/Feature)
prd: ""               # Notion PRD id/title, if any
---

# <Short title> (<US/Bug/PR ref>)

One-paragraph summary: the problem/need, and what shipped. Written so that in 3 months "oh, THAT thing" clicks immediately.

## Azure / docs
- US … → Tasks …
- PRD: Notion `…`

## PRs
- [#NNNN](https://github.com/taller-projects/echo-backend/pull/NNNN) → dev — merged YYYY-MM-DD
- FE: [#NNNN](https://github.com/taller-projects/echo-frontend/pull/NNNN) — if the FE was involved, note the contract impact (routes, response shapes, permissions)

## How
- Implementation essence: key files/patterns/migrations. Not a diff replay — the *shape* of the solution.

## Decisions
- Choices made and why (esp. ones a future reader might want to revisit).

## Gotchas
- Anything that bit us / would bit us again.

## Pending
- Follow-ups, uncovered edge cases, gated steps. **Empty this section explicitly when done.**

## Related
- [[Map - …]] · [[other deliveries]]
