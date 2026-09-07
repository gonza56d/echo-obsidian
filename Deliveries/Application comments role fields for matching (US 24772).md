---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, application, comments, matching, internal-api]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2224"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24772"
prd: ""
---

# Application comments role fields for matching (US 24772)

Nico Lizondo (Data / matching-products) request, PRD artifact "Application Comments para Matching" (2026-09-03): the matching service consumes `GET /internal/applications/comments?talent_id=` as evaluation context, but to label a comment written on *another* application with its role it did 1 + N GETs per candidate (`GET /applications/{id}` per referenced app just to read the role name). We added `role_id` + `role_name` to every comment and reply so it's 1 GET; the matching client auto-detects the fields and skips its lookups — no coordinated deploy.

## Azure / docs
- [US 24772](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24772) — assigned to Gonzalo, Active
- PRD: Claude artifact `90755dba-2652-48f2-9f61-0355d7579ab5` (Application Comments para Matching); sibling artifact `0c0d6d3b-94b4-4bab-a8c2-82585ae8957b` (batch-status polling guide — NOT picked up, optional, would land in `vectorizer_service`)

## PRs
- [#2224](https://github.com/taller-projects/echo-backend/pull/2224) → dev — OPEN 2026-09-07; self-review (skill /pr-review, full mode) 2026-09-07: 0 blockers, verdict READY WITH NITS; nits addressed in `c72f1b80`. Leo APPROVED 2026-09-07 16:02 (0 blockers); his nits (role_name-per-app assertion, deleted-reply masking, public-surface line in body) addressed in `f4a49b17` + PR body edit

## How
- `ApplicationComment` gained an `application` relationship (the composite FK `(application_id, tenant_id)` already existed — no migration).
- `ApplicationCommentListResponse` + `ApplicationCommentReplyResponse` gained `role_id` / `role_name` via `AliasPath("application", "role_id")` and `AliasPath("application", "role", "name")` — the schema-driven planner (`app/modules/db/`) derives the joins from the 3-segment path, so the SELECT projects them with no repo/service changes.
- Fields are `| None = None` (additive safety), though `application.role_id` is NOT NULL in practice — deliberate: if the planner ever stops projecting the join, validation degrades to `None` instead of a 500 (why-comment now in `schemas.py`).
- Tests: roots + replies carry the fields; per-application role correctness across two applications of the same talent; deleted comment masks `content` but keeps role fields (`tests/unit/test_application_comments_internal.py`).
- Review nit fix (`c72f1b80`): `Role.role_workflow_step` is mapper-level `lazy="joined"`, so joining `Application.role` dragged all ~20 of its columns twice (root + replies paths). Suppressed in `ApplicationCommentSQLRepository._base_query` via `defaultload(...).lazyload(Role.role_workflow_step)` — compiled SQL verified: role_workflow_step joins 2 → 0, application/role joins intact. A generic planner-level suppression of un-requested eager rels was deliberately NOT done (global blast radius; e.g. surfaces relying on `role_workflow_step.allows_new_applications`).

## Decisions
- Fields also appear on the public `GET /applications/{id}/comments` (same schema) — harmless/additive, FE ignores extra fields.
- `ApplicationCommentResponse` (create/update responses) deliberately untouched — PRD only asks for the list surface.
- Kept everything the PRD lists as "must not change": is_system, deleted masking, nesting, pagination, mention markup, route order.

## Gotchas
- `source scripts/venv.sh` before pytest leaks `.env` (`ENABLE_ACCESS_CONTROL=True`) → every Protected route 404s. Run `uv run pytest` in a clean shell (bit us again this session).
- Kforce fork is GONE (unified 2026-09-03; kforce-dev/kforce-master frozen) — one PR to dev now serves all deployments.

## Pending
- Ask Nico: does the matching client treat `role_name: null` as "field absent" (i.e. would it silently fall back to 1+N lookups)? OpenAPI advertises the fields nullable.
- Follow-up (unticketed, out of PR scope): cross-tenant negative test for the internal by-talent listing in `tests/multitenancy/` (pre-existing gap); pre-existing commented-out `application` relationship stub in `app/modules/application/status_history/models.py:32-34` — implement or delete.
- CI on `f4a49b17` → squash-merge #2224 (approved).
- Post-merge verification per PRD: Loki `{app="matching-products-api-<env>"} |~ "\[APP_COMMENTS\]"` — role-lookup lines disappear; zero `GET /internal/applications/{id}` with UA `python-httpx`.
- US 24772 → Ready to Test after dev deploy.
- Sibling PRD (batch-status polling) unscheduled — no ticket filed.

## Related
- [[Map - JazzHR integration]] · matching-products consumer: `taller_ttit_matching_products/api/src/candidate_matching.py`
