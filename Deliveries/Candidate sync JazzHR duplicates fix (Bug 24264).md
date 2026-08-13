---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, jazzhr, talent, entity-resolution]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2058"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24264"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24239"
prd: ""
---

# Candidate sync JazzHR duplicates fix (Bug 24264)

The external-partner "Add Candidate" flow (`POST /talents/{ats_role_id}/sync`) both **blocked the upload** with "A record with these details already exists" **and** left **duplicate prospects in JazzHR** on every retry. Root cause: the candidate lookup matched by email only, so a real duplicate (same LinkedIn, different email) fell through to the create path and the talent INSERT collided on a unique constraint — *after* the irreversible Jazz push had already run, with no rollback for Jazz. This is the Echo-side fix; the data team owns the idempotent Jazz push + historical cleanup under Bug 24239.

## Azure / docs
- [Bug 24264](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24264) — Echo-side fix (this note).
- [Bug 24239](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24239) — original repro; data-side (idempotent `/candidates/sync_data` + Jazz dedup). Data team synced (Gonzalo).

## PRs
- [#2058](https://github.com/taller-projects/echo-backend/pull/2058) → dev — **in review** (2026-08-12). Follow-up commit `fac68195` (2026-08-12) addresses the review coverage nits. Commit `7d266cb0` (2026-08-13) implements **A3** and answers Pedro's round-2 review (below).

## Review round 2 (Pedro, 2026-08-13) — [comment](https://github.com/taller-projects/echo-backend/pull/2058#issuecomment-5273235910)
Verdict **CHANGES REQUESTED**, 2 blockers. Resolved:
- **Blocker A3 (`jazz_person_id` not propagated)** → **implemented** in `7d266cb0`. The `None` was a deliberate change (`44996df0`, "null when creating new Talent") and `TalentSyncCreate` inherits `jazz_person_id`, so a naive revert would relay a request-body value for a brand-new person. Fix passes the id **explicitly from the caller** (never from the body): existing candidate (update path + `apply_talent_to_role`) forwards `talent.jazz_person_id`; new candidate (`talent_is_new` gate) stays `None`. 3 new unit tests. **Data-team confirm still needed** before prod enablement: ER hasn't received the field in ~5 months — verify `/candidates/sync_data` upserts on a provided `jazz_person_id`.
- **Blocker phone (add to dup-check)** → **rebutted** (my [reply](https://github.com/taller-projects/echo-backend/pull/2058#issuecomment-5280694827)). `Talent.phone` has **no tenant-unique index** (`models.py:94-96` only cover email + linkedin), so a phone-only match cannot cause the post-`sync_data` INSERT collision this bug is about — and matching on phone would send genuinely-different people who share a number down the update path (false-positive merge → wrong Jazz sync). Proposed: keep email OR linkedin, fix the ticket AC wording to "email OR LinkedIn". Matches the prior 3-agent review's Q4. No code change.
- Split-identity Question: reaffirmed as pre-existing accepted residual (offered a follow-up ticket, kept out of this PR's scope).

## Review (2026-08-12, 3-agent `/pr-review`)
Verdict **BLOCKED ON CLARIFICATION** — no code defect forces a rewrite; the delivered A0/A1/A4/A5 are sound and tested (arch 12 PASS/0 FAIL; tests-security 10 PASS/1 FAIL→downgraded). It hinges on one gating question. Consolidated:
- **Q1 (top, blocker-adjacent — A3 dropped):** the update path still calls `sync_data` with the user's **new** email and `jazz_person_id=None`. If ER's `sync_data` isn't yet idempotent in prod (create-or-get covering the LinkedIn-match/new-email case), that call can still create a **new** Jazz prospect for the existing person — the same symptom, moved from create→update path (A4 won't catch a genuinely new `prospect_id`). A3 was the Echo-side guard. **Safe to drop only if idempotent `sync_data` is already live** — else re-add A3 or gate the merge on the data-side deploy. Needs confirmation before merge.
- **Q2 (split-identity, not a regression):** `check_duplicate` (email OR linkedin, no `ORDER BY`) returns an arbitrary row; if the incoming email matches talent A but the LinkedIn matches a different talent B, the update writes the other's unique value and re-collides on the *other* index **after** `sync_data`. The old email-only code collided here too, so no regression — but "no new duplicate" doesn't fully hold. Decide: reject-before-sync deterministically, or document as accepted residual (data-side idempotency neutralizes the Jazz side).
- **Q3 (CI gap):** the listener rewrite + AC4 atomicity are covered **only** by `tests/system/`, which this repo's CI never runs. Record a manual `./scripts/test.sh system` run on the PR before merge.
- **Q4 (phone):** A1/AC1 literally list phone; the PR omits it. Defensible — phone has no tenant-unique index so it can't cause the collision (and could cause false-positive merges). No code change; update the ticket wording to "email OR LinkedIn".
- **Q5 (consumer):** external "Add Candidate" caller now gets 200-on-duplicate (was 400) — confirm it treats a 200-update as success.
- **Nits fixed in `fac68195`:** unit test for the non-list `ats_external_ids` legacy guard (string must coerce to list, not splat into chars); system tests for the two uncovered `set_source` listener branches (already-linked vendor→source guard = no duplicate `vendor_sources` row; `vendor_id is None` early return = source created, no link); stale `get_talent_by_email` comment in `sync_talent_with_jazz_and_vendor` reworded. Nits deliberately **not** taken: explicit `created_at/updated_at` in the Core insert (documented deliberate choice — explicitness/atomicity), and the `__new__`/`SimpleNamespace` fixture fragility (pre-existing file convention).

## How
`TalentService.create_and_sync_talent` → `sync_talent_with_jazz_and_vendor` (`app/modules/talent/service.py`). Four changes:
- **A1 (core):** resolve the existing candidate with `check_duplicate(email, linkedin_url)` instead of `get_talent_by_email` — a real duplicate takes the **update** path instead of a colliding INSERT. The two tenant-unique identifiers (`tenant_email_uniq_idx`, `tenant_linkedin_url_uniq_index`) are exactly the ones that were throwing.
- **A4:** dedupe `ats_external_ids` (append-if-absent) so a stable `prospect_id` from an upserting Jazz push no longer accumulates.
- **A5:** rewrote the `set_source` `before_insert` listener (`app/modules/talent/models.py`) to run Core statements on the **flush `Connection`** instead of a nested `Session(conn)` that `commit()`-ed mid-flush — restores `create_talent` atomicity.
- **A0:** `echo_exception_handler` now logs `DuplicateError.constraint` (the client only ever sees the generic "Item already exists").

Genuine duplicate → update existing + sync to the same Jazz person, return the talent (no 400, no new duplicate) — the chosen UX.

Tests: 3 existing sync tests updated for the new collaborator; new service-level unit tests (dup-by-linkedin → update path, blocked sync makes **zero** `sync_data` calls, ats dedupe, append-new); exception-handler constraint-logging tests; real-Postgres system tests for the listener (`tests/system/test_talent_set_source.py`: new source, reuse, **atomicity-on-rollback**, vendor-link). 111 relevant tests green, lint clean.

## Decisions
- **A3 `jazz_person_id` — initially dropped, then implemented** (`7d266cb0`, after Pedro's round-2 blocker). Forwarded only for an already-synced candidate, passed explicitly from the caller (never the request body), `None` for a new talent via the `talent_is_new` gate — restoring the update-path behavior `44996df0` over-broadly removed while keeping null-on-create. Echo-side guard so no new Jazz prospect even if ER idempotency (Bug 24239) isn't live yet.
- **Phone NOT added to the dup-check** (Gonzalo's call, round 2): no tenant-unique index on `phone` → can't cause the collision + risks false-positive merges. Fix the ticket AC wording instead.
- **Duplicate = update, not 409** (Gonzalo's call): a re-sync is a legitimate action (new CV, recruiter reassignment) — erroring would just re-break the flow.
- **Listener rewritten with Core `conn.execute`, not commit→flush**: `TimestampMixin` uses Python-side defaults, so the Core insert supplies `id`/timestamps explicitly; unambiguously atomic vs. relying on nested-session close semantics.

## Gotchas
- The bare "Item already exists" message maps to constraints whose names lack the substring `talent` (`DuplicateError.from_db_string`): `tenant_email_uniq_idx`, `tenant_linkedin_url_uniq_index`, `vendor_sources_pkey`. The app never logged the pgerror on a handled 400 → A0 fixes that.
- Prod blast radius (Taller, 2026-08-12): **~16,184 surplus Jazz prospects across 8,246 candidates** (one at 702) from the non-idempotent push — cleanup is data-side.
- Local unit run 404s all success-path talent endpoints (documented TestClient issue, green in CI) → the fix is tested at the **service** layer, and the listener via **system** tests.

## Pending
- **Await Pedro's re-review of `7d266cb0`** (A3 implemented + phone rebuttal). If he accepts the phone rebuttal, update the ticket AC wording to "email OR LinkedIn".
- **Data-team confirm before prod enablement**: ER `/candidates/sync_data` handles a provided `jazz_person_id` (upsert on that person) — the field hasn't been sent in ~5 months. A3 is the Echo-side guard regardless.
- Merge #2058 → dev; then qa/main promotion.
- Data team (Bug 24239): idempotent `/candidates/sync_data` (create-or-get) + honest 4xx/5xx; historical Jazz dedup (~16k).
- Confirm the exact firing constraint from prod once A0 logging lands (email vs linkedin).

## Related
- [[Map - JazzHR integration]] · [[Per-application recruiter from Jazz back-sync (Bug 24241)]] · [[Push Applications Echo to JazzHR (Feature 24051)]]
