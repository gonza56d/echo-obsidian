---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-17
tags: [feature, case-studies, ai]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1842"
  - "https://github.com/taller-projects/echo-backend/pull/1843"
  - "https://github.com/taller-projects/echo-backend/pull/1852"
  - "https://github.com/taller-projects/echo-backend/pull/1853"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23613"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23619"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23620"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23621"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23622"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23623"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23624"
prd: "https://app.notion.com/p/39daedca11f08140819ccec08e77dafb"
---

# Case studies per-card management (US 23613)

Per-item management for generated case-study cards: edit, delete, regenerate, and find-similar — replacing the all-or-nothing regeneration flow.

## Azure / docs
- [US 23613](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23613) → [tasks 23619](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23619)–[23624](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23624) (were "In revision" pre-merge)
- PRD: [PRD Técnico: Case Studies (Edit + Regenerate) — Backend](https://app.notion.com/p/39daedca11f08140819ccec08e77dafb) · [business PRD](https://app.notion.com/p/399aedca11f080e39053c32e50bbc879)

## PRs (both → dev, merged 2026-07-16)
- [#1842](https://github.com/taller-projects/echo-backend/pull/1842) **M1** ([23619](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23619)/[23620](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23620)) — per-card **edit (PATCH)** and **delete** endpoints (head `f2ccdbb9`)
- [#1843](https://github.com/taller-projects/echo-backend/pull/1843) **M2** ([23621](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23621)–[23624](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23624)) — per-card **regenerate** and **find-similar** endpoints (head `56232772`; approved by Pedro, review nits addressed)

## Key decisions
- **Forma B** API shape (chosen during PRD review).
- **null-vs-soft-fail** semantics: a failed regeneration doesn't destroy the existing card.
- **`position` computed in the INSERT** (no read-modify-write race for card ordering).

## Merge coordination note
- [#1843](https://github.com/taller-projects/echo-backend/pull/1843) stacked on [#1842](https://github.com/taller-projects/echo-backend/pull/1842) — the rule was: merge [#1842](https://github.com/taller-projects/echo-backend/pull/1842) first; re-merge into [#1843](https://github.com/taller-projects/echo-backend/pull/1843) if [#1842](https://github.com/taller-projects/echo-backend/pull/1842) moved. Both landed 2026-07-16 in order.

## Dev e2e QA vs real Team Builder (2026-07-17) — PASSED ✅

Data team (Rodri) deployed `/case_studies/regenerate` + `/case_studies/find_similar` to TB dev; ran the full e2e the same day. Results documented in a comment on [US 23613](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23613) (moved **In development → Ready to Test**) and in the PRD's M2 milestone.

- **Tenant**: e2e must run on **Navitec** (`a0329c9a`) — the only TB-registered tenant in dev. The Taller dev tenant (`9541a5d4`) is NOT registered in TB CaseStudies (`generate`/`regenerate`/`find-similar` → external 404 "tenant not registered"). Project used: *QA Test Proposal* (`ab6c6a9e`), plus a Taller project for negative paths.
- **All 6 endpoints passed**: GET (empty+populated) · generate (atomic replace, ~20s) · PATCH (exclude_unset, whitespace strip, `tech_stack: null`→`[]`, `{}` no-op, explicit-null revert) · DELETE (204 empty body, re-delete 404) · regenerate (same id/pos, content+consultant swapped, siblings byte-identical, ~23s) · find-similar (×4, each appends exactly one card at max+1, no cap).
- **Negative paths**: 404 bogus/cross-project/cross-tenant on all card ops, 422 oversized field, 401 no-auth, TB transport error → soft-fail with previous set intact (observed live via the unregistered Taller tenant).
- **TB contract validated directly** (X-Echo-internal, Forma B payload): single `StructuredCaseStudy` with nested `provenance` | `null`, always 200; `mode=vectorize` → 422.

### Gotchas found (no blockers)
- **`inspired`/`application` dedups by `source_talent_id` only** → regenerate/find-similar can return a card with the same `company_name` as an existing one (saw two "Walmart" + two "John Deere" cards live). Per contract; FE/product should be aware.
- **`null` (no-candidate) path not reproducible** on Navitec — pool too large even after 4 find-similars. Covered by unit tests + TB contract only.
- **Pre-existing generate quirk** (unchanged endpoint, NOT this US): project without `tech_stack` → TB 422 (`project.tech_stack` null rejected; echo sends `tech_stack: null` via `build_proposal_request`). Candidate for a tiny follow-up (send `[]` instead of null, or TB accepts null).
- Grafana API key expired during QA → `case_study.generation` structured-log verification pending (unit-tested; needs new key in `~/.zshrc`).

## Promotion to QA / PROD (cherry-pick, 2026-07-17)

Feature promoted from `dev` to the release branches as a bundle (both dev PRs = one US, one promotion PR per env), following the per-feature `cherry-pick/*` convention (precedent: dispatcher #1839/#1840). Merge with a **merge commit**, not squash.

- **→ qa**: [#1852](https://github.com/taller-projects/echo-backend/pull/1852) — branch `cherry-pick/case_studies_per_card_qa` — **merged 2026-07-17** (merge commit)
- **→ main (PROD)**: [#1853](https://github.com/taller-projects/echo-backend/pull/1853) — branch `cherry-pick/case_studies_per_card_main` — **merged 2026-07-17** (merge commit) → **in production**

Promotion recorded as a comment on [US 23613](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23613) (2026-07-17); US stays **Ready to Test** pending feature QA.

Mechanics: each branch has **2 clean commits** (M1 #1842, M2 #1843), produced by `git cherry-pick -m 1` of the two dev **merge commits** (`13cd03d9`, `b8953097`) then rewording. qa/main were 19 commits behind dev but all 7 touched files were byte-identical to dev's pre-feature base → **cherry-picks applied cleanly, zero conflicts**; net diff verified byte-identical to dev's post-feature tree. **No schema changes / no migrations.** Both cherry-picked directly from dev (parallel, like the dispatcher precedent), main body notes to merge after qa. Feature is `TenantFeature.CASE_STUDIES`-gated → no-op for tenants without the flag. Local promotion worktrees: `../echo-backend-cs-qa`, `../echo-backend-cs-main` (removable once merged).

## Pending
- FE overlay integration (remove Regenerate All + Lock; per-card Edit/Delete/Regenerate/Find Similar; message the `null` "no result" state).
- Decide whether Data should register the **Taller dev tenant** in TB CaseStudies so QA isn't Navitec-only.
- Optional follow-up: `tech_stack: null` 422 on generate for projects without tech stack (pre-existing).
