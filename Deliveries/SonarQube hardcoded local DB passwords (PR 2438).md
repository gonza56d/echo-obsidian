---
type: delivery
status: in-review
env: both
delivered:
tags: [security, sonarqube, vanta, chore, scripts]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2438"
fe_prs: []
tickets: []
prd: ""
---

# SonarQube hardcoded local DB passwords (PR 2438)

Alan posted in #echo-data-devops on 2026-10-09 (https://taller-tech.slack.com/archives/C08ECBFTQJC/p1791515577428749) a table of open SonarQube "hardcoded credentials" findings across Taller repos and asked each owner to remove the references so the scan stops failing. The echo-backend row names two files: `scripts/fase6/reset_clone.sh` (lines 5, 7, 13, 14, 15) and `scripts/seed_kforce_tenant.py` (line 65), both PostgreSQL passwords. Both are local-only values (the throwaway pg17 KForce clone on `localhost:5433` from the Fase 6 convergence tooling, and a docstring example), so Alan's "rotate if it is a prod DB" clause does not apply. Fixed 2026-10-20 in [#2438](https://github.com/taller-projects/echo-backend/pull/2438): no credentials left in the repo, nothing runtime touched.

## Azure / docs
- No Azure ticket (Slack request, chore). Sonar project `taller-projects_echo-backend_AY97urhTcAV8DED7N6yA`, scan runs from `.github/workflows/test.yml` (`SONAR_TOKEN` / `SONAR_HOST_URL`).
- Slack: Alan's request https://taller-tech.slack.com/archives/C08ECBFTQJC/p1791515577428749 · the findings table https://taller-tech.slack.com/archives/C08ECBFTQJC/p1791515579269999 (a Slack table, not an image; the API returns it as an empty attachment, read it in the web client). Read-only, no reply posted.
- The same table lists other repos (taller_kforce_integration_api, notebooks in 7 Echo Core repos, 4 retired repos); only echo-backend is ours here.

## PRs
- [#2438](https://github.com/taller-projects/echo-backend/pull/2438) → dev — OPEN 2026-10-20 (branch `chore/sonar_hardcoded_db_passwords`, head `7d1ae49a`, assignee gonza-taller). Three files, 18+/9-.

## How
- `scripts/fase6/reset_clone.sh`: `URL` comes from `KFORCE_CLONE_URL` (`${VAR:?msg}` fails fast when unset); the five `PGPASSWORD=clone` prefixes are gone, `psql` takes the password from the caller's `PGPASSWORD` / `~/.pgpass`. Stale `scratchpad/` usage path fixed.
- `scripts/seed_kforce_tenant.py` docstring: the usage example is now `PGPASSWORD=... python ... --db-url postgresql://postgres@localhost:5433/postgres` (libpq via psycopg2 honors `PGPASSWORD`, and `validate_target` only inspects the host).
- `scripts/fase6/README.md`: documents the new invocation.
- Verified: `bash -n`, the guard aborts with its message without the env var, ruff check + format clean on the seed script, grep for `user:pass@` / `PGPASSWORD=<literal>` in the touched files → none.

## Decisions
- Scope = exactly Alan's two findings. `tests/conftest.py` (`PostgresContainer(..., password="test")`) and `.env.copy` (`POSTGRES_PASSWORD=postgres`) also hold local test passwords but Sonar did not flag them, so they were left alone.
- Placeholder style follows CLAUDE.md's psql guidance (password-less DSN + `PGPASSWORD`), not `<password>` inside the URL, so the secret-detection rule has nothing URL-shaped to match.

## Gotchas
- Sonar's table says "GitHub, not ADO" for this repo: the finding lives in the GitHub-side SonarQube project, not Azure DevOps.
- Reading Slack tables: `slack_read_thread` shows `Attachment: [no preview available]` and file search finds nothing; the web client (`app.slack.com/client/TDSJQ944T/C08ECBFTQJC`) renders the table and `get_page_text` returns it.
- SSH push to github.com worked again today (it had timed out on 2026-10-19).

## Pending
- Review + squash-merge to dev; qa/main promotion with the next release.
- Confirm on the next SonarQube scan of `dev` that both findings close; no reply to Alan requested (read-only thread).

## Related
- [[Map - Pentest 2026]] (Vanta/security hygiene) · [[Map - Kforce]] (Fase 6 convergence tooling the script belongs to)
