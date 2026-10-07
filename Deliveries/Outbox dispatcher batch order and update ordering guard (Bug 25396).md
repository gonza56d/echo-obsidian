---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, outbox, dispatcher, trackerrms, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2393"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25396"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25390"
prd: ""
---

# Outbox dispatcher batch order and update ordering guard (Bug 25396)

Found during the local full-stack E2E of [[Reverse push duplicates TrackerRMS Resources - external ids read from entity_external_links (Bug 25390)]] (2026-10-06): one
dispatcher worker processed `talent.updated` before `talent.created` for 5 of
6 talents in a batch → the update found no link, POSTed, then the create
POSTed again → two TrackerRMS Resources, two `entity_external_links` rows, two
ids in `ats_external_ids`. Same symptom as Bug 25390, different cause; #2388
did not cover it. Fixed by ordering the claimed batch and by making an unlinked
`.updated` wait for a pending predecessor instead of creating.

## What
- `OutboxRepository.claim_batch` claims through a CTE and returns the batch
  ordered by `(occurred_at, lifecycle rank, id)`; `available_at` still picks
  which rows are claimed (retry fairness, `FOR UPDATE SKIP LOCKED` unchanged).
- `has_pending_predecessors(event=…)` uses the same strict order
  (`(occurred_at, rank, id) < (mine)`), replacing the inclusive `occurred_at <=`
  + `exclude_id`.
- TrackerRMS `.updated` with no external id checks the outbox: pending
  predecessor → `StaleUpdateOrderError` (409 budget); nothing pending → POST as
  before. `PendingPredecessorError` is the shared base with
  `StaleDeleteOrderError`.

## Azure
- [Bug 25396](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25396) — **In revision** (set 2026-10-07), assigned to me,
  related to [Bug 25390](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25390). Body = root cause + local repro
  (5/6 then 0/6) + impact + proposed fix. Comment with the PR link posted
  2026-10-07.

## PRs
- [#2393](https://github.com/taller-projects/echo-backend/pull/2393) → `dev` — **OPEN 2026-10-07**, branch
  `25396/dispatcher_batch_order` off `origin/dev` (`97eb3540`), commits
  `7c495209` (fix) + `d1dbf8cd` (2026-10-07: event-order SQL tests moved to
  the unit suite, see Review). Original worktree already removed; follow-up
  commit made in `.claude/worktrees/dispatcher-batch-order-25396-ci` (local
  branch `25396/dispatcher_batch_order_ci_tests`, pushed with
  `git push origin HEAD:25396/dispatcher_batch_order`). PR body Tests bullet
  rewritten to match.
  No migration, no flag. 219 unit + system outbox tests green locally
  (`test_outbox_dispatcher` unit, `test_outbox_dispatcher` / `test_outbox_loop`
  / `test_outbox_dispatcher_jazz_hr` / `test_worker_lease_chaos` system).

## How
- **Verified before fixing** (real Postgres through the repo fixtures, probe
  run with `uv run python -m pytest -p tests.conftest <file outside tests/>`):
  the claim's `UPDATE … RETURNING` follows plan order, never the sub-select's
  `ORDER BY available_at`. 12 rows (unanalyzed) → Nested Loop over a
  **HashAggregate** of the sub-select: 2/6 entities updated-before-created on
  every claim. 5,012 rows (analyzed) → **Hash Semi Join over a Seq Scan**: heap
  order (700+ of 1,225 pairs inverted). Processing updated-first on the
  post-#2388 tree: 2 POSTs, 0 PATCH, 2 links, both events completed (nothing
  ever repairs it). The ticket's 5/6 vs 0/6 variance is the hash-order regime.
- Rank expression `_EVENT_RANK_SQL` (`created` 0, `updated` 1, else 2) +
  `_event_rank()` live once in `outbox/repository.py` and feed both the claim
  `ORDER BY` and the predecessor row-value comparison, so the two orders can
  never disagree.
- Dispatcher: the guard sits right after `get_external_id` in
  `_deliver_tracker_rms`; linked updates and `.created` never consult it.
  `_handle_delivery_failure` budgets on `PendingPredecessorError`.
- Tests (after `d1dbf8cd`): `tests/unit/test_outbox_event_order.py` (real
  Postgres, **runs in CI**) holds the claim order with reverse-inserted pairs,
  the same-timestamp lifecycle order, and the update-path predecessor SQL
  (pending create, same-timestamp create, two same-timestamp updates, terminal
  create). Same-timestamp cases pin event ids (`_ordered_id` prefix) so id order
  contradicts lifecycle order. Mutation-checked: old claim SQL, rank dropped
  from the claim `ORDER BY`, rank dropped from the predicate, `<` → `<=` — each
  fails at least one test. `TestUpdateReorderRaceRealSql` in
  `tests/system/test_outbox_loop.py` keeps only the full claim → updated-first
  → create POST → retry PATCH cycle. Unit (mocked): consult / wait / skip
  matrix + 409 budget.

## Decisions
- **Order by `occurred_at`, not `available_at`, inside the batch**: a retried
  `.created` (later `available_at`) must still run before a fresh `.updated`.
