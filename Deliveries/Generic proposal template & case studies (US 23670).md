---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, proposals, case-studies, export]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1878"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23670"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23671"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23672"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23673"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23674"
prd: "https://app.notion.com/p/3a2aedca11f08145b822f16d751c693f"
---

# Generic proposal template & case studies (US 23670)

Proposals & case studies were a privileged-tenant capability: proposal export 404'd for any tenant without a custom `proposal_template` (only Navitec had one — and the generic fallback file the code referenced never existed), and case-study generation was gated by the `case_studies` tenant feature flag (41/43 dev tenants excluded). This delivery ships **M1 (generic Echo proposal PDF template)** + **M3 (tenant-gate removal)** of the backend US, **PDF-first**: PPTX stays gated until M2. Executes deferred R6 of Phase 5.

## Azure / docs
- [US 23670](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23670) → Tasks [23671](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23671) (M1, this PR) · [23672](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23672) (M2, deferred) · [23673](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23673) (M3, this PR) · [23674](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23674) (M4, deferred)
- PRD: [Generic Proposal Template & Case Studies for All Tenants](https://app.notion.com/p/3a2aedca11f08145b822f16d751c693f) (added the "Backend Milestones" section decomposing the backend rollout bullet into M1-M4)
- Approved design: Echo Proposal Template — 10 slides (claude.ai design `32867681`)

## PRs
- [#1878](https://github.com/taller-projects/echo-backend/pull/1878) → dev — **open** (M1 + M3, PDF-first). Formal 3-agent `/pr-review` 2026-07-21: **READY WITH NITS** — 0 code blockers, **CI green** (`test and lint` pass) + 138 unit tests pass locally; cross-tenant isolation (explicit `tenant_id` repo filter, *not* RLS), auth + role gates intact after the gate removal; no dangling refs to the removed enum/exception. PRD 15/21 fully + PPTX-flag PDF-first tradeoff (→M2) + design-fidelity/footer QA-reconciles. First-round nits fixed `bef5b680`; second-round test-coverage nits fixed `70f6c661`.
- FE: **required, not yet opened** — ungating + data-readiness warnings (R5); `has_custom_export_project` becomes always-true so the FE always shows the export action, and the FE must **not** offer PPTX for template-less tenants (still 403 until M2).

## How
- **M1** — new `app/modules/export/templates/tenant/generic_proposal.jinja` (WeasyPrint print layout) adapting Navitec's proven structure to the Echo design: teal `#18858C` accent, dark-teal cover, serif headings + teal underline, per-page masthead (tenant logo) + "Powered by Echo for Staffing" footer with `counter(page)/counter(pages)`, slide-6 case-study label/value table, resource allocation w/ bill rates, tech stack, no-contact-block closing. `export/service.py`: template-less tenants resolve to the generic template (replaces the dead `else "proposal.jinja"` branch); timeline gate widened to `proposal_template == "navitec" or not proposal_template` (PDF only — PPTX gates timeline in its own renderer until M2).
- **M3** — removed the `CASE_STUDIES` feature check from `_get_project_and_tenant` (renamed from `_get_project_and_tenant_gated`) in `case_study/service.py`; deleted `CaseStudiesFeatureDisabledError` + the `TenantFeature.CASE_STUDIES` enum value; removed the export 404 guard in `project/routers.py`; `has_custom_export_project = True` always. Logo fallback needed no code — `_get_logo_url(None)` already returns bundled `echo_logo.png`.
- No migration (`TenantFeature` is a `StrEnum`; `available_features` is free-form `ARRAY(String)`).

## Decisions
- **PDF-first** (user): this PR = M1 + M3 minus the PPTX-flag removal. Kept the `case_studies_ppt_export` gate because branded generic PPTX needs M2 (renderer theme is Navitec-hardcoded); removing it now would expose an off-brand deck.
- **Gates removed from code, not kept as kill-switches** (PRD 2026-07-20) — flags would force a backfill for every new tenant.
- **Design source**: couldn't fetch the claude.ai design (share links 403); adapted from Navitec structure + a user screenshot of slide 6 + Echo tokens. Cover/objectives/delivery-phases/resource/closing inferred — reconcile vs the approved design in QA.
- One PR for M1+M3 in a worktree off updated `dev`.
- **Review nits fixed (`bef5b680`)**: (a) dropped the vestigial tenant `SELECT` on the update/delete/regenerate/find-similar write paths — only `generate` needs the tenant config; (b) block-scoped `{% autoescape %}` over the generic template body; (c) added service-level + render-branch test coverage. export + case-study unit suites green, ruff clean.
- **Review nits fixed (`70f6c661`)**: second round, from the formal 3-agent `/pr-review` — added generic-template test coverage: (a) Echo-logo fallback fills masthead/cover/closing when the tenant has no logo (R2), mirroring the service wiring; (b) no-rate resource row renders the em-dash fallback (isolate the row, assert no `$`); (c) logo-URL attribute-context escaping under the block-scoped autoescape. `test_proposal_graphics.py` 24 passed locally.

## Gotchas
- `generic_proposal.jinja` section names live in CSS comments/selectors ("Delivery Phases", "Executive Summary", …) → text-based test assertions false-positive; assert on rendered `class="..."` markup instead.
- **Autoescape must be block-scoped, never global**: the shared export `Environment` (`export/service.py::_setup_jinja`) has no autoescape and registers a `markdown` filter — several templates emit raw HTML via `{{ x | markdown }}`. Flipping the env to autoescape would double-escape that output and regress CV/JD/Navitec renders. The generic template opts in with `{% autoescape true %}` around its body only (it uses no `| markdown`/`| safe`).
- Echo-logo fallback on the **dark cover/closing** is low-contrast (bundled `echo_logo.png` is dark) — needs a light logo variant (same pattern Navitec solved with `wordmark_light`).
- Footer separator has a small **center gap** (WeasyPrint margin-box border quirk).
- Azure **Tasks reject `System.State='Active'`** (and `In Progress`/`Doing`) — their workflow uses other values; only the User Story accepted `Active`. PR-link comments were posted on all three; task states left as-is.
- The local-TestClient-404 quirk did **not** bite the case-studies API tests (project endpoints, not talent) — all green locally.

## Pending
- **M2** ([Task 23672](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23672)): parameterize the PPTX renderer theme (extract Navitec-hardcoded palette/font) + Echo-logo fallback in `_load_logo` + widen PPTX timeline gate; then remove the `case_studies_ppt_export` gate.
- **M4** ([Task 23674](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23674)): Team Builder error transparency (typed domain errors instead of opaque 404/500) + `tech_stack` null→[] 422 fix.
- **Paired FE PR** (must ship with this): ungating + data-readiness warnings (R5); hide PPTX for template-less tenants until M2.
- Design-fidelity reconcile: cover / resource allocation / tech stack / closing vs the approved 10-slide design (awaiting screenshots).
- Cosmetic: footer-rule center gap; light Echo logo for dark pages.
- External long pole: Team Builder must accept all tenants without registration (TB team owns) — blocks generation for unregistered tenants; export ships independently.

## Related
- [[Case studies per-card management (US 23613)]] · [[WeasyPrint 62 to 68 upgrade (US 23479)]] · [[Industry-agnostic Echo (PRD 398aedca)]]
