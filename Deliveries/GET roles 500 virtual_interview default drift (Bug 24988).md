---
type: delivery
status: in-review
env: taller
delivered:
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2275"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24988"
prd:
---

# GET /roles 500 — virtual_interview default drift (Bug 24988)

`GET /roles?allows_new_applications=true&page=1` (Taller, dev) 500s with `ResponseValidationError` serializing `RoleListResponse`. Reported via Slack 2026-09-16 (logs 17:23–17:24 UTC, `unhandled_exception_in_request`, truncated traceback). Surfaced when the FE dropped `external_id__isnull=false` on the Add Candidate dropdown (Jazz cutover annex) — the poison rows all have `external_id IS NULL`, so the old filter hid them.

## Mechanism — the predicted follow-up #2 of [[Roles listing NULL-row hardening (Bug 24132)]]
Live `role.virtual_interview` DB default is `'{}'::jsonb` while the model declares `server_default="[]"` and the field is `list[Question]`. The drift was **codified by kf9cnv1tnt01** (M4: `virtual_interview default '[]'->'{}'` — shape-codification of live DBs, no ledger row / semantic intent). Inserts omitting the column at SQL level (dict/raw-SQL paths; `BaseService.create` full-dumps so standard creates are safe) store an empty OBJECT in a list field. `_null_to_field_default` only coerces `None`, so `{}` fails and one row 500s the whole Page.

Dev at fix time: **141 poison rows**, all exactly `{}`, all `external_id IS NULL`, Taller only, created 2025-06-24 → 2026-08-25. Two matched the repro filter (`allows_new_applications=true`): `1a6805f9` (Sr. Dynamics 365 Engineer), `2f5e9403` (Sr Platform/Infrastructure Engineer).

## Fix — PR [#2275](https://github.com/taller-projects/echo-backend/pull/2275) → dev (branch `24988/fix_role_virtual_interview_default_drift`, commit `1f575333`)
- Migration `wxtz7gwf7wqb` (parent `trwqpe2orkxb`): `SET DEFAULT '[]'::jsonb` + idempotent lossless heal (`WHERE virtual_interview='{}'::jsonb`). Downgrade restores `'{}'` default, does NOT un-heal (healed `[]` indistinguishable from legit empty).
- `RoleListResponse._null_to_field_default` extended: `{}` coerces to field default **on list-typed fields only** (isinstance-of-list check on the declared default). Non-empty objects still fail loudly; `{}` stays valid for `interview_questions`/`code_challenge`; create/update contracts untouched (pinned by test).
- 4 new tests in `tests/unit/test_roles.py`. Full unit+multitenancy 4856 green; migration exercised on throwaway pgvector Postgres (chain green, heal verified with seeded poison row, downgrade/upgrade round-trip).
- Commit `18437270` (post-review, 2026-09-16): `tests/unit/test_role_virtual_interview_default_migration.py` — runs the REAL `wxtz7gwf7wqb` upgrade/downgrade in-suite (`_load_migration` pattern from test_role_note_migration.py; `downgrade()` first to re-create the drifted `'{}'` default, then upgrade: default fixed, poison healed, legit row untouched, idempotent re-run) + rejection test now pins `loc == virtual_interview`.

## Review (round 1, 2026-09-16 — /pr-review, 3 subagents)
Verdict **READY WITH NITS** — 0 blockers, 0 questions. Arch 12P/0F, Tests+Sec 12P/0F, ticket compliance 7/8 (+1 partial). CI green.
- Nits 1+2 (migration heal test in-suite; pin rejection error loc) → **addressed in `18437270`**.
- Nits 3+4 skipped by choice: e2e from_attributes/Page regression (dict-based style matches 24132 precedent); `public.role` vs `public."role"` quoting cosmetics.
- Review confirmed: kf9cnv1tnt01:2587 is the ONLY jsonb default it codified — no sibling columns need healing; rollout race (old pods mid-deploy) absorbed by validator.

## Decisions / gotchas
- Reverting a convergence-codified default is safe here: kf9cnv1tnt01 matched live shape, it did not choose `{}` semantically (no unification-ledger row).
- Throwaway-Postgres chain run needs Supabase stubs: `CREATE SCHEMA auth` + minimal `auth.users` before `alembic upgrade head`.
- `PublicRoleResponse` does NOT expose `virtual_interview` — no public-api leg for this bug.

## Pending
- PR #2275 merge (review round 1 done, READY WITH NITS, nits addressed); dev deploy verify (re-run the Slack repro); qa/main promotion later.
- Bug 24988 → Closed on merge.
- **File follow-up ticket**: `app/modules/role/models.py:399` `Mapped[Dict]` → `Mapped[list]` — the type-level lie that ancestored this bug family (flagged independently by 2 reviewers).
- **Ops at deploy**: record pre/post `'{}'` counts on qa/prod/kforce on the ticket (per its System-info note).
- Still-unfiled siblings from 24132 review: #1 `PublicRoleResponse` JSON-null hardening (skills fields), #3 `ApplicationResponse` inherits-create-contract audit.

## Related
- [[Roles listing NULL-row hardening (Bug 24132)]] — predicted this exact failure (follow-up #2, was never ticketed)
- [[Push Applications Echo to JazzHR (Feature 24051)]] — the Jazz cutover whose FE filter removal surfaced it
