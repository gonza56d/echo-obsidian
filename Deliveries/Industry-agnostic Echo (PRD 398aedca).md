---
type: delivery
status: merged
env: taller
delivered: 2026-07-14
tags: [feature, ai, tenants, matching]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1816"
  - "https://github.com/taller-projects/echo-backend/pull/1818"
  - "https://github.com/taller-projects/echo-backend/pull/1819"
  - "https://github.com/taller-projects/echo-backend/pull/1821"
  - "https://github.com/taller-projects/echo-backend/pull/1834"
  - "https://github.com/taller-projects/echo-backend/pull/1835"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23548"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23549"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23571"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23576"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23583"
prd: "Notion 398aedca — Industry-agnostic Echo"
---

# Industry-agnostic Echo (PRD 398aedca)

Make Echo's AI services work for non-tech tenants: a single **tenant industry signal** resolved once and propagated to the 5 matching-products calls plus the other AI services. Contract guarantee: `tech`/null tenants keep emitting **byte-identical requests** (zero behavior change for existing tenants).

## PRs (all → dev)
- [#1816](https://github.com/taller-projects/echo-backend/pull/1816) **M1** (2026-07-13) — resolution point: `Tenant.industry` property (`null ⇒ "tech"`), `TenantService.get_industry()/get_current_industry()`, `industry_resolved` structured log; propagate to `vectorize_talent/job_description/text`, `evaluate_application(_batch)`; `industry` added to the `@lru_cache` keys (no cross-industry vector collisions).
- [#1818](https://github.com/taller-projects/echo-backend/pull/1818) **M2** — propagate to resume parser + assessment creator.
- [#1819](https://github.com/taller-projects/echo-backend/pull/1819) **M3** — propagate to team builder.
- [#1821](https://github.com/taller-projects/echo-backend/pull/1821) **M4** — gate `matching_diff` endpoint by tenant industry (code-challenge skip for generic).
- [#1834](https://github.com/taller-projects/echo-backend/pull/1834) **M5** ([Task 23576](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23576), 2026-07-14) — **generic seniority ladder** for non-tech tenants.
- [#1835](https://github.com/taller-projects/echo-backend/pull/1835) ([23583](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23583), 2026-07-14) — expose resolved `industry` on `/users/me` (FE's permission oracle — additive).

## QA
- **Dev HTTP QA PASSED 2026-07-14**: Coca-Cola tenant `3f1c4697` flipped to `generic` + QA user; verified code-challenge skip, get_skills, team_builder, parser, matching, logs. QA also surfaced [[Project creation consumer_id 422 (Bug 23571)]].

## Client context
- First consumer: **Battle Tested** (veteran-staffing client, [Epic 23300](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23300): career page, Hiring our Heroes scrape, API key). "Enabled Force" = possible 2nd brand, unconfirmed.

## Pending
- **No prod `generic` tenant until matching-products promotes the assessment-creator data.**
- Admin surface to set a tenant's industry.

## Related
- [[Deep pagination selectin fix (23553)]] — found while QA'ing lists on this feature branch
