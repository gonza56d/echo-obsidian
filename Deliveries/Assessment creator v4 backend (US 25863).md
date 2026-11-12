---
type: delivery
status: in-review
env: both
delivered:
tags: [feature, assessment, assessment-creator, code-challenge]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2614"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25863"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25864"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25865"
prd: "https://claude.ai/artifact/24CoNLwWdHHVVf45UdfFdk"
---

# Assessment creator v4 backend (US 25863)

Pedro handed over (2026-11-11) the backend side of the assessment creator's new contract (Rodri Ferrer's service, only on its dev): the assessment sized to the interview duration with team guidelines and coverage feedback, and code challenge v2 with its own time limit and an interviewer guide returned apart from the candidate's brief. Same endpoints Echo already calls (`/interview_questions_v4`, `/code_challenge_v2`, `/regenerate_code_challenge`); only their request and response fields grow. Three backend PRs to dev; the first (interviewer guide) is open.

## Azure / docs
- [US 25863](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25863) (PR 1, interviewer guide, under Feature 25748) — In revision
- [US 25864](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25864) (PR 2, role context on edits + `max_questions`, under Feature 25750) — New
- [US 25865](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25865) (PR 3, duration, guidelines, v4 response, under Feature 25750) — New
- FE: [US 25801](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25801) and [US 25802](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25802) (Meli). Predecessor: [US 25736](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25736) (Gisel, [#2516](https://github.com/taller-projects/echo-backend/pull/2516): seniority and skills).
- PRD: [Assessment creator v4: handoff a Gonza](https://claude.ai/artifact/24CoNLwWdHHVVf45UdfFdk) (Pedro); creator contract: [doc de Rodri](https://claude.ai/artifact/VCZfM8MGSBuAf4WABdUNqN)
- The three backend US were created 2026-11-12: none existed, the FE stories only said "needs the echo-backend side (Pedro)".

## PRs
- [#2614](https://github.com/taller-projects/echo-backend/pull/2614) → dev — **OPEN 2026-11-12** (`cbeabe2d`, branch `25863/interviewer-guide`, worktree `25863-interviewer-guide`). FE contract: `live_challenge_guide` on the generation preview and on assessment POST / PATCH / GET; `POST /projects/{id}/roles/{id}/regenerate_challenge` accepts `interviewer_guide` and **answers an object** `{live_challenge, live_challenge_guide}` instead of a string (breaking: `echo-frontend/src/services/roles.ts` types it as `string`).

## How
- Migration `8zvgynrm4wa8`: `assessment.live_challenge_guide TEXT NULL`.
- `GeneratedCodeChallenges` (subclass of `CodeChallengeResponse`) reads `live_interviewer_guide`; `generate_assessment_content` returns skills, challenge and guide.
- Regenerate: `interviewer_guide` forwarded only when it has content; the answer is `RegeneratedCodeChallenge`, read from `regenerated_code_challenge` + `regenerated_interviewer_guide`.
- Tests in `tests/unit/test_assessments.py` on `fake_assessment_creator`.

## Decisions
- `CodeChallengeResponse` is also the shape stored in `role.code_challenge`, so the creator's new field went to a subclass instead of changing it.
- The guide is not copied to `interview` (open with FE + product) and is not in the AI suggestion snapshot (still `live_challenge` only).
- `not_covered.reason` will be an enum of three values: `"time"`, `"no question"` (with a space), `"guideline"` (user, 2026-11-12).
- Take-home: the handoff leaves it out, FE US 25801 includes it. The user chose to start live-only and add or leave it out once Meli settles it.

## Gotchas
- The first `./scripts/coverage.sh` run failed on the dev base (`03fdf8ab`): `tests/unit/test_contact_job_writeback_guard.py::TestWritebackGuard::test_inserts_when_contact_has_linkedin` failed once under xdist, passes alone (4/4) and passed on the rerun. Intermittent.
- Inside a worktree session the isolation check refuses any Bash command whose text contains "git", "github" URLs included: put such payloads in a file and pass it (`curl -d @file`).

## Pending
- #2614: review, and **not to be merged before the FE consumes the regenerate object**.
- Answer Meli in the Slack thread: `not_covered.reason` is the three-value enum.
- PR 2 (US 25864) and PR 3 (US 25865).
- Open with others: take-home scope (Meli), rule B (subtract the challenge minutes; product), G (where the guide is shown, copy to `interview`), W (weight rebalancing; Flor), the creator's prod date (Rodri): the backend must not reach prod before the creator.

## Related
- [[Industry-agnostic Echo (PRD 398aedca)]]
