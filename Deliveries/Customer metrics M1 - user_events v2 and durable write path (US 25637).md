---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, adoption, customer-metrics, rls, migration]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2458"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25637"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25649"
prd: "https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj"
---

# Customer metrics M1 - user_events v2 and durable write path (US 25637)

Customer metrics M1. `user_events` gets entity / source / client event id columns. Business events stop riding the best-effort telemetry bus: they are written inside the transaction of the action that causes them. `POST /events` stores what only the browser sees. Builds on [[Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)]].

## Azure / docs
- [US 25637](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25637): In revision 2026-10-22, PR linked (GitHub Pull Request link), decisions comment posted. Parent [Feature 25635](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25635); business contract [CR 25592](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25592).
- Tech PRD: [Customer Metrics Event History — Technical PRD](https://claude.ai/artifact/3MtNDQyKXG1K6egnELoAQj), section 6 Milestone 1, updated to rev 65 with every decision below.
- Follow-up: [US 25649](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25649), user_events growth (partition monthly vs cut page_viewed). Backlog, assigned to me.

## PRs
- [#2458](https://github.com/taller-projects/echo-backend/pull/2458) → dev, OPEN 2026-10-22 (`fb8d4b92`, branch `25637/user-events-v2`, worktree `.claude/worktrees/25637-user-events-v2`).
  - Opened before the second full-suite run finished. Run 1: 6568 passed, 1 failed (my own new test, see Gotchas; fixed before commit).
  - Leo's review r1 (2026-10-26, comment 6417526841): CHANGES REQUESTED, 4 blockers + 9 nits + 3 outside-PR notes. Fixed in `31ea7db2` (worktree `.claude/worktrees/25637-user-events-v2-r2`, branch `25637/user-events-v2-r2` = origin/25637/user-events-v2 + merge of origin/dev 81496eca, pushed `HEAD:25637/user-events-v2`): (1) second alembic head → `down_revision = buzhuenvl99s`, file renamed `2026_10_26_1200-w305gb1epmd1_…`; (2) `tests/unit/test_user_events_rls_policies.py` runs the real policies through `tests/rls_probe.py` (on dev since Bug 25504); (3) `TalentCvService.create_version` owns the cv-versions flow (event first, DocumentService commits before echo-document again, `commit` kwargs reverted) and `record()` lost its `commit` kwarg (callers commit: `record_export` → `repo.db_session.commit()`); (4) kforce-dev EXPLAIN evidence in the PR body (rolled-back transaction as `echo_backend`). Nits taken: lock order `LOCK TABLE user_sessions, user_events`, 15 min statement timeout / no lock timeout for the builds, validate-before-dedupe in `record_client_events`, `occurred_at: AwareDatetime`, user_group `_record_event` outside the IntegrityError handlers, 401 + naive-offset tests, polled routes resolved by name, bulk timing (1,500 rows 166 ms / 10k 1.35 s). Skipped with reasons: body cap (ingress, per `file_validation.py`), rate limit, id existence checks, tenant-switch onboarding test. PR body refreshed; reply to Leo drafted, not posted.
  - Self-review r1 (2026-10-22, `/pr-review` full mode, 3 reviewers): 1 blocker (`cv_downloaded` was committed in a second transaction after the CV version, PRD §3 "same transaction") + nits → fixed in `f821f3d6`, pushed from worktree `.claude/worktrees/25637-user-events-v2-review` (branch `25637/user-events-v2-review` → `HEAD:25637/user-events-v2`): `commit=False` threaded through `DocumentService.create_talent_cv_version` / `create_talent_document` / `create_document`, one commit with the event; 4 KB limit measured on UTF-8 bytes (`ensure_ascii=False`); `user_event.write_failed` also on the POST /events insert; `open_session_ids` filters by tenant; schema-qualified INVALID-index probe in the migration; `UserEventSpec.data` → `payload_schema`; new tests (version rolled back with a failed event write, entity/id null pairs, 4096-byte boundary, non-ASCII payload). 285 tests in the touched files green locally. No PR comment posted (user's call).

## How
- **Migration `w305gb1epmd1`** (parent `buzhuenvl99s` since r2; was `7rpzhrwn1jy7`, a second head on dev):
  - `LOCK TABLE user_sessions, user_events IN ACCESS EXCLUSIVE MODE` first (the telemetry worker reads a session then inserts the event; the reverse order deadlocks).
  - 4 columns, metadata-only.
  - 3 indexes CONCURRENTLY in an autocommit block under `statement_timeout = 15min`, `lock_timeout = 0` (CONCURRENTLY waits on older transactions through virtualxid lock waits, which a 20 s lock_timeout aborts), rebuilt only when missing or INVALID. All partial: client_event_id NOT NULL, entity_id NOT NULL, event_type <> 'page_viewed'.
  - RLS: the old ALL policy is dropped. INSERT = request tenant; SELECT = adoption.view OR own rows; user_sessions gains an own-row SELECT.
  - Policy specs mirrored in `UserEvent` / `UserSession` `__table_args__`, in canonical pg_get_expr form.
- **Catalog** in `adoption/schemas.py`: `UserEventType` + one `UserEventData` model per type (`extra="forbid"`) + `USER_EVENT_CATALOG` (entity types, entity required, client emittable). The M5 FE types are already in.
- **Write path**:
  - `UserEventRepository` (Core inserts, no RETURNING, 1000-row chunks; `insert_skipping_duplicates` = ON CONFLICT DO NOTHING + rowcount).
  - `UserEventService.record(*events)`: never commits (the caller owns the transaction; r2 removed the `commit` kwarg); skips `/internal` like `write_outbox_event`; tenant from the request; `source=api` when `api_key_id` is set; `no_autoflush` so the action's own constraint errors surface at its own commit; `user_event.write_failed` + re-raise.
  - `record_client_events` behind `POST /events` (`events_router` in `adoption/routers.py`, mounted on the auth router).
- **Emitters moved off the bus**:
  - Contact/org trackers via `bulk_create(commit=False)` then record, then `repo.commit()`. The org tracker's `emit_event` param was removed.
  - user_group records before each commit, inside the IntegrityError try blocks.
  - Usage export `record_export` is now an instance method, `commit=True`.
  - cv_downloaded in `TalentCvService.create_version` (export module; the route is one call): hash → render → `record` → `DocumentService.create_talent_cv_version` (blob upload, `repo.save` commits version + event, echo-document indexing after the commit) → `db_session.commit()` for the deduped case.
- **Polling exclusion**: regex in `app/core/logging.py` for GET `/notifications`, `/notifications/unread_counts`, `/applications/{id}/comments`.
- **Drop log**: `TelemetryEventBus._on_queue_full` → `telemetry.event_dropped`.

## Decisions
- cv_downloaded is on `POST /talents/{id}/cv-versions`, not `/export/talent` as the PRD first said. The FE Download Resume button stores and opens CV versions since FE #3273 (2026-08-27); `/export/talent` is preview-only. Every call counts, a deduped version included.
- Counting rule (user, 2026-10-22, re-confirmed after the prod numbers): only inserted trackers count; re-tracks, unattributed tracks and /internal tracks write nothing, for contacts and companies.
  - Prod impact, contact_tracked over 90 days: prod 5,095 automated vs 1,006 manual (~84% drop); kforce-prod 32,345 vs 903 (~97% drop).
  - Dami/Paloma/Nico must be told before prod.
- A system admin exporting another tenant's usage gets the row in their own tenant + `target_tenant_id` (the INSERT policy only allows the request tenant).
- Partial indexes (user): prod user_events is 21.1M rows / 5.4 GB, +10.1M per 30 days; kforce-prod 2.86M / 704 MB, +886k; ~99.9% page_viewed. Partitioning moved to [US 25649](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25649).
- FE `occurred_at` is stored in `event_data.occurred_at`; `created_at` = receive time.

## Gotchas
- **`tests/rls_probe.py` exists on dev** (Bug 25504): installs `auth.jwt()` / `authorize()` / a non-superuser role and the models' `rls_policies` specs inside one rolled-back transaction, so the real policies CAN run in the unit suite. Set `request.tenant_id` with `set_config(..., true)` in the probe session before `acting_as`. Build rows with a dict and `UserEventRepository(SimpleNamespace(session=probe))` so the repository's own statements run under RLS.
- With the own-row SELECT policy, `INSERT ... RETURNING` of the user's OWN row passes; it fails for a row the user cannot read back (another user's event). That is what the probe test pins for the no-RETURNING rule.
- **FastAPI 0.139**: `app.routes` holds `_IncludedRouter` lazies, not `APIRoute`s, so `route.matches(scope)` finds nothing; resolve routes by name (`route.url_path_for(name, **params)` on the non-`Mount` entries; the `/internal` Mount comes first and shares function names like `get_comments`).
- kforce-dev's `auth.jwt()` reads `request.jwt.claim` OR `request.jwt.claims`; the `postgres` role there has BYPASSRLS, so plans must run under `SET LOCAL ROLE echo_backend` (allowed for postgres) with `set_config('request.jwt.claims', …)`.
- **RLS + RETURNING / ON CONFLICT**: Postgres checks the new row of `INSERT ... RETURNING` and of `INSERT ... ON CONFLICT` against the SELECT policies.
  - An insert-only policy is not enough: an ORM `session.add` (SQLAlchemy adds RETURNING for server defaults) fails for a Member, and so does the dedupe insert.
  - Verified with `.claude/worktrees/tmp/rls_check.py` on a migrated throwaway Postgres (SET LOCAL ROLE + jwt claims). Tests run without RLS and can't see it.
  - Fix: Core inserts without RETURNING + own-row SELECT policy. This extension of decision 3 was flagged to the user.
- The full alembic chain does not run from an empty DB (an old migration fails on `project_scope_enum`). The smoke used `create_all` + rewinding user_events to the pre-M1 shape + stamping the parent on the throwaway DB.
- `capture_logs` misses `EventBus` logs in the full suite (the bus caches its bound logger). Mock `bus.logger` like `test_event_bus.py` does.
- Same family, module loggers: structlog runs with `cache_logger_on_first_use=True`, so `adoption/service.py`'s `logger` binds once per process and `capture_logs` only sees it when the capturing test is the FIRST user of that logger → pass/fail depended on file order (write_path before tracker tests broke `test_a_failed_event_write_fails_the_track_and_keeps_nothing`). Assert with `patch("app.modules.adoption.service.logger")` instead; both log assertions were switched in `f821f3d6`.
- `DocumentService.create_document` → `repo.save` commits by default, so the cv-versions route committed the version before the event. Fixed with a `commit` kwarg down the three methods; the blob upload and the Echo document indexing stay outside the transaction (a failed upload now rolls the Document row back instead of leaving it committed).
- Supabase SQL editor shows only the LAST statement's result: run multi-statement queries one at a time. kforce-prod has 5 `user_events` relnames (other schemas); filter on `public`.
- `ruff format` on test files reformats unrelated lines (CI only lints `app/`). Restore the file from HEAD and re-apply only your edits.

## Evidence
- kforce-dev 2026-10-26 (339k rows / 87 MB; migration DDL in one rolled-back transaction, plans as `echo_backend` with a viewer's and a Member's claims): plain index builds 50-65 ms each (8 kB / 8 kB / 296 kB); per-type-per-month 90 d 28.7 ms, contact_tracked per month YTD 10.3 ms, distinct users per month 12.4 ms, all on `ix_user_events_tenant_type_created`; entity lookup 0.03 ms; Nico's page_viewed-per-day query unchanged (`ix_user_events_tenant_date`, 218 ms for 68.5k rows); Member insert 14.6 ms, dedupe 4.7 ms then 0.1 ms, own session 1.3 ms, sees own rows only. Script: worktree `.claude/worktrees/tmp/kforce_dev_m1_explain.sql` (+ `.out`).
- Local bulk `record()`: 1,500 rows 166 ms; 10,000 rows 1.35 s.
- Upgrade → downgrade -1 → upgrade on a throwaway Postgres; policies printed in canonical form.
- At 1.5M rows (301 MB): upgrade 3.9 s; partial indexes 56 kB / 8 kB; per-tenant/type/month query 3.1 ms (index-only scan); one durable write adds p95 0.99 ms locally.

## Pending
- [ ] CI on `31ea7db2`, post the reply to Leo (drafted in the session, not posted), his re-review, squash-merge. The PR branch now contains a merge of origin/dev (no rebase: no force-push).
- [ ] Leo's outside-PR notes: US 25637 description is behind PRD rev 65 (cv_downloaded route, own-row SELECT, policy names, partial indexes); PRD M1 checklist should say `bulk_candidate_email_sent` stays on the bus until M2; pre-existing `adoption.export.succeeded` logs `search_query` + `user_ids`.
- [ ] r1 items that need my call, not code (kforce-dev EXPLAIN now DONE in r2): (1) kforce-dev EXPLAIN of the index builds + Nico's per-tenant/type/month query — the ticket says "before merge, attached to the PR" and I attached a 1.5M-row synthetic run instead → pre-build the partial indexes on kforce-dev by hand (`IF NOT EXISTS`, seconds at 339k rows) and attach, or amend AC 9 + PRD; (2) AC 2 says "on dev before merge", impossible since dev gets the migration on merge → reword to "migrated Postgres before merge, dev Member check before qa"; (3) AC 12 clause 2 (write time of a KForce-sized batch) → paste the 1,500-row insert timing or amend now that /internal writes nothing; (4) Grafana alert → Task under US 25637 so the US cannot close without it; (5) Nico's `.sql` under docs/ (PRD Lineage: per milestone) → now or with M5; (6) onboarding auto-tracks (`workspace_setup`, `super_admin`) now land as `company_tracked` `source=ui` on the new user → decide whether they should be `system`; (7) US 25641 (M5 BE) scope now that the FE types are already client-emittable.
- [ ] AC 2: manual RLS check on dev with a Member user (track a contact, download a CV, POST /events). AC 7: p95 from Loki `http_access.process_time_ms` on dev.
- [ ] Grafana alert on `telemetry.event_dropped|Event queue full` > 10/min per env (needs an editor token; LogQL in the PR body).
- [ ] Tell Dami/Paloma + Nico: the contacts tracked drop (84% / 97%), polling no longer counts in sessions/page views, and the cross-tenant export rule; dashboard note with the deploy date.
- [ ] Tell Flor: optional `role_id` on cv-versions; the POST /events flush must use `fetch` with `keepalive` (sendBeacon can't send the Bearer header); ticket 25642.
- [ ] qa / main promotion; the migration builds the partial indexes on prod (expect ~1 min).
- [ ] [US 25649](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25649): re-measure growth 2 weeks after the M1 deploy.

## Related
- [[Customer metrics M0 - tracked events on the telemetry bus (Bug 25636)]] · [[Map - Observability & Reliability]] · [[EventBus watchdog + telemetry bus split (Bug 25276)]]
