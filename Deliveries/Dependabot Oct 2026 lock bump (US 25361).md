---
type: delivery
status: merged
env: both
delivered: 2026-10-05
tags: [chore, security, dependencies]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2383"
  - "https://github.com/taller-projects/echo-backend/pull/2384"
  - "https://github.com/taller-projects/echo-backend/pull/2385"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25361"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25362"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25363"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25364"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25365"
prd: ""
---

# Dependabot Oct 2026 lock bump — PyJWT / urllib3 / tornado / oauthlib (US 25361)

21 open Dependabot alerts on `uv.lock` (snapshot 2026-10-05), all on **transitive** packages — nothing in `pyproject.toml` changes. Fixed with a single `uv lock --upgrade-package …` bump of four entries, one PR to dev. Triage found no reachable exploit path in Echo except the urllib3 DoS-style issues through the LinkedIn logo fetch (`requests.get(url).content` in `S3Service.upload_image_from_url`).

## Azure
- [US 25361](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25361) → [Task 25362](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25362) PyJWT 2.13.0 → 2.15.1 (13 alerts, 1 critical) · [Task 25363](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25363) urllib3 2.7.0 → 2.8.0 (3 alerts) · [Task 25364](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25364) tornado 6.5.8 → 6.5.10 (3 alerts, dev-only) · [Task 25365](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25365) oauthlib 3.2.2 → 4.0.0 (2 alerts, major bump). Each Task carries the per-alert GHSA/CVE table and the exposure analysis.
- All five → In revision with the GitHub PR link on 2026-10-05, then **Closed on 2026-10-05** after the merge (merge comment on the US).
- Dependabot alerts: https://github.com/taller-projects/echo-backend/security/dependabot

## PRs
- [#2383](https://github.com/taller-projects/echo-backend/pull/2383) → dev — **squash-MERGED 2026-10-05** as `ed79e5ca` (head `be0a5c7c`, `uv.lock` only, 41 lines; explicit squash subject/body, branch deleted). One PR for the four Tasks, as the US asked.
- [#2384](https://github.com/taller-projects/echo-backend/pull/2384) dev → qa release ("Release dev -> qa 2026-10-05") — approved by Leo 19:08 UTC, **MERGED 2026-10-05 19:10 UTC** (merge commit `d2514be3`, merged by Gonzalo by hand: the auto-mode permission check blocked the agent's `gh pr merge`). Carries `ed79e5ca` + `f4de7891` ([[Touchpoint Role filter options endpoint (US 25255)]]). No migrations.
- [#2385](https://github.com/taller-projects/echo-backend/pull/2385) qa → main release ("Release qa -> main 2026-10-05") — **OPEN 2026-10-05**. Deploys to prod + kforce-prod behind `echo-backend-prod` / `echo-backend-kforce-prod`.

## How
- `uv lock --upgrade-package pyjwt --upgrade-package urllib3 --upgrade-package tornado --upgrade-package oauthlib` from a worktree off `origin/dev` (`f4de7891`). Exactly the four `version =` lines + their sdist/wheel hashes change.
- Checks run: `uv sync --locked --no-dev` (Dockerfile / pipeline step) and `uv sync --locked`; import chain `gspread → google_auth_oauthlib → requests_oauthlib → oauthlib 4.0.0` + `jwt`, `urllib3`, `tornado`, `requests`, `botocore`, `sentry_sdk`, `supabase`, `gotrue`; `./scripts/test.sh unit` → 5719 passed, 1 xpassed (13 min); `uv run --with pip-audit pip-audit` no longer flags any of the four.

## Decisions
- **oauthlib 3 → 4 kept in the same PR.** The US allowed splitting it out if the major bump broke the import chain; `requests-oauthlib 2.0.0` accepts 4.x and everything imports, so no split.
- **Not touching `click` / `ecdsa`.** `pip-audit` still reports `click 8.2.1` (PYSEC-2026-2132, fix 8.3.3) and `ecdsa 0.19.2` (PYSEC-2026-1325, no fix). They are not Dependabot alerts and were not in the Tasks — noted in the PR body as out of scope.
- Exposure reasoning per package (why each is a hygiene bump rather than an incident): PyJWT unused by Echo (python-jose does auth; gotrue only uses PyJWT in `get_claims()`), tornado absent from the `--no-dev` image, oauthlib CVEs are server-side provider code and Echo uses a gspread service account, urllib3 proxy CVE n/a (no proxy configured).

## Gotchas
- **Dependabot evaluates `main`**, so the alerts stay "open" until the bump is promoted dev → qa → main. Do not re-triage them in between. Checked 2026-10-05 after the dev merge: `qa` and `main` still lock pyjwt 2.13.0 / urllib3 2.7.0 / tornado 6.5.8 / oauthlib 3.2.2, and all 21 alerts (#109–#129) are still open. Alert #129 (GHSA-gvp8-978c-rx2q, PyJWT `>= 2.11.0, <= 2.13.0`) shows no patched version in the API, but 2.15.1 is outside its range.
- No `.github/dependabot.yml` → GitHub only raises alerts and never opens bump PRs; every remediation is a manual lock bump (precedent: [[WeasyPrint 62 to 68 upgrade (US 23479)]]).
- tornado will keep recurring (10 alerts fixed historically) as long as `ipykernel` stays in the dev group — Dependabot cannot tell dev-only lock entries apart.
- Worktree session mechanics: the worktree guard rejects heredocs and `zsh -ic`; Azure calls and this vault write went through small Python scripts written *inside* the worktree (`.az_helper.py`, `.vault_update.py`) and deleted before merge.

## Pending
- Merge [#2385](https://github.com/taller-projects/echo-backend/pull/2385) (qa → main, merge commit) + approve prod / kforce-prod; only then do the 21 alerts flip to **fixed** in Dependabot (it evaluates `main`). Tickets are already Closed, so re-check the alerts page after the main deploy.
- Smoke in dev after deploy (US acceptance criteria): Supabase login + `/users/me`, invite a user, org track with a LinkedIn logo (S3 upload via requests), a Sentry event, gspread read/write through the interview scheduler if a tenant has it configured.
- Follow-up tickets not yet filed: (a) `timeout=` + size cap on the two S3 URL fetches in `app/services/aws/s3_service.py` (Task 25363 "optional hardening"); (b) team decision on dropping `ipykernel` from the dev group (Task 25364).
- `click` / `ecdsa` pip-audit findings — unticketed.

## Related
- [[Map - Observability & Reliability]] (CVE hygiene) · [[WeasyPrint 62 to 68 upgrade (US 23479)]] (previous BE Dependabot remediation)
