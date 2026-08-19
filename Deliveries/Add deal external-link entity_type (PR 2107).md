---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, external-links, trackerrms]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2107"
fe_prs: []
tickets: []
prd: ""
---

# Add deal external-link entity_type (PR 2107)

Added `deal` to the `/external-links` `entity_type` enum so an external id can be mapped to an Echo **deal** (`OrganizationDeal`). Pure enum addition — the endpoints now accept/store/resolve/list/delete `deal` links, keyed by `OrganizationDeal.id` (UUID PK). Same `entity_external_links` table the org/role/talent/application/contact/touchpoint/interaction types already use (see [[External links writeback (US 23126)]]).

## Azure / docs
- No ticket (ad-hoc request from the API docs view).

## PRs
- [#2107](https://github.com/taller-projects/echo-backend/pull/2107) → dev — open (in review). Branch `feat/deal-external-link-entity-type`, commit `062645a7`.

## How
- One line: `deal = "deal"` added to `ExternalLinkEntityType` in `app/modules/external_link/schemas.py`.
- Added `test_upsert_accepts_the_deal_entity_type` (bind + resolve through the generic path) in `tests/unit/external_link/test_endpoints.py`.
- 92/92 external_link unit tests green; ruff clean on `schemas.py`.

## Decisions
- **No migration.** `entity_external_links.entity_type` is a plain `String` column (not a Postgres enum, no CHECK) — adding an enum member is a Python-only change.
- **No per-type wiring.** Service/repository are entity-type agnostic (store/resolve the opaque string). Only the router's `organization` branch does a canonical-merge check; every other type (incl. `deal`) binds generically with no existence check — matched that behavior deliberately.
- Test placed as its own method, not folded into the `test_upsert_accepts_the_activity_entity_types` parametrize, because a deal is not an activity.

## Gotchas
- `ruff format` on the test file reformats pre-existing over-length lines (tests are NOT linted by CI, only `app/`), producing scope-creep diff noise. Reverted and re-applied only the new method — commit only touches the enum line + the new test.

## Pending
- Merge to dev (then qa/main promotion if desired — no ticket gating).
- **Optional consumer wiring, out of scope for this PR** (only if deals need to be fully surfaced):
  - Deep-link URLs: a `deal` link resolves but its `url` stays `None` until a tenant's integration `config.entity_paths` gains a `"deal"` key (`external_link/service.py::_build_deeplink_url`).
  - Embedding `external_links` in deal API responses needs an `attach_deeplinks(ExternalLinkEntityType.deal, ...)` call in the deal routers (only org/talent/role/contact call it today).
  - TrackerRMS sync auto-binding: `tracker_rms_sync_service._ALLOWED_LINK_ENTITY_TYPES = {"role","application","talent"}` does not include `deal` (the generic POST endpoint does not consult it).

## Related
- [[External links writeback (US 23126)]] · [[ATS deep-links Open in ATS (US 23507)]]
- [[Map - TrackerRMS integration]]
