---
type: delivery
status: in-review
env: kforce
delivered: 2026-08-10
tags: [feature, contacts, kforce, release, crm]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2007"
  - "https://github.com/taller-projects/echo-backend/pull/2020"
  - "https://github.com/taller-projects/echo-backend/pull/2031"
  - "https://github.com/taller-projects/echo-backend/pull/2033"
fe_prs:
  - "https://github.com/taller-projects/echo-frontend/pull/3138"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24038"
prd: ""
---

# CRM organization on contact read models (Feature 24038)

Kforce client renders the company line under the contact name; it used to read
`last_relationship.company`, which is **not** the Dynamics Account Name (a
contact may hold relationships with orgs that are not its CRM account, and
`ContactListResponse.last_relationship` is `relationships[0]` with no ordering
validator — which relationship wins is not even fixed). Feature 24038 exposes
`crm_organization` (id / name / logo, `CompanyName | None`) on
`ContactResponse`, `ContactListResponse` and `ContactDashboardListResponse`,
resolved from the `crm_organization_id` anchor. Feature authored by **Melina**
([#2031](https://github.com/taller-projects/echo-backend/pull/2031)); my part
(2026-08-10) = the **kforce-master release cherry-pick**
[#2033](https://github.com/taller-projects/echo-backend/pull/2033).

## Azure / docs
- [Feature 24038](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24038) — Show company below contact name (sourced from Dynamics Account Name)

## PRs
- [#2007](https://github.com/taller-projects/echo-backend/pull/2007) (Leo) → kforce-dev — the `crm_organization_id` anchor + `crm_company_match` re-anchor (kforce migration `c3n8rkq2wp51`); **already on kforce-master** (merge `16a5a1f6`)
- [#2020](https://github.com/taller-projects/echo-backend/pull/2020) → dev — Taller port of the anchor final state (migration `91eebppm0zva`)
- [#2031](https://github.com/taller-projects/echo-backend/pull/2031) (Melina) → kforce-dev — the read models; squash `ff1aeb1b`, merged 2026-08-10. **No migration, no new column.**
- [#2033](https://github.com/taller-projects/echo-backend/pull/2033) → **kforce-master** — release cherry-pick of `ff1aeb1b` (commit `3ec803b3`, original author/message preserved) — **OPEN, in review**
- FE: [#3138](https://github.com/taller-projects/echo-frontend/pull/3138) → FE kforce-dev — merged 2026-08-10; reads the new `crm_organization` field instead of `last_relationship.company`. Contract impact: 3 contact read models gain `crm_organization: {id, name, logo} | null`.

## How
- `Contact.crm_organization` relationship/property on the model + the field on the three schemas (`app/modules/contact/models.py`, `schemas.py`); schema-driven loading derives the join. Tests in `tests/unit/test_contact_crm_organization_id.py` (18).
- Release: branch `cherry_pick/24038_crm_organization_kforce_master` from `origin/kforce-master`, `git cherry-pick ff1aeb1b`, applied clean.

## Decisions
- **Cherry-pick release, not whole-branch promotion**: `kforce-dev` also carries [#2012](https://github.com/taller-projects/echo-backend/pull/2012) (open-jobs org_job fields) and [#2021](https://github.com/taller-projects/echo-backend/pull/2021) (people-involved AM/recruiter split) — not part of this release. Precedent: [#1804](https://github.com/taller-projects/echo-backend/pull/1804) (`cherry_pick/23536_client_active_kforce_master`).
- Kept the original squash message + author (no `-x` line), matching how `4b65aad3` was done in #1804.
- Merge #2033 with a **merge commit**, never squash (release-branch convention).

## Gotchas
- #2031 overlaps #2021 on `contact/models.py` + `contact/schemas.py`; the pick auto-merged. Verified **content-identical** to the reviewed diff via diff-of-diffs (`diff <(git show ff1aeb1b) <(git show HEAD)` → only blob hashes/hunk offsets differ).
- A later `kforce-dev → kforce-master` promotion will re-carry `ff1aeb1b`; if #2021's neighboring lines conflict, resolve to kforce-dev's version (same shape as the `9d9d733a` resolution after #1804).

## Pending
- [#2033](https://github.com/taller-projects/echo-backend/pull/2033) review + merge (merge commit) → then flip this note to `shipped-prod`.
- **Ordering**: BE #2033 must reach kforce prod **before/with** the FE kforce prod release, or the client's company line reads an absent field.
- Melina/Leo own the feature QA; #2012 / #2021 remain unreleased on kforce-dev (their own releases, not mine).

## Related
- [[Map - Kforce]] · [[Map - Contact Relationships]] · [[Kforce Contact Relationships port (US 23370)]]
