---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, reporting, strategy-tracker, review]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2233"
fe_prs:
  - "https://github.com/taller-projects/echo-frontend/pull/3312"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24826"
prd: ""
---

# Strategy Tracker bucket bands (US 24826)

Florencia's PR moves the Strategy Tracker bucket→band grouping from the FE into the `GET /reporting/pipeline/by-role` contract: each bucket now carries `group: {id, label} | null` (AR ungrouped). My part: full /pr-review (scoped mode, 3 agents), then pushed the review fixes myself on the PR branch and approved.

## Azure / docs
- [US 24826](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24826) (parent Feature 24547; related FE [US 24697](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24697))

## PRs
- [#2233](https://github.com/taller-projects/echo-backend/pull/2233) → dev — Florencia's; review fixes pushed `61dc9761` (2026-09-08), APPROVED by me
- FE: [#3312](https://github.com/taller-projects/echo-frontend/pull/3312) — consumes `group`, marked `⛔ NEEDS BE ⛔`; **BE must merge+deploy first** (field is additive, so safe either way, but FE depends on it)

## How
- `buckets.py`: `BucketGroup` NamedTuple + `GROUP_BY_BUCKET` (bucket→band, versioned next to phase→bucket). Bands: AA–AB Candidates in Screening, AC–AD Candidates in Internal Qualification, AH–AJ TA Funnel: Internal screenings, AK–AQ TA Funnel: External interviews, AR null.
- `schemas.py`: `PipelineBucketGroup {id, label}`, `group` optional on `PipelineBucketInfo`. No migration.
- My review-fix commit `61dc9761`: moved `TestBucketContract` to `tests/unit/test_reporting_pipeline_buckets.py` (CI only runs unit+multitenancy — the invariants never executed in CI); added literal band-membership + id/label + contiguity tests; `BucketGroupId` StrEnum typing end to end; `PIPELINE_BUCKETS` built once at import (unmapped bucket now fails startup, not every request).

## Decisions
- Review verdict was CHANGES REQUESTED (1 blocker: invariant tests in a suite CI never runs) — Gonzalo had me fix blocker+nits directly on the PR instead of a review round.
- Band ids (`candidates-in-screening`, …) are now a cross-repo contract — pinned with literal assertions BE-side.

## Gotchas
- The endpoint is gated by `TenantFeature.PIPELINE_METRICS`; the `/reporting` mount's `Protected([Permission.ReportingView])` is still commented out pending Task 24422 — feature gate is the only access control today (pre-existing).
- `ReportingPipelineService`/`Repository` rely on injector implicit binding (not in `dependency_registry`) — works, inconsistent with siblings (pre-existing, unfiled).

## Pending
- FE parity check: confirm the 4 group ids/labels match exactly what [#3312](https://github.com/taller-projects/echo-frontend/pull/3312) consumes (esp. AD under Internal Qualification, AP/AQ under External interviews) — asked in my approval.
- Merge #2233 (Florencia) → dev deploy → then release FE #3312.
- qa/main promotion later with the usual batch.

## Related
- [[Map - Observability & Reliability]]
