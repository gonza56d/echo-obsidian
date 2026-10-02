---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, touchpoints, future-interaction, applications, roles, navitec, review]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2375"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25255"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25256"
prd: ""
---

# Touchpoint Role filter options endpoint (US 25255)

Follow-up to [[Touchpoints filter by Role (US 25143)]]: the FE Role filter on `/touchpoints` took its options from `GET /roles`, so most options landed on an empty queue. Florencia added `GET /future-interactions/roles?name__ilike=&page=&size=` → `Page[{id, name}]`, ordered by name: the roles that a **visible** candidate with a **pending** touchpoint holds a **non-matched** application to — the same predicate `role_id__in` filters by, so every option returns rows. Workspace-wide (does not follow the Owner filter, product decision). My part: full `/pr-review` r1 and a nit-fix commit pushed to her branch.

## Azure / docs
- [US 25255](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25255) — BE (Florencia, "In development"; PR hyperlink attached 2026-10-02). FE counterpart [US 25256](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25256) ("Developed": dropdown consumes the new endpoint, keeps name search + infinite scroll, hydrates selected ids via `GET /roles/{id}`).
- No Notion PRD; the Azure description + AC are the whole spec. Predecessor PRD: [Touchpoints — Filtro por Role — PRD Técnico](https://app.notion.com/p/3e5aedca11f0816a9118d23413fc431d).

## PRs
- [#2375](https://github.com/taller-projects/echo-backend/pull/2375) → dev — **OPEN** (Florencia, branch `25255/touchpoint-role-options`). Her commits `cba00ed2` + `1a7237fc` + `ab3cc9dc` + `079864d1`; my nit commit `46f11194` (2026-10-02, pushed from worktree `25255-touchpoint-role-options-r1`, local branch `25255/touchpoint-role-options_r1`). CI green on `079864d1`.
- FE: none from me. Contract: one new list route, `Page[T]` + `__ilike`, no permission / `/users/me` change. FE on `echo-frontend` origin/dev already consumes it (`TOUCHPOINT_ROLES_ENDPOINT`, `getDisplayText: item.name`, `searchParam: 'name__ilike'`).

## How
- Router: `GET /roles` declared **before** `GET /{touchpoint_id}` (else "roles" parses as a UUID); inherits the router-level `Protected([Talents | ContactsView])`; `allowed_entity_types` without candidate → empty page before any query.
- `FutureInteractionService.list_role_options_for_viewer`: `ensure_enabled()` (TOUCHPOINTS, 403) → `_person_ids_matching(owner_user_id=None, allowed_entity_types={candidate}, status=PENDING)` (new optional `status` on it and on `repo.get_person_refs`) → `ApplicationService.get_role_ids_applied_by_talents(talent_ids)` → `RoleService.get_all(RoleFilter(id__in, name__ilike, order_by=["name"], commitments=None), response_model=TouchpointRoleOption)`.
- `ApplicationRepository`: after `46f11194` both sibling lookups (`get_talent_ids_applied_to_roles`, `get_role_ids_applied_by_talents`) build on one private `_non_matched_application_ids(column, talent_ids, role_ids=None)` — explicit tenant predicate + `status IS NOT NULL OR workflow_step_id IS NOT NULL`, `DISTINCT`.
- Constant 6 queries per request; indexes already present (`application.talent_id`, `future_interaction (status, due_at)`, `role.name`). KForce has no TOUCHPOINTS flag → inert there.

## Review r1 (2026-10-02, full mode, not posted)
READY WITH NITS — arch 15 PASS / 0 FAIL / 1 N/A, ticket 26/26, T&S 11 PASS / 1 FAIL (test gap) / 4 N/A, CI green. All code/test nits fixed by me in `46f11194`:
- step-only (workflow) application test for the new predicate (Navitec prod: 100% of qualifying rows are step-only — same gap I blocked on in #2350 r1; a verbatim copy here, so NIT);
- shared private select for the two sibling repo methods;
- `name__ilike` as `Query(None, max_length=255, description=…)`;
- `name__ilike=""` = no filter and non-matching term = empty page tests;
- dropped the incidental `sorted(role_ids)`;
- seam test pins `get_role_ids_applied_by_talents([])`;
- `workflow_step` fixture promoted to module level (shared by `TestRoleFilter` and `TestRoleOptions`).
Local: 177 passed across `test_future_interaction.py`, `test_future_interaction_internal.py`, `multitenancy/test_future_interaction_isolation.py`, `test_multiple_active_applications.py`; `ruff check app/` clean.

## Decisions
- `name` (bare `Role.name`) in the option, per the ticket's `{id, name}`, while `name__ilike` matches `display_name` (`{short_id} - {name}` / external-id form) exactly as `/roles` does — a superset of "by name". Left as a question for FE/product, not changed.
- Role ids are **not** narrowed by `visible_organizations` (`role` has no RLS; `RoleService.get_all` is tenant-scoped only) — inherits the accepted deviation documented on `_resolve_roles` in #2350, keeps options consistent with `role_id__in`.
- Pyright in the worktree flagged `InstrumentedAttribute` as undefined — false positive (no editable install), the import is real.

## Gotchas
- The worktree guard refuses `source …/activate` and `cd … &&` chains inside a worktree session: call `.venv/bin/ruff` / `.venv/bin/python -m pytest` by absolute path from the worktree cwd instead.
- `ruff format --check tests/…` reports two pre-existing long lines in `test_future_interaction.py` (lines ~884 and ~1567); `lint.sh` / CI only format `app/`, so they are not ours to touch.

## Pending
- Florencia: answer the two questions (name vs `display_name` label/search mismatch; `visible_organizations` deviation acceptable for options) — no code change expected.
- Pedro / team review + squash-merge of [#2375](https://github.com/taller-projects/echo-backend/pull/2375); then [US 25255](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25255) → In revision / Closed (state untouched by me, only the PR hyperlink).
- Out-of-scope notes surfaced in the review, unticketed: FE default Owner chip can still open an offered role on an empty queue (explicit "no depende del owner"); FE gates the filter by `PROJECTS_VIEW` while BE answers on `Permission.Talents`; `_person_ids_matching(term=None)` could use `talent_service.filter_existing_ids` instead of materializing name projections (pre-existing shape).
- Cross-module copies of the non-Matched predicate remain in `talent/repository.py`, `talent/models.py` (×2), `talent/filters.py` — the `Application.is_not_matched()` centralization from the 25143 note is still open.

## Related
- [[Touchpoints filter by Role (US 25143)]] (the filter this feeds; predicate, seam-test convention, `commitments=None` trap)
- [[Public bulk-create touchpoints endpoint (US 24835)]] (same module)
