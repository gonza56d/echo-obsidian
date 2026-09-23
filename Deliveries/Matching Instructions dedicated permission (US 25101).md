---
type: delivery
status: merged
env: taller
delivered: 2026-09-23
tags: [feature, permissions, matching-instructions, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2337"
  - "https://github.com/taller-projects/echo-backend/pull/2338"
  - "https://github.com/taller-projects/echo-backend/pull/2339"
  - "https://github.com/taller-projects/echo-backend/pull/2340"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25101"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25103"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25104"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22717"
prd: "https://app.notion.com/p/3e4aedca11f0812a8529d48a206c85dd"
---

# Matching Instructions dedicated permission (US 25101)

Navitec wanted Matching Instructions limited to its Admins plus Tyler Tenpas (a `Member`). That was impossible with data alone:
- everything was gated on `projects.edit`, and removing it breaks role/project editing;
- `Member` is a system role that `_sync_system_roles` recomputes whenever modules change.

What shipped: a new `matching_instructions.edit` permission, required together with `projects.edit`. A data migration grants it to every role that has `projects.edit`, so there is zero change outside Navitec. Navitec's exception is data only (a custom role plus the permission stripped from its two Full Access roles), applied after deploy.

## Azure / docs
- [US 25101](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25101) (BE, mine, In revision) → [Task 25104](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25104) (Navitec prod runbook, post-deploy)
- [US 25103](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25103) (FE, Web Team, unassigned)
- Parent: [Epic 22717 Navitec Sales Rollout](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22717). The earlier MI Features (23289, 23607, 24171) are all Closed.
- PRD: [Matching Instructions — Permiso dedicado por usuario — PRD Técnico](https://app.notion.com/p/3e4aedca11f0812a8529d48a206c85dd). Owner Pedro Rocha, Tier B, Draft. Open blocker: validating the permission name. The page was not shared with the Notion integration at first (404); the user granted access.

## PRs
- [#2337](https://github.com/taller-projects/echo-backend/pull/2337) → dev — MERGED 2026-09-23 (merge `6fc81949`)
- [#2338](https://github.com/taller-projects/echo-backend/pull/2338) → dev — OPEN 2026-09-23 (`b9a2c4a5`): empty merge migration `zolvj810zl6j` over `pf2rzvc97b81` (#2333) + `pl4ai19616w3`
- FE: not yet (US 25103). Contract impact:
  - new permission string `matching_instructions.edit` in `/users/me` `access_role.permissions[]`;
  - `generate` now 404s without it;
  - role PATCH/create answers 403 `error.code = matching_instructions_forbidden` when the field changes without it.
- [#2339](https://github.com/taller-projects/echo-backend/pull/2339) — release `dev` → `qa` MERGED 2026-09-23 (`26e57503`; 31 commits, 7 migrations, single head `zolvj810zl6j`).
- [#2340](https://github.com/taller-projects/echo-backend/pull/2340) — release `qa` → `main` OPEN 2026-09-23 (prod + kforce-prod behind Azure approvals).

## How
- `Permission.MatchingInstructionsEdit` sits in `TenantModuleConfig.RECRUITING` + `SOLUTIONING`, the same modules as `projects.edit`. A test asserts that parity for every module.
  - The templates then do the rest: Admin, Member and Full Access include it; Viewer doesn't (`.edit` suffix).
  - KForce has neither module, so it can't hold the permission.
- `generate` endpoint: `Protected([ProjectsEdit, MatchingInstructionsEdit])` (list = AND).
- `RoleService.assert_can_write_matching_instructions(new, current, *, allowed)` raises 403 only when the normalized value actually changes (`""`/whitespace → `None`). Call sites:
  - PATCH: `ProjectService.update_role(..., can_write_matching_instructions=...)` compares against `old_role` before `_update`. The default is True, so internal API-key callers stay ungated.
  - `POST /projects/{pid}/roles` and `POST /roles`: in the routers.
  - create-from-job: `OrganizationJobService.create_role_from_job`.
- Migration `pl4ai19616w3` (parent `q7fkc2npl8rs` after the r1 rebase; merged with #2333's `pf2rzvc97b81` by `zolvj810zl6j`): `permissions || '["matching_instructions.edit"]'` WHERE `? 'projects.edit' AND NOT ? 'matching_instructions.edit'`. Downgrade: `permissions - '...'`.

## Decisions
- **403 only on a real change**, because the FE's `RoleOverlayContext.tsx:162` PATCHes `{...role, code_challenge, interview_questions}`, which re-sends the stored instructions on unrelated saves.
- **Dropped the PRD's tenant-feature layer.** `TenantFeature.MATCHING_INSTRUCTIONS` and its `FeatureGateError` were removed by the ungate (#1885 / FE US 23699). The FE constant is gone too.
- **`user.has_permissions` instead of the PRD's `RequestContext.permissions`.** `get_user_permissions` isn't wired on the role routes, and the raw permissions skip the tenant intersection and admin bypass.
- **Covered create-from-job too.** `RoleCreateFromJob` inherits `RoleBase.matching_instructions`, and the PRD didn't list it.
- No milestones: one BE PR, one FE PR, and an ops Task.

## Gotchas
- **Order matters for the Navitec runbook.** It must run AFTER the migration has run in prod. If it runs earlier, the migration re-grants the permission to the custom roles, since they hold `projects.edit`.
- **The custom role drifts.** "Member - No Matching Instructions" is not a system role, so it won't pick up future Member permissions. Re-copy it whenever Navitec's modules change.
- **Cached `/users/me`.** It uses `staleTime: Infinity`, so affected Navitec users must log in again.
- **Alembic heads by file date can be wrong.** The newest file (`td9m2kqp7v3x`, 2026-09-22 16:00) was not the head (`b8fq3mzv7kdn` was). Always use `alembic heads`.
- **Double alembic head after merging.** Pedro's #2333 (`pf2rzvc97b81`) and #2337 (`pl4ai19616w3`) both revise `q7fkc2npl8rs`; each was single-head on its own branch, so CI was green on both, but `dev` ended with 2 heads and `apply_migrations.sh` (`alembic upgrade head`) fails. Fixed with a merge migration (#2338), not by re-parenting: a merge works whether an env's DB sits at the fork point or at either head. `downgrade -1` from the mergepoint is "Ambiguous walk"; downgrade with an explicit target.
- **The full alembic chain needs Supabase `auth.users`.** #2337 was verified in isolation via `Operations.context` on a throwaway pgvector container: parity, running twice, downgrade, re-upgrade. For #2338 the full chain ran after stubbing on a FRESH database (a failed first run leaves enum types behind): `CREATE SCHEMA auth; CREATE TABLE auth.users (id uuid PRIMARY KEY, email text, raw_user_meta_data jsonb, raw_app_meta_data jsonb, created_at timestamptz, updated_at timestamptz)`, then `DB_URL=... alembic upgrade head`.
- **Worktree-guard limits.** It blocks `source`, `$S`-variable python one-liners and inline `-d` Azure payloads. Do Azure and vault work after `ExitWorktree(keep)`.
- **Stale FE checkout.** The local echo-frontend checkout is from June 2026. Read FE `dev` through `gh api .../tarball/dev` into the scratchpad instead.

## Pending
- Merge [#2338](https://github.com/taller-projects/echo-backend/pull/2338) — the dev migrate step fails until it lands. Then the qa/main promotions (must carry #2333, #2337 and #2338 together).
- Tell Pedro about the three PRD deviations (the dropped feature layer, `has_permissions` instead of `RequestContext.permissions`, create-from-job) and validate the permission name, which is the PRD's open blocker.
- FE US 25103 (Web Team).
- Task 25104: the Navitec prod runbook, after the prod deploy. Also tell Navitec which role to use for new invites.
- Navitec prod counts in the PRD (11 Admin / 11 Member / 4 Sourcing Full Access) not re-verified by me; the prod read was blocked by the classifier.

## Related
- [[Enhancement queue v2 Postgres-backed (PRD 7444)]] · [[Reuse JD v2 skills in enhance_role (US 24316)]] (earlier Matching Instructions work)
- [[Referral Attribution M1 permission+gating (US 24996)]]: same pattern (dedicated permission, backfill migration, field-level gate)
