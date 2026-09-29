---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, security, multitenancy, kforce, contacts, interactions, internal-api]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2367"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25222"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25223"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25231"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25232"
prd: ""
---

# Internal bulk tenant checks - interaction created_by + contacts PATCH (Bug 25222)

Two tenant-isolation holes left open in the review of [#2360](https://github.com/taller-projects/echo-backend/pull/2360) (see [[Kforce interactions write path + internal list (Task 25072)]]), filed 2026-09-29 as [Bug 25222](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25222) and [Bug 25223](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25223) (both Sev 2, Sprint 45, parent [Feature 24972](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24972)). `/internal` runs under `DisableRLS`, so the service/repo predicates are the only isolation:
- **25222**: `contact_interaction.created_by_id` (single-column FK to `user.id`) was stored as received on the internal bulk POST/PATCH **and** the per-contact create/update (shared `InteractionBase`; that router is mounted on the public app AND under `/internal/contacts/{id}/interactions`). A foreign user was accepted and every later read embedded its `created_by` (`UserProfileResponse`, email). Unknown uuid → FK 500.
- **25223**: `PATCH /internal/contacts/bulk` → `ContactRepository.bulk_update_by_ids` updated `WHERE id = cte.id` only, no ownership check → cross-tenant overwrite + `refresh_contacts` of the foreign contact.

## Azure / docs
- [Bug 25222](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25222), [Bug 25223](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25223): `AB#` links in the PR body (Azure Boards auto-link); state still New when the PR opened.
- Same contract as [[Activities bulk tenant ownership gate (Bug 25158)]]. Map: [[Map - Kforce]].

## PRs
- [#2367](https://github.com/taller-projects/echo-backend/pull/2367) → dev, opened 2026-09-29, branch `25222/internal-bulk-tenant-refs` (one PR, two tickets), commits `5313ffb1` (25222) + `cedc63d7` (25223). Assigned gonza56d. Self `/pr-review` r1 (CI green): READY WITH NITS, 0 blockers → nits fixed in `69702cc2` (pushed 2026-09-29 from worktree `.claude/worktrees/25222-nits`, branch `25222/internal-bulk-tenant-refs-nits`, refspec `HEAD:25222/internal-bulk-tenant-refs`; not posted as a GitHub review). Pedro (rocha-p) APPROVED `69702cc2` on 2026-09-29 (review 5354732878) with 5 non-blocking nits → all addressed in `aacddc66` + Bugs 25231/25232 filed; reply posted on the PR.

## How
- **25222**: `InteractionService` injects `UserService`; `_assert_references(items, interaction_ids=())` batches `user_service.filter_existing_ids(created_by_ids)` (+ the pre-existing interaction ownership lookup on the bulk PATCH, merged into one 404 with per-kind context `{"interactions": [...], "users": [...]}`). Called from `bulk_create`, `bulk_update`, and new `create` / `update` overrides. 404 `unknown_reference`. `None` never looked up; inactive / soft-deleted own users accepted (tenant-only `UserRepository` predicate).
- **25223**: `ContactService.bulk_update` pins `self._current_tenant_id()` (fail-closed) → `_assert_owned(contact_ids)` via `filter_existing_ids` → 404 `unknown_reference` `{"contacts": [...]}` before the prior-linkedin lookup / write / tracking / refresh. `ContactRepository.bulk_update_by_ids(updates, tenant_id)` adds `Contact.tenant_id == tenant_id` to every UPDATE (defense in depth). The later `tenant_id = self._current_tenant_id()` inside the linkedin block was dropped (reuses the pinned one).
- Tests: new `test_interaction_created_by_reference.py` (13 cases) + `test_contact_bulk_update_tenant_scope.py` (6 cases). Adjusted: `InteractionService(...)` constructions get `user_service=MagicMock()`; `_make_service()` in `test_contact_service.py` sets `repo.filter_existing_ids.side_effect = set`; `tenant_context` fixture (fork_request_context) on the 4 bulk_update tests of `test_contact_crm_organization_id.py` and inline in `test_crm_company_match_recompute.py`.

- **Review follow-ups (`69702cc2`)**: `_assert_references` pins `get_tenant_id(required=True)` first, so `create` / `update` / `bulk_create` fail closed like `bulk_update`; fail-closed test parametrized over all five entry points. Interactions bulk PATCH rejection tests assert no `refresh_contacts` (that route schedules it as a background task; `refresh_contact_attributes` is what POST + per-contact use) + unknown-user PATCH case. `bulk_update` docstring + OpenAPI descriptions of the three internal bulk routes state the all-or-nothing 404 `unknown_reference` (the bulk POST description was a stale contact copy-paste). Module-level context imports in `test_crm_company_match_recompute.py`. Touched modules: 165 passed.

- **Pedro's nits (`aacddc66`)**: `UnknownReferenceError(ResourceNotFoundError)` in `app/exceptions.py` (`error_code=unknown_reference`, ctor takes `{kind: ids}`, drops empty kinds, builds detail `Unknown references in this tenant: <kind> [...]`); used by `ActivityService._assert_references`, `InteractionService._assert_references`, `ContactService._assert_owned` (contacts detail wording changed, code/context same). `InteractionService.create/update` take `BaseModel` (no incompatible override); `_assert_references(items: Iterable[BaseModel])` uses `getattr(item, "created_by_id", None)`. New `test_rejected_batch_never_reaches_tracking` (monkeypatches `ContactTrackerService.register_mappings/update_tracker`). 246 tests green across touched + activity modules.

## Verification
- Full unit + multitenancy: 5646 passed, 1 failed (`test_crm_company_match_recompute::test_bulk_update_crm_organization_id_recomputes_without_refresh`, no request tenant → fixed); touched files re-run 169 passed. The 12 negative tests fail on `origin/dev`, the 7 acceptance ones pass on both.
- **Localhost E2E vs dev DB** (user asked): worktree app on :8010, 20/20 HTTP checks. Taller tenant `9541a5d4…` as request tenant, foreign data from `Cortez Group - Synthetic` `bb4455eb…` (user `6ecbb7bc…`, contact `123295ec…`, interaction `4044ebc9…`); foreign payloads reused the rows' current values so a failed check would be a no-op; foreign rows' `updated_at` unchanged afterwards. Throwaway contact `d4deeb93…` + 2 interactions deleted via the API, 0 rows left, 0 `integration_outbox` rows.

## Decisions
- **Public per-contact create/update included** (Gonzalo, conditional on proof the FE does not break): FE `origin/dev` `AddInteractionForm.tsx` is the only contact-interaction writer and sends `created_by_id: user.id` (from `/users/me`, modules tenants only) on create AND edit; public request tenant = `user.tenant_id` (`app/user/permissions.py`). Touchpoint completion (`FutureInteractionService._write_interaction` → `bulk_create`) already validates `completed_by_id` (`_assert_users_in_tenant` internal / owner equality public), so the new check never fires there.
- One PR for both bugs (same rollout, same pattern).
- 404 for foreign and unknown alike (does not reveal existence elsewhere), per 25158.

## Gotchas
- **No `/internal` API key for dev on disk**: the Bruno collection key is `sk_echo_…` (not the `echo_` internal format, no `api_key.suffix` match). Local E2E used the legacy shim instead: run uvicorn with `LEGACY_INTERNAL_TENANT_ID=<tenant>` (process env only) + header `X-Echo-internal: settings.ECHO_INTERNAL_API_KEY` → same `ctx.set_tenant_id` as the key path, zero credential writes to dev.
- `ContactCreate` email validation rejects reserved TLDs (`.invalid`) → 422.
- The worktree branch created by `git worktree add -b … origin/dev` tracks `origin/dev`: push with an explicit refspec (`git push -u origin <branch>:<branch>`), never a bare `git push`.
- Tests calling `ContactService.bulk_update` outside a request now need a request tenant (`fork_request_context(RequestContext(tenant_id=…))` + `cleanup_request_context()`).
- Running the app locally also starts every scheduler (candidate emails, notification emails, touchpoint reminders) against dev.

## Pending
- Review + squash-merge [#2367](https://github.com/taller-projects/echo-backend/pull/2367) → Bugs 25222 / 25223 Closed (team convention: straight to Closed after merge); qa/main promotion.
- Tell Emi: contacts bulk PATCH is now all-or-nothing on ids outside the tenant (e.g. a contact deleted since the pipeline read it → 404 listing ids; before: silently skipped). Unknown `created_by_id` on interactions: 404 instead of 500.
- **Filed 2026-09-29 (Pedro's nits)**: [Bug 25231](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25231) contact `created_by_id` on `POST /internal/contacts` + `PATCH /internal/contacts/{id}` (Sev 2) · [Bug 25232](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25232) `crm_organization_id` visibility check (Sev 3; `organization` is global, rule needs product). Both New, backlog (no sprint), parent 24972, assigned Gonzalo.
- Confirm with Emi that the Kforce pipeline drops the ids in `error.context.contacts` and retries (Pedro's ask).
- Still unticketed, same hole class: talent interactions `created_by_id` / `updated_by_id` on the `/internal/talents` bulk routes (`TalentInteractionService` has no reference check); `InteractionBase.related_company_id` (org FK, needs a different check); `FutureInteractionService._assert_users_in_tenant` raises without `error_code=unknown_reference`; `BulkContactsUpdate.contacts` has no `max_length`.
- Vault `CLAUDE.md` says "NEVER push" but `CLAUDE.local.md` + the hook say push — reconcile.

## Related
- [[Kforce interactions write path + internal list (Task 25072)]] · [[Activities bulk tenant ownership gate (Bug 25158)]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Map - Kforce]]
