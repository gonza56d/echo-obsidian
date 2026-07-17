---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-07
tags: [bugfix, contact, relationships, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1745"
  - "https://github.com/taller-projects/echo-backend/pull/1746"
  - "https://github.com/taller-projects/echo-backend/pull/1747"
tickets: []
---

# Client Active gate relaxation (PR 1745)

Prod report (Navitec): **Martin Juan**, Client at Centene, emailed 5 days ago — showed `Past`. The Client Active rule required recent activity AND an **open `contact_job` at the relationship's company**, but client-side contacts usually have no scraped job history → the gate always failed. It conflated *"history shows they left"* with *"no history at all"*. Impact: 145 Navitec Client contacts wrongly Past, 52 could **never** be Active.

## PRs
- [#1745](https://github.com/taller-projects/echo-backend/pull/1745) → dev · [#1746](https://github.com/taller-projects/echo-backend/pull/1746) → qa · [#1747](https://github.com/taller-projects/echo-backend/pull/1747) → main — merged 2026-07-07

## How
Account gate now passes (Active-eligible) when ANY of:
1. relationship has no `company_id` *(existed)*
2. open `contact_job` at `company_id` *(existed)*
3. **contact has no `contact_job` at all** — can't prove they left *(new)*
4. **recent (12-month) interaction tied to that same company** *(new)*

Centralized in `_relationship_is_active_expr` → fixes both `Contact.relationship_state` and per-rel `Relationship.state`. Validated against prod Navitec: 143/145 flip to Active; 2 correctly stay Past; branch #4 EXISTS rides `idx_contact_interaction_date_desc` (~0.1ms).

## Follow-ups this spawned
- Branch #4 over-fired for contacts who **moved away** → [[Moved-away Client contacts Past (Bug 23519)]]
- Semantics re-tightened later by [[Client Active significant activity (US 23536)]]
- Kforce port: [[Kforce Client Active no-job gate (Bug 23545)]]

## Related
- [[Map - Contact Relationships]]
