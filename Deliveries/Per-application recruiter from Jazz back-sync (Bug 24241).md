---
type: delivery
status: merged-gated
env: taller
delivered: 2026-08-12
tags: [bugfix, jazzhr, back-sync, applications, recruiter-owner, process-history]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2049"
  - "https://github.com/taller-projects/echo-backend/pull/2059"
  - "https://github.com/taller-projects/echo-backend/pull/2060"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24241"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24244"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24245"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24275"
prd: ""
---

# Per-application recruiter from Jazz back-sync (Bug 24241)

A candidate's **Process History in Echo showed the same recruiter (e.g. Camila) on every application**, not matching JazzHR — where each application's candidate-record has its own owner (Nestor / Camila / Milagros). Root cause: Echo modelled recruiter ownership at the **talent** level (`talent.jazz_owner_id`, a single mutable value overwritten on every back-sync); each application's owner was derived/snapshotted from that one value, never from the Jazz record's recruiter. Another agent had told Gonzalo "already fixed, old data lost/unrecoverable" — **both halves wrong**: the May-2026 sticky-owner work only stopped the *live* retroactive overwrite (and its backfill froze the wrong talent-level value into history), and the correct per-application recruiter is **not lost** — it lives in JazzHR (system of record) and is fully re-syncable. This delivery is the **backend enablement**: Echo can now store & honor a per-application recruiter supplied by the back-sync.

## Azure / docs
- [Bug 24241](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24241) — the reported bug (Process History collapses onto the most recent recruiter). Assigned Paloma.
- [Task 24244](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24244) — **this backend enablement** (child of 24241, mine, In development).
- [Task 24245](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24245) — **data-team follow-up** (child of 24241): back-sync sends the per-application recruiter + one-time backfill. Unassigned (data team). Gated on #2049 merged + deployed.

