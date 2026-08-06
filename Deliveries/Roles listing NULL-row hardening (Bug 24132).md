---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, roles, schemas, hardening]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2008"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24132"
prd:
---

# Roles listing NULL-row hardening (Bug 24132)

One role row with NULL in columns the response schema types as non-Optional **500s every variant of `GET /roles`** (the whole `Page[RoleListResponse]`) plus the single-role GET. Found 2026-08-06 in dev: a raw-SQL-seeded JazzHR test fixture role broke Patricio's FE work on the Jazz role picker — see the incident write-up in [[Push Applications Echo to JazzHR (Feature 24051)]].

## Mechanism
`RoleListResponse` inherits `RoleCreate`/`RoleBase` → read-side validation enforces the **create contract**. Under `from_attributes`, pydantic reads the ORM attribute's explicit `None`, and field defaults only apply to *missing* attributes — never to present-but-None. Vulnerable fields: non-Optional with nullable backing columns (`skills_required`, `skills_nice_to_have`, `country_restrictions`, `interview_questions`, `code_challenge`, `virtual_interview`, `notes`, `screening_questions`, `behavioral_questions`, `project_specific_questions`, `enhancement_stage`, `quantity`, `enabled_for_interviews`). Any non-standard write path (raw SQL, `/internal`, migrations, backfills) can produce such a row. Same read-validates-create-schema fragility as Bug 24010's `ApplicationResponse` note.

## Fix — PR [#2008](https://github.com/taller-projects/echo-backend/pull/2008) → dev (branch `24132/roles-response-null-hardening`, commit `5b6c8e6c`)
- Generic `mode="before"` validator `_null_to_field_default` on **`RoleListResponse` only** (create/update input contracts unchanged — explicit `null` on POST still 422s; `RoleResponse`/`SingleRoleResponse` inherit): `None` → the field's declared default via `model_fields[...].get_default(call_default_factory=True)`, **deepcopy'd** (get_default returns the SHARED default object for model/list defaults — responses must not share mutable instances). Mirrors the pre-existing `_default_company_name` guard.
- Tests in `tests/unit/test_roles.py` (same schema-level pattern as `test_role_list_response_tolerates_null_company`): all 13 fields nulled → defaults (incl. `required_talents` computed off `quantity`), + deepcopy instance-independence test.
- Full unit suite 3528 green, ruff clean.

## Decisions / notes
- **Response-side only** — coercing on `RoleBase` would silently loosen the create contract (explicit `null` would become the default instead of 422).
- **`quantity=0` deliberately NOT coerced**: `Gt(0)` would still fail a response for a real `0` row, but coercing `0→1` changes data meaning; 0 such rows exist in dev (verified); separate decision if it ever occurs. Noted in the Bug.
- Dev/prod data clean at fix time (0 poison rows after healing the fixture role by copying columns from its clone source `708ca2d4`).

## Pending
- Review + merge #2008; Bug 24132 → Resolved after.
- Possible sibling: `ApplicationResponse` inherits `ApplicationCreate` (Bug 24010 side-finding) — same pattern could 500 application listings; not audited here.

## Related
- [[Push Applications Echo to JazzHR (Feature 24051)]] — the incident that surfaced this
- [[On Hold candidates invisible in pipeline buckets (Bug 24010)]] — the ApplicationResponse sibling fragility
