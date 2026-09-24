---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, kforce, contacts, internal-api, filters]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2344"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25111"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
prd: ""
---

# Kforce contacts kforce_external_id__in item cap (Bug 25111)

Follow-up of [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]]. Emiliano's canary against kforce-dev (2026-09-23) found the new `GET /internal/contacts?kforce_external_id__in=` filter capped at 100 **characters**, not 100 ids: a Kforce id is a 36-char GUID, so 2 fit per call and 100 answer `422 string_too_long`. That blocked contact adoption: the offset sweep 500s from page ~1,000 (20s `statement_timeout`), and 2 ids/call = ~1M requests vs ~19.8k. Fixed by enforcing the cap on the split list.

## Azure / docs
- [Bug 25111](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25111) (parent [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972)) — In revision
- Sibling ask from the same message: [Task 25112](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25112) (PRD P1-3, org `updated_at__gte` + `merged_into_id`) → [[Kforce org updated_at filter for merges (Task 25112)]]
- PRD source: Emiliano's `docs/prd-pedidos-a-echo-backend-2026-09-21.md` in `taller_kforce_integration_api` (a copy sits untracked at `echo-backend/prd-pedidos.md`), section P0-1 "Actualización 2026-09-23"

## PRs
- [#2344](https://github.com/taller-projects/echo-backend/pull/2344) → dev — open 2026-09-24, branch `25111/kforce-external-id-in-item-cap`, commit `969b27f0`

## How
- `ContactFilter.kforce_external_id__in: List[str] | None = None` (no `Field(max_length=...)`); `@field_validator` `_cap_kforce_external_id_batch` raises when the split list has more than `KFORCE_EXTERNAL_ID_BATCH_MAX = 100` ids (`app/modules/contact/filters.py`).
- Tests in `tests/unit/test_contact_kforce_external_id_filter.py`: 100 real GUIDs through the route → 200 (fails on dev with the exact `string_too_long`), 101 → 422. Unit + multitenancy: 5235 passed.

## Decisions
- Keep the cap at 100 ids (Emi explicitly asked for items, not a bigger number); it matches the `/internal/contacts` page size.
- Validator over `Annotated`/custom type: the generated FilterDepends model is built with `create_model` and no base, so class validators never reach the `str` query param; they only run on the real `ContactFilter(**data)`.

## Gotchas
- **fastapi-filter `FilterDepends` → `_list_to_str_fields` deep-copies each list field's `FieldInfo` onto a `str` param.** Any `max_length`/`min_length` on a list field in a `Filter` caps the raw comma-joined string. Never use them on `__in` fields; validate the split list instead.
- The US 25054 tests missed it: model-level checks used Python lists, route tests used 15-char ids.
- Tenant-scope question (C4): kforce-dev has ONE tenant (`018a3ca4…` Kforce Inc.), so `count(*)` global = tenant = 1,636,903 proves nothing by itself. Real evidence: `TenantScopedRepository._base_query` adds `contact.tenant_id = <key's tenant>` (internal app runs under `DisableRLS`) + `test_other_tenants_contacts_stay_invisible`.

## Pending
- Review + merge #2344 → Bug 25111 Closed, dev deploy (kforce-dev auto on green).
- Reply to Emiliano: fix PR + counts answer (1,636,903 both, single-tenant DB) + code evidence.
- qa/main promotion.

## Related
- [[Map - Kforce]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Kforce org updated_at filter for merges (Task 25112)]]
