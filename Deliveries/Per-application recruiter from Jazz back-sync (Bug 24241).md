---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, jazzhr, back-sync, applications, recruiter-owner, process-history]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2049"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24241"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24244"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24245"
prd: ""
---

# Per-application recruiter from Jazz back-sync (Bug 24241)

A candidate's **Process History in Echo showed the same recruiter (e.g. Camila) on every application**, not matching JazzHR — where each application's candidate-record has its own owner (Nestor / Camila / Milagros). Root cause: Echo modelled recruiter ownership at the **talent** level (`talent.jazz_owner_id`, a single mutable value overwritten on every back-sync); each application's owner was derived/snapshotted from that one value, never from the Jazz record's recruiter. Another agent had told Gonzalo "already fixed, old data lost/unrecoverable" — **both halves wrong**: the May-2026 sticky-owner work only stopped the *live* retroactive overwrite (and its backfill froze the wrong talent-level value into history), and the correct per-application recruiter is **not lost** — it lives in JazzHR (system of record) and is fully re-syncable. This delivery is the **backend enablement**: Echo can now store & honor a per-application recruiter supplied by the back-sync.

## Azure / docs
- [Bug 24241](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24241) — the reported bug (Process History collapses onto the most recent recruiter). Assigned Paloma.
- [Task 24244](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24244) — **this backend enablement** (child of 24241, mine, In development).
- [Task 24245](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24245) — **data-team follow-up** (child of 24241): back-sync sends the per-application recruiter + one-time backfill. Unassigned (data team). Gated on #2049 merged + deployed.