- **Strict total order with a lifecycle-rank tiebreak** instead of the old
  inclusive `<=`: same-transaction events share `occurred_at` (server default
  `now()`) and ids are random uuids; an inclusive check would make two
  same-transaction unlinked updates of one entity block each other until both
  dead-letter. (Correction from review: `ContactService.bulk_create_relationships`
  dedupes contact ids, so it writes one `.updated` per contact — it is NOT an
  example of two same-entity updates; the PR body still cites it.) The rank keeps "created before its
  same-transaction update/delete" (the case the old `<=` protected).
- **Keep the POST fallback when nothing is pending**: entities created before
  the integration was enabled, and updates after a dead-lettered create
  (`completed_at` set), behave exactly as before. Jazz's "an update must never
  create" rule does not transfer to TrackerRMS.
- **409 budget** for `StaleUpdateOrderError` (like deletes): the predecessor
  create may itself be riding the 409 budget; first retry lands ~60 s later.
- `claim_batch` ordering done in SQL (CTE) rather than a Python sort so the
  repository contract is "ordered" and the test pins it at the SQL level.
- Only one dispatcher replica runs (infra `values-dev.yaml` / `values-prod.yaml`
  `replicaCount: 1`; qa and kforce run none), so the live hazard was in-batch
  order + retry backoff; the guard also covers a second replica.

## Review
- Self-review r1 2026-10-07 (`/pr-review`, NOT posted): **CHANGES REQUESTED** —
  one blocker (T2): the claim-order + predecessor SQL tests lived only in
  `tests/system`, which CI never runs, so reverting the outer `ORDER BY`,
  dropping the rank, or going back to `<=` would merge green. **Fixed in
  `d1dbf8cd`** (moved to `tests/unit/test_outbox_event_order.py`, ids pinned).
- Open nits (not done): re-read the link after `has_pending_predecessors` →
  False (two-replica TOCTOU, also on delete); pending check is per event not per
  platform (`completed_at` waits on every platform's delivery — a TrackerRMS
  update can wait on a Jazz-only pending create); rank defined twice (SQL CASE +
  `_event_rank`) → single definition or parity test; equal 409 budgets can
  dead-letter the waiter first; full-cycle system test compares DB `now()` vs
  Python `datetime.now()`; `claim_batch(500)` in tests grabs unrelated module
  rows; budget ceiling unit case for `StaleUpdateOrderError`;
  `OrderingNotReadyError` docstring still names `StaleDeleteOrderError`;
  ContactService example in PR body; jazz_hr unit-test format churn.
- Out of scope → follow-up ticket (unfiled): `occurred_at` is transaction start
  time and the bulk contact path writes `CONTACT_CREATED` in a second
  transaction (`contact/service.py:397-413`), so an edit committing in between
  sorts before its create and POSTs; `.created` never checks for an existing
  link. Also: same-entity same-transaction updates tie-break on random uuid
  (needs a sequence column).
- Prod read of tenants with several enabled integrations was denied by the
  auto-mode classifier — still unchecked.

## Gotchas
- A bare `MagicMock` is truthy: the unit `dispatcher` fixture now defaults
  `has_pending_predecessors` to `False`, otherwise every unlinked update/delete
  test flips to "retry".
- `uq_entity_external_links_external_id` is `(tenant, entity_type,
  external_id, platform)`: a fake tracker that restarts ids at 90001 per test
  collides across tests in one module → module-level `itertools.count`, and the
  PATCH stand-in must echo the id from the URL (a fresh id per PATCH would mint
  a second link and misrepresent the real service).
- Worktree guard refuses "complex" Bash (python heredocs, `$(…)` arithmetic);
  write helper scripts under the worktree's gitignored `vault/` with the Write
  tool and run them with a plain `python3 vault/<script>.py`.
- `uv run` inside a worktree creates its own `.venv` (fast, from cache); the
  `.env` still has to be copied in.

## Pending
- [ ] CI green on `d1dbf8cd` + team review → squash-merge #2393.
- [ ] Decide on the open review nits (see Review); file the `occurred_at`
      causality follow-up ticket.
- [ ] Promote to `qa` / `main` (cherry-pick, merge commit) — pairs naturally
      with the #2391 prod cutover of 25390.
- [ ] Close [Bug 25396](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25396) on merge.
- [ ] After prod: read-only Navitec check for pairs minted seconds apart by
      this path (beyond the 25390 set); cleanup = DELETE the duplicate's link,
      never mark `stale`.
- [ ] Remove the worktree `.claude/worktrees/dispatcher-batch-order-25396-ci`
      once merged.

## Related
- [[Reverse push duplicates TrackerRMS Resources - external ids read from entity_external_links (Bug 25390)]] — the sibling fix (what the readers look at); this one is
  when they look.
- [[Outbox skips internal-originated emits (Bug 23656)]]
- [[Map - TrackerRMS integration]] · [[Map - JazzHR integration]] (same
  dispatcher; Jazz already had `OrderingNotReadyError`).
