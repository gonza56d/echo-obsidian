---
type: delivery
status: merged
env: both
delivered: 2026-09-24
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
- [#2344](https://github.com/taller-projects/echo-backend/pull/2344) → dev — **MERGED 2026-09-24** (squash `7b4c3726`), branch `25111/kforce-external-id-in-item-cap`, commits `969b27f0` (fix) + `7651c88f` (my r1 nits) + `71533086` (Pedro's nits)

## Review
- `/pr-review` r1 2026-09-24 on `969b27f0`: **READY WITH NITS**, 0 blockers, CI green (arch 9 PASS / 1 FAIL nit A14 / 6 N/A; ticket 7/7 in-scope; tests-sec 12 PASS / 0 FAIL / 4 N/A). Not posted to GitHub.
- Nits fixed in `7651c88f`: return type on `_cap_kforce_external_id_batch`; FilterDepends rationale kept once (field comment), docstring keeps only the why-100; tests derive 99/100/101 + message from `KFORCE_EXTERNAL_ID_BATCH_MAX`; 422 test pins `error.code == "validation_error"` + `detail[0].loc == ["kforce_external_id__in"]`. PR body corrected: org filter has item semantics but NO cap (not "same contract"); cap also hits `GET /contacts/relationships`.
- **Pedro (rocha-p) APPROVED** 2026-09-24 on `7651c88f`, READY WITH NITS (verified dev 422 vs PR 200 with 100 real GUIDs). Fixed in `71533086`: error msg drops the backticked field name (`loc` names it; msg is now `Value error, accepts at most 100 ids per call.`); 422 test asserts `loc[-1]` only (survives a fastapi-filter `query` prefix); new `test_public_list_accepts_a_full_batch_of_guids` on `GET /contacts`; comment on `KFORCE_EXTERNAL_ID_BATCH_MAX` (100 GUIDs ~3.7k chars vs nginx-ingress 8k request line → ~200 ceiling).
- Pedro nits NOT changed: duplicates / empty items count toward the cap (`split_str` is shared by every `__in`; results stay correct via the unique index; Kforce sends clean lists). His OOS: a `docs/`/`AdvancedFilter` note that `_list_to_str_fields` copies ANY `FieldInfo` constraint (`max_length`, `min_length`, `pattern`) onto the joined str; `GET /contacts/relationships` has no coverage of this filter (pre-existing).
- Left as out-of-scope (not built): per-item length cap (`List[Annotated[str, Field(max_length=64)]]`), org filter cap symmetry, cap `description` in OpenAPI, EXPLAIN evidence from kforce-dev.
- Verified: `FilterWrapper.__new__` re-raises `ValidationError` as `RequestValidationError` → 422, never 500 (only via FilterDepends; a direct `ContactFilter(...)` in service code would 500, no caller today). `split_str` doesn't trim/dedupe → trailing comma counts as an item.

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
- Bug 25111 → Closed; confirm dev + kforce-dev deploy of `7b4c3726` went green, then Emi re-runs the canary with 100 GUIDs.
- Reply to Emiliano: fix PR + counts answer (1,636,903 both, single-tenant DB) + code evidence.
- qa/main promotion.

## Related
- [[Map - Kforce]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Kforce org updated_at filter for merges (Task 25112)]]