## PRs
- [#2049](https://github.com/taller-projects/echo-backend/pull/2049) → dev — **OPEN** (2026-08-12). Backend enablement. Latest commit `5f9b6e14`.

## Review (r1, 2026-08-12, /pr-review)
- **Verdict: BLOCKED ON CLARIFICATION.** Everything clean — architecture 16/16, tests+security no blockers (tenant isolation on `get_by_jazz_id` confirmed: `MemberRepository` is `TenantScopedRepository`, the sole guard since `/internal` runs under `DisableRLS`; no public leak of `jazz_owner_id`; migration chain valid) — **except one ticket-internal contradiction**.
- **The open decision:** on an **unresolvable `jazz_owner_id` UPDATE**, the code clears `owner_id=NULL` (faithfully mirroring `TalentService._get_owner_id`, per Task 24244 req #1) — but req #4 says "missing-member → **leave prior**". Verified end-to-end: the assignment lands in `entity.model_fields_set` → survives `repo.update`'s `exclude_unset=True` → persists NULL; then `_snapshot_owner_if_leaving_matching` may re-stamp the talent-level owner = the exact Bug-24241 collapse. Self-heals on the next sync (persisted `jazz_owner_id` re-resolves) + `effective_owner` read-fallback, so moderate not catastrophic. **My recommendation: make the resolver path-aware** — leave-prior (skip the assignment) on UPDATE, clear OK on CREATE — which satisfies *both* ticket clauses. Left for the author/product call; **not** changed in the nit pass.
- **Nits addressed (commit `5f9b6e14` + PR body):** (1) added CI-executing unit coverage that the snapshot does **not** clobber a Jazz-resolved owner (`TestSnapshotDoesNotClobberResolvedOwner`, 2 cases incl. a non-vacuous contrast) → **8 unit** tests now; (2) added the **Kforce-sibling note** to the PR body (N/A — see below).
- **Nit intentionally NOT applied — `max_length` on `jazz_owner_id`:** the whole jazz-id field family is deliberately unbounded (`talent.jazz_owner_id`, and critically `user.jazz_user_id` — the column this resolves *against* — is an unbounded `mapped_column(unique=True)`). Capping the input below what `user.jazz_user_id` accepts could reject a legitimately-resolvable id, and bounding `application.jazz_owner_id` alone breaks the "mirrors talent" symmetry. Net-negative → skipped.

## Investigation (prod, talent `1e35969f-aac0-4bed-bec4-64c5ead1fe15`)
- Tenant **Taller**, `recruiter_by_jazz_id` **ON**. `talent.jazz_owner_id` = `usr_20221214155503_W2QMGVSNY5FJXI9Z` → **Milagros Valdes** (the talent's *current* single owner); `talent.owner_id` NULL.
- 5 applications: **4 frozen at `owner_id` = Camila Alcaraz** (`80845c62…`, from the 2026-05-29 backfill), **newest at Milagros** (`adf9bfbb…`, snapshotted post-migration when the talent owner had flipped). Jazz shows **three** distinct owners across the records — proof Echo can't represent them with one talent-level value.
- The "fix" the other agent meant = sticky `application.owner_id` (US 22870 / PR #1471 + migration `rpkt72nlggbj`, 2026-05-29): stopped the live flip, but the snapshot source is still `talent.current_owner`, so displayed owners stay wrong; its backfill collapsed every historical row to the single talent owner.

## How
- New column **`application.jazz_owner_id`** (migration `k3n8owxr2p9m`, chains onto `habp5kg5dvpo`), mirroring `talent.jazz_owner_id`. Nullable, no backfill.
- `ApplicationCreateInternal` / `ApplicationUpdateInternal` gain `jazz_owner_id` (raw Jazz user id); the **internal update endpoint now uses `ApplicationUpdateInternal`** (was `ApplicationUpdate`, which has no `owner_id` — the structural blocker: the back-sync literally could not push an owner on updates).
- `ApplicationService._resolve_owner_from_jazz` (mirrors `TalentService._get_owner_id`): resolves `jazz_owner_id` → member → `owner_id` on internal create/update. Called first in `create()` and `update()`. A Jazz id **wins over** any `owner_id` on the payload and **overrides a prior/stale snapshot**; unresolved id clears `owner_id` (falls back to talent owner) + logs `application_owner_jazz_id_unresolved`. `_snapshot_owner_if_leaving_matching` is unchanged (only fills when `owner_id` is NULL) so a synced owner survives.
- Display path (`Application.effective_owner` → `owner` (owner_id) else `talent.current_owner`; `ApplicationResponse.owner` = `effective_owner`) **unchanged** — the fix flows through the existing `owner_id`.
- Public create/update flows untouched (no `jazz_owner_id` on public schemas → resolver no-ops).
- Tests: 8 unit (`tests/unit/test_application_owner_from_jazz.py`) + 2 system (`tests/system/test_application_owner_backsync.py`, through `/internal/applications`).

## Decisions
- **Persist `application.jazz_owner_id` as a column** (not transient input): mirrors talent, and lets `owner_id` be re-resolved later if the recruiter's member didn't exist at sync time.
- **Accept the raw Jazz id and resolve inside Echo** (not require the data team to send an Echo member id): cheapest for the back-sync; same contract as `talent.jazz_owner_id`.
- **Sync wins over the snapshot** (authoritative overwrite): required so M3's backfill can repair the frozen-wrong history.

## Gotchas
- **`MemberService.get_by_jazz_id` explodes a bare `str`**: a `str` is a `collections.abc.Sequence`, so a bare string is iterated into individual characters and matches nothing. Must pass a **single-element list** `[jazz_owner_id]`. This is also why `TalentService._get_owner_id`'s write-time resolution is effectively inert for jazz tenants (talents survive via the SQL `Talent.owner` relationship; applications have **no** such SQL fallback, so this had to be right). Left the talent caller alone (out of scope; harmless there).
- Local `tests/unit` 404s on all success-path endpoint tests (documented TestClient artifact; CI green) — verified the 54 combined-run failures reproduce on the clean baseline (my code stashed) → not mine.
- `git add -A` in this repo sweeps in unrelated session-start junk (pentest.pdf, pngs, csv, `.claude/projects/`) — staged only the 7 real files.

## Pending
- **Merge #2049** to dev (then qa/main promotion — no data change on merge; ships inert until the back-sync uses it).
- **Task 24245 (data team)** — M2 back-sync sends `jazz_owner_id` per application on create AND update; **M3 one-time backfill/re-sync** of historical rows from Jazz (matched by `application.external_id` = `projob_…`). This is what actually repairs Process History.
- **Open questions**: precedence of a manual `PATCH /applications/{id}/owner` reassignment vs a later back-sync (currently sync wins); the review r1 unresolved-on-update clear-vs-leave-prior decision (see Review above). **Kforce sibling: N/A** — Bug 24241 is Taller-specific (`recruiter_by_jazz_id` tenant); Kforce is single-tenant with no Jazz tenant, so nothing to port (noted in the PR body).

## Related
- [[Push Applications Echo to JazzHR (Feature 24051)]] — same JazzHR integration surface (Echo↔Jazz applications).
- [[Map - JazzHR integration]]
