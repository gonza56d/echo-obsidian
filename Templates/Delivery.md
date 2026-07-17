---
type: delivery
status: in-progress   # in-progress | in-review | merged | shipped-prod
env: taller           # taller | kforce | both | infra
delivered:            # date of last merge (YYYY-MM-DD)
tags: []              # feature | bugfix | hotfix | security | chore + domain tags
prs: []               # PR numbers, plain (e.g. [1799]) — clickable links go in the BODY
fe_prs: []            # echo-frontend PR numbers, if any
tickets: []           # Azure work item ids (US/Task/Bug/Feature), plain numbers
prd: ""               # short Notion PRD id/title — titled clickable link goes in the BODY
---

# <Short title> (<US/Bug/PR ref>)

One-paragraph summary: the problem/need, and what shipped. Written so that in 3 months "oh, THAT thing" clicks immediately.

## Azure / docs
- [US NNNNN](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/NNNNN) → Tasks …
- PRD: [<PRD title>](https://app.notion.com/p/<32-hex-page-id>)

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
