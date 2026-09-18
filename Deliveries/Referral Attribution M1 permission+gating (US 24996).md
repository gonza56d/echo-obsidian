---
type: delivery
status: merged
env: both
delivered:
tags: [feature, talent, application, access-control, referral-attribution]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2289"
  - "https://github.com/taller-projects/echo-backend/pull/2290"
  - "https://github.com/taller-projects/echo-backend/pull/2291"
  - "https://github.com/taller-projects/echo-backend/pull/2292"
  - "https://github.com/taller-projects/echo-backend/pull/2293"
  - "https://github.com/taller-projects/echo-backend/pull/2295"
  - "https://github.com/taller-projects/echo-backend/pull/2296"
  - "https://github.com/taller-projects/echo-backend/pull/2297"
  - "https://github.com/taller-projects/echo-backend/pull/2301"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24996"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24999"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25000"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25001"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25002"
prd: "https://app.notion.com/p/3deaedca11f081b39e81c49c7ffb2ce3"
---

# Referral Attribution M1 — edit_source permission + gating (US 24996)

First of 5 stacked milestones of the Referral Attribution feature (record who referred a candidate, at intake or by editing the source). M1 creates the dedicated permission `recruitment.edit_source` and moves every source/referrer write behind it: new `PATCH /talents/{id}/source` contract, gate swap on `PATCH /applications/{id}/source`, and field-level gating on the generic talent PATCH.

