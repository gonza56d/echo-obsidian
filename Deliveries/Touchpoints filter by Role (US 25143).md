---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, touchpoints, future-interaction, applications, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2350"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25143"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25144"
prd: "https://app.notion.com/p/3e5aedca11f0816a9118d23413fc431d"
---

# Touchpoints filter by Role (US 25143)

Navitec asked (2026-09-24, direct request, no Capa 1) to filter the Touchpoints list by Role so that, combined with the Owner filter, they can see how many candidates of a process each person is working. A touchpoint stores only the linked person, so the filter is **derived**: "touchpoints of candidates with a non-Matched application to any of these roles". Shipped as `role_id__in` on `GET /future-interactions` (and the internal list), no schema change, no flag.

## Azure / docs
- [US 25143](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25143) — BE (this note). Successor: FE [US 25144](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25144) (Role multi-select in the Touchpoints filter bar, reuses the Strategy Tracker role selector, hidden without roles permission, tooltip "Candidates applied to this role").
- PRD técnico (Tier B, Pedro): [Touchpoints — Filtro por Role — PRD Técnico](https://app.notion.com/p/3e5aedca11f0816a9118d23413fc431d). Tier B only because it adds a query param to the public contract.

## PRs
- [#2350](https://github.com/taller-projects/echo-backend/pull/2350) → dev — OPEN 2026-09-25, branch `25143/touchpoints_role_filter`, commit `b06058d5`.
- FE: none yet (US 25144). Contract impact: one additive query param `role_id__in` (comma-separated UUIDs); response shape unchanged.

## How
- `FutureInteractionFilter.role_id__in` (`app/modules/future_interaction/filters.py`), consumed and cleared like `search`.
- `FutureInteractionService._resolve_roles`: takes the candidate refs already in touchpoints (`repo.get_person_refs`), asks `ApplicationService.get_talent_ids_applied_to_roles(role_ids, talent_ids)` (new, tenant-scoped `DISTINCT talent_id`, predicate `status IS NOT NULL OR workflow_step_id IS NOT NULL`, request session so RLS applies), intersects with any supplied `linked_entity_id__in`, and narrows `linked_entity_type__in` to candidates. Runs in `list_for_viewer` right after `_restrict_entity_types` and BEFORE `_restrict_to_visible_people`, so the talent-side data_scope intersection still wins; also in `list_internal` after `_resolve_search`.
- `ApplicationService` injected into `FutureInteractionService` (no DI cycle: nothing under application/talent/role imports touchpoints).
- Contract: empty match → `200` empty page (never the unfiltered list); malformed UUID → `422` standard shape; contacts excluded while the filter is active.

## Decisions
- **Not** `TalentFilter.applications` (the multi-active EXISTS): `TalentRepository._gate_applications_filter` silently sets it to `None` on tenants without `MULTIPLE_ACTIVE_APPLICATIONS`, which would return the unfiltered list, exactly what the PRD forbids. `last_application_role_id__in` is wrong too (last application only, not "≥1"). A dedicated bounded query through the applications module works identically with the flag on or off.
- Bounded to the people already referenced by touchpoints (same reason as `search`): the `IN` grows with the queue, not with a role's applicant count.
- No cap on the number of role ids (PRD sizes latency for 1–10 but sets no limit; user agreed to leave it uncapped).
- Persisting `role_id`/`application_id` on the touchpoint was explicitly discarded in the PRD for this iteration (migration + FE create changes + no backfill); revisit in the KPIs follow-up.

## Gotchas
- **Wire format is comma-separated**, not repeated params: `FilterDepends` turns list fields into a single `str`, so `role_id__in=a&role_id__in=b` keeps only the last value. The PRD example shows repeated params and should be corrected; the FE already sends `a,b` for every other `__in`.
- data_scope cannot be exercised end to end in tests (RLS off under testcontainers). Pinned at the service seam instead: `test_role_matches_are_intersected_with_visible_people` asserts the applications answer is intersected with the talent service's result, never used alone.
- `ApplicationFactory` randomizes `status`; `None` turns the row into a Matched suggestion. Every test application pins `status` explicitly.
- Navitec prod numbers (2026-09-25, read-only `EXPLAIN ANALYZE`): 4002 touchpoints, 73 distinct candidates with touchpoints, 39.5k applications. Refs 3.6 ms, resolution 10 roles 1.7 ms (BitmapAnd on `application_role_status_idx` + `application_talent_id_idx`), 1 role 0.1 ms (unique `(tenant, role, talent)` index), page + count 0.3 ms. Criterion p95 < 1 s met by orders of magnitude.

## Pending
- Team review + merge of [#2350](https://github.com/taller-projects/echo-backend/pull/2350); dev deploy.
- Azure: [US 25143](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25143) → In revision + assign + formal "GitHub Pull Request" link (see vault commit for what was automated).
- FE [US 25144](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25144) (unassigned); tell the FE dev the wire format is comma-separated.
- Tell Pedro: PRD contract example (repeated params) needs correcting; data_scope covered at the seam, not end to end.
- QA gating: feature complete (BE + FE) before qa/main promotion; QA plan in PRD §5 (3 h, multi-active tenant).
- Follow-up (outside PRD): role/touchpoint KPIs for management dashboards, where exact attribution (persist role/application on the touchpoint) gets decided.

## Related
- [[Public bulk-create touchpoints endpoint (US 24835)]] (same module, the `search` resolution pattern this reuses)
- [[Candidates Stage filter divergence (Bug 24242)]] (multi-active `applications` EXISTS and its gate)
