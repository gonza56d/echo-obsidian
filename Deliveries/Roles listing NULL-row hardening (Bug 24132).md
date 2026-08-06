---
type: delivery
status: delivered
env: taller
delivered: 2026-08-06
tags: [bugfix, roles, schemas, hardening]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2008"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24132"
prd:
---

# Roles listing NULL-row hardening (Bug 24132)

One role row that hydrates as Python `None` in fields the response schema types as non-Optional **500s every variant of `GET /roles`** (the whole `Page[RoleListResponse]`) plus the single-role GET. Found 2026-08-06 in dev: a raw-SQL-seeded JazzHR test fixture role broke Patricio's FE work on the Jazz role picker — see the incident write-up in [[Push Applications Echo to JazzHR (Feature 24051)]].

## Mechanism (corrected in review round 1)
`RoleListResponse` inherits `RoleCreate`/`RoleBase` → read-side validation enforces the **create contract**. Under `from_attributes`, pydantic reads the ORM attribute's explicit `None`, and field defaults only apply to *missing* attributes — never to present-but-None. **The guarded columns are all NOT NULL in the DDL** (original bug/PR text wrongly said "nullable columns"): the real poison vector is a JSONB **JSON null** (`'null'::jsonb`), which passes the SQL constraint yet loads as Python `None`. That reaches the 10 jsonb-backed fields (`skills_required`, `skills_nice_to_have`, `country_restrictions`, `interview_questions`, `code_challenge`, `virtual_interview`, `notes`, `screening_questions`, `behavioral_questions`, `project_specific_questions`); the `enhancement_stage`/`quantity`/`enabled_for_interviews` legs are defensive against future constraint drift only. Any non-standard write path (raw SQL, `/internal`, migrations, backfills) can produce such a row. Same read-validates-create-schema fragility as Bug 24010's `ApplicationResponse` note.

## Fix — PR [#2008](https://github.com/taller-projects/echo-backend/pull/2008) → dev (branch `24132/roles-response-null-hardening`, commits `5b6c8e6c` + review r1 `1b751804`)
- Generic `mode="before"` validator `_null_to_field_default` on **`RoleListResponse` only** (create/update input contracts unchanged — explicit `null` on POST still 422s; `RoleResponse`/`SingleRoleResponse` inherit): `None` → the field's declared default via `model_fields[...].get_default(call_default_factory=True)`, deepcopy'd as **belt-and-suspenders** (pydantic ≥2's `get_default` already `smart_deepcopy`s plain defaults — the original "shared default object" comment was wrong; the wrap stays because that behavior is undocumented). Mirrors the pre-existing `_default_company_name` guard.
- Tests in `tests/unit/test_roles.py` (same schema-level pattern as `test_role_list_response_tolerates_null_company`): all 13 fields nulled → defaults (incl. `required_talents` computed off `quantity`), deepcopy instance-independence test, + r1 regression test pinning that `RoleCreate` keeps rejecting explicit nulls (`RoleUpdate` is `@partial_model` → accepts None by design, not pinned).
- Full unit suite 3528 green, ruff clean.

## Review round 1 (2026-08-06, /pr-review 3-agent protocol)
- Verdict CHANGES REQUESTED on **one documentation-only blocker**: comment + PR body + ticket misstated the mechanism (nullable columns → actually JSON null; verified vs DDL migrations + live dev `information_schema`). Fixed in `1b751804`, PR body + ticket note corrected same day.
- Nits applied in `1b751804`: deepcopy comment reworded (kept the wrap); `RoleCreate` null-rejection regression test added.
- Compliance 9/9, architecture 11 PASS/1 FAIL (the comments), tests-security 7 PASS/0 FAIL. Dict-with-None tests exercise the same before-validator path as `from_attributes` (verified empirically both ways).
- GitHub Actions was DOWN at PR creation (no suite created, workflow_dispatch 500'd for ~25 min) — recovered ~18:45Z, pull_request run queued on `1b751804`.

## Decisions / notes
- **Response-side only** — coercing on `RoleBase` would silently loosen the create contract (explicit `null` would become the default instead of 422).
- **`quantity=0` deliberately NOT coerced**: `Gt(0)` would still fail a response for a real `0` row, but coercing `0→1` changes data meaning; 0 such rows exist in dev (verified); separate decision if it ever occurs. Noted in the Bug.
- **Silent coercion, no logging** — matches the `_default_company_name` precedent; per-row logs inside a validator risk flood on a poisoned page. Open question to reviewers whether a Sentry breadcrumb outside the hot path is worth it.
- Dev/prod data clean at fix time (0 poison rows after healing the fixture role by copying columns from its clone source `708ca2d4`; live query for `'null'::jsonb` across all 10 jsonb columns → 0 rows).

## Pending
- ~~Review + merge~~ → **MERGED to dev 2026-08-06 18:58Z** (squash `2d9b3e7c`, approved by Leo, merged by Gonza). **CI never ran on the branch** (GitHub Actions outage swallowed every event: PR-creation run auto-cancelled, the `1b751804` synchronize event dropped, merge-push to dev dropped too); post-merge validation = manually dispatched run `31126659589` on dev @ `2d9b3e7c`.
- Bug 24132 → move to Resolved.
- **Follow-up tickets NOT filed yet** (surfaced by review r1):
    1. `PublicRoleResponse` (`app/modules/public_api/schemas.py`) — same failure class: JSON null in `skills_required`/`skills_nice_to_have` would 500 the public career-page `Page[PublicRoleResponse]`.
    2. `virtual_interview` DB default drift — live dev `column_default` is `'{}'::jsonb` vs model `server_default="[]"` (`app/modules/role/models.py:402`); a raw-SQL insert taking the server default yields `{}` → bypasses the None-guard and fails `list[Question]` validation → same one-row-500. Needs a small alignment migration.
    3. `ApplicationResponse` inherits `ApplicationCreate` (Bug 24010 side-finding) — same pattern could 500 application listings; not audited.

## Related
- [[Push Applications Echo to JazzHR (Feature 24051)]] — the incident that surfaced this
- [[On Hold candidates invisible in pipeline buckets (Bug 24010)]] — the ApplicationResponse sibling fragility
