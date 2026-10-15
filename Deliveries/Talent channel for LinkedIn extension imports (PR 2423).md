---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, talent, access-control, vendor, visibility, migration]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2423"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25504"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25510"
prd: "https://claude.ai/code/artifact/34631c54-12ea-4b80-8690-6db066703db9"
---

# Talent channel for LinkedIn extension imports (PR 2423)

`talent.source` held two facts: who is credited (a vendor — vendor-scope RLS and reporting key on it) and, for Chrome-extension imports only, how the candidate arrived (`LinkedIn`). After [[External vendors see all LinkedIn candidates via channel source (Bug 25504)]] two things were left: an external vendor-scope recruiter importing from the extension got a 403, and on prod Taller the `(Taller Recruitment, LinkedIn)` link made `LinkedIn` an external source, gating every extension import behind `recruitment.edit_source`. This delivery adds `talent.channel` and credits LinkedIn imports to the creator's vendor at intake — backend only, no extension release, no FE change. Branch `feat/talent_channel` (no ticket yet), worktree `.claude/worktrees/talent_channel`.

## Azure / docs
- PRD (Claude Doc, team-reviewed 2026-10-15, Tier B, all tenants, no flag): [PRD: Talent channel (LinkedIn extension)](https://claude.ai/code/artifact/34631c54-12ea-4b80-8690-6db066703db9)
- Lineage: [Bug 25504](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25504) / [#2414](https://github.com/taller-projects/echo-backend/pull/2414). Follow-up [Task 25510](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25510) (vendor channel-source guard) is NOT in this PR.
- **No Feature / US created yet** — the PRD proposes: Bug "Accreditation to Taller Recruitment broken by trailing space in vendor name" (M0 + schema strip), Feature "Talent channel" + backend US (M1), optional extension-cleanup Task.

## PRs
- [#2423](https://github.com/taller-projects/echo-backend/pull/2423) → dev — **OPEN** 2026-10-15, commit `97e8bfa1`, assignee gonza56d. Local: full unit + multitenancy green (4551 + 1793 + 37 in two runs after one expected test update), `tests/system/test_talent_set_source.py` 12 green.
- FE contract: additive only — `channel` (`"linkedin" | null`) on talent detail + list responses, accepted on `POST /talents` / `/sync` (422 on unknown), filters `channel` / `channel__in` / `channel__isnull`. No FE PR.

## How
- `TalentChannel(StrEnum)` (`linkedin`) in `app/modules/talent/schemas.py`; column `talent.channel` = native enum `talent_channel_enum` mapped like `process_status`, partial index `ix_talent_tenant_channel (tenant_id, channel) WHERE channel IS NOT NULL`. On `TalentCreate`, `TalentResponseBase`, `TalentListBase` — never on `TalentBase` (`TalentUpdate` is `@partial_model` over it), so PATCH ignores it (test pinned).
- `TalentService.classify_intake(talent_create, user)` — called by `POST /talents` and `POST /talents/{role}/sync` **before** `writes_attribution`: infer `channel=linkedin` from `source=LinkedIn` (any spelling, `is_linkedin_source`) or explicit `channel`; if the creator has a vendor and the source is absent/LinkedIn → `source = user.vendor_name.strip()`; no vendor → `LinkedIn` stays. `_infer_channel` also runs inside `create_talent`, so `/internal/talents`, user-bound keys and any direct caller get the channel (source as sent). `logger.info("classify_intake: LinkedIn import", created_by_id, vendor_id, re_credited, source)`.
- `LINKEDIN_SOURCE` + `is_linkedin_source` in `app/modules/talent/source/constants.py`; `CHANNEL_SOURCES` unchanged.
- Outbox `build_talent_payload` gains `channel` (talent.created / talent.updated).
- Migration `5nnel6f7gwfi` (`2026_10_15_1200-5nnel6f7gwfi_add_talent_channel.py`): enum `checkfirst` + `add_column if_not_exists` + index `if_not_exists`; backfill `channel` by `lower(unaccent(source)) = 'linkedin'`; re-credit LinkedIn talents whose creator has a vendor to the tenant row named `btrim(vendor.name)` (get-or-create + `vendor_sources` link, `talent_change_history` row with `changed_by_id` NULL, `application.source_id` moved where the snapshot was the old LinkedIn row); delete every `(external vendor, LinkedIn)` link (Referral links kept). Downgrade structural only. Run end-to-end in `tests/unit/test_migration_talent_channel.py` through alembic's `Operations` context (precedent: `test_migration_last_interaction_index.py`).
- Whitespace: `VendorBase(BaseModel, str_strip_whitespace=True)` (covers `VendorCreate`/`VendorUpdate`), `classify_intake` strips the stamped name, `canonical_source_id_for_vendor` wraps the vendor name in `btrim` (belt — the PRD called it optional).
- Tests: `tests/unit/test_talent_channel.py` (16 route-level cases), RLS probe case in `test_talent_rls_policies.py` (external vendor-scope + extension payload → INSERT accepted once classified), snapshot case with a trailing-space vendor name in `test_application_source_recruiter_override.py`, `TalentFactory.channel = None` pinned (polyfactory randomizes enums).

## Decisions
- `channel` on `TalentResponseBase` + `TalentListBase` (every view, including restricted): the PRD said "TalentResponseBase, recruitment list"; the channel reveals nothing attribution-sensitive, so it is not gated like `source`. Flagged in the PR.
- Inference universal (internal API, public API, direct callers); re-credit JWT paths only — per the PRD.
- `btrim` belt in `canonical_source_id_for_vendor` included (cheap, makes the snapshot test meaningful).
- Enum guard = `sa.Enum(...).create(checkfirst=True)` (precedent `eenjg7rqq0s8`), not a `pg_type` lookup as the PRD text said.
- Log line lives in `classify_intake` (decision point, no talent id yet) with `created_by_id` / `vendor_id` / `re_credited` instead of the PRD's `talent_id`.

## Gotchas
- `tests/unit/test_referral_source_validation.py::test_post_with_channel_source_by_external_recruiter_does_not_link_vendor` asserted `source_id == LinkedIn row` for an external recruiter — renamed to `..._never_links_the_channel` and now asserts the credit to the agency's own row + no LinkedIn link.
- In a shared module tenant, a test that links the LinkedIn row to an external vendor turns `LinkedIn` into an attribution source for every later test (404 without `edit_source`). `test_talent_channel.py` has an autouse fixture that deletes `(external, LinkedIn)` links after each test; `_source()` there is get-or-create because `(tenant_id, source)` is unique.
- `uv run` inside a worktree creates a second `.venv` there (163 packages) — use `/Users/gonza56d/taller/repos/echo-backend/.venv/bin/python -m pytest` and `.venv/bin/ruff` directly; the worktree guard refuses `source …` lines.
- fastapi-filter list params are comma-separated (`id__in=a,b`), not repeated keys.
- Downgrade + upgrade leaves re-credited talents without a channel (source is the vendor now) — documented in the revision docstring; history rows are the trail.

## Pending
- [ ] Review + merge [#2423](https://github.com/taller-projects/echo-backend/pull/2423) (pipeline: dev + kforce-dev auto-deploy; migration is a no-op on KForce).
- [ ] **M0 prod data fix, before the prod release**: `UPDATE vendor SET name = btrim(name)` for `Taller Recruitment ` from the terminal (`PGSERVICE=echo-prod`); tell Guadalupe the manual `PATCH /applications/{id}/source` is no longer needed. Not verified from this session.
- [ ] Azure tickets (Bug whitespace / Feature + US talent channel / optional extension Task) — create and link the PR (`GitHub Pull Request` relation) once they exist.
- [ ] Product sign-off on the Taller `by_source` change (historical LinkedIn imports now count for `Taller` / `Taller Recruitment`) before `main`.
- [ ] Post-release verification: `GET /talents?channel=linkedin`, no `(external, LinkedIn)` `vendor_sources` row, `classify_intake` lines in Loki.
- [ ] Open product question: referred candidates worked by `Taller Recruitment` — `Referral` or `Taller Recruitment`?
- [ ] Later: `self_applied` enum value (`ADD VALUE IF NOT EXISTS` inside `op.get_context().autocommit_block()`); optional extension cleanup (send `channel`, drop the `LinkedIn` stamp).

## Related
- [[External vendors see all LinkedIn candidates via channel source (Bug 25504)]] · [[Referral Attribution M1 permission+gating (US 24996)]] · [[Role sync overwrites Referral source (Bug 25028)]]
