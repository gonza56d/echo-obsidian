---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-06-17
tags: [bugfix, application, comments, rls]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1573"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23112"
---

# Application comment RLS write denial (Bug 23112)

Migration `aigtlrr5wami` (2026-06-08) enabled RLS on `application_comment` but created only a `FOR SELECT` policy. Postgres does not authorize writes through a SELECT policy, so every comment INSERT/UPDATE/DELETE by the RLS-bound auth role was default-denied — `POST /applications/{id}/comments` 500'd (`new row violates row-level security policy`) for **every** user from the migration's deploy (~2026-06-09) until the fix. Filed and fixed the same day (2026-06-17): the policy was recreated as `FOR ALL`.

## Azure / docs
- [Bug 23112](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23112) — filed + fixed 2026-06-17; sat in **New** until 2026-07-27, then Closed "Fixed and verified" with a resolution comment (backfill session).

## PRs
- [#1573](https://github.com/taller-projects/echo-backend/pull/1573) → dev — merged 2026-06-17 (squash `37987035`; the same commit is on `qa` and `main` via the release train → in prod).

## How
- Migration `dvmw0w899yrl` drops the SELECT-only "Allow access via parent application" policy and recreates it `FOR ALL` with the same `USING` (EXISTS on parent `application` matching `application_id` + `tenant_id`). Postgres applies `USING` as the `WITH CHECK` when none is given, so write authorization = parent-application visibility — the same shape as the `application` table's own policy. RLS stays enabled.
- Heads-merge migration `rk7m2qwz9x4n` reconciles it with the concurrent adoption head.
- Guard tests in `tests/unit/test_application_rls_policies.py` rewritten: `test_comment_rls_policy_is_select_only` (which *enforced the bug*) replaced by `test_comment_rls_policy_allows_writes`, `test_comment_rls_fix_migration_allows_writes`, plus parent-reference and RLS-enabled assertions on the model spec + migration source.

## Decisions
- Kept authorization fully delegated to RLS (no app-layer permission gate on comment create) — only the policy was fixed to actually grant writes.
- `FOR ALL` with `USING` only (no separate `WITH CHECK`): identical predicate for read and write, mirroring the `application` policy.

## Gotchas
- The SELECT-only policy was **intentional and locked by a unit test** whose rationale ("comments are written through the service layer, not directly by the DB user") was wrong — the service layer's writes run as the RLS-bound auth role. A guard test can enforce a bug.
- CI could not catch it: the testcontainers harness bypasses RLS (`create_all`, owner role, `ENABLE_ACCESS_CONTROL=False`), so RLS regressions are invisible in tests. DDL-assertion unit tests over the model spec + migration files are the real guard (the `test_application_rls_policies.py` pattern).
- No app-layer gate means an RLS denial surfaces as a **500**, not a 403 — total-but-quiet breakage: no comment was created on dev between 2026-06-09 and the fix, and nobody filed it for 8 days.
- `application_comment_mention` has RLS disabled → unaffected.

## Verification
- DEV DB (2026-07-27): `pg_policy` shows the single policy with `polcmd = *` (ALL); 36 comments created after 2026-06-17, latest 2026-07-21 — writes healthy. QA/prod not queried directly (QA blocked in session, no prod creds) but both branches carry the migration and no recurrence in 6 weeks.

## Pending
- (none)

## Related
- Bug [23106](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23106) / [#1568](https://github.com/taller-projects/echo-backend/pull/1568) — mentionable-users `uuid = text` fix; found in the same investigation, different root cause. [[Mentionable users uuid=text fix (Bug 23106)]]
