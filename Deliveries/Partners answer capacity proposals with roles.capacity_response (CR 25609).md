---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, access-control, commitments, capacity, partners]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2445"
fe_prs:
  - "https://github.com/taller-projects/echo-frontend/pull/3566"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25609"
prd: ""
---

# Partners answer capacity proposals with roles.capacity_response (CR 25609)

**Problem.** Partner recruiters (`[External] Recruiter`, `Partner`, `Partner Recruiter`) could not accept, counter or reject the capacity Taller proposed to them. The FE showed the buttons only with `roles.edit`, which would also let them edit the role. Camila Alcaraz (Techwarely) reported it via Paloma (CSR); 2 proposals were stuck on role 102880.

**What shipped.** A new `roles.capacity_response` permission (RECRUITING module). The capacity endpoints are now really gated: before this, the BE only required a logged-in user. A partner can only answer its own vendor's capacity. A migration grants the permission to the partner roles.

Melina Cantamutto authored the PR. I reviewed it and pushed the nit fixes.

## Azure / docs
- [CR 25609](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25609): In development, assigned to Melina. Source: [Slack thread](https://taller-tech.slack.com/archives/C0B8B5QH7NW/p1792523581582979).

## PRs
- [#2445](https://github.com/taller-projects/echo-backend/pull/2445) → dev, **OPEN**.
  - Melina's commits: `7736fc18`, `5b439de3`.
  - My nits commit: `cb851bdc` (2026-10-21).
  - Patricio Etcheverry's commits (2026-10-21, product-confirmed rules):
    - `32e8a1d8`: only the other side accepts or rejects.
    - `68ccdce9`: `POST /commitments` gated, plus the vendor check on create.
  - My r2 commit: `6c15c119`, module-off test covers create. PR body refreshed.
- FE: [#3566](https://github.com/taller-projects/echo-frontend/pull/3566).
  - Adds `ROLES_CAPACITY_RESPONSE` to `ACCESS_LEVELS`.
  - Accept / Counter / Reject show with `roles.edit` OR `roles.capacity_response`.
  - Adds a "Respond to Capacity" switch in Access Levels.
  - The `/users/me` shape is unchanged; the response just gains a new permission value.

## How
- `Permission.RolesCapacityResponse = "roles.capacity_response"` is in the `TenantModuleConfig.RECRUITING` list.
  - `.capacity_response` was added to `EDIT_PERMISSION_SUFFIXES`, so Viewer templates don't get it.
- `app/modules/role/commitment/routers.py`: create (since `68ccdce9`), propose, accept and reject use `Protected([RolesEdit | ProjectsEdit | RolesCapacityResponse])`, which returns 404.
- `CommitmentService._get_answerable_commitment`: a partner (`recruitment_role_name == Partner`, meaning `vendor.kind = 'external'`) on another vendor's commitment gets `NotFoundError`. RLS on `vendor_role_commitment` already hides those rows.
  - `create` uses the same check (`_is_another_vendor`) and answers `Vendor <id> not found`.
  - `accept` / `reject` go through `_get_counterparty_proposal`: the commitment must be Pending and proposed by the other side, otherwise 400 `state_precondition`. The vendor 404 runs first.
- Migration `7rpzhrwn1jy7` (revises `07mq6am8dpgm`): `UPDATE access_role` matching on `btrim(name)`.
  - Since `cb851bdc` it only touches tenants with the `recruiting` or `all` module enabled.
  - Downgrade strips the permission from every role.
- Tests:
  - `tests/unit/test_capacity_response_permission.py` runs with access control on. It covers module-off, R1 (PATCH role/placement → 404) and the cross-vendor case asserting the service's 404.
  - `tests/unit/test_grant_capacity_response_migration.py` executes the real migration against the test DB.

## Decisions
- **Counter = `propose`.** It is one endpoint for both sides, so Taller's propose is gated too.
- **Product (via Patricio) widened the scope beyond the CR's wording.**
  - Partners can *offer* capacity on an unassigned role with `roles.capacity_response`.
  - The rule is symmetric: nothing becomes Active unless the other side agrees.
  - The permission name and the FE switch "Respond to Capacity" now also cover Add Capacity.
- **`projects.edit` is in the BE OR-set but not the FE.** Role edit itself is gated by `projects.edit`, so it would be odd to deny it here. Same pairing as `9l2oltiymw26`.
- **Exact, case-sensitive name match.** On qa, the unbracketed `External Recruiter` has 8 internal-vendor users. Granting it would let Taller staff answer as Taller without `roles.edit`.
- **Rollout window accepted.** The pipeline migrates before the ArgoCD rollout, so old pods return 500 on `/users/me` for the granted roles until the new image is live. Same as `9l2oltiymw26`. I wrote this into the PR body, replacing the wrong "Deploy order" section.

## Gotchas
- **The grant is a no-op on dev.** Dev's partner role is `External Recruiter` (no brackets). qa has `[External] Recruiter`. Prod names were not checked yet.
- **Existing roles don't get the permission at deploy.**
  - Admin / Member roles only pick it up at the next module sync.
  - Per-module Full Access roles are never re-synced.
  - No impact: they all hold `roles.edit`.
- **The FE gates on raw permissions; the BE on effective ones** (access role ∩ tenant modules). A user with `roles.edit` on a tenant without recruiting would see the buttons but get a 404. Commitments only exist in Taller, so this is moot today.

## Pending
- **Prod name check before the `main` deploy.** The query is in the PR body. If the names differ, the grant silently does nothing.
- Leo / teammate review → squash-merge → qa / main. FE #3566 merge.
- ~~Follow-ups for the turn rule and create gating~~: Patricio did both in this PR (`32e8a1d8`, `68ccdce9`). `GET /commitments` is still login-only (RLS scopes it).
- Maybe update CR 25609 to record product's wider scope (partners can offer capacity; symmetric rule).
- Close CR 25609 once it ships to prod and Camila confirms.

## Related
- [[Pentest 4.1.1 broken access control (23012)]] — the same "BE gate was FE-only" pattern.
