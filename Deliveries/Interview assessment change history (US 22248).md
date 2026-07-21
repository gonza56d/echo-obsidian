---
type: delivery
status: merged
env: taller
delivered:
tags: [feature, bugfix, interviews, migrations, tests]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1848"
  - "https://github.com/taller-projects/echo-backend/pull/1879"
  - "https://github.com/taller-projects/echo-backend/pull/1880"
fe_prs:
  - "https://github.com/taller-projects/echo-frontend/pull/2970"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22248"
prd: ""
---

# Interview assessment change history (US 22248)

Melina's BE PR for US 22248 (reopen finished interviews + assessment change
history): reuses `InterviewHistory` with a new `ASSESSMENT_UPDATED` action, a
trigger in `InterviewService.update` on content-field changes, a paginated
`GET /assessments/interviews/{id}/change-history` endpoint, and a data
migration (`3gufg5ykw01g`) that rescues coordinator edits stranded in "BASE"
snapshots (~51 prod rows). My contribution (2026-07-17): fixed the red CI
pipeline, found + fixed a real ordering bug in the backfill migration, ran
the full /pr-review protocol (verdict READY WITH NITS, 0 blockers), and
pushed the nit fixes (`cd3c0c80` + `4cae3e48`).

## Azure / docs
- [US 22248](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22248)

