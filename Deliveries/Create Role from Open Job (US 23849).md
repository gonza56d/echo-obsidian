---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, roles, open-jobs, authorization, transactions]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1933"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23849"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23850"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23851"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23852"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23853"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23854"
prd: "https://app.notion.com/p/3abaedca11f081588a20dbf247a4887e"
---

# Create Role from Open Job (US 23849)

Turn a scraped open job into an Echo role and keep them linked via `role.organization_job_id`, with **one role per (tenant, open job)** enforced by a partial unique index. Built M0-M3 in one branch off `origin/dev`; the PRD is [[Create Role from Open Job (PRD 887e)]], resolved across two review rounds before any code was written.

## Azure / docs

- [US 23849](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23849) (created this session, no parent — re-parent if the team wants it under an Open Jobs Feature) → Tasks [23850](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23850) M0 · [23851](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23851) M1 · [23852](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23852) M2 · [23853](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23853) M3 · [23854](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23854) M4
- PRD: [Crear Rol desde Open Job](https://app.notion.com/p/3abaedca11f081588a20dbf247a4887e)

## PRs

- [#1933](https://github.com/taller-projects/echo-backend/pull/1933) → `dev`, **open**. Branch `23849/create-role-from-open-job` off `origin/dev` (local `dev` was 3 commits behind, and those 3 touched `project/service.py`, `role/service.py`, `sql_repository.py` — the exact files — so branching from the remote mattered). Migration `r5e4wdsxzb6l` on head `m4qr8v2kx9wp`.
- **2026-07-29 Pedro's review (round 2) addressed in `856b2c51`**: B1 migration rebuilt on the `fe10vb1aflw3` locking pattern (CONCURRENTLY in `autocommit_block()`, FK `NOT VALID` + `VALIDATE CONSTRAINT`); B4 409 `detail` switched to the PRD dict `{code, message, role_id}`; B6 both testing ACs delivered (durability-at-JD-call assertion, plan-limit 403 over HTTP via `custom_limits`); plus his B3/B5 complements (404 nonexistent job over HTTP, dirty-session `SELECT 1/0` JD failure, revert-verified). His blockers 2/3/5 were already covered by `8e9f5e69`.
- **2026-07-29 review round 1 addressed in `8e9f5e69`** (same branch, pushed): both blockers + all nits from the rubric review fixed in one commit — explicit-null overrides no longer 500, `tests/system/test_role_from_open_job.py` with `ENABLE_ACCESS_CONTROL=True` incl. barrier-synced concurrent double submit (Task 23853's ask), `tests/multitenancy` wired into CI via `scripts/test.sh`, plus the smaller nits (id-only 409 lookup, `OrganizationJobRoleSeed` projection, `enhance_role_with_context` made public, constant moved next to its 409, rollback guard after failed sync JD, `save() -> T`).

## How

- **M0** — `role.organization_job_id` + partial unique index `(tenant_id, organization_job_id) WHERE NOT NULL`, plain FK (`organization_job` has no `tenant_id` to compose with), `ON DELETE SET NULL`. Field on `RoleListResponse`, **not** `RoleBase` — there `RoleCreate`/`RoleUpdate` (`@partial_model`) would inherit it and let a client write the link.
- **M1** — `repo.save(commit=False)` flushes instead of committing, so the role insert owns the single commit and a rejected role rolls its project back; declared explicitly on `TenantScopedRepository` rather than riding inside `**extra_fields`. Sync JD generation moved after the commit and guarded.
- **M2** — `POST /company/jobs/{job_id}/roles`, derivation server-side, authorization in the service (403), 409 with `role_id` in `error.context`, `requirements` always from `job.description`, log `role_created_from_job`.
- **M3** — `retry-enhancement` widened to `ProjectsEdit | RolesEdit`; multitenancy isolation tests; RLS-policy drift guard.

## Decisions

- **Authorization in the service, not a route dependency.** `Protected` raises **404** (`app/user/permissions.py:87-94`) — on this endpoint indistinguishable from "job not found" — and the data-scope half of `project`'s INSERT policy can't be expressed as a permission at all. So the service mirrors the whole `with_check` and raises 403 before the INSERT. Contract: 404 = job absent or no `companies`; 403 = visible but not allowed.
- **409 detail shape — REVERSED in round 2 (`856b2c51`)**: round 1 shipped `detail` = human string + `role_id` in `error.context`, flagging the PRD for correction. Pedro's review showed the PRD shape is load-bearing: the FE helpers (`getApiErrorCode`) read `jsonResponse.detail.code`, no FE helper reads `.error`, and the sibling plan-limit error (`LimitExceededError`, `subscription/exceptions.py`) already puts the dict in `detail` — that's why it works today. Now shipped as the PRD says: `detail = {code, message, role_id}` (dict), `job_id`/`role_id` still duplicated in `error.context`. No PRD correction needed for the shape.
- Widened only `retry-enhancement`, not `DELETE` — freeing a job stays an escalation to `projects.edit`.
- Left three adjacent defects alone to keep the diff scoped; filed as tickets instead (below).
- **Review round 1 (rubric protocol, 2026-07-29)**: two blockers confirmed and fixed same-day. (1) `@partial_model` makes every override field nullable at the wire level, so `{"name": null}` passed request validation and blew up inside the service as a raw `pydantic.ValidationError` → 500; fix = drop None-valued keys in the merge (explicit null now means "use the derived value"), verified by reverting and watching the new unit + system tests fail. (2) Task 23853's system test existed only as unit-level substitutes; now `tests/system/test_role_from_open_job.py` runs the real app with `ENABLE_ACCESS_CONTROL=True` (201/404/403 both directions/409 wire shape) and a concurrent double submit where a `threading.Barrier` holds both requests past the cheap pre-check so the partial unique index is what rejects the loser.

## Gotchas

- **The `short_id` sequence commits the session.** `tenant/sequence/service.py:34` does `db_session.commit()` to bump the counter, which silently split M1's shared transaction and left the placeholder project committed anyway. Fixed by reserving the number *before* the transaction opens (`RoleService.reserve_short_id`). Any future "make these writes atomic" work in this area has to account for it.
- **My first M1 test passed for the wrong reason** — it patched `RoleService._create` out entirely, so the sequence commit never ran. The M2 racing test is what exposed it. Both atomicity fixes are now verified by reverting them and watching the tests fail; the M1 test patches `BaseService.create` so everything before the role INSERT still executes.
- `OrganizationJobResponse` deliberately omits `organization_id`, and the schema-driven planner therefore never loads it — the create path reads the ORM row (`_get_job_row_for_tenant`) instead of the response.
- Adding constructor deps to `OrganizationJobService` broke two hand-built service fixtures (`test_organization_jobs.py`, `test_matching_diff_industry.py`) — the [[reference_dunder_new_test_fixtures]] trap, `rg "OrganizationJobService(" tests/` before touching a constructor.
- `ProjectCreate(description=...)` in the placeholder call is dead: `ProjectBase` has no `description` field, so Pydantic drops it. Pre-existing on `dev`; placeholder projects are identifiable only by name.
- **Unique indexes on `role` must go `CONCURRENTLY`** — the repo precedent is `fe10vb1aflw3` (same shape: partial unique on `role`, built inside `op.get_context().autocommit_block()`), and FKs go `NOT VALID` + `VALIDATE CONSTRAINT`. Round 1 of review (mine) called the missing `CONCURRENTLY` "consistent with repo practice" — wrong, the precedent existed; Pedro's review caught it.
- **`create_entity` detaches shared module fixtures**: passing a module-scoped ORM instance (e.g. `mocked_organization`) as an m2m value attaches it to the helper's short-lived session and leaves it expired → `DetachedInstanceError` poisons every later test in the module. Pass ids and load fresh instances inside the factory instead.
- **`Tenant.enabled_modules` is a property**, not a column — modules live as `TenantModule` rows. An `UPDATE tenant SET enabled_modules=...` fails with `'property' object has no attribute '_bulk_update_tuples'`; insert a `TenantModule(module="recruiting", enabled=True)` row instead.
- The "local TestClient can't resolve `/company/jobs/*`" claim in `test_open_job_match.py`'s docstring is **stale** — request-level tests against those routes pass locally now (probed before writing the system tests).
- **10 pre-existing local failures in `tests/system`** (tracker sync ×5, contact bulk check, relationship rollup ×3, open-job match hides-other-tenant) — verified identical on a clean HEAD baseline via stash, so not regressions; env-dependent. CI never runs `tests/system`, so they linger.
- Azure PAT extraction: `.zshrc` uses **single** quotes, so the `azure-devops` skill's documented `cut -d\'"\'` gives garbage and every call 302s to a sign-in page. Use `cut -d"\'" -f2`.

## Pending

- Round 3 of review on [#1933](https://github.com/taller-projects/echo-backend/pull/1933) = verification-only over `8e9f5e69` + `856b2c51` (per protocol, round 3 is also the hard stop). Reply to Pedro's comment mapping blockers → commits still owed.
- **Q1 resolved** (409 shape now matches the PRD dict — decided by Pedro's round 2). Still open: (Q2) closed jobs (`is_open=False`) are convertible — decide and pin with a test; (Q3) RLS-mirror placement (Pedro nits it toward `ProjectService.assert_can_create_standalone_role`; standalone `POST /roles` data-scope 500 stays deferred to [Bug 23858](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23858)); (Q4) admin-bypass parity between `User.has_permissions` and the SQL policy's `authorize()`; (Q5, Pedro's) 409 without `role_id` when the winner's role is invisible to the loser under real RLS — the shape now serialises `role_id: null`, but the PRD should document the case.
- FE ticket must now specify the paired FE work reads `detail.code`/`detail.role_id` (no `getApiErrorContext` helper needed after the shape change).
- **Correct the PRD**: 409 payload is `detail` (string) + `error.context.role_id`, not a dict `detail`. Changelog entries owed for both cross-endpoint changes at approval.
- FE ticket not created: Open Jobs overlay action, 409 → open the existing role via `error.context.role_id` (`renderError` shows `'API Error'` today, needs `getApiErrorStatus`/`getApiErrorDetailMessage`), and replicate `useLicenseLimit('standalone_roles')` on that surface.
- Post-merge: verify on `dev` against a real seeded job (with and without `description`), then M4's handoff items.
- Capa 1 business PRD still owed; v1.1 "already converted" signal committed in the PRD.
- Follow-ups filed: [Bug 23858](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23858) RLS denial → 500 repo-wide · [Bug 23859](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23859) `top_tech` string default on JSONB · [Task 23860](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23860) tenant scoping of open-job reads.

## Related

- [[Create Role from Open Job (PRD 887e)]] · [[Enhancement queue v2 Postgres-backed (PRD 7444)]] (absorbs this path at cutover; its M1 must list this endpoint) · [[Open Jobs 1-5 matching (US 23640)]] · [[Role enhance pool timeout unhandled (Bug 23808)]] · [[Map - Observability & Reliability]]
