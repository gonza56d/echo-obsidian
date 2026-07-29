---
type: delivery
status: in-progress
env: taller
delivered:
tags: [feature, roles, open-jobs, prd, planning]
prs: []
fe_prs: []
tickets: []
prd: "https://app.notion.com/p/3abaedca11f081588a20dbf247a4887e"
---

# Create Role from Open Job (PRD 887e)

Reverse direction of the Open Jobs feature: today an `organization_job` (scraped LinkedIn / board posting) can only be *viewed* and *matched against* (`POST /company/jobs/{job_id}/match` → [[Open Jobs 1-5 matching (US 23640)]]); this feature lets a tenant **create an Echo role from an existing open job** and keeps the two linked forever via a new `role.organization_job_id`. The role is created through the *standard standalone path* (placeholder project + background enhancement) with the payload derived server-side from the posting — exactly as if a user had typed the "Create Role" modal by hand. **PRD Draft as of 2026-07-28: no code, no Azure tickets, no Capa 1 (business PRD) yet.**

## Azure / docs

- PRD (Tier B, Draft, owner Gonzalo): [Crear Rol desde Open Job — PRD Técnico](https://app.notion.com/p/3abaedca11f081588a20dbf247a4887e) — parent = [Echo Backend — Task Docs](https://app.notion.com/p/356aedca11f081ac871ede4f5c6caf45)
- Sibling PRD it depends on operationally: [[Enhancement queue v2 Postgres-backed (PRD 7444)]] — the enhancement this feature triggers migrates to that queue at its cutover, **no contract change here**
- Business PRD (Capa 1): **does not exist** — this technical PRD came straight off a team request. Open question #5.
- Azure: nothing created yet.

## Contract the PRD commits to

- **Recommended (Option 1)**: `POST /company/jobs/{job_id}/roles` — derivation 100% server-side, body = optional overrides, `201` with the same `RoleResponse` shape as `POST /roles`; `404` unknown job; `409` this tenant already converted the job; plan-limit codes identical to `POST /roles`.
- **Alternative (Option 2)**: optional `organization_job_id` on `POST /roles` (keeps `company_id` required, `422` if it disagrees with `job.organization_id`). Less new surface, but conditional semantics on a heavily-used schema and derivation split between FE and BE.
- Derivation v1: `name ← job.title`, `company_id ← job.organization_id` (not overridable), `job_description ← job.description`, `organization_job_id ← job.id`, everything else = standard defaults, all overridable except the two links.
- `organization_job_id` added to existing role list/detail responses (nullable, additive → no FE break).
- Cardinality **1 role per (tenant, open job)**, enforced in Postgres:
  ```sql
  ALTER TABLE role ADD COLUMN organization_job_id VARCHAR NULL
      REFERENCES organization_job(id) ON DELETE SET NULL;
  CREATE UNIQUE INDEX uq_role_tenant_id_organization_job_id
      ON role (tenant_id, organization_job_id) WHERE organization_job_id IS NOT NULL;
  ```
  One alembic revision, no backfill, no downtime; the partial index doubles as the reverse-lookup index.
- Estimate 3-5 days backend, 3-4 h QA, single sprint (no milestones). Backend first, FE integrates after.

## Decisions already taken (2026-07-28, with the team)

- **The open job row is never mutated** — no `converted`/`closed` flag, no per-tenant state. `organization_job` is *shared across tenants*, so any per-tenant state on it is a scope explosion. An "already converted" signal in the jobs list is a v1.1 follow-up (tenant-scoped subquery over the link).
- **Ships on the current `BackgroundTasks` enhancement**, knowingly — the queue PRD absorbs this path at cutover. Incremental volume judged low.
- **Simple FK, not composite** `(id, tenant_id)` — impossible here, see verified facts.
- `ON DELETE SET NULL`: the ingest pipeline re-ingests/deletes postings; the role must survive, losing only the link.
- Not idempotent-by-response: a second attempt gets `409`, not the existing role (open question #2 asks whether the 409 should carry `role_id` so the FE can navigate).
- OUT of scope: compensation mapping (`compensation_*` → pay rates: incompatible period/currency), `location` → `country_restrictions` (free string vs country list), seniority inference from the posting, bulk conversion, Kforce (open-job boards don't exist there).

## Code-verified facts (checked on `dev` @ `b9465656`, 2026-07-28)

- `OrganizationJob` — `app/modules/organization/job/models.py:38`: `__tablename__ = "organization_job"`, `id: Mapped[str]` **PK is a plain string** (LinkedIn id, or `"{source}:{source_id}"`, with `uq_organization_job_source_source_id`), `organization_id` FK → `organization.id` ON DELETE CASCADE. **No `tenant_id` column** — the only `tenant_id` occurrences in the file (lines ~109-110) are inside the `matched_talents` JSONB tenant-tag filter from the 1-5 matching work. → a composite `(id, tenant_id)` FK is *not possible*; the PRD's simple FK is the only option, and `role` is where tenant scoping lives.
- `Role` — `app/modules/role/models.py:195`: `tenant_id` at :326, three composite `ForeignKeyConstraint`s at :198/:205/:212. The new column is a deliberate exception to the repo's composite-FK convention — the PRD states why, and a reviewer will ask.
- Standalone creation path — `ProjectService.create_role_with_placeholder_project`, `app/modules/project/service.py:719`:
  `check_limit("max_standalone_roles")` (:724) → placeholder project with **`requirements = role.short_description or role.job_description`** (:733) → `_auto_assign_workflow` → `role_service._create(..., enhance_role=False)` → **synchronous** `regenerate_job_description` **only** `if not created_role.job_description` (:747-748) → `_publish_role_event(..., "created")` (:750). Both PRD claims about plan limit + `role.created` event hold.
- Enhancement — `RoleService.enhance_role`, `app/modules/role/service.py:449`: **always overwrites** `job_description` with a TeamBuilder-generated JD built from `project.requirements` + `TeamBuilderRole.from_role(role)` (:476-489). The posting text reaches the LLM **only through `project.requirements`** — the PRD's "regenerates the JD from the posting via the placeholder project's requirements" is mechanically correct.
- Latency claim holds: with a non-empty posting `description` the JD is present at creation, so the in-request sync generation at :747-748 is skipped (the empty-`description` posting falls back into it — the PRD's documented edge case).
- Route mounting — `app/routers.py:475-483`: `organization_job_router` is included under `/company/jobs` with `dependencies=[Protected([Permission.Companies])]`.
- Role creation permissions — `POST /roles` (`independent_role_router`, `app/modules/role/routers.py:355`) carries only `Depends(UserDependencyManager.get_user_tenant_id)` + `AuthenticatedUser`; `POST /projects/{project_id}/roles` (`routers.py:91`) has **no `Protected(...)` either**. Backend role-creation is gated by auth + tenant only; the "Edit Roles" permission is an FE-side gate.

## Technical review — 13 items, now a section **inside** the PRD (2026-07-28)

Unsigned (PRD B's twin section is signed by Pedro Rocha; same date, same method), verified against `dev` `b946565`, `origin/kforce-dev` `45fde63` **and** `echo-frontend`. Everything below I re-verified in the repo — **all of it holds**. Six items block `Approved`:

1. **The enhancement overwrites the posting's JD, unguarded.** `enhance_role` does `repo.update(role_id, RoleUpdate(job_description=jd))` with no guard (`role/service.py:474-489`; contrast `_generate_skills`, which *does* guard at `:316-317`). So the posting text is returned in the 201 and replaced by the LLM seconds later — for a feature whose point is importing a real posting, that's a product decision the PRD never states.
2. **Permissions: the endpoint inherits only `companies`, and the failure is a 500, not a 403.** The jobs router is mounted `Protected([Permission.Companies])` (`app/routers.py:475-482`), but the placeholder-project INSERT is gated by RLS on `projects.create OR (is_roles_only AND roles.edit)` (`project/models.py:92-146`). A companies-only user therefore hits RLS 42501 → `ProgrammingError` → **`handle_commit_errors` only matches `IntegrityError`** (`sql_repository.py:71-96`, `case _: raise e`) → HTTP 500. And `ENABLE_ACCESS_CONTROL` defaults to `False` (`config.py:46`), so it never reproduces locally. Supersedes my own version of this finding, which assumed the Companies-only user would simply *succeed*.
3. **No check that the tenant tracks the job's organization** — `get_job_for_tenant` only validates `job.source in tenant.job_sources`; `organization_tracker` is keyed by user, not tenant, and `POST /roles` never validates `company_id` either. Accept it (same exposure as `GET /company/jobs/{id}`) or add the check — explicitly.
4. **The unique index blocks the job forever: `role` has no soft delete.** Close/archive is a `role_workflow_step_id` change; the row survives. A mistakenly closed role or a job re-posted next year leaves a permanent 409, and a partial index can't filter on stage (it lives in `role_workflow_step`).
5. **The 409 would actually come out as a 400 today**: unique violation → `DuplicateError`, `status_code = 400`, `error_code=duplicate_item` (`repositories/exceptions.py:21-26`) — 409 requires catching `IntegrityError` explicitly (pattern in `user_group/service.py:138-143`). FE side: `renderError` surfaces `'API Error'`, and no 409 handling exists at all — which also constrains open question 2 (a `role_id` in the 409 needs a structured `detail`).
6. **On the duplicate, the placeholder project is left orphaned and committed** — `SQLAlchemyRepository.save` commits immediately (`sql_repository.py:211-219`), the project at `project/service.py:728` and the role at `:741`. "Double click → exactly one role and a 409" is true for the role, false for the system. Needs one transaction (`add` + `flush` + translate) or cleanup in the `except`.

**Factual corrections to the draft** (7-10): `organization_job` **does exist on `kforce-dev`** (8 blobs; `POST /company/jobs/{job_id}/match` is there too) — the OUT is right, the stated reason is wrong; the correct one is "parallel fork, older module version, no tenancy". • The "jobs re-ingested/deleted" risk is backwards: ingest is an idempotent PK upsert (`on_conflict_do_update`, `job/repository.py:184-206`) and closing flips `is_open` — **nothing is ever deleted**, and a re-ingest keeps the same id, so the link survives. • "Posting without `description`" is **Medium**, not Low: `""` falls into the unguarded synchronous `regenerate_job_description` *after* project and role are already committed, so a provider failure 500s the request and strands a `pending` role. • The plan limit is a **403** with a structured detail (`subscription/exceptions.py:7-29`), and the FE pre-checks it with `useLicenseLimit('standalone_roles')` only on the Roles page; the manual retry lives on `POST /projects/{pid}/roles/{rid}/retry-enhancement` behind `ProjectsEdit`, which a companies-only user lacks — so "same backstop" is only partly true.

**Contract/testing precisions** (11-13): put `organization_job_id` on **`RoleListResponse`**, not `RoleBase` — `RoleUpdate` is `@partial_model(RoleBase)` and `RoleListResponse` inherits `RoleCreate`, so a base-level field becomes client-writable and contradicts "Override: No" (verified: `role/schemas.py:198-204`, `:233`). Zero join cost either way (scalar → `LoadOnlyNode`). • **There is no test of `POST /roles` at all today** — this PRD writes the first coverage of the path; add a `tests/multitenancy/` isolation test and run the system test with `ENABLE_ACCESS_CONTROL=True`, or item 2 escapes to QA. • Close the loop with the queue PRD: its M1 lists "the 4 creation/retry endpoints" and does **not** include this new one.

## Resolutions — folded into the PRD 2026-07-28 (status → "Draft, revisión resuelta, listo para `Approved`")

Every item now has a decision in a **"Resolución de la revisión técnica"** section, and the body was corrected in place (criteria, contract code block, risk table, scope table, estimate, open questions).

- **1 JD overwrite → accepted and declared.** The role ends with the pipeline-generated JD; the posting survives in `organization_job.description` and as the placeholder's `requirements`. Identical to a hand-typed JD today, so the feature inherits the behavior rather than introducing it. Literal-posting-as-JD would be a separate feature.
- **2 Permissions → superseded by the second pass below.** (First attempt: `Protected([Permission.ProjectsCreate | Permission.RolesEdit])` on the route. Wrong tool — `Protected` returns 404, and a permission gate can't cover the policy's data-scope clause.) Option 1 kept. The repo-wide "RLS denial → untranslated 500" is a separate ticket.
- **3 Tracked-org check → accepted exposure + ticket.** Same as `GET /company/jobs/{id}` and `POST /roles`; the correct check doesn't exist yet (`organization_tracker` is keyed by user, not tenant).
- **4 Permanent 409 → accepted.** A real re-post gets a new `{source}:{source_id}` id (new row, no collision); the residual case has a workaround (delete the role). The "already converted" signal moves from *if product asks* to **committed for v1.1**.
- **5 409 → own translation with structured detail** `{code, message, role_id}` (`user_group/service.py:138-143` pattern) + a cheap pre-INSERT SELECT, index as race backstop. **Closes open question 2: yes, the 409 carries `role_id`.** FE must read `getApiErrorStatus`/`getApiErrorDetailMessage`.
- **6 Orphan project → atomicity is now a technical criterion**: project + role in one transaction (`add` + `flush` + translate + single commit), with a regression test that `POST /roles` is unchanged.
- **7-10 corrections applied in the body**: Kforce OUT reason rewritten (module exists there, older + no tenancy); the re-ingest risk row replaced by "organization CASCADE" (ingest is an idempotent PK upsert, never deletes); no-`description` mitigation now a try/except, **in scope**; plan limit declared as 403 + structured detail, with the FE `useLicenseLimit` pre-check as a new dependency and the `projects.edit`-gated retry accepted for v1.
- **11-13 adopted**: field on `RoleListResponse`; multitenancy test + system test under `ENABLE_ACCESS_CONTROL=True`; the queue PRD's M1 now lists this endpoint.
- **14 (mine)**: `requirements` is set **always** from `job.description` in this path, regardless of a `short_description` override.
- **Estimate 3-5 → 4-6 days.** Open questions 1-4 closed; only the Capa 1 business PRD stays open and it doesn't block backend.

## Second pass on the resolution — Pedro, 2026-07-28 (6 items, all valid, all resolved)

He confirmed 10 of 13 closed cleanly. The six that came back — three of them corrections to *my* resolution — all verified in the repo:

1. **`Protected` raises 404, not 403** (`app/user/permissions.py:87-94`, `detail="Not Found."`), so the "403 por permisos" criterion didn't exist, and on this endpoint it would have collided with the job-not-found 404.
2. **The permission gate doesn't eliminate the RLS 500.** The project INSERT `with_check` has a second AND: `project.consumer_id = aro.organization_id` (i.e. `job.organization_id`) **OR** the user has no organizations assigned. A restricted-data-scope user passes any permission gate and still trips RLS. Unlike item 3 of the first pass, **the data already exists** (`access_role_organizations` = the FE's `visible_organizations`), so it isn't new design.
3. **Items 6 and 9 collided**: one atomic transaction + in-request JD generation = a write transaction held open across the LLM call — exactly what `enhance_role` avoids with its `db_session.close()` calls.
4. **Items 6 and 9 change the shared helper**, so they alter the failure contract of `POST /roles` and `POST /internal/roles` undeclared — and `repo.save()` commits unconditionally, so item 6 can't be built on it.
5. **Items 4 and 10 cancelled out**: with `companies + roles.edit` the user creates the role but can neither retry the enhancement nor delete the role to free the job (**both** routes are `Protected(Permission.ProjectsEdit)`) → failed enhancement is terminal and the job is blocked forever. Verified, and the dead end **pre-exists** for any standalone role created by a `roles.edit`-only user, since `POST /roles` has no permission gate.
6. **Section 5 was never actually updated** — item 12 claimed "ampliado" while the table and the 3-4 h QA figure were untouched.

**Decisions folded in (a "Resolución — segunda pasada" section, plus body fixes and `↳` markers on the superseded first-pass items):**

- **1+2 together → authorization moves into the service.** The route adds no `Protected` of its own; the service replicates the whole policy — (`projects.create` OR `roles.edit`) **and** the data scope over `job.organization_id` — and raises `AuthorizationError` (403, `app/exceptions.py:150-155`). Final contract: **404** = job doesn't exist *or* caller lacks `companies` (indistinguishable by design, the repo's anti-enumeration posture); **403** = can see the job but can't create the role, or it's outside their data scope. The 403 leaks nothing new — reaching it proves the caller can already see open jobs.
- **3 → write order declared.** (1) One transaction, DB only: insert project + insert role + translate the unique violation → single commit. (2) *After* commit, the guarded sync JD generation runs as a short independent write. With a posting that has a `description`, step 2 never fires.
- **4 → the shared change is accepted and declared**: no more orphan placeholder project on failure, no more 500-after-commit on a JD-provider failure, for `POST /roles` and `POST /internal/roles` too. Strictly fewer failure modes, no shape or status-code change; regression tests on both endpoints + a Changelog entry at approval. Implementation note: not via `repo.save()`.
- **5 → `retry-enhancement` widens to `Protected([Permission.ProjectsEdit | Permission.RolesEdit])`.** Recovering your own enhancement shouldn't need a higher permission than creating the role. `DELETE` stays on `projects.edit` — freeing a job becomes an **escalation**, not a dead end, and the v1.1 "already converted" signal must name the linked role so the escalation is actionable.
- **6 → section 5 rebuilt for real**: unit cell (404-vs-403 incl. data scope, structured 409, `requirements` precedence, JD guard), system row now under `ENABLE_ACCESS_CONTROL=True` + concurrent-double-submit atomicity, new Multitenancy row, new shared-path regression row, QA row with the permission matrix and the `roles.edit` retry. **QA 3-4 → 5-6 h, estimate 4-6 → 5-7 days.**

## Superseded — my earlier framing

- **A `short_description` override silently discards the posting.** `requirements = short_description or job_description` (`project/service.py:733`) and the enhancement regenerates the JD from `requirements` alone — so an override of `short_description` keeps the posting out of the LLM input entirely. Related to review item 1 but distinct: item 1 is about the *output* JD being replaced, this is about the *input* disappearing. Pin the derivation precedence.
- The 409 also needs the `IntegrityError` translation to be scoped to *that* index specifically (same shape trap as [[Contact bulk_track IntegrityError (Bug 23251)]]).

## Open questions (from the PRD)

1. Gate on `is_open`? v1 accepts any existing job (the FE only lists open ones) — confirm with product.
2. Should the `409` return the existing `role_id` so the FE can navigate to it?
3. "Already converted" signal in the open-jobs list — v1.1?
4. Compensation mapping when currency/period are compatible — v2?
5. Create + link the Capa 1 business PRD.

## Pending

- **Third-pass sign-off → flip the PRD to `Approved`.** Two review rounds resolved (13 + 6 items); nothing technical is open. The JD-overwrite decision remains the one a product person could still veto.
- Two declared cross-endpoint changes need to survive review when the code lands: the shared-helper failure-contract change (`POST /roles`, `POST /internal/roles`) and the `retry-enhancement` permission widening. Both get a Changelog entry at approval.
- Create the Azure Feature/US + tasks. FE ticket: Open Jobs overlay action, 409 → navigate to the existing role via `detail.role_id`, `useLicenseLimit` pre-check on that surface.
- Spin off the two follow-up tickets the resolution creates: repo-wide RLS-denial translation (42501 → 403, today a 500 everywhere) and tenant scoping for the open-jobs read paths.
- Capa 1 business PRD — still owed, does not block backend.
- v1.1 commitment: the "already converted" signal in the open-jobs list.
- Kforce: explicitly out of scope (no open-job boards there).

## Related

- [[Enhancement queue v2 Postgres-backed (PRD 7444)]] · [[Open Jobs 1-5 matching (US 23640)]] · [[Role enhance pool timeout unhandled (Bug 23808)]] · [[Roles company filter (Feature 23719)]] · [[Map - Observability & Reliability]]
