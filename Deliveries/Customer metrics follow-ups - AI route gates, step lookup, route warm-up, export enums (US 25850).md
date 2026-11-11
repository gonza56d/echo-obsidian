---
type: delivery
status: in-review
env: both
delivered:
tags: [follow-up, customer-metrics, permissions, tests]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2572"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25850"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics follow-ups - AI route gates, step lookup, route warm-up, export enums (US 25850)

One ticket + one PR for the review follow-ups of Feature 25635 (user asked 2026-11-11, after #2499 merged).

## PR
- [#2572](https://github.com/taller-projects/echo-backend/pull/2572) → dev, branch `25850/customer-metrics-followups`, worktree `.claude/worktrees/25850-cm-followups`, commit `2f443a7c`.

## What
- `team_composition_v3` → `Protected(ProjectsEdit)`; `role_v3` + `regenerate/job_description` → `Protected([ProjectsEdit | RolesEdit])`. They only had router-level `projects.view` (`app/routers.py` mounts /projects and /roles with it), so a viewer could run them; the JD regenerate writes the role. FE: every caller already behind those permissions (Team / ProposedTeam Add role = PROJECTS_EDIT; JobDescription = ROLES_EDIT or PROJECTS_EDIT, `hasPermission` is any-of).
- `RoleWorkflowService.get_step` (tenant-scoped repo get); `RoleService._resolve_step_for_step_id` uses it.
- Session `app` fixture: `app.url_path_for("build every route")` under `suppress(NoMatchFound)` builds every included router (FastAPI 0.139 `_IncludedRouter.effective_candidates` is lazy) and the unnamed mounts; `test_role_close.py` drops `_routes_built`. Baseline proven: without it the file fails with `FastAPIError: Invalid args for response field ... datetime.date | None`.
- `app/modules/export/enums.py`: ExportFormats / ProposalType (annotations dropped); 21 importers (app + tests) rewritten.
- Not done: M4 "6c role-attribution" test (proof test of docs SQL; user's no-proof-tests rule) — said in the ticket.

## Gotchas
- `Protected` is a no-op in tests unless `act_as` turns ENABLE_ACCESS_CONTROL on; members also need `projects.view` (router level) and the `recruiting` module.
- `ruff format` on tests reformats untouched files (CI formats only app/): restore and re-apply import-only changes.

## Pending
- [ ] CI, reviews (Leo, Pedro, Gisel), squash-merge → US 25850 Closed.
- [ ] qa / main with the next release.

## Related
- [[Customer metrics M2 follow-up - close_reason required on the user role PATCH (US 25744)]] · [[Customer metrics M3 - AI suggestion snapshots (US 25639)]] · [[Customer metrics M4 - proposal versions (US 25640)]]
