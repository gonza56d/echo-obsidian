---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, matching, vectorizer, polling, fe-contract]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2225"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24773"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24774"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24775"
prd: ""
---

# Matching batch status proxy (US 24774)

Backend half of [Feature 24773](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24773) (from Nico Lizondo's matching-products integration guide, artifact `0c0d6d3b-94b4-4bab-a8c2-82585ae8957b`): matching runs were fire-and-forget so nobody knew when a run finished. The matching API (QUEUE_ENABLED=true, on in dev) now returns `batch_id` in its 202s + exposes `GET /candidate_matching/batches/{batch_id}`. We capture the batch_id, surface it in the rematch response, and proxy the status endpoint for FE polling.

## Azure / docs
- [Feature 24773](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24773) → BE [US 24774](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24774) (Gonzalo, Active) + FE [US 24775](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24775) (unassigned)
- Upstream contract: matching service Swagger `/docs` is authoritative; PRD "Cola de Matching" artifact `06511816-fa64-4e0f-8f11-eff46ea99cb3`

## PRs
- [#2225](https://github.com/taller-projects/echo-backend/pull/2225) → dev — OPEN 2026-09-07

## How
- `VectorizerService.evaluate_application(_batch)` → `_enqueue_evaluation`: synchronous POST, `read_timeout=settings.MATCHING_EVALUATE_READ_TIMEOUT` (new, 15s) + `max_retries=0`, exceptions swallowed → `str | None` batch_id (`.get()` — absent = queue off / legacy).
- `RematchResponse.matching_batch_id` (additive) — rematch is the first flow surfacing the ticket.
- `GET /matches/batches/{batch_id}` (Protected Talents + get_current_user) → `MatchService.get_matching_batch_status`: tenant check (upstream payload `tenant_id` vs ctx, else 404 `batch_not_found`), response schema drops tenant_id, upstream 404/503 pass through as ExternalApiException.
- `MOCK_MATCHING_BATCH_ID` fixed constant in mocks; mock status echoes ctx tenant.

## Decisions
- `status` is a plain `str` (not Literal) — upstream may grow states; FE branches on `in_progress` vs rest.
- Other callers (application create, `create_match_applications`) ignore the returned batch_id for now — FE-scoped follow-up under the Feature.
- Auth: added `get_current_user` dependency besides `Protected` — Protected is inert when ENABLE_ACCESS_CONTROL=False, and match_talents in the same router already uses it.
- Trade-off documented in PR: enqueue callers can now block up to 10s connect + 15s read on a hung matching API (was 0s threaded); failure degrades to old behavior.

## Gotchas
- `tests/unit/test_vectorizer_service.py` patched `fire_and_forget` in 8 tests → now patch `post` (body asserts unchanged).
- `MatchService.__new__` fixture in test_industry_propagation needed `evaluate_application_batch.return_value = None` (MagicMock fails RematchResponse validation) — the known `__new__` collaborator trap.
- Anonymous-401 route tests are impossible in this harness: conftest overrides `AuthenticatedUser.current_user_id` app-wide.

## Review (2026-09-07)
- Leo APPROVED (review 5134256170, 9 nits) + own /pr-review (2 blockers = Leo's nits 1-2, several nits). **All addressed in `6eca2aed`**: bounded status GET (15s/0 retries, kwargs pinned by test); `capture_batch_id` opt-in — only rematch pays sync cost, create + per-role loop back to fire_and_forget (kills the N×25s amplification); `logger.opt(exception=True)` on swallow; upstream 404 unified into `batch_not_found` (no existence oracle); mount-level gate only (endpoint `Protected` was double-gating); `extra="ignore"` explicit; str-vs-UUID note; tests for 503 passthrough, response-level null, single swallow, no-upstream-tenant 404, ctx-None 404, malformed-id 422, fire-and-forget default.
- Untestable in harness (documented): anonymous 401 / negative-permission 403 (conftest overrides auth app-wide).

## Pending
- CI green on `6eca2aed` → squash-merge #2225 (authorized by Gonzalo).
- FE US 24775 (poll + UI; decide which screens beyond rematch).
- Dev e2e once merged: rematch a role on dev → poll the proxy until `completed`.
- qa/main promotion.

## Related
- [[Application comments role fields for matching (US 24772)]] — sibling PRD from the same matching-products batch.