## PRs
- [#1848](https://github.com/taller-projects/echo-backend/pull/1848) → dev — **merged** (merge commit `5057e358`), author Melina; my fix commits `9854cfac` + `d30bf929` pushed 2026-07-17
- FE: [#2970](https://github.com/taller-projects/echo-frontend/pull/2970) — must merge AFTER the BE PR (FE stops PATCHing the BASE snapshot and edits the interview directly)

## How
- Fix 1 — CI (5 setup errors): `InterviewFactory` is the first factory whose
  product gets **persisted** via `create_entity`; polyfactory fills optional
  UUIDs randomly → FK violations on `interviewer_id` / `created_by_id` /
  `scheduled_by_id`. Pinned all three to `None` in `tests/factories.py`
  (same rationale as `RoleFactory`).
- Fix 2 — migration no-op bug: the backfill's shared CTE has an idempotency
  guard (`NOT EXISTS` an `ASSESSMENT_UPDATED` row at `base.updated_at`), and
  the coordinator-edit seed **inserts exactly that row**. Each statement
  re-evaluates the CTE, so the interview-overwrite step (run last) always
  selected 0 rows — coordinator edits were never copied onto the interview.
  Fix: `UPGRADE_STATEMENTS` tuple as single ordered source (submission seed
  → overwrite → coordinator-edit seed LAST); `upgrade()` and the system
  tests iterate the same tuple.
- Review round 1 (2026-07-17, /pr-review full mode, 3 parallel agents):
  9/9 BE-scoped ticket requirements implemented, 0 blockers. Nit fixes
  pushed as `cd3c0c80` (migration hardening) + `4cae3e48` (module cleanup):
  - Migration: `NULLIF(base_content->'<jsonb_field>', 'null'::jsonb)` — an
    explicit JSON null in BASE content is `'null'::jsonb`, NOT SQL NULL, so
    it survived COALESCE and would overwrite real data; skip interviews
    where `finished_at = base.updated_at` (submission seed would collide
    with the idempotency marker → stranded half-migrated); `updated_at
    DESC` tie-break on newest-BASE selection; trimmed AI-process note from
    docstring.
  - `change_history`: `assessment_interview_id` removed from the filter
    (was a client-settable OpenAPI param the router always overwrote) —
    now flows router → `get_all(assessment_interview_id=...)` kwarg →
    repo `_base_query` override (application-comments pattern); bare
    `model =` attribute.
  - New tests: explicit-null content edit records ASSESSMENT_UPDATED;
    `order_by=-created_at`; system tests for jsonb-null BASE content and
    the marker-collision skip. Reverted formatting-only churn in
    `test_interview_history.py` (diff now purely additive).
  - Verified: 35/35 tests green locally (unit + system incl. migration).

## Decisions
- Fixed at factory level (not per-test fixture pins) so future persisted
  interviews are safe by default.
- Reorder over guard-rewrite: the submission seed must read pre-overwrite
  content, and the marker-planting statement simply has to run last.

## Gotchas
- **CI only runs `tests/unit`** (sh-vs-bash bug in `scripts/test.sh`) — the
  3 failing system tests that exposed the migration bug would NEVER have
  failed in CI. A green check on a data-migration PR proves nothing about
  the migration; run `scripts/test.sh all` locally.
- Polyfactory + `create_entity`: any `ModelFactory` whose schema has
  optional FK UUID fields will randomly violate FKs when persisted — check
  new factories for FK fields and pin them to `None`.
- The idempotency-marker pattern (guard on a row you also insert) makes
  statement ORDER load-bearing; keep order in one tuple that tests import.

## Pending
- Before running the backfill in prod: re-confirm divergence COUNT with a
  read-only SELECT (~51 expected, per PR description). Also add
  `AND updated_at - created_at > interval '1 second'` to size the
  TimestampMixin microsecond-drift false positives (created_at/updated_at
  are two separate `now()` lambdas at INSERT).
- Merge order: BE [#1848](https://github.com/taller-projects/echo-backend/pull/1848) first, then FE [#2970](https://github.com/taller-projects/echo-frontend/pull/2970).
- Open review questions for Melina (non-blocking):
  1. Confirm FE #2970 consumes the MIXED-action timeline (endpoint returns
     all actions, no `action` filter); if FE filters to ASSESSMENT_UPDATED,
     content edits bundled with interviewer/time changes become invisible
     (elif chain records only INTERVIEWER_UPDATED/CHANGED_TIME).
  2. Deploy-window drift: coordinator edits between the BE deploy
     (migration runs) and the FE deploy still PATCH the BASE snapshot and
     are never backfilled — keep the window short / re-check COUNT after
     FE deploy.
  3. `modified_attributes` may mint spurious ASSESSMENT_UPDATED rows on
     no-op re-sends of jsonb content (shallow dict compare vs stored
     JSONB) — sanity-check with a real FE payload.
- Follow-up PR (out of scope here): promote `modified_attributes` from
  `app/modules/role/service.py` to `app/core/` (3 modules import it now).

(Closed 2026-07-17: CI green on both check runs after the fix push; the 30
local `test_application_*` failures were confirmed pre-existing local-only
artifacts — identical test-by-test in a pre-fix baseline run, green in CI.)

## Promotion to qa/main — 2026-07-21

Cherry-picks opened to promote #1848 up the pipeline, **batched with Open Jobs 1-5 matching (US 23640, [[Open Jobs 1-5 matching (US 23640)]])** so both features release to `main`/prod together:

- **qa: PR [#1879](https://github.com/taller-projects/echo-backend/pull/1879)** — branch `cherry-pick/interview_change_history_qa` → `qa`.
- **main/PROD: PR [#1880](https://github.com/taller-projects/echo-backend/pull/1880)** — branch `cherry-pick/interview_change_history_main` → `main`.

**How built:** the 5 feature commits of #1848 cherry-picked **cleanly (zero conflicts)** onto `origin/qa` and `origin/main` via isolated scratch worktrees. The 13 feature files are **byte-identical to dev**; only `app/routers.py` differs (qa/main's existing content + the one-router wiring). Full branch diff vs base = exactly the 14 PR files (`+1536/-1`). ruff `app/` clean, single alembic head.

**Gotcha — do NOT cherry-pick the merge commit's `parent1..parent2` diff.** #1848 merged to dev via merge commit `5057e358`, but its branch was never rebased onto the newer dev, so `5057e358^1..5057e358^2` is polluted by unrelated `case_study`/`role`/`solution_service` **deletions** (a separate PR that landed on dev meanwhile). The true PR diff is `merge-base(^1,^2)..^2` = the 5 commits `a0e330c8..4cae3e48` — cherry-pick those.

**Migration chain:** `3gufg5ykw01g` keeps its dev `down_revision = q8vd3mzk7w2p` (the current qa/main head, confirmed applied in both the qa **and** PROD DBs read-only — no rebase needed, byte-identical to dev). It ships **before** the open-jobs wipe: the batched chain on each release branch is `q8vd3mzk7w2p → 3gufg5ykw01g → ehjnwsqitqve` (open-jobs' `ehjnwsqitqve` `down_revision` re-pointed onto `3gufg5ykw01g` on [#1875](https://github.com/taller-projects/echo-backend/pull/1875)/[#1876](https://github.com/taller-projects/echo-backend/pull/1876)). `51r81g9s8arp` (dev's contact-index between them) is a separate unshipped feature — **skipped**. **⚠️ Merge order per env: THIS interview PR first, then the open-jobs PR.** Both merge with a merge commit (release convention).

**Before the prod backfill (#1880):** re-confirm the divergence COUNT on PROD with a read-only `SELECT` (~51 at authoring); the backfill mutates prod interview data (downgrade is a documented no-op).

## Related
- [[Pending interview notifications (US 23321)]] — same interviews module
