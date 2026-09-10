---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, contact, background-job, migration]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2248"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24873"
---

# Last Interaction stale for future-dated interactions (Bug 24873)

Jake (Battle Tested, prod) added interactions and the Contacts list kept showing **Last Interaction = N/A**. `contact.last_interaction_*` / `client_visits_count` recompute only on write and (since [#1711](https://github.com/taller-projects/echo-backend/pull/1711)) only count `date <= now()` — so a "log it now" interaction stamped by a client clock a few seconds ahead is excluded at create time and never re-evaluated, and a legitimate future follow-up is never promoted when its date arrives. Measured stale (2026-09-10): **prod 112** (Navitec 53, Taller 45, Battle Tested 14), **kforce-dev 407**.

## Azure / docs
- [Bug 24873](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24873) — Active, assigned Gonzalo; PR link + fix summary commented.

## PRs
- [#2248](https://github.com/taller-projects/echo-backend/pull/2248) → dev — OPEN 2026-09-10 (branch `24873/last_interaction_refresh`); self-review round 1 fixes pushed `45bd6d86` 2026-09-10 (clamp moved write-side, null guard, tenant filter on schedule feed)

## How
- **Clamp clock skew** — `InteractionInput.date` field_validator (`app/modules/contact/interaction/schemas.py`), a write-side base between `InteractionBase` and create/update: dates ≤ `CLOCK_SKEW_TOLERANCE` (5 min) in the future clamp to server `now()`, preserving naive/aware form; `InteractionResponse` sits on `InteractionBase` so reads never clamp. Guards `None` (partial_model widens `date` to Optional). FE keeps sending `new Date().toISOString()` untouched.
- **Deferred refresh for matured follow-ups** — new `JobKind.CONTACT_ATTRIBUTES_REFRESH`; `ContactService.refresh_contacts` (single choke point for every interaction write path) calls `schedule_future_interaction_refresh`: per contact with a still-future interaction, `enqueue_job_if_absent(available_at = min future date + 5s buffer)` (`MATURED_FOLLOW_UP_REFRESH_BUFFER`), `BULK_PRIORITY`. Handler (`ContactAttributesRefreshJobHandler`) re-runs `refresh_contacts` under the job's tenant context; **chaining to the next follow-up happens in `on_terminal`**, because the running job still holds the active `(kind, entity)` unique slot during `__call__`.
- **Writer support** — `enqueue_job_if_absent` gained `available_at`; new `lower_pending_available_at` pulls a PENDING deferral earlier (never later) when a sooner follow-up lands while the slot is taken.
- **Backfill migration `xixzu7qk7bos`** — k7n3wq9x2rmp's recompute re-scoped to "has an occurred interaction newer than the denormalized `last_interaction_date`". Idempotent; `SET LOCAL lock_timeout 10s` + `statement_timeout 120s` (justified in-file: scope scan ~11s on kforce-dev's 2.7M `contact_interaction`).
- Tests: `tests/unit/test_matured_follow_up_refresh.py` (17) — clamp variants + tolerance boundary + null-date update + response round-trip, end-to-end "seconds-ahead interaction wins immediately", scheduling (enqueue / no-op / pull-forward / never push back), handler promote / missing-contact ack / terminal chaining; `tests/multitenancy/test_contact_refresh_job_isolation.py` (2) — schedule feed ignores foreign contacts, handler acks foreign-tenant jobs untouched.

## Decisions
- Clamp lives in the **schema** (team convention: validation in Pydantic, not services); tolerance 5 min — beyond it the date is a real follow-up and the deferred job owns it.
- Backfill scope is "denormalized behind an occurred interaction", NOT k7n3wq9x2rmp's "has a future interaction" — the clock-skew rows' dates have already passed, the old scope misses them entirely.
- Migration (not manual SQL) so qa + kforce-prod heal too; verified the scope query returns exactly the 112 prod contacts and found 407 on kforce-dev.
- `on_terminal` re-schedules on EVERY terminal status (even dead) — a dead job must not orphan remaining follow-ups; refresh is cheap/idempotent so this can't loop hot (next available_at is in the future).
- (r1 review) Clamp is **write-side only**: field validators also run on `model_validate(orm_row)`, so on `InteractionResponse` it rewrote stored follow-up dates inside the tolerance window on every read (and an FE read-modify-write would persist that). Hence the `InteractionInput` intermediate.
- (r1 review) `next_future_interaction_dates` filters by context tenant in the repo: `contact_interaction`'s RLS policy is the permissive "Backend full access", so repo-level filtering is the only isolation; `lower_pending_available_at` now requires `tenant_id` too.

## Gotchas
- `Interaction.date` is a **naive** timestamp column while `background_job.available_at` is timestamptz — attach `timezone.utc` when scheduling (`run_at.replace(tzinfo=...)`).
- The active-entity unique index (`uq_background_job_active_entity`) covers pending AND running — a handler can never re-enqueue its own entity from `__call__`; use the terminal hook.
- Migration smoke-tested on throwaway pgvector Postgres: the alembic chain needs a stubbed Supabase `auth.users` table (`CREATE SCHEMA auth; CREATE TABLE auth.users (...)`) to get past an early trigger migration.
- Worktree sessions: `source scripts/venv.sh` is blocked by the worktree bash guard — call `/Users/gonza56d/taller/repos/echo-backend/.venv/bin/python|alembic|ruff` binaries directly; `.env` copied into the worktree cwd.
- A validator on a schema base class leaks into every subclass — including the Response model (`InteractionResponse(TimestampOrmBaseModel, InteractionCreate)` was the trap). Put input sanitization on an input-only intermediate, and remember `@partial_model` widens every field to Optional, so validators must tolerate `None` or PATCH with an explicit null 500s.

## Pending
- Team review → merge #2248 → dev deploy (migration runs the backfill on dev + kforce-dev). Self-review (full rubric, 3 agents) done 2026-09-10: 3 blockers + 4 nits found and fixed in `45bd6d86` (CI green on `260e1c22`; pending on `45bd6d86`).
- Verify on dev: create interaction → Last Interaction immediate; future follow-up → pending `contact_attributes_refresh` job.
- Bug 24873 → Ready to Test after dev verification; qa/main promotion (prod backfill heals the 112; kforce-prod heals via same deploy).
- Consider the ticket's optional periodic-sweep safety net only if a stale contact ever reappears (deliberately left out — chaining covers it).

## Related
- [[Future-dated interactions fix (Bug 23383)]] — the #1711 fix whose write-path-only scope this completes.
- [[Map - Contact Relationships]]
