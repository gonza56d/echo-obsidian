---
type: delivery
status: merged
env: both
delivered: 2026-11-19
tags: [contacts, multitenancy, internal-api, kforce]
prs:
  - https://github.com/taller-projects/echo-backend/pull/2684
fe_prs: []
tickets:
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25960
  - https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25951
prd:
---

# Contacts refresh empty body scoped to the caller's tenant (Bug 25960)

## What

`POST /internal/contacts/refresh` with an empty body recomputed every contact of every tenant from any tenant's API key (about 1M contacts on KForce). No data leaked (no response body, values right), but one tenant's caller loaded all tenants. Now an empty body refreshes the caller's tenant only, and ids dropped for belonging to another tenant are logged.

## Azure

- [Bug 25960](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25960): **Closed** 2026-11-19 (comment 29380136 with the caller findings and decisions; closing comment with the description correction and the follow-up).
- Follow-up of [Bug 25951](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25951) (Closed), which scoped the id list in [#2648](https://github.com/taller-projects/echo-backend/pull/2648); raised by Pedro's review of that PR.

## PRs

- [#2684](https://github.com/taller-projects/echo-backend/pull/2684) to dev, branch `25960/refresh_empty_body_tenant_scope`, **MERGED dev `f61530f9`** 2026-11-19 (squash; Leo approved on `4c4534d3`, his nits in `ccebcd26`, CI green 18m37s), worktree `.claude/worktrees/25960-refresh-tenant-scope`. Reviewers Leo, Pedro, Gisel.

## How

- `ContactSQLRepository._every_contact_as_member()`: the `members` CTE of a refresh with no ids, filtered on `get_tenant_id()` when there is a request tenant. Used by `refresh_contact_attributes_bulk` and `refresh_activity_companies_count_bulk`.
- `recompute_crm_company_match`: with no ids, the pairs (and the open-jobs CTE, for cost only) filter on the request's tenant.
- `refresh_relationship_metrics` already filtered on the tenant; `schedule_future_interaction_refresh` already does nothing for an empty list (the ticket's "queues every tenant's follow-up jobs" did not happen).
- `ContactService.refresh_own_contacts` logs `contact.refresh.dropped_ids tenant_id=... dropped=... requested=...` (loguru warning).
- Route summary / description and `docs/contact-groups.md` recovery line updated.
- Test: `test_post_internal_contacts_refresh_leaves_another_tenants_contacts_alone` in `tests/unit/test_contacts.py` gains a `no_ids` row and checks every derived value on the other tenant's contact plus the log line.

## Decisions

- **Empty body = caller's tenant**, not "all tenants for a system key": API keys always carry a tenant, so no system key exists, and nobody sent an empty body in 30 days (Loki access logs `content_length`: kforce-prod about 7,700 calls, all `python-httpx` id batches; kforce-dev 504; prod 0).
- **Dropped ids: log only** (user's choice 2026-11-19). Response stays 201 with no body, the Data team's contract is untouched.
- Outside a request (script, migration) the repository methods still cover the whole table.
- All tenants, no flag: isolation fix.

## Gotchas

- Leo's review (APPROVED, nits only, all taken in `ccebcd26`): return type on the helper, one guard form (walrus) in the CRM match with the reason the open-jobs filter exists, stale "whole table" wording in `refresh_relationship_metrics` and the rollout step of `docs/contact-groups.md`, precondition assert before the request.

- The CRM match needs BOTH filters removed to leak when the other tenant's verdict is `unknown`: the open-jobs filter alone leaves the verdict `unknown`. The test seeds a stale `mismatch` so removing the pairs filter alone is caught.
- The access log's `content_length` is what tells an empty-body call from an id batch (an empty JSON list is 2 bytes; one uuid is 40).
- `docs/` is gitignored: a tracked file there still commits, but `git add docs/...` together with other paths prints the ignore error.

## Pending

- Promotion to qa / main with the next release.
- Not ticketed (Leo's review, out of scope): on kforce-prod KForce is practically the only tenant, so `[]` is still three UPDATEs over about 1M rows in one synchronous request. Nobody sends it; if needed, route the empty case through chunked `CONTACT_ATTRIBUTES_REFRESH_BULK` jobs.
- The contact-groups recovery call with `[]` does not schedule the deferred follow-up refreshes (an empty list never did); the runbook does not say so.

## Related

- [[Testing practice - Given-When-Then tests through real entry points (Feature 25717)]] (where #2648 and Bug 25951 live)
- [[Internal bulk tenant checks - interaction created_by + contacts PATCH (Bug 25222)]]
- [[Map - Contact Relationships]] · [[Map - Kforce]]
