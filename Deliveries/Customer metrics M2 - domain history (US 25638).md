---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, adoption, customer-metrics, migration, rls]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2469"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25638"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M2 - domain history (US 25638)

Customer metrics M2. The domain tables start recording what the metrics need: talent status history, role close date and reason, application origin and first score/rank, score and rank at every stage change, the notification a touchpoint or bulk email answers, deal origin. Six durable events join the catalog. Builds on [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]] and is STACKED on its branch.

## Azure / docs
- [US 25638](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25638) (New, 4-6 days). Parent [Feature 25635](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635); business contract [CR 25592](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592).
- Tech PRD: [Customer Metrics Event History](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj), section 6 Milestone 2; rev 71 (2026-10-26) carries the five M2 changelog rows and the checklist wording below.
- Nico's SQL for this milestone: `docs/customer_metrics_m2_domain_history.sql` (8 per-tenant/per-month queries; `docs/` is gitignored, added with `-f`).

## PRs
- [#2469](https://github.com/taller-projects/echo-backend/pull/2469) → `25637/user-events-v2` (STACKED on M1), OPEN 2026-10-26 (`34c9bddf`, branch `25638/domain-history`, worktree `.claude/worktrees/25638-domain-history`, based on `31ea7db2` = M1 + Leo's r1 fixes). Retarget to dev and rebase once #2458 merges. Opened on the user's call without waiting for the local full suite (CI runs it); PR body in the worktree's `.claude/worktrees/tmp/pr_m2_body.md`.
  - CI run 1 on `34c9bddf`: 17 failed + 3 errors / 6,683 passed. All test-side: `__new__`-built stubs missing the new collaborators (`user_event_service`, `notification_service`, `status_history_service`), `create()` calls without `origin`, native-apply stubs without `channel`, and the RLS probe `viewer` fixture rolling a random `vendor_id` (M1 file, flaky FK). Fixed in `65458df3` (stubs) + `39857338` (viewer vendor; cherry-picked onto the M1 branch as `fa2eb388` and merged back, `8273429f`). Run 2 on `8273429f`: test and lint GREEN (30 min 34 s).
- `80373fdc` (2026-10-26): merge of `origin/25637/user-events-v2` at M1 r3 `f6b7949e` into `25638/domain-history`, clean (the `bulk_create(commit=)` change was already identical), pushed; CI pending. Lint clean on the merged tree.

## How
- **Migration `m8qz4tkv2wdc`** (parent `w305gb1epmd1`): `talent_status_history` (composite FK to talent, RLS via parent talent like `talent_change_history`, indexes tenant/talent/created_at + tenant/new_status/created_at); `role.closed_at` (naive, like `open_at`) + `close_reason varchar(32)`; `application.origin/origin_rank/origin_score`; `application_workflow_step_history.rank_at_change/score_at_change`; `source_notification_id` on `contact_interaction`, `talent_interaction`, `candidate_email_batch` (FK notification SET NULL, added `NOT VALID` + `VALIDATE` in the autocommit block because contact_interaction is 3M rows on kforce-dev; partial indexes CONCURRENTLY); `organization_deal.origin`; `ix_application_role_matching_score (tenant_id, role_id, matching_score) WHERE matching_score IS NOT NULL` CONCURRENTLY (tenant_id first: with `(role_id, matching_score)` the dev planner kept using `uq_application_tenant_role_talent` and filtered the score in memory, 8.8 ms for a 1,500-row role). All additive and nullable. Same `_long_step_timeouts` (15 min statement / no lock timeout) and INVALID-index probe as M1.
- **Catalog** (`adoption/schemas.py`): `talent_status_changed`, `application_created`, `similar_candidates_run`, `candidate_email_sent`, `bulk_candidate_email_sent` + `UserEventEntityType.APPLICATION`. `deal_created` dropped.
- **Talent status**: new submodule `talent/status_history/` (model, repo, `TalentStatusHistoryService.record(... commit=False)` + event). `TalentService._record_status_change` runs before the committing repo call in both `update()` branches and in `create_talent` (`self.create(..., commit=False)` + `repo.commit()`). Source `sync` on `/internal` (row only, `changed_by_id` NULL), `user` otherwise; a cleared status writes nothing.
- **Role close**: `RoleService._update` stamps `db_role.closed_at` on entering Closed/Archived, clears `closed_at` + `close_reason` on leaving; `RoleUpdate.close_reason` (`RoleCloseReason` StrEnum) is dropped from the payload unless the role ends up closed. `RoleListSummaryResponse` gains both fields. Filled is not a close (OQ9).
- **hired_at**: `RolePlacementService._stamp_status_change(old_status, entity, current_hired_at)` stamps `hired_at = status_change_at.date()` only on a move to Filled with no hire date in the payload and none on the row; the create path mirrors it. Changes the "nothing stamps hired_at" contract pinned by `test_placement_hired_at.py` (test rewritten; the reporting value is unchanged because `_hired_at()` already coalesced to `status_change_at`).
- **Applications**: `ApplicationService.create(..., origin: ApplicationOrigin)` keyword-only; callers: `POST /applications` manual, `/internal/applications` import, native apply (`talent.channel == linkedin` → extension, else manual), public apply self_applied, partner `/integrations` create → import. `application_created` only when `user_id` is set (record() skips /internal anyway). `create_match_applications(..., origin=MATCHING_ENGINE, actor_id=None)`: repo inserts with `bulk_create(commit=False)`, the service records per-row events for the actor and commits (`TenantScopedRepository.bulk_create` gained `commit`). `MatchService.match_*` take `actor_id` (public `POST /matches` passes the user; internal/engine none). Expand: `expand_matches_for_role(role_id, actor_id)` records `similar_candidates_run` BEFORE the insert (same commit; counts = len(talent_scores), exact unless a concurrent insert races) and on the cap branch commits it itself. `_create_step_history(application, ...)` computes rank = 1 + `count_better_scored(role_id, score)`; `bulk_update_matching` runs `_FIRST_SCORE_SQL` to fill `origin_score/origin_rank` where NULL.
- **source_notification_id**: `NotificationService.ensure_owned(notification_id, user_id)` → 404 `notification_not_found` (named `ensure_`, not `assert_`: MagicMock treats `assert_*` attributes as invalid assertions). Public create bodies are new subclasses `InteractionCreateRequest` / `TalentInteractionCreateRequest` so the bulk and internal shapes stay untouched; the services read the caller from `get_request_context().user_id or api_key_user_id` because the contact interaction router is included under BOTH `/contacts/...` and `/internal/contacts/...` (a JWT dependency broke the API-key path). `BulkCandidateEmailRequest/Response` gain the field; `enqueue_bulk` validates it before any write.
- **Emails**: `CandidateEmailService._record_events` writes `bulk_candidate_email_sent` + one `candidate_email_sent` per recipient before the enqueue commit; `_record_telemetry` removed. The batch gets an explicit `id=uuid.uuid4()` so the events can reference it before flush (also what the `__new__`-based unit tests need).
- **Deals**: `origin: Literal["inbound","outbound"] | None` on `OrganizationDealBase` (internal create/update + response).

## Decisions (user, 2026-10-26, all 7 recommendations)
- `application_created` only for user-caused creations; engine runs, self-apply and /internal imports carry `origin` on the row alone.
- `origin_score` / `origin_rank` filled at the first scoring (bulk matching callback), never moved.
- Partner `/integrations/v1/applications` creates = `import`.
- `candidate_email_sent` at enqueue (same transaction), not in the worker.
- `deal_created` dropped (deals only via /internal).
- `source_notification_id` on the two interaction POSTs + bulk email only.
- Own `talent_status_history` table; stacked branch on M1.
- `closed_at` naive UTC like `open_at` (PRD said timestamptz). `hired_at` takes the transition date (an import's `status_change_at` when sent) rather than "today": same value for live moves, right value for replays.

## Gotchas
- FastAPI 0.139 / tests: the suite's auth override returns the user id without running `get_user_id`, so `get_request_context().user_id` is None in request tests. Services that read the actor from the context need a test override that sets it (`test_source_notification.py::_user_in_request_context`); services that take the actor from a route dependency (expand, talent interaction) work with the plain override.
- `TestClient` tests of `/internal/contacts/{id}/interactions` share the public router object: never add a JWT-only dependency to a route of `contact/interaction/routers.py`.
- The hired_at test module pinned "nothing stamps hired_at" with `_stamp_status_change` unit tests; the new contract is documented in its docstring.
- Polyfactory `UserFactory` randomizes `vendor_id`: pass `vendor_id=mocked_vendor.id` or the composite FK `fk_user_vendor_tenant` fails.
- Migration smoke (temp test, deleted): rewind to the M1 shape + stamp `w305gb1epmd1` → upgrade / downgrade -1 / upgrade OK; FKs validated, 6 indexes valid, policy canonical, timeouts restored.

## Evidence
- Targeted suites 2026-10-26: new M2 tests 80 passed; regression around the touched services 545 passed (+ native apply fixed, 12 passed). Full unit + multitenancy left to CI (local run stopped on the user's call).
- kforce-dev 2026-10-26 (rolled-back DDL): contact_interaction 3.05M rows / 3.0 GB → ADD COLUMN + ADD CONSTRAINT NOT VALID 0.3 s, VALIDATE CONSTRAINT 8.2 s, partial index (plain build) 14.6 s / 8 kB. dev (application 128,639 rows): rank count for the role with most scored applications 0.29 ms index-only on `(tenant_id, role_id, matching_score)` vs 8.8 ms with `(role_id, matching_score)` (planner kept `uq_application_tenant_role_talent`); first-score fill for 30 ids 23 ms vs 140 ms. Scripts: worktree `.claude/worktrees/tmp/m2_kforce_dev_evidence.sql`, `m2_echo_dev_evidence.sql` (+ `.out`).

## Pending
- [ ] Leo's review, merge AFTER #2458 (CI green on `8273429f` 2026-10-26).
- [ ] After #2458 merges: retarget the PR to dev and rebase.
- [ ] Tell Flor: `close_reason` values, `closed_at` / `close_reason` in role responses, `origin*` in application responses, `source_notification_id` on the two interaction POSTs + bulk email (echoed), 404 `notification_not_found`.
- [ ] Tell Nico: `docs/customer_metrics_m2_domain_history.sql`; every series starts at the M2 deploy date.
- [ ] US 25638 description: `deal_created` dropped, hired_at date rule, application_created rule.

## Related
- [[Customer metrics M1 - user_events v2 and durable write path (US 25637)]] · [[Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)]]
