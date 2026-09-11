---
type: delivery
status: delivered
env: taller
delivered: 2026-09-11
tags: [feature, emails, notifications, design-system]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2253"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24886"
prd: ""
---

# Shared email shell for all app emails (US 24886)

Every HTML email Echo sends now extends one Jinja shell (`email_shell.jinja`) carrying the Echo newsletter design that Email Notifications shipped in [#2236](https://github.com/taller-projects/echo-backend/pull/2236): logo, optional eyebrow, H1, body, optional pill CTA + secondary teal link, "— The Echo Team", footer with the reason for the email. Welcome, interview scheduled/cancelled and commitment change lose their drifted per-template styling (legacy blue `#1a73e8`, own `<style>` blocks, "Allocation Team." signature). PRD is a Claude artifact (Pedro), not Notion: https://claude.ai/code/artifact/beb16aa6-2ad9-4432-89c2-9175146854ce

## Azure / docs
- [US 24886](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24886) — parent [Epic 23131](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23131) (UI Redesign), related [US 24550](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24550) (Email Notifications, the design source).

## PRs
- [#2253](https://github.com/taller-projects/echo-backend/pull/2253) → dev — MERGED 2026-09-11 (squash, `53b80fb7`). No FE impact (emails only).
- Review r1 (2026-09-11, /pr-review, full mode): **0 blockers**, verdict ready-with-nits gated on Design/Product sign-off. Nits fixed in `685cddb6`: shell macros `paragraph`/`cta_button`/`footer_link` dedupe brand tokens out of child templates (all 6 renders verified **byte-identical** before/after); escaped-form `&lt;script&gt;` assertions on every XSS test; “Manage your notification preferences” absence asserted on non-preference emails; `support_message` + `more_count=0` branches covered; `echo_logo_url()` base pinned to `FRONTEND_URL`; ticketless TODO dropped in `_send_commitment_emails`. Review QUESTIONS routed to the design review: Manage-interview button→link demotion, ALLOCATION/INTERVIEW eyebrow labels, welcome copy drops (© year line, “Enjoy your experience!”) — noted on the US.
- Leo APPROVED (review 5181186866, 0 blockers). His nits 1–3 fixed in `473f41e5`: AC2 golden snapshot test for single/list (fixtures `tests/unit/email_golden/`, regen `SAVE_GOLDEN=true`; guard verified to fail on perturbation), XSS payloads on role_title / list item.title+eyebrow / commitment subject, empty `items=[]` render. Nit 4 (mail_renderer home) deferred until a third non-notification consumer; nit 5 (PII in logs) filed as [Task 24891](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24891).

## How
- `app/modules/notification/mail_renderer.py`: single Jinja env (`autoescape=True`) + `echo_logo_url()` — the only places email rendering config lives. Consumed by `notification/service.py`, `notification_email_scheduler_service.py`, `welcome_email_service.py`.
- `email_shell.jinja` extracted from `notification_email_single.jinja`; the 6 templates are now thin `{% extends %}` children (blocks: title/body/cta/footer/cell_style; eyebrow via child-level `{% set %}`). Brand tokens live in the shell chrome + macros (`paragraph` via `{% call %}`, `cta_button`, `footer_link`) — parent-defined macros are directly visible in child blocks, no import needed.
- #1/#2 (notification single/list) re-platformed with a verified whitespace-normalized-identical render (before/after script) — the reference did not change visually.
- Commitment email: `from_name` "Allocation" → "Echo", signature → "— The Echo Team".
- Render tests in `tests/unit/test_email_shell.py` incl. a repo-guard test: every template extends the shell, no `<style`, no `#1a73e8` in any template source.

## Decisions
- Eyebrows on transactionals (WELCOME none, INTERVIEW, ALLOCATION) and footer reason copy implemented as the PRD proposes — flagged in the PR as pending Product/Design sign-off (PRD open questions). One-line reverts if rejected.
- Support line (`echosupport@tallertechnologies.com`) added to all transactional footers (per PRD mock), inlined per template rather than a partial.
- Interview scheduled: two old blue buttons → 1 pill CTA (Evaluate Candidate) + secondary teal link (Manage interview), per PRD contract; redundant "use the link below" helper paragraphs dropped.
- Tenant customization audit: `tenant_email_config`/`tenant_email_domain` (from_name + sending domains; rows for Manpower/GoToTravel/Taller in dev) feed ONLY bulk candidate outreach (#7, stays plain text). No DB-driven templates for transactional emails; `cv_template`/`proposal_template` are PDF-only.

## Gotchas
- Three Jinja envs used to load the same folder and only the sweep's escaped — commitment/interview rendered vendor/role names unescaped (fixed by the single env). Autoescape turns `'` into `&#39;` in HTML: harmless visually, but exact-substring assertions on rendered content can break.
- `tests/unit/test_interview_scheduled_email.py` fixtures imported `TEMPLATES_FOLDER` from the service (removed) — the `__new__`-fixture trap again; they now use `mail_template_env`.
- The shell's Jinja comment can't contain literal `<style>`/`#1a73e8` — the guard test scans template SOURCE including comments.
- Interview emails still hardcode ART timezone — explicitly out of scope, needs its own ticket (PRD open question, unfiled).
- Pre-existing (review finding, Leo confirmed + welcome `to_email`): email send paths log recipient addresses (PII) vs domain-only policy in `sendgrid_service.py` — FILED as Task 24891.

## Pending
- ~~Team review / merge~~ Leo approved; MERGED 2026-09-11 (`53b80fb7`); US 24886 CLOSED.
- Design review (Paloma/Damián) of the 7 rendered variants; Product OK (Florencia) on from_name "Echo" + footer reason copy + eyebrows.
- Manual QA cross-client (Gmail web, Outlook web/desktop, mobile) — QA emails sent to Gonza's inbox 2026-09-11 from dev SendGrid.
- File the interview-emails timezone ticket (hardcoded `America/Argentina/Buenos_Aires`).
- qa/main promotion after dev verification.

## Related
- [[Map - Observability & Reliability]] · Email Notifications (US 24550, no note — pre-dates none; backfill if touched again)
