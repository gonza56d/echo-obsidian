---
type: delivery
status: in-review
env: both
delivered: 2026-09-23
tags: [bugfix, matching, vectorizer, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2334"
  - "https://github.com/taller-projects/echo-backend/pull/2335"
fe_prs: []
tickets: []
prd: ""
---

# Evaluate batch scoped to new candidates (PR 2334)

Navitec reported that role 3093's LLM scores changed "on their own". Every Add Candidates, Get 10 more or talent onboarding sent `evaluate_batch` with only `job_id`. The matching API reads that as "re-evaluate every application of the role", and because the model is non-deterministic, existing candidates' scores re-rolled. For example, 3 added candidates produced 257 OpenAI evaluations on 2026-09-08. Pedro's [#2334](https://github.com/taller-projects/echo-backend/pull/2334) sends `candidate_ids` for the talents each role just matched. `rematch_role` stays role-only on purpose, because it is the explicit full re-evaluation. The follow-up [#2335](https://github.com/taller-projects/echo-backend/pull/2335) (Gonzalo) adds the missing regression tests and closes the gaps the review found.

## Azure / docs
- No ticket for either PR. Upstream contract: `POST /candidate_matching/evaluate_batch` accepts `job_id + candidate_ids` (the matching team confirmed this to Pedro).

## PRs
- [#2334](https://github.com/taller-projects/echo-backend/pull/2334) → dev: Pedro, MERGED 2026-09-23 as merge commit `67d06c51`. I reviewed it: /pr-review r1 verdict CHANGES REQUESTED (2 test blockers), posted as an APPROVE review at the user's request ([review 5293638485](https://github.com/taller-projects/echo-backend/pull/2334#pullrequestreview-5293638485)).
- [#2335](https://github.com/taller-projects/echo-backend/pull/2335) → dev: my follow-up, OPEN 2026-09-23 (`e53dc50c`).
- FE: no contract change. The per-row "Re-match candidate" button (`MatchingScoreCell.tsx` → `POST /matches?role_id&talent_id`) now re-evaluates only that pair.

## How
- `VectorizerService.evaluate_application_batch(job_id, tenant_id, *, candidate_ids=None, ...)` (real and mock). The body carries `candidate_ids` only when given. An empty list returns `None` with no call.
- `ApplicationService.create_match_applications` groups the returned rows by `(role_id, tenant_id)` into `talents_by_role` and makes one batch call per role.
- The flows that reach it:
  - Add Candidates: `match_single_talent_to_role`, upsert.
  - Get 10 more: `expand_matches_for_role`, `"ignore"`.
  - `match_single_role`: role enhancement and `POST /matches?role_id=`.
  - Onboarding: `match_single_talent`, broken, see Gotchas.

## Decisions
- **Empty `candidate_ids` → skip the call, NOT `if candidate_ids:`.** Dropping the key widens the call into the role-wide batch, which is the original bug. My posted #2334 review wrongly suggested `if candidate_ids:`; #2335 does the early return instead.
- Params after `tenant_id` are keyword-only. The mock has no `@validate_call`, so a positional `instructions` would have bound silently to `candidate_ids`.
- Re-adding an already-applied talent re-evaluates that pair. This is intended: the FE "Re-match candidate" button depends on it. The upsert `RETURNING` yields the updated row.

## Gotchas
- `on_conflict="update"` RETURNING includes upserted pre-existing rows, not only inserts. Only expand uses `"ignore"`.
- The worktree session's Bash refuses compound `cd … && git …` / heredoc-python commands ("too complex to verify"). Write a temp script inside the worktree and run it plainly.
- ruff on `tests/` reformats unrelated code, because CI lints only `app/`. Restore the test files and re-apply only your edits.
- `match_single_talent` (`POST /matches?talent_id=` with no role_id) raises AttributeError on dev. `ApplicationRepository.get_match_talent_to_roles` joins on `Role.workflow_step_id`, but the real column is `role_workflow_step_id`. It has been broken since [#1225](https://github.com/taller-projects/echo-backend/pull/1225) (`29a23d6f`), so the onboarding flow #2334 listed never reaches the batch.

## Pending
- Merge [#2335](https://github.com/taller-projects/echo-backend/pull/2335) to dev.
- Dev verification: run Add Candidates on a role that has applications, then confirm in Loki (`matching-products-api`) that only the added candidate was evaluated.
- Answers from Pedro or the matching team: is `candidate_ids` deployed on every matching env (dev/qa/prod/kforce-dev/kforce-prod)? Fire-and-forget swallows 422s. What does upstream do with ids that have no application row?
- Open product question: after role enhancement, `match_single_role` now evaluates only the top-N rows it returns. Apps outside the new top-N on a retried FAILED role keep evaluations made against the old JD. Is that acceptable, with rematch as the full re-evaluation?
- File a Bug for the `match_single_talent` AttributeError (unfiled).
- qa/main promotion.

## Related
- [[Matching batch status proxy (US 24774)]]: `capture_batch_id` opt-in; only rematch captures a batch id.
- [[Map - Observability & Reliability]]