## PRs
- [#2049](https://github.com/taller-projects/echo-backend/pull/2049) → dev — **MERGED** 2026-08-12 (squash `7215044d`, by Gonzalo). Backend enablement. Not yet promoted to qa/main.
- [#2059](https://github.com/taller-projects/echo-backend/pull/2059) → qa — cherry-pick of `7215044d` (branch `cherry_pick/24244_per_app_recruiter_qa`), opened 2026-08-13. Merge with merge commit, before #2060.
- [#2060](https://github.com/taller-projects/echo-backend/pull/2060) → main — cherry-pick of `7215044d` (branch `cherry_pick/24244_per_app_recruiter_main`), opened 2026-08-13. Merge with merge commit, after #2059. **Merging = prod deploy (argo auto-sync).**

## Bug 24275 diagnostic (2026-08-13) — CSR re-report of the same bug
- [Bug 24275](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24275) (Paloma, CSR, Sprint 43, assigned Gonzalo): application owner ≠ profile recruiter (Keila Ortiz / Laura Castellano on apps vs Sara Abero / Rosario Valdes on profile; repro candidates Aldo Esparza, Nilson Junior). **Same root cause as 24241**, seen through Application Details instead of Process History.
- Verified in prod DB: Nilson Junior (`cf7d6f7d`) profile→Rosario Valdes, ~35 apps frozen at Laura Castellano; his 2026-08-12 app correctly snapshotted Rosario (only history is wrong). Aldo Esparza (`2f494577`) profile→Sara Abero, Feb app frozen at Guido Egea. The Keila-vs-Sara example = other CSR candidates (e.g. Wallas Abreu `63aab640`, 2 apps).
- **Tenant-wide blast radius: 1,128 applications / 364 talents** where `application.owner_id` ≠ the live jazz-resolved owner (top pairs: Milagros→Rosario 45, Laura→Rosario 28, Sara→Keila 18, Rosario→Sara 17).
- Prod schema confirmed pre-#2049: `alembic_version = habp5kg5dvpo`, no `application.jazz_owner_id`. So "yesterday's fix" couldn't have fixed it (dev-only + inert). Recommended: fold 24275 into 24241; repair = promote #2049 + data-team Task 24245 (M2 back-sync + M3 backfill).
- Promotion PRs #2059/#2060 opened 2026-08-13 (see PRs). Azure comment with links posted on Task 24244 (comment 28593502).

## Status / where to pick up (2026-08-12)
- **PR #2049 merged to dev.** Ships **inert** — no behavior change until the data-team back-sync (Task 24245) actually sends `jazz_owner_id`.
- **[Task 24244](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24244) deliberately left at "Developed" (NOT Done/Closed).** Gonzalo's call: the backend is merged but the *visible* Bug-24241 fix still needs the data part, so the ticket stays open as the tracking anchor. **Do not close it** until the data team delivers Task 24245 (back-sync + backfill) and Process History is verified corrected in prod. When resuming: check whether Task 24245 has been picked up, whether #2049 was promoted to qa/main, and only then move 24244 → Done.

## Review (Leo, 2026-08-12) — READY WITH NITS, addressed
- Leo's human review ([comment](https://github.com/taller-projects/echo-backend/pull/2049#issuecomment-5270846673)): `READY WITH NITS`, **0 blockers**, 4 AC met, no scope creep — noted the resolver is *more* correct than the `_get_owner_id` it mirrors (wraps the id in a list, dodging the `str`-is-`Sequence` bug). Two questions + a few nits.
- **All addressed in `b9f4c934`** ([reply](https://github.com/taller-projects/echo-backend/pull/2049#issuecomment-5270975964)):
  - **Q1 (the r1 open decision, now RESOLVED):** made `_resolve_owner_from_jazz` **path-aware** via `clear_if_unresolved`. CREATE clears (snapshot falls back to talent owner — no prior to protect); **UPDATE leaves `owner_id` untouched** (early-return, stays out of `model_fields_set` → `exclude_unset` preserves the DB value) so an unresolvable id can't wipe a prior/manual owner and trigger the Bug-24241 re-stamp. Satisfies AC#1 (create) **and** AC#4 (update).
  - **Q2 (outbox `owner_id: None`): no change, correct.** `write_outbox_event` hard-returns for `is_internal` (`writer.py:32`, Bug 23656) → the Jazz back-sync **never emits** CREATED/UPDATED, so that field never reaches a consumer; for front-facing creates the owner is resolved by the snapshot *after* the emit, so it's genuinely unknown then. Pre-existing, no regression.
  - **Nits:** added unresolved-path coverage end-to-end (create-clears+fallback, update-leaves-prior) + multi-member `members[0]` pick → **10 unit + 4 system**. `max_length` deliberately skipped (see below). Typing left broad (called with public schemas too; `getattr`-guarded). Talent `_get_owner_id` bare-str bug = separate ticket.

## Review (r1, 2026-08-12, /pr-review)
- **Verdict: BLOCKED ON CLARIFICATION.** Everything clean — architecture 16/16, tests+security no blockers (tenant isolation on `get_by_jazz_id` confirmed: `MemberRepository` is `TenantScopedRepository`, the sole guard since `/internal` runs under `DisableRLS`; no public leak of `jazz_owner_id`; migration chain valid) — **except one ticket-internal contradiction**.
- **The open decision (RESOLVED in `b9f4c934`):** on an **unresolvable `jazz_owner_id` UPDATE**, the code cleared `owner_id=NULL` (faithfully mirroring `TalentService._get_owner_id`, per Task 24244 req #1) — but req #4 says "missing-member → **leave prior**". Verified end-to-end: the assignment lands in `entity.model_fields_set` → survives `repo.update`'s `exclude_unset=True` → persists NULL; then `_snapshot_owner_if_leaving_matching` may re-stamp the talent-level owner = the exact Bug-24241 collapse. **Fixed** by making the resolver **path-aware** (`clear_if_unresolved`): leave-prior on UPDATE, clear on CREATE — satisfies *both* ticket clauses. Leo independently raised the same as his Q1; confirmed + implemented (not deferred).
- **Nits addressed (commit `5f9b6e14` + PR body):** (1) added CI-executing unit coverage that the snapshot does **not** clobber a Jazz-resolved owner (`TestSnapshotDoesNotClobberResolvedOwner`, 2 cases incl. a non-vacuous contrast) → **8 unit** tests now; (2) added the **Kforce-sibling note** to the PR body (N/A — see below).
- **Nit intentionally NOT applied — `max_length` on `jazz_owner_id`:** the whole jazz-id field family is deliberately unbounded (`talent.jazz_owner_id`, and critically `user.jazz_user_id` — the column this resolves *against* — is an unbounded `mapped_column(unique=True)`). Capping the input below what `user.jazz_user_id` accepts could reject a legitimately-resolvable id, and bounding `application.jazz_owner_id` alone breaks the "mirrors talent" symmetry. Net-negative → skipped.

## Investigation (prod, talent `1e35969f-aac0-4bed-bec4-64c5ead1fe15`)
- Tenant **Taller**, `recruiter_by_jazz_id` **ON**. `talent.jazz_owner_id` = `usr_20221214155503_W2QMGVSNY5FJXI9Z` → **Milagros Valdes** (the talent's *current* single owner); `talent.owner_id` NULL.
- 5 applications: **4 frozen at `owner_id` = Camila Alcaraz** (`80845c62…`, from the 2026-05-29 backfill), **newest at Milagros** (`adf9bfbb…`, snapshotted post-migration when the talent owner had flipped). Jazz shows **three** distinct owners across the records — proof Echo can't represent them with one talent-level value.
- The "fix" the other agent meant = sticky `application.owner_id` (US 22870 / PR #1471 + migration `rpkt72nlggbj`, 2026-05-29): stopped the live flip, but the snapshot source is still `talent.current_owner`, so displayed owners stay wrong; its backfill collapsed every historical row to the single talent owner.

## How
- New column **`application.jazz_owner_id`** (migration `k3n8owxr2p9m`, chains onto `habp5kg5dvpo`), mirroring `talent.jazz_owner_id`. Nullable, no backfill.
- `ApplicationCreateInternal` / `ApplicationUpdateInternal` gain `jazz_owner_id` (raw Jazz user id); the **internal update endpoint now uses `ApplicationUpdateInternal`** (was `ApplicationUpdate`, which has no `owner_id` — the structural blocker: the back-sync literally could not push an owner on updates).
- `ApplicationService._resolve_owner_from_jazz(app, *, clear_if_unresolved)` (mirrors `TalentService._get_owner_id`): resolves `jazz_owner_id` → member → `owner_id` on internal create/update. Called first in `create()` (`clear_if_unresolved=True`) and `update()` (`clear_if_unresolved=False`). A resolved Jazz id **wins over** any `owner_id` on the payload and **overrides a prior/stale snapshot**. **Unresolved id** always warns (`application_owner_jazz_id_unresolved`), but: CREATE clears `owner_id` (snapshot falls back to talent owner), UPDATE **leaves it untouched** (protects a prior/manual owner). `_snapshot_owner_if_leaving_matching` is unchanged (only fills when `owner_id` is NULL) so a synced owner survives.
- Display path (`Application.effective_owner` → `owner` (owner_id) else `talent.current_owner`; `ApplicationResponse.owner` = `effective_owner`) **unchanged** — the fix flows through the existing `owner_id`.
- Public create/update flows untouched (no `jazz_owner_id` on public schemas → resolver no-ops).
- Tests: 10 unit (`tests/unit/test_application_owner_from_jazz.py` — incl. path-aware unresolved cases + multi-member pick + snapshot-no-clobber) + 4 system (`tests/system/test_application_owner_backsync.py`, through `/internal/applications` — resolve, override-stale, create-unresolved-fallback, update-unresolved-leave-prior).

## Decisions
- **Persist `application.jazz_owner_id` as a column** (not transient input): mirrors talent, and lets `owner_id` be re-resolved later if the recruiter's member didn't exist at sync time.
- **Accept the raw Jazz id and resolve inside Echo** (not require the data team to send an Echo member id): cheapest for the back-sync; same contract as `talent.jazz_owner_id`.
- **Sync wins over the snapshot** (authoritative overwrite): required so M3's backfill can repair the frozen-wrong history.

## Gotchas
- **`MemberService.get_by_jazz_id` explodes a bare `str`**: a `str` is a `collections.abc.Sequence`, so a bare string is iterated into individual characters and matches nothing. Must pass a **single-element list** `[jazz_owner_id]`. This is also why `TalentService._get_owner_id`'s write-time resolution is effectively inert for jazz tenants (talents survive via the SQL `Talent.owner` relationship; applications have **no** such SQL fallback, so this had to be right). Left the talent caller alone (out of scope; harmless there).
- Local `tests/unit` 404s on all success-path endpoint tests (documented TestClient artifact; CI green) — verified the 54 combined-run failures reproduce on the clean baseline (my code stashed) → not mine.
- `git add -A` in this repo sweeps in unrelated session-start junk (pentest.pdf, pngs, csv, `.claude/projects/`) — staged only the 7 real files.

## Pending
- ✅ ~~Merge #2049 to dev~~ — done 2026-08-12 (`7215044d`). ✅ ~~Open qa/main promotion~~ — cherry-pick PRs #2059 (qa) / #2060 (main) opened 2026-08-13. **Still to do: merge #2059 then #2060 (merge commits, never squash)** — inert on deploy, but main merge = prod deploy.
- **Keep Task 24244 open at "Developed"** until the data part lands (see Status section) — then close.
- **Task 24245 (data team)** — M2 back-sync sends `jazz_owner_id` per application on create AND update; **M3 one-time backfill/re-sync** of historical rows from Jazz (matched by `application.external_id` = `projob_…`). This is what actually repairs Process History.
- **Open questions**: precedence of a manual `PATCH /applications/{id}/owner` reassignment vs a later back-sync (currently sync wins); the review r1 unresolved-on-update clear-vs-leave-prior decision (see Review above). **Kforce sibling: N/A** — Bug 24241 is Taller-specific (`recruiter_by_jazz_id` tenant); Kforce is single-tenant with no Jazz tenant, so nothing to port (noted in the PR body).

## Related
- [[Push Applications Echo to JazzHR (Feature 24051)]] — same JazzHR integration surface (Echo↔Jazz applications).
- [[Map - JazzHR integration]]