## Azure / docs
- [US 24996](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24996) — M1, In revision.
- [US 24999](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24999) — M2, In revision.
- [US 25000](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25000) — M3, In revision.
- [US 25001](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25001) — M4, In revision.
- [US 25002](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25002) — M5, In revision.
- PRD: [PRD Técnico — Referral Attribution](https://app.notion.com/p/3deaedca11f081b39e81c49c7ffb2ce3) · business: [Referral Attribution (set at intake or by editing the source)](https://app.notion.com/p/3deaedca11f0812cb3d6eb0ae5f34f39) + Dami's [Editable Candidate Source & Referral Attribution](https://app.notion.com/p/3deaedca11f081e2a32dcae3ef1e28f3)

## PRs
- M1 [#2289](https://github.com/taller-projects/echo-backend/pull/2289) → dev — MERGED 2026-09-17 (`8ee501cb`).
- M2 [#2290](https://github.com/taller-projects/echo-backend/pull/2290) → dev — MERGED 2026-09-17 (`169a78f2`).
- M3 [#2291](https://github.com/taller-projects/echo-backend/pull/2291) → dev — MERGED 2026-09-17 (`79fc6af1`).
- M4 [#2292](https://github.com/taller-projects/echo-backend/pull/2292) → dev — MERGED 2026-09-17 (`37c712ab`).
- M5 [#2293](https://github.com/taller-projects/echo-backend/pull/2293) → dev — MERGED 2026-09-17 (`dcc77a93`).
- Chain fix [#2295](https://github.com/taller-projects/echo-backend/pull/2295) → dev — MERGED 2026-09-17 (alembic chain repair after the stack landed).
- **Promotion [#2296](https://github.com/taller-projects/echo-backend/pull/2296) dev → qa — OPEN 2026-09-18.** Riders: #2287 (chat bubble_id backfill), #2294 (gitignore).
- **Promotion [#2297](https://github.com/taller-projects/echo-backend/pull/2297) dev → main — OPEN 2026-09-18** (qa == main at open time; prod deploy behind Azure Environment approvals). Same content + riders as #2296.

## How
- `Permission.EditSource = "recruitment.edit_source"` in `app/user/schemas.py`, wired into `TenantModuleConfig.RECRUITING` (NOT ADMIN_PERMISSIONS) → appears in available-permissions for recruiting tenants.
- New `PATCH /talents/{talent_id}/source` (`Protected(EditSource)`, 202 empty): `TalentSourceUpdate {source?, referred_by?}` merge semantics; `source: null` clears; `TalentService.update_source` — get-or-create source (exact match, insensitive matching = M2), writes `talent.referral`, outbox TALENT_UPDATED, `source_transferred` structlog (no referrer PII, only `referral_changed` bool). Idempotent no-op skips outbox+log.
- `PATCH /applications/{id}/source`: gate `ManageOwnership` → `EditSource`. Migration `vq3rk8ne5t7d` backfills `edit_source` onto roles holding `manage_ownership` (idempotent, downgrade strips it from all roles).
- Generic `PATCH /talents/{id}`: payload containing `source`/`referral` → 404 without the permission (mirrors Protected); with it, still writable.
- `_is_edit_permission` in `app/modules/super_admin/templates.py`: added `.edit_source` suffix so auto-generated Viewer templates exclude it.

### M2 (Referral source + validation)
- Insensitive `lower(unaccent())` get-or-create in the 3 source-resolution paths: `TalentSourceRepository.get_by_name`, `Talent.get_source`, `set_source` before-insert hook. Oldest row wins. No new migration (unaccent installed by `54f5e7260319`; test conftest creates it).
- `canonical_source_name`: Referral rows always stored as `Referral` regardless of first-write casing — otherwise the exact-match `talent_source__source=Referral` filter misses (caught by the multitenancy test).
- 422 `referral_requires_referred_by`: `TalentCreateRequest` (public POST only), `TalentSourceUpdate` validator + post-merge invariant in `update_source` and `update()` (public `TalentUpdate` only — `TalentUpdateInternal` exempt so Jazz/internal keep their contract). Leaving Referral KEEPS the referrer (PRD proposed default).
- POST /talents gating: FE sends `source: authUser.vendor.name` on every create (AddCandidate.tsx:89) — so only attribution-CHANGING writes are gated (referrer present, or source ≠ own vendor_name → 404 without permission).

### M3 (conflict + cascade + ownership + RLS Camino A)
- Conflict: source change away from an EXTERNAL-vendor source blocked (400 `external_source_active_process`) while an app in category active sits on a role whose step stage = Open. `referral_conflict_blocked` structlog event. Decisions (user): Camino A + new-rule-only (legacy 2-business-day blocker stays sync-only).
- Ownership exception: `owner_id` on TalentSourceUpdate accepted ONLY when from-source external + no active process + new source Referral → reuses `transfer_owner` (member assert + jazz lockstep). Else 422 `owner_assignment_outside_referral_exception` before any write.
- Cascade: on marking Referral, active non-external apps get the Referral source via `ApplicationService.transfer_source` per app (validation + logs). External/inactive apps keep theirs.
- Camino A: `VendorRepository.link_source_to_internal_vendors` (pg INSERT ON CONFLICT DO NOTHING) ensured on every referral marking + intake; `external_source_ids` defines "external source". RLS verified at data level (testcontainers don't enforce RLS).
- App endpoint: PATCH /applications/{id}/source to a Referral source 422s unless the talent carries a referrer.

### M4 (referrer suggestions + canonical referrer)
- `GET /talents/referrers?search=`: Page[str] DISTINCT over talent.referral, `lower(unaccent())` LIKE both sides, ordered; same pattern as /talents/skills. Registered BEFORE `/{talent_id}` (UUID route would swallow it → 422).
- `TalentRepository.find_canonical_referrer` (oldest talent wins) applied on dedicated PATCH + public intake (`TalentCreateInternal` exempt). Variant of own value = no-op; new names stored as typed.

### M5 (audit trail)
- Tables `talent_change_history` + `application_change_history` (migration `nq8ke2vwt5rz`): JSONB old/new, changed_by SET NULL, composite (parent, tenant) FK CASCADE, RLS "Allow access via parent" in the SAME revision. Verified upgrade/downgrade + policies on throwaway PG.
- Writers: dedicated PATCH ({source, referred_by} snapshot), generic public PATCH (router passes changed_by; TalentUpdateInternal exempt), ApplicationService.transfer_source ({source} by name; covers cascade) + NEW no-op guard on transfer_source (same source_id → no write/history/log).
- Read: GET /talents/{id}/change-history + GET /applications/{id}/change-history — Page, Protected(Talents), 404 via parent visibility (not empty page).

## Decisions
- **Gate swap + backfill** (user picked over OR/PermissionSet and replace-only): satisfies PRD criterion "sin edit_source ⇒ 404" with zero regression.
- Permission lives in RECRUITING module per PRD ⇒ **new tenants' Member/Full Access system roles get it by default** (Viewer excluded); existing tenants only via backfill (admins) or manual assignment. Flagged in PR for product sign-off.
- New endpoint returns 202 empty (repo convention for transfer endpoints) instead of the PRD sketch's 200+view — the endpoint the PRD referenced also returns 202 empty.
- POST /talents create-path gating + Referral⇒referred_by 422 validation deferred to M2 (matches milestone checkboxes; avoids breaking intake before FE pairs).

## Gotchas
- The suffix heuristic `EDIT_PERMISSION_SUFFIXES` silently classifies any `x.edit_y` permission as read-only for Viewer templates — check it whenever adding a permission whose verb is a prefix, not a suffix.
- Full unit suite caught exactly one regression: `test_recruiting_viewer_specific_permissions` (exact-set assertion on Viewer).
- FE does NOT consume `PATCH /applications/{id}/source` today (checked echo-frontend) — gate swap has no FE regression, but `ACCESS_LEVELS` mirror of `recruitment.edit_source` is needed in the paired FE PR.

- `TalentService` positional construction in `tests/unit/test_interviews.py` (`TalentService(*[None]*17)`) breaks every time the service gains a collaborator — bumped to 18 for `talent_source_service` (the known `__new__`/positional fixture trap).
- Canonical casing of a source row = first write, EXCEPT Referral (pinned). The Source filter is exact-match; any future "special" source value needs the same pinning.

## Pending
- Merge promotions [#2296](https://github.com/taller-projects/echo-backend/pull/2296) (qa) and [#2297](https://github.com/taller-projects/echo-backend/pull/2297) (main) — **merge commit, never squash**; prod/kforce-prod deploy needs the Azure Environment approvals.
- kforce-prod Referral case-variant spot-check (optional, low risk): dev=1 canonical, kforce-dev=0, **prod=0 (verified read-only 2026-09-18)**; kforce-prod has no local creds — check via Supabase `hslptkvpsrawnrouwkhc` if wanted.
- FE paired work = [US 24993](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24993) (Melina) — description + AC filled 2026-09-18 with full BE contract (8-point scope). Parent [US 24973](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24973) (title typo'd "referrral" — searches miss it).
- Feature-level QA (PRD: 6–8h, two tenants, four profiles) — **must use a non-system_admin user** (system_admin bypasses all permission gates by design). Bruno folder `Referral Attribution (24996)` in ~/taller/Echo has the 25-step flow.
- PRD changelog + close open questions (Camino A, new-rule-only, keep-referrer, 202-empty — all implemented; ATS precedence documented as proposed).

## Post-merge verification + promotion (2026-09-18)
- Deep post-deploy testing on dev + kforce-dev DBs: all 3 migrations at head, audit tables + RLS + composite FKs correct, backfill gap 0, canonical Referral row intact, audit tables start empty, unaccent present. Suite 4983 passed (5 fails = known flaky adoption tests).
- Live HTTP QA (25 checks, dev API + local run with RLS role `echo_backend`): full matrix green — 422/400 error codes, canonicalization both fields, cascade active-only, ownership exception (invalid owner = zero partial writes), no-op writes nothing (history + outbox exact), closed-app editable, filter + suggestions accent-insensitive.
- **Gating verified for real** via temporary user-row swap (role=member + permission-less access_role, then reverted): all gated writes 404 on BOTH local and deployed dev; member + edit_source → 202. Key lesson: `role=system_admin` bypasses `has_permissions` entirely (app/user/models.py:268) — earlier "dev flag off" hypothesis was WRONG; dev runs ENABLE_ACCESS_CONTROL=True.
- FE-safety audit for BE-first release: FE calls none of the new/re-gated endpoints; create sends source only as own-vendor echo (AddCandidate.tsx:89 = the carve-out); EditTalentInfoForm has no source/referral fields (talentSourceOptions schemas are dead code). BE ships dormant.
- Legacy data note: 1 dev talent (`fae8baaf`, 2024) holds Referral source + NULL referrer (pre-feature; write-path invariant unaffected).

## M2 review round 1 (2026-09-17)

Self-review of #2290 via /pr-review (3 agents: arch, PRD, tests-sec). PRD compliance 12/12. 3 blockers + nits, all fixed in `16698b34` (pushed; M1 #2289 had merged to dev `8ee501cb`, so #2290 auto-retargeted to dev):

- **BLOCKER — atomicity**: `TalentSourceRepository.get_or_create` used `save()` (commit=True) → creating a row mid-`update()` COMMITTED pending experiences/custom-fields without their outbox event when a later 422 hit; the DuplicateError race path did a FULL session rollback discarding pending state. Fix: `commit=False` mode = savepoint + raw add/flush (M1's `_resolve_source` mechanics moved into the repo layer — save()'s `handle_commit_errors` does a full rollback on IntegrityError, so the savepoint path must NOT go through save()). Both `update()` and `update_source()` pass commit=False (also kills the orphan-row-on-422).
- **BLOCKER — legacy variant rows defeat the filter**: pre-M2 `referral`/`REFERRAL` row absorbs new referred talents (oldest-row-wins) while exact-match `talent_source__source=Referral` misses them (writes succeed, reads silently fail — AC 4). Fix: migration `xj4qk9wr2vbn` (canonical = exact row else oldest; repoints talent/application/vendor_sources; merges dups; renames survivor). Verified converged + idempotent on throwaway Postgres (alembic full chain NOT runnable locally — needs Supabase `auth.users`; tested the migration in isolation via `Operations.context`). Data: dev = 1 canonical row, kforce-dev = 0, prod/kforce-prod UNVERIFIED (session read blocked) → **spot-check before promotion**.
- **BLOCKER — dead code**: `Talent.get_source` (only caller was the dropped `_resolve_source`) — deleted.
- Nits fixed: POST own-vendor gate compares via `normalize_source_name` both sides; `set_source` hook insert = `ON CONFLICT DO NOTHING` + re-read; `TalentCreateRequest` caps source/referral 255 (public only — shared `TalentRecruitmentFields` untouched so integrations keep their contract); vacuous multitenancy leak test fixed (foreign talent now on other tenant's Referral row + asserts 202); `test_interviews` → `TalentService.__new__` (needed `art_tz` set manually — `__init__` won't run).
- 9 new tests incl. both get_or_create race paths (MagicMock gotcha: `begin_nested.return_value.__exit__.return_value = False` or the mock CM swallows the IntegrityError).
- Test-order gotchas found: module-scoped tenant accumulates committed Referral rows across tests → `_clear_referral_rows` helper for tests needing the creation path / exact filter; multitenancy fixture made get-or-create for the same reason.
- FE heads-up recorded in PR: dual 422 shapes (schema-level = list detail, no error.code; service-level = `referral_requires_referred_by`); POST field `referral` vs PATCH `referred_by`.
- Local full-suite run hit `psycopg2.errors.DiskFull` (Docker VM disk full → 2806 cascade ERRORs, NOT the diff); pruned ~12GB and reran; user watches CI upstream.

## Review round 1 (2026-09-17)

Self-review via /pr-review (3 agents). 1 blocker + nits, all fixed in `bf11dec0`:

- **BLOCKER — module placement**: `manage_ownership` (old gate) is in `ADMIN_PERMISSIONS` = available to EVERY tenant; `edit_source` was RECRUITING-only, so talent-/solutioning-only tenants could never assign it → backfill stripped at the role ∩ available_permissions intersection, source edits locked out for good. Fix: added to TALENT + SOLUTIONING lists too (multi-list pattern like `email_template.create`). **Lesson: when swapping a gate, check which bucket the old permission lived in (ADMIN vs module) — availability, not just role membership.**
- `TalentSourceUpdate` hardened: `str_strip_whitespace`, min 1 / max 255 — blank source no longer creates an empty-named `TalentSource` row; clearing is null-only.
- `TalentService._resolve_source`: race-safe get-or-create (savepoint flush + re-read on unique violation), dedupes `update()` and `update_source()`. **M2's insensitive matching must build on this helper.**
- Tests: outbox write/no-op contract, blank 422s, `referred_by: null` clear, module-disabled 404, viewer exclusion asserted against `EDIT_PERMISSION_SUFFIXES` + explicit `edit_source` check (3 modules), wiring test covers 3 lists.
- Kept `referred_by` as the wire name (PRD contract); column stays `referral` — documented in PR body.
- Open question routed to M3: `update_source` bypasses `_get_source_change_blocker` (active-application guard) — M3 must decide if EditSource holders bypass it.
- Backlog (pre-existing, out of scope): `talent_source` has no RLS; `talent.source_id` FK not composite.

Suites after fixes: 4914 passed (unit + multitenancy). CI green.

## Related
- [[Map - Kforce]] (shared schema — talent_source per-tenant)


## M3 review round 1 (2026-09-17)

Self-review of #2291 via /pr-review (3 agents: arch, PRD, tests-sec). **Verdict: READY WITH NITS, zero blockers.** PRD compliance 6/6; arch 15 PASS/0 FAIL; tests-sec 10 PASS/0 FAIL. Migration-absence claim verified (composite PK `vendor_sources_pkey (vendor_id, source_id)` from `a141397e73dc` → `ON CONFLICT DO NOTHING` valid; `vendor.kind` from `2b1454dfdc70`; both predate this PR).

Two actionable nits fixed in `9697162c` (pushed):
- **[arch A9] update_source length**: extracted the prospective source/referral resolution into `_prospective_source` staticmethod — shrinks the orchestrator body.
- **[tests] missing coverage**: added `test_explicit_owner_id_null_is_ignored_not_rejected` — proves an explicit `owner_id: null` is ignored (not rejected), the `TalentSourceUpdate` docstring contract. Test file now 19 passed.

Nits deliberately NOT fixed (out of scope / follow-up):
- Foreign-ORM read coupling in `_has_active_open_application`/`_referral_cascade_targets` (reads `Application`/`Role`/`RoleStage` off `get_applications_with_roles`) — pre-existing pattern debt, all *writes* route through owning services; codebase-wide, not this PR's to fix.
- Cascade per-app commits → partial-cascade on mid-loop failure, self-heals on next marking — flagged as possible follow-up ticket if it bites at volume.

Open questions (non-blocking, surfaced by review):
- `create_talent` intake link uses `commit=True` (standalone commit) vs `update_source`'s `commit=False` — confirmed intentional (talent row already persisted at that point).
- FE milestone must consume 3 new `error.code`s (`external_source_active_process`, `owner_assignment_outside_referral_exception`, `referral_requires_referred_by`) + additive `owner_id` body field. Backend contract intact (202 + detail/error.code preserved).
- Notion Tech PRD is auth-gated — open-question resolutions (Camino A, new-rule-only) confirmed against PR body, not re-fetched from Notion.

## Prod regression fix — POST /talents attribution gate (#2301, 2026-09-18)

After M2 reached prod (2026-09-17), `POST /talents` answered **404** for any user without `recruitment.edit_source` whose payload `source` differed from their own vendor name. Prod 2026-09-18: 0 such 404s the three prior days, **13 that day across Battle Tested + Taller**. Root cause: the M2 intake gate compared `source` to `user.vendor_name` (string equality) — wrong because the Chrome extension sends `source: "LinkedIn"` on every profile, tenant-configured source names differ from the vendor name (`Taller - Recruiter` vs `Taller Recruitment`), and vendorless users (`vendor_name IS NULL`) tripped on any non-null source.

- **Fix (Pedro, `23abe8cc`)**: gate on whether the payload writes *attribution*, not on vendor-name equality. `TalentService.writes_attribution(payload)` = referrer set OR source is `Referral` OR `VendorService.is_external_source_name(source)` (case/accent-insensitive name lookup via `talent_source_repo.get_by_name`, then the existing `is_external_source`). Channel sources (LinkedIn, own vendor, tenant-internal names, brand-new names) stay open; a referrer / `Referral` / an external-vendor source still 404 without the permission. The `vendor_name` compare + the `normalize_source_name` import are gone. PATCH `/{id}/source` + generic PATCH untouched (verified they never shared the premise — bug was POST-only).
- Branch `fix/talent-intake-attribution-gate` (NOT ticketed — no US/Task in the body). PR [#2301](https://github.com/taller-projects/echo-backend/pull/2301) → dev **MERGED 2026-09-18 (squash `8fa7862d`)** — auto-deploys dev + kforce-dev on green.
- **Temporary prod unblock applied 2026-09-18** (revert after deploy): `recruitment.edit_source` added to Battle Tested's `Member` access role `aa2637f5-73e3-42a1-955b-737a01799719`.
- **Self /pr-review 2026-09-18 (full, 3-agent): READY WITH NITS, 0 blockers.** Arch 12 PASS. PRD compliance 3/5 fully (`Referral`⇒referrer 422, external=`Vendor.kind=external`, M2 404 preserved) + 2 intentionally narrowed. Tests-sec no privilege regression (new gate is strictly narrower than the old one — only channel/internal/new-name sources newly open, none are attribution).
- **Contract-text drift flagged (OUT-OF-SCOPE, non-code PRD follow-up)**: the Tech PRD's Criterio "Autorización" ("toda escritura de source/referrer responde 404") and Anexo POST ("consistente con la edición") no longer hold literally — intake now gates attribution only, while edition still gates all source writes. Amend the PRD text (or accept the intake-vs-edition asymmetry explicitly).
- Open QUESTION (non-blocking): a permissionless user can create a talent with a brand-new source name that is *later* linked to an external vendor — that intake write was never gated. Consistent with "no row ⇒ not external yet" and corrected on the fully-gated edit path; confirm product accepts.
- **My contribution — 2 completeness tests `4c3894f4`** (pushed to the PR branch, no behavior change): `test_post_with_internal_vendor_source_201_without_permission` (row linked to an INTERNAL vendor → 201; symmetric counterpart of the external-vendor 404, pins the "row exists + internal vendor" branch the no-row 201 cases never reached) + `test_post_with_external_source_of_other_tenant_201` (the external check is tenant-scoped — a source external in another tenant must not gate a create here). Full file 30 passed via main `.venv`; ruff clean.
- Pending: **revert the temp BT `Member` `edit_source` unblock after dev deploy verifies the fix**; PRD-text amendment (Autorización/Anexo); product confirm on the edge above; qa/main promotion rides the Referral Attribution promo train (#2296/#2297).
