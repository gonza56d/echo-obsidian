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

## Gotchas / review findings (raised 2026-07-28, not yet in the PRD)

1. **Option 1 silently changes the authorization posture.** FastAPI `include_router(dependencies=[...])` applies to every route in the router and **cannot be removed per-route** — so `POST /company/jobs/{job_id}/roles` would require `Permission.Companies`, while every existing role-creation endpoint requires *no* permission. Net: a roles-editor without Companies gets 403; a Companies-only user gains a role-creation path they don't have on the Roles screen. The PRD's "same posture as `POST /roles`" is true *about `POST /roles`* but not about the endpoint it recommends. Needs an explicit call: accept the Companies gate, mount the route on the roles router instead, or take Option 2 (which keeps the posture byte-identical). ← the strongest reason to reconsider Option 1.
2. **A `short_description` override silently discards the posting.** Since `requirements = short_description or job_description` and `enhance_role` regenerates the JD from `requirements` alone, a client override of `short_description` means the posting's `description` never reaches the LLM (and the derived `job_description` gets overwritten anyway). The derivation table should pin the precedence: posting `description` → `job_description` **and** `short_description` when not overridden, or state the `requirements` rule explicitly.
3. The `409` is enforced by the partial unique index, so a double-submit race is safe at the DB layer — but the service must translate `IntegrityError` on that specific index into the 409 (same shape trap as [[Contact bulk_track IntegrityError (Bug 23251)]]).

## Open questions (from the PRD)

1. Gate on `is_open`? v1 accepts any existing job (the FE only lists open ones) — confirm with product.
2. Should the `409` return the existing `role_id` so the FE can navigate to it?
3. "Already converted" signal in the open-jobs list — v1.1?
4. Compensation mapping when currency/period are compatible — v2?
5. Create + link the Capa 1 business PRD.

## Pending

- Team review of the Draft; pick Option 1 vs 2 **with finding #1 on the table**.
- Fold findings #1 and #2 into the PRD (derivation precedence + auth posture) before `Approved`.
- Create the Capa 1 PRD; create the Azure Feature/US + tasks; FE ticket for the Open Jobs overlay action + 409 handling.
- Kforce: explicitly out of scope (no open-job boards there).

## Related

- [[Enhancement queue v2 Postgres-backed (PRD 7444)]] · [[Open Jobs 1-5 matching (US 23640)]] · [[Role enhance pool timeout unhandled (Bug 23808)]] · [[Roles company filter (Feature 23719)]] · [[Map - Observability & Reliability]]
