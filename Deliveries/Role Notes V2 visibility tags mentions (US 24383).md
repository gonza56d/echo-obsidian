---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, roles, notes, mentions, visibility, rls]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2113"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24383"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24384"
prd: ""
---

# Role Notes V2 — visibility, tags, mentions (US 24383)

Pato's PR [#2113](https://github.com/taller-projects/echo-backend/pull/2113) adds `app/modules/role/note/` (dedicated `role_note` + `role_note_mention` tables): internal/external visibility, JSONB tags with autocomplete, mentions, soft delete, creator-only mutation. I took over the review-fix round (2026-08-20): shipped the missing migrations + full test suite and fixed all 7 review blockers (IDOR, no-op visibility, dead permission, N+1, tags path, mention validation).

## Azure / docs
- [US 24383](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24383) (Pato, "Being defined") — BE implementation
- [US 24384](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24384) — FE migration from embedded JSONB to API-driven
- PRD: Chiron Eidetic plan (https://chiron.taller.ai/projects/yCFJ68zsAXhh3wIbxJlt/plan/view)

## PRs
- [#2113](https://github.com/taller-projects/echo-backend/pull/2113) → dev — OPEN. Pato's base (`4205fd33`, `ac9d5523`) + my review-fix commits `0c2c3866` (blockers, migrations, tests), `e13ccd3f` (vendor-mention rule), and `28929264` (round-2 fixes, 2026-08-20).

## Round-2 review fixes (`28929264`)
- **B1 atomic mentions**: `mention_user_ids` deduped via schema `field_validator` (dupes 500'd on the mention PK); `create()` uses `repo.save(commit=False)` → add mentions → `repo.commit()` so note+mentions are one transaction.
- **B2 visibility flip**: PATCH → internal with omitted `mention_user_ids` now 400s if the note holds vendor mentions (only incoming ids were checked); clearing them in the same PATCH is legal.
- **B3 tag leak**: `get_tags` is viewer-aware (`viewer_is_vendor` → external-only) — vendors could enumerate internal-note tags.
- **Nits**: POST resolves parent role first (`ensure_role_exists` → 404; was 400 w/ raw pg constraint detail leaking tenant UUID); mentionable-users 404s unknown/foreign roles; response slimmed to application's `MentionableUserResponse` + `load_only` covers `full_name` (killed per-row deferred SELECT); `filter_vendor_ids` moved to `UserService`/`UserRepository`; backfill `created_at` via exception-safe `pg_temp.try_timestamptz` (malformed ts → now(), no migration abort); mentionable-users declared before `/{note_id}`; `TimestampOrmBaseModel`; TYPE_CHECKING `User` import; ~11 new tests.

## How
- **Visibility (B3 fix)**: the PR's org filter was a functional no-op (`User.organization_id` is a `column_property` == `Tenant.organization_id`, so every tenant user shares one org). Re-modeled: INTERNAL notes hidden from vendor users (`User.vendor_id IS NOT NULL`); vendors can't set internal visibility; internal notes can't mention vendor users. `organization_id` stays denormalized on the row for future multi-org scoping.
- **Override (B4 fix)**: reverted the unseeded `Permission.NotesManage` (dead code — not in templates or any tenant's `available_permissions`) to the ticket's `UserRole.ADMIN` check in the service.
- **IDOR (B2 fix)**: `repo.get_for_role(note_id, role_id)` — mutations resolve the note with a role predicate, 404 on mismatch; soft-deleted → 404 (unreachable `is_deleted` branch removed).
- **N+1 (B6 fix)**: list passes `response_model=RoleNoteResponse` → schema-driven planner eager-loads `created_by`/`updated_by`/`mentions.user`.
- **Migrations**: `mri8yyq9eo8u` (tables + indexes + composite FK `(role_id, tenant_id)` + RLS enable + FOR ALL policy via parent role — FOR ALL not FOR SELECT, per the `application_comment` `dvmw0w899yrl` lesson) and `6qxl59edvobq` (backfill from legacy `role.notes` JSONB: `[{id, content, section, created_at, creator_name}]` → `section`→tag, `creator_name` matched to user full name (NULL when ambiguous/absent, e.g. "Echo"), external visibility, invalid ids regenerated).
- **Nullable authorship**: `created_by_id`/`updated_by_id` nullable (`SET NULL` FKs) because legacy notes carry only a display name; authorless notes are mutable only by ADMIN.
- **Tests**: `tests/unit/test_role_notes.py` (29 router tests: visibility, ADMIN override, soft delete, IDOR 404s, tags, mentions incl. cross-tenant + vendor-mention rejection, mentionable users, cross-tenant isolation) + `tests/unit/test_role_note_migration.py` (executes both real migrations: schema, RLS policy, backfill assertions, downgrades — alembic.op-binding pattern from `test_group_hierarchy_migration.py`).

## Decisions
- **Internal = hidden from vendor users** — Gonzalo's call (AskUserQuestion 2026-08-20) after confirming the org filter can never distinguish anything within a tenant. Ticket text says "misma org", which is the no-op; ticket wording should eventually be updated.
- **`UserRole.ADMIN` override** (ticket's design) over seeding a permission — no template/tenant/FE mirror work needed.
- **Canonical tags path `GET /roles/{role_id}/note-tags`** (ticket's path; separate `tags_router` mounted beside `/notes`). FE #24384 must use this one.
- Q4 (DisableRLS on mentionable-users) kept — matches the application comments precedent, hand-rolled tenant filter in the query.

## Gotchas
- **`source scripts/venv.sh` exports `.env` → `ENABLE_ACCESS_CONTROL=True` leaks into pytest** (conftest uses `environ.setdefault`), and then EVERY `Protected` route 404s ("Not Found.") — looks exactly like broken routing. Run `uv run pytest` without sourcing venv.sh. Cost ~40 min of debugging lazy `_IncludedRouter` internals.
- Azure work items live under org **TallerInternTools** (`dev.azure.com/TallerInternTools`), NOT `tallertechnologies` — the PAT is fine; wrong org 401s.
- Default `mocked_user` conftest fixture is a **vendor** user (`vendor_id=mocked_vendor.id`) — vendor-visibility tests need a module-level non-vendor override.
- FastAPI build resolves included routers lazily at request time (`_IncludedRouter.effective_candidates`); `app.routes` top-level path introspection is useless — use `/openapi.json`.

## Pending
- CI + Pedro/Gonzalo re-review → merge to dev.
- ~~Prod pre-flight queries~~ **DONE 2026-08-20**: NULL `tenant.organization_id` = 0 in prod/qa/dev; duplicate legacy note ids = none in prod/qa, 1 in dev (Pato's identical "TEst" note copied onto 2 roles — `ON CONFLICT` skip is harmless). 805 prod / 2 qa / 612 dev legacy notes, zero malformed timestamps or empty content anywhere. Migration is data-safe in all envs.
- Open design Q: vendor author of a note later flipped internal by ADMIN can still PATCH it (author trumps visibility on mutation) — confirm intended.
- Open design Q: mentionable-users pick-list is not visibility-aware (vendor appears, 400 only at submit) — FE US 24384 may want a `visibility` param.
- Ticket 24383 wording: "misma org" → vendor-based semantics; move state from "Being defined".
- FE US 24384: consume `/roles/{role_id}/note-tags`, JSONB→API migration; no `accessControl.ts` change needed anymore (notes_manage dropped).
- `role.notes` JSONB column drop — separate step after FE migrates.
- qa/main promotion after dev QA; kforce twin not evaluated (module is Taller-shaped: tenant_id, RLS).

## Related
- [[Map - Observability & Reliability]]
