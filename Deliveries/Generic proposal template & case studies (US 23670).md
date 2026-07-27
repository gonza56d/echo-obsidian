---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-24
tags: [feature, proposals, case-studies, export]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1878"
  - "https://github.com/taller-projects/echo-backend/pull/1883"
  - "https://github.com/taller-projects/echo-backend/pull/1887"
  - "https://github.com/taller-projects/echo-backend/pull/1891"
  - "https://github.com/taller-projects/echo-backend/pull/1899"
  - "https://github.com/taller-projects/echo-backend/pull/1903"
fe_prs:
  - "https://github.com/taller-projects/echo-frontend/pull/3025"
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
- **BACKEND COMPLETE — IN PROD** since the 2026-07-23/24 dev→qa→main releases. All four milestones merged, plus Pedro's follow-ups (below).
- **M1 + M3 — MERGED** ([#1878](https://github.com/taller-projects/echo-backend/pull/1878), squash `1aa8afec`, 2026-07-21). **M2 + M4 — MERGED** ([#1883](https://github.com/taller-projects/echo-backend/pull/1883), merged by Pedro 2026-07-22).
- **Pedro's follow-ups while I was out (2026-07-22 → 24, all merged + in prod)** — see the dedicated section below: [#1887](https://github.com/taller-projects/echo-backend/pull/1887) PDF design fidelity, [#1891](https://github.com/taller-projects/echo-backend/pull/1891) PPTX mirror, [#1899](https://github.com/taller-projects/echo-backend/pull/1899) outbound `tech_stack` null→[], [#1903](https://github.com/taller-projects/echo-backend/pull/1903) optional `next_steps`/`contact`.
- **FE ungating — SHIPPED**: [echo-frontend #3025](https://github.com/taller-projects/echo-frontend/pull/3025) (show Case Studies for all tenants) merged 2026-07-24. Data-readiness warnings (R5) still unshipped.
- **TB registration — external long pole (TB team owns)** — still blocks generation AND export for unregistered tenants (Pedro's e2e attempt was still 409-blocked on 07-22).
- **Azure + PRD reconciled 2026-07-27**: Tasks 23671–74 **Closed**, US 23670 → **Ready to Test**; Feature [23541](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23541) → In development (Pedro, 07-22); PRD status line updated to match.

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
- **#1883 remaining review nits fixed (`c2fd9703`)**: the M4 typed error (`TeamBuilderTenantNotRegisteredError`, a `DependencyMissingError` — NOT an `ExternalApiException`) bypassed the two `except ExternalApiException` soft-fail handlers in `case_study/service.py`, silently dropping the `case_study.generation` `outcome="error"` telemetry for the tenant-not-registered case — the dominant failure mode during ungating rollout until TB accepts every tenant. The set was still safe (persistence runs only after a successful TB response), but the failure went invisible in telemetry. `generate()` + `_request_single_study()` now also catch the typed error, log it at **warning** (no stack trace — expected precondition, avoids Sentry spam) and still record `outcome="error"`; genuine transport failures keep the error + traceback. Added regression-lock tests: typed 409 propagates + the persisted set is never touched across generate/regenerate/find-similar + telemetry fires. 85 case-study/TB/export tests green, ruff clean.

## Follow-ups while I was out (2026-07-22 → 24, Pedro)

- [#1887](https://github.com/taller-projects/echo-backend/pull/1887) **PDF design fidelity** (merged 07-22, 4 commits): white Echo wordmark (`echo_logo_white.png` + `logo_on_dark`) so the logo is visible on the dark-teal cover/closing — resolves my "light Echo logo" pending; Mona Sans bundled (SIL OFL, DS substitute for Proxima Nova); DS palette tokens (ink `#080808`, body `#4D4D4D`, hairlines `#E9E9E9`); zebra-free resource table; 16px pill badges; delivery phases ≤3/slide; **16:9 render** (`13.333in × 7.5in`) + single `position: fixed` footer hairline — resolves the footer-rule center-gap pending; generic PPTX ends on the Thank-you closing.
- [#1890](https://github.com/taller-projects/echo-backend/pull/1890) opened 07-22 19:25 from the same branch **after #1887 had merged** (18:46) and **closed unmerged 4 minutes later** — a stale duplicate; its PPTX half became #1891. Nothing was lost (the PDF fixes are #1887 commits — verified on `dev`).
- [#1891](https://github.com/taller-projects/echo-backend/pull/1891) **PPTX design-fidelity mirror** (merged 07-22): soft corner-glow ripple (disc + 3 rings), teal Delivery-Phases header + "Duration" + big teal numeral + square bullets, neutral-grey case-study label column — all gated on `theme.echo_layout`, Navitec byte-identical (structurally verified).
- [#1899](https://github.com/taller-projects/echo-backend/pull/1899) **outbound `tech_stack` null→[]** (merged 07-24): `proposal_builder.py` sent `tech_stack or None` and TB's *request* model declares it non-optional → 422 (seen in prod, project intive). **Settles the Task-23674 open question: the 422 existed in BOTH directions** — #1883 fixed inbound (TB response), this fixes outbound. TB-side contract fix (optional in their request model) tracked as non-blocking follow-up.
- [#1903](https://github.com/taller-projects/echo-backend/pull/1903) **`next_steps`/`contact` optional** (merged 07-24): TB omitted both keys for a prod proposal (Sentry `ECHO-BACKEND-BA`, generic template) and `@validate_call(validate_return=True)` 500'd before rendering; now `| None` + PPTX/Navitec renderers skip the sections (the generic template never rendered them).
- **FE**: [echo-frontend #3025](https://github.com/taller-projects/echo-frontend/pull/3025) removed the `case_studies` FE feature gate (merged 07-24).
- All of it reached prod via the 07-23 (#1897/#1898) and 07-24 (#1901/#1902, #1904/#1906) releases.

## Gotchas
- **Export is NOT independent of Team Builder** (corrects the earlier M1/M3 note): `ProjectService.export_proposal` calls `solution_service.generate_proposal` — a TB `self.post` — on *every* export. So proposal export hits the same "tenant not registered" long pole as case-study generation; M4 makes it a clear 409 but does not make it succeed.
- **PPTX theme refactor**: color tokens were module constants used in method bodies AND default params. Default params (`color=TEXT`, `bar_color=RED`) can't reference `self.theme`, so they became `None` + in-body resolution; body refs were word-boundary swapped to `self.theme.*`. Tech-badge text maps to `badge_text` (`#146D73`), not the primary accent.
- **`test_proposal_graphics` no-panel tests**: the Echo-logo fallback now adds logo pictures, so `_count_pictures == 0` broke — added `_panel_picture_count` that excludes pictures whose blob == the bundled Echo logo.
- **`tech_stack` needs `mode="before"`**: the field is non-optional `List[str]`, so an "after" validator never runs on `null` (type validation rejects it first).
- Echo logo is dark → low-contrast on the dark-teal cover/closing; light Echo wordmark is a follow-up (same as the PDF).
- Azure Tasks rejected `System.State` transitions on 2026-07-21, but on 2026-07-27 a direct PATCH to `Closed` worked on all four — the project uses a custom state set (New/Being defined/…/In development/Developed/Ready to Test/Testing/Closed); the default Agile `Active` is NOT valid for these types (legacy value on old items), which is the likely cause of the earlier rejections.

## Pending
- **External long pole**: Team Builder must accept/register all tenants (TB team owns) — still blocks generation AND export for unregistered tenants (409 as of 07-22).
- **FE data-readiness warnings (R5)** — not shipped (FE #3025 only removed the gate); PRD wants warn-on-zero roles (`sourced`) / talents (`inspired`).
- Feature QA (US 23670 is Ready to Test): generic PDF+PPTX vs the approved 10-slide design on a real tenant + Navitec regression pass.
- Product follow-ups flagged out-of-scope in #1887: objectives numbered-list merge (pain_points+outcomes semantics) · categorized tech stack (needs TB data change).
- TB request-model fix (make `tech_stack` optional TB-side) — non-blocking, noted in #1899.

## Related
- [[Case studies per-card management (US 23613)]] · [[WeasyPrint 62 to 68 upgrade (US 23479)]] · [[Industry-agnostic Echo (PRD 398aedca)]]
