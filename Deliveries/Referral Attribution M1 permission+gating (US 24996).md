---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, talent, application, access-control, referral-attribution]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2289"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24996"
prd: "https://app.notion.com/p/3deaedca11f081b39e81c49c7ffb2ce3"
---

# Referral Attribution M1 — edit_source permission + gating (US 24996)

First of 5 stacked milestones of the Referral Attribution feature (record who referred a candidate, at intake or by editing the source). M1 creates the dedicated permission `recruitment.edit_source` and moves every source/referrer write behind it: new `PATCH /talents/{id}/source` contract, gate swap on `PATCH /applications/{id}/source`, and field-level gating on the generic talent PATCH.

## Azure / docs
- [US 24996](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24996) — In revision. One US per milestone (M2–M5 tickets created when each starts).
- PRD: [PRD Técnico — Referral Attribution](https://app.notion.com/p/3deaedca11f081b39e81c49c7ffb2ce3) · business: [Referral Attribution (set at intake or by editing the source)](https://app.notion.com/p/3deaedca11f0812cb3d6eb0ae5f34f39) + Dami's [Editable Candidate Source & Referral Attribution](https://app.notion.com/p/3deaedca11f081e2a32dcae3ef1e28f3)

## PRs
- [#2289](https://github.com/taller-projects/echo-backend/pull/2289) → dev — OPEN 2026-09-17. Branch `24996/referral-attribution-m1-permission-gating`. M2–M5 will stack on it (each PR notes the previous must merge first).

## How
- `Permission.EditSource = "recruitment.edit_source"` in `app/user/schemas.py`, wired into `TenantModuleConfig.RECRUITING` (NOT ADMIN_PERMISSIONS) → appears in available-permissions for recruiting tenants.
- New `PATCH /talents/{talent_id}/source` (`Protected(EditSource)`, 202 empty): `TalentSourceUpdate {source?, referred_by?}` merge semantics; `source: null` clears; `TalentService.update_source` — get-or-create source (exact match, insensitive matching = M2), writes `talent.referral`, outbox TALENT_UPDATED, `source_transferred` structlog (no referrer PII, only `referral_changed` bool). Idempotent no-op skips outbox+log.
- `PATCH /applications/{id}/source`: gate `ManageOwnership` → `EditSource`. Migration `vq3rk8ne5t7d` backfills `edit_source` onto roles holding `manage_ownership` (idempotent, downgrade strips it from all roles).
- Generic `PATCH /talents/{id}`: payload containing `source`/`referral` → 404 without the permission (mirrors Protected); with it, still writable.
- `_is_edit_permission` in `app/modules/super_admin/templates.py`: added `.edit_source` suffix so auto-generated Viewer templates exclude it.

## Decisions
- **Gate swap + backfill** (user picked over OR/PermissionSet and replace-only): satisfies PRD criterion "sin edit_source ⇒ 404" with zero regression.
- Permission lives in RECRUITING module per PRD ⇒ **new tenants' Member/Full Access system roles get it by default** (Viewer excluded); existing tenants only via backfill (admins) or manual assignment. Flagged in PR for product sign-off.
- New endpoint returns 202 empty (repo convention for transfer endpoints) instead of the PRD sketch's 200+view — the endpoint the PRD referenced also returns 202 empty.
- POST /talents create-path gating + Referral⇒referred_by 422 validation deferred to M2 (matches milestone checkboxes; avoids breaking intake before FE pairs).

## Gotchas
- The suffix heuristic `EDIT_PERMISSION_SUFFIXES` silently classifies any `x.edit_y` permission as read-only for Viewer templates — check it whenever adding a permission whose verb is a prefix, not a suffix.
- Full unit suite caught exactly one regression: `test_recruiting_viewer_specific_permissions` (exact-set assertion on Viewer).
- FE does NOT consume `PATCH /applications/{id}/source` today (checked echo-frontend) — gate swap has no FE regression, but `ACCESS_LEVELS` mirror of `recruitment.edit_source` is needed in the paired FE PR.

## Pending
- PR [#2289](https://github.com/taller-projects/echo-backend/pull/2289) review + merge.
- M2 (Referral source + 422 validation + insensitive get-or-create), M3 (conflict rules + cascade + ownership exception + RLS decision A/B), M4 (`GET /talents/referrers`), M5 (audit trail tables + read endpoints) — stacked.
- FE paired PR (ACCESS_LEVELS mirror, toggle in Add Candidates, read-only states).
- PRD open questions before M3: RLS Camino A/B; guard existing vs new conflict rule; keep-vs-clear referrer; ATS precedence.
- qa/main promotion at feature level (after all milestones).

## Related
- [[Map - Kforce]] (shared schema — talent_source per-tenant)
