---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, proposals, case-studies, export]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1878"
  - "https://github.com/taller-projects/echo-backend/pull/1883"
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

Proposals & case studies were a privileged-tenant capability: proposal export 404'd for any tenant without a custom `proposal_template` (only Navitec had one — and the generic fallback file the code referenced never existed), and case-study generation was gated by the `case_studies` tenant feature flag (41/43 dev tenants excluded). Backend rollout = 4 milestones: **M1** generic Echo PDF template + **M3** tenant-gate removal (PDF-first, #1878), **M2** generic PPTX theme + drop the PPTX gate + **M4** Team Builder error transparency & `tech_stack` fix (#1883). Executes deferred R6 of Phase 5.

## Status
- **M1 + M3 — MERGED → `dev`** ([#1878](https://github.com/taller-projects/echo-backend/pull/1878), squash merge `1aa8afec`, 2026-07-21).
- **M2 + M4 — PR [#1883](https://github.com/taller-projects/echo-backend/pull/1883) open → `dev`** (2026-07-21). Formal 3-agent `/pr-review` **READY WITH NITS** — 0 blockers, **CI green** (`test and lint` pass), 15/15 M2+M4 acceptance criteria satisfied (arch 14/14 PASS, tests-security 10/10 PASS); nits fixed `926571d1`. 381 unit tests green (testcontainers), `ruff check app` clean.
- **FE PR — required, not yet opened** (ungating + data-readiness R5; must also surface PPTX for template-less tenants now that PPTX is ungated).
- **TB registration — external long pole (TB team owns)** — still blocks *generation* (and export — see gotcha) for unregistered tenants.

## Azure / docs
- [US 23670](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23670) → Tasks [23671](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23671) (M1, #1878) · [23673](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23673) (M3, #1878) · [23672](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23672) (M2, #1883) · [23674](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23674) (M4, #1883)
- PRD: [Generic Proposal Template & Case Studies for All Tenants](https://app.notion.com/p/3a2aedca11f08145b822f16d751c693f)
- Approved design: Echo Proposal Template — 10 slides (claude.ai design `32867681`)

## How
### M1 (#1878)
- New `generic_proposal.jinja` (WeasyPrint): Echo teal `#18858C`, dark-teal cover, serif headings, per-page masthead + "Powered by Echo for Staffing" footer, slide-6 case-study table, resource allocation w/ bill rates, tech stack, closing. `export/service.py`: template-less tenants resolve to it; timeline gate widened to `navitec or not proposal_template` (PDF; PPTX gated in its own renderer until M2).
### M3 (#1878)
- Removed `CASE_STUDIES` gate from `_get_project_and_tenant`; deleted `CaseStudiesFeatureDisabledError` + `TenantFeature.CASE_STUDIES`; removed export 404 guard; `has_custom_export_project = True` always. No migration.
### M2 (#1883)
- `proposal_pptx_renderer.py`: extracted the hardcoded Navitec palette/font into a `ProposalTheme` frozen dataclass — `NAVITEC_THEME` (values unchanged) + `ECHO_THEME` (teal `#18858C` / cover `#0F3D3D` / ink `#1A1A1A` / body `#5A5A5A` / badge `#E7F2F2`+`#146D73`), picked by `_theme_for(proposal_template)`. `_load_logo(None)` → bundled `echo_logo.png`. Renderer timeline gate → `if timeline_phases:` (service owns the per-template gate). Removed the `CASE_STUDIES_PPT_EXPORT` 403 guard in `export_proposal` + the enum value + now-unused `HTTPException`/`TenantFeature` imports. No migration (`available_features` is free-form `ARRAY(String)`).
### M4 (#1883)
- New `TeamBuilderTenantNotRegisteredError(DependencyMissingError)` → **409**, group 2, `error_code=team_builder_tenant_not_registered`, plain-string detail. Mapped at `ProjectSolutionService.post` (overrides base, catches `ExternalApiException`, string-matches "not registered", re-raises typed; everything else passes through) so every TB generate path benefits. `mode="before"` `tech_stack` null→[] validators on `CaseStudyGenerated` + `ProposalResourceAllocation`.

## Decisions
- **PDF-first split** (M1+M3 first, then M2+M4) — user's call; branded generic PPTX needed M2 before the PPTX gate could go.
- **Gates deleted, not flagged** (PRD 2026-07-20).
- **M4 error = `DependencyMissingError` (409)** — semantically "a prerequisite (TB registration) must be set up first", not a transient 5xx; plain-string detail restores the FE `{detail:<string>}` contract (the raw upstream error leaked a *list*).
- **Translate at the TB client chokepoint** (`ProjectSolutionService.post`), not per-caller — one place covers proposal export + case-study generate/regenerate/find-similar + team/role gen. String-match "not registered" (TB owns the message; documented).
- **`ProposalTheme` dataclass** over per-tenant PPTX master files — matches the M2 ticket ("parameterize the renderer theme"); a designer-authored master stays a follow-up.
- M2+M4 in one PR (#1883) in a worktree off `origin/dev` (already carries #1878), so the diff is only M2+M4.
- **#1883 review nits fixed (`926571d1`)**: `_load_logo` now logs a warning when the bundled Echo wordmark is unreadable (a deploy regression should not silently yield logo-less decks); corrected the now-stale `export/service.py` timeline comment (post-M2 the gate feeds both PDF and PPTX); typed `_iter_tb_error_messages(detail: object)`; added two TB-error boundary tests (list-detail pass-through without the marker + the intended broad case-insensitive "not registered" substring match). 110 affected export/TB unit tests green, ruff clean.

## Gotchas
- **Export is NOT independent of Team Builder** (corrects the earlier M1/M3 note): `ProjectService.export_proposal` calls `solution_service.generate_proposal` — a TB `self.post` — on *every* export. So proposal export hits the same "tenant not registered" long pole as case-study generation; M4 makes it a clear 409 but does not make it succeed.
- **PPTX theme refactor**: color tokens were module constants used in method bodies AND default params. Default params (`color=TEXT`, `bar_color=RED`) can't reference `self.theme`, so they became `None` + in-body resolution; body refs were word-boundary swapped to `self.theme.*`. Tech-badge text maps to `badge_text` (`#146D73`), not the primary accent.
- **`test_proposal_graphics` no-panel tests**: the Echo-logo fallback now adds logo pictures, so `_count_pictures == 0` broke — added `_panel_picture_count` that excludes pictures whose blob == the bundled Echo logo.
- **`tech_stack` needs `mode="before"`**: the field is non-optional `List[str]`, so an "after" validator never runs on `null` (type validation rejects it first).
- Echo logo is dark → low-contrast on the dark-teal cover/closing; light Echo wordmark is a follow-up (same as the PDF).
- Azure **Tasks reject `System.State` transitions** — PR-link comments posted on 23672/23674; states left as-is.

## Pending
- **Paired FE PR** (must ship with this): ungating + data-readiness warnings (R5); surface PPTX for template-less tenants (now ungated).
- **External long pole**: Team Builder must accept/register all tenants (TB team owns) — blocks generation AND export for unregistered tenants.
- **Confirm the `tech_stack` 422 direction before closing Task 23674** (`/pr-review` open question): the fix coerces the *inbound* TB-response schemas (`CaseStudyGenerated`/`ProposalResourceAllocation`), but `proposal_builder.py:72` still sends `tech_stack=... or None` *outbound*. Correct iff TB echoes null back and echo's own `validate_return` is what 422s (the PR's claim; the added tests confirm the response path). Verify against one real TB call — no regression either way.
- Design-fidelity reconcile vs the approved 10-slide design (PDF + now PPTX).
- Cosmetic: PDF footer-rule center gap; light Echo logo for dark pages.
- Close Azure tasks on merge (23671/23673 already merged via #1878; 23672/23674 in review).

## Related
- [[Case studies per-card management (US 23613)]] · [[WeasyPrint 62 to 68 upgrade (US 23479)]] · [[Industry-agnostic Echo (PRD 398aedca)]]
