---
type: delivery
status: merged
env: taller
delivered: 2026-10-15
tags: [feature, talent, access-control, vendor, visibility, migration]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2423"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25572"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25573"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25574"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25575"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25504"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25510"
prd: "https://claude.ai/code/artifact/34631c54-12ea-4b80-8690-6db066703db9"
---

# Talent channel for LinkedIn extension imports (PR 2423)

`talent.source` held two facts: who is credited (a vendor — vendor-scope RLS and reporting key on it) and, for Chrome-extension imports only, how the candidate arrived (`LinkedIn`). After [[External vendors see all LinkedIn candidates via channel source (Bug 25504)]] two things were left: an external vendor-scope recruiter importing from the extension got a 403, and on prod Taller the `(Taller Recruitment, LinkedIn)` link made `LinkedIn` an external source, gating every extension import behind `recruitment.edit_source`. This delivery adds `talent.channel` and credits LinkedIn imports to the creator's vendor at intake — backend only, no extension release, no FE change. Branch `feat/talent_channel` (no ticket yet), worktree `.claude/worktrees/talent_channel`.

## Azure / docs
- PRD (Claude Doc, team-reviewed 2026-10-15, Tier B, all tenants, no flag): [PRD: Talent channel (LinkedIn extension)](https://claude.ai/code/artifact/34631c54-12ea-4b80-8690-6db066703db9)
- Lineage: [Bug 25504](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25504) / [#2414](https://github.com/taller-projects/echo-backend/pull/2414). Follow-up [Task 25510](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25510) (vendor channel-source guard) is NOT in this PR.
- Azure (created 2026-10-15 after the merge, all under Sprint 45 except the Feature/Task): Feature [25572](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25572) (New; PR + commit linked) → US [25573](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25573) (**Closed** on merge, PR #2423 + commit `b70a79bc` as GitHub links, AC = the PRD contract) · Bug [25574](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25574) (**In development** until the M0 prod `btrim` UPDATE runs; related to 25504; PR linked) · Task [25575](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25575) (optional extension cleanup, unassigned, no deadline). Comments posted on Bug 25504 (supersedes its "no re-attribution" decision; Referral-403 leftover) and Task 25510 (still needed).

## PRs
- [#2423](https://github.com/taller-projects/echo-backend/pull/2423) → dev — **OPEN** 2026-10-15, commit `97e8bfa1`, assignee gonza56d. Local: full unit + multitenancy green (4551 + 1793 + 37 in two runs after one expected test update), `tests/system/test_talent_set_source.py` 12 green.
- Rubric review 2026-10-15 (`/pr-review`, full mode, PRD as the source): **no blockers**, 0 missing requirements, 0 scope creep, CI green; 14 nits + 1 informational question. Commit `d6a77e0b` (same day, pushed to the PR) closes 13 nits: new route cases (channel + partner source → 404/201 as sent, channel + own vendor, every spelling for external/no-vendor, real `/sync` update branch, `talent.updated` payload), migration `INSERT … ON CONFLICT DO NOTHING` + re-read and typed helpers, migration test with a second tenant + `RESET` of the session timeouts, RLS probe via the injector, shared `tests/act_as.py`, stripped vendor name on `/sync`. The 14th (golden `openapi` waiver) was moot — see Gotchas.
- Review r1 ([Leo](https://github.com/taller-projects/echo-backend/pull/2423#issuecomment-6199770970), 2026-10-15, CHANGES REQUESTED): one blocker — explicit `channel=linkedin`, no `source`, creator without vendor → `source_id=NULL`; plus nits (migration `updated_at`, duplicated vendor-name strip, `str | None` typing, internal PATCH pin, non-null PATCH pin value, `is_re_credited`, `tests/act_as.py` body text) and 4 PRD text fixes. Another agent had pushed `d6a77e0b` (review-gap tests, `tests/act_as.py`, migration ON CONFLICT, RLS probe via injector) before Leo's review.
- r2 `9349d1d2` (this session, pushed 2026-10-15): blocker fixed (`elif not source: source = LINKEDIN_SOURCE` + test), all nits applied, PRD doc rev 31 updated (outbox events, Loki fields, RLS-probe wording). PR body amended via `gh api`.
- **MERGED** 2026-10-15 20:24 UTC as squash `b70a79bc` → dev (auto-deploys dev + kforce-dev). Pre-merge chain check: [#2416](https://github.com/taller-projects/echo-backend/pull/2416) had landed migration `hx4m7ctq2ve9` on the same parent `ffbs5lissmfa`, so `origin/dev` was merged into the branch and `down_revision` bumped to `hx4m7ctq2ve9` (`25ceb2ac`). Verified: `alembic heads` = single head `5nnel6f7gwfi`, both migration e2e tests + 107 PR/change-history tests green locally, CI green (12m52s), Leo's approval survived the push.
- Conflict check vs merged [#2414](https://github.com/taller-projects/echo-backend/pull/2414) (2026-10-15): none — branch based on `c5c544a2`, hook untouched, `CHANNEL_SOURCES` identical, #2414's tests kept/extended. #2414's wrong assumptions (LinkedIn = Taller-internal only; the accepted 403; `(Taller Recruitment, LinkedIn)` left in place) are each corrected here. Leftover from #2414 still in force: external vendor-scope recruiter + Referral **with** `edit_source` → RLS 403 (not claimed by the PRD).
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
- The PRD's "RLS probe case that still denies another external vendor's source" does not exist at the policy level: the insert hook links the creator's vendor to ANY non-channel source, so a vendor-scope recruiter WITH `edit_source` crediting a partner gets linked to the partner's row and the INSERT passes (pre-existing, Task 25510 territory). The denial is the router's 404 without `edit_source`; covered at route level with `channel` sent.

## Gotchas
- A migration PR that waits a day must re-check `down_revision` before merging: #2416 landed `hx4m7ctq2ve9` with the same parent. Fixed from a sibling worktree (`.claude/worktrees/talent_channel_chain`, branched off `origin/feat/talent_channel`, merge of `origin/dev`, push `HEAD:feat/talent_channel`) because the PR worktree is owned by another session (worktree-owner hook) — the hook's own recipe.
- Worktree isolation refuses compound shell lines and heredoc text that name the VCS tool: one plain command per Bash call, no `cd`, and vault notes written from inside a worktree must avoid that word.
- Fast-forwarding another agent's push into my worktree: `git fetch origin feat/talent_channel && git merge --ff-only origin/feat/talent_channel` from the worktree (clean tree, not ahead) — no second worktree needed when the branch is mine and I am only behind.
- `gh pr create --assignee gonza56d` silently leaves the PR unassigned (not a collaborator); assign `gonza-taller` via `gh api -X POST repos/…/issues/<n>/assignees`.
- `tests/unit/test_referral_source_validation.py::test_post_with_channel_source_by_external_recruiter_does_not_link_vendor` asserted `source_id == LinkedIn row` for an external recruiter — renamed to `..._never_links_the_channel` and now asserts the credit to the agency's own row + no LinkedIn link.
- In a shared module tenant, a test that links the LinkedIn row to an external vendor turns `LinkedIn` into an attribution source for every later test (404 without `edit_source`). `test_talent_channel.py` has an autouse fixture that deletes `(external, LinkedIn)` links after each test; `_source()` there is get-or-create because `(tenant_id, source)` is unique.
- `uv run` inside a worktree creates a second `.venv` there (163 packages) — use `/Users/gonza56d/taller/repos/echo-backend/.venv/bin/python -m pytest` and `.venv/bin/ruff` directly; the worktree guard refuses `source …` lines.
- fastapi-filter list params are comma-separated (`id__in=a,b`), not repeated keys.
- Downgrade + upgrade leaves re-credited talents without a channel (source is the vendor now) — documented in the revision docstring; history rows are the trail.
- `tests/golden_snapshots/baseline/openapi.json` carries NO `/talents*` routes and no `Talent*` schemas (recorded from the fork, which had no recruiting) — adding fields to talent schemas or filters needs no `[openapi]` waiver.
- `tests/act_as.py` is now the shared impersonation helper (ENABLE_ACCESS_CONTROL on + `current_user_id` override). Two private copies remain untouched in `test_application_source_transfer.py` and `test_candidate_email_send_permission.py`.
- Pyright in the worktree reports unresolved `sqlalchemy` / `alembic` imports — venv not resolved there, not a real error; ruff + pytest from the main `.venv` are the signal.

## Pending
- [x] Leo APPROVED r2 → **MERGED dev `b70a79bc` 2026-10-15** (dev + kforce-dev auto-deploy; migration is a no-op on KForce).
- [ ] Promote dev → qa → main (merge commit, never squash) after M0 and the product sign-off below.
- [x] Comment on Bug 25504 posted 2026-10-15 (supersession + Referral-403 leftover). Still to do: one-line fix of the hook comment at `app/modules/talent/models.py:733` (the "accepted 403" is Referral/Self-applied only now); PRD contract row for Referral by an external vendor-scope recruiter with `edit_source` → 403.
- [ ] Chore (not this PR): 4 other test modules still carry their own `_act_as` copy → migrate them to `tests/act_as.py`.
- [ ] **M0 prod data fix, before the prod release**: `UPDATE vendor SET name = btrim(name)` for `Taller Recruitment ` from the terminal (`PGSERVICE=echo-prod`); tell Guadalupe the manual `PATCH /applications/{id}/source` is no longer needed. Not verified from this session.
- [x] Azure tickets created 2026-10-15: Feature 25572, US 25573 (Closed), Bug 25574 (In development), Task 25575; PR #2423 body updated with the links; GitHub PR/commit relations on Feature + US + Bug.
- [ ] Product sign-off on the Taller `by_source` change (historical LinkedIn imports now count for `Taller` / `Taller Recruitment`) before `main`.
- [ ] Post-release verification: `GET /talents?channel=linkedin`, no `(external, LinkedIn)` `vendor_sources` row, `classify_intake` lines in Loki.
- [ ] Open product question: referred candidates worked by `Taller Recruitment` — `Referral` or `Taller Recruitment`?
- [ ] Review question (informational): prod `SELECT count(*) FROM talent` or an `EXPLAIN` of the backfill — `talent.source_id` has no index, both data statements hash-join over a full `talent` scan; sub-second at tens of thousands of rows, unmeasured against the 25 s cap.
- [ ] PRD text to amend for the documented deviations: `channel` on `TalentListBase` (every list view), log fields (`created_by_id`, no `talent_id`), "pg_type lookup" → `checkfirst=True`, inference on every `create_talent` caller.
- [ ] Later: `self_applied` enum value (`ADD VALUE IF NOT EXISTS` inside `op.get_context().autocommit_block()`); optional extension cleanup (send `channel`, drop the `LinkedIn` stamp).

## Related
- [[External vendors see all LinkedIn candidates via channel source (Bug 25504)]] · [[Referral Attribution M1 permission+gating (US 24996)]] · [[Role sync overwrites Referral source (Bug 25028)]]
