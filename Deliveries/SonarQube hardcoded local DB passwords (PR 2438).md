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
- [#2438](https://github.com/taller-projects/echo-backend/pull/2438) → dev — OPEN 2026-10-20 (branch `chore/sonar_hardcoded_db_passwords`, assignee gonza-taller). First cut `7d1ae49a` (three files, 18+/9-).
- Leo r1 **CHANGES REQUESTED** 2026-10-20 ([comment](https://github.com/taller-projects/echo-backend/pull/2438#issuecomment-6299636008)): blocker = once the DSN came from `KFORCE_CLONE_URL` with no check, the script's `DROP SCHEMA public/auth/echo CASCADE` (output hidden, `ON_ERROR_STOP=0` restore, `alembic_version` overwrite) could hit any DB, e.g. a pasted pooler DSN (`postgres.<ref>` owns `public`; dev/qa/kforce-dev have no IP allowlist). Nits: silent failure of the first `psql`; possible new Sonar hotspots on test fixtures.
- r1 fixes pushed **`c7b6ce48`** 2026-10-21 (from my own worktree `.claude/worktrees/sonar_reset_clone_local_guard`, branch `chore/sonar_reset_clone_local_guard`, pushed to `HEAD:chore/sonar_hardcoded_db_passwords`; the original worktree is owned by another session). Reply to Leo drafted, **not posted**.

## How
- `scripts/fase6/reset_clone.sh`: `URL` comes from `KFORCE_CLONE_URL` (`${VAR:?msg}` fails fast when unset); the five `PGPASSWORD=clone` prefixes are gone, `psql` takes the password from the caller's `PGPASSWORD` / `~/.pgpass`. Stale `scratchpad/` usage path fixed.
- `scripts/seed_kforce_tenant.py` docstring: the usage example is now `PGPASSWORD=... python ... --db-url postgresql://postgres@localhost:5433/postgres` (libpq via psycopg2 honors `PGPASSWORD`, and `validate_target` only inspects the host).
- `scripts/fase6/README.md`: documents the new invocation.
- r1 (`c7b6ce48`): `KFORCE_CLONE_URL` optional again, default `postgresql://postgres@localhost:5433/kforce_clone` (no password); anchored regex `^postgres(ql)?://([^@/?]*@)?(localhost|127\.0\.0\.1|\[::1\])(:[0-9]+)?/[A-Za-z0-9_]+$` refuses everything else before any `psql`; `unset PGHOSTADDR PGSERVICE`; reset `psql` keeps stderr (`2>&1` dropped) and mutes the CASCADE notices with `SET client_min_messages = warning`. README + usage line say optional / local-only.
- r1 verification: `psql` stub on PATH, 14 DSNs → 5 local forms (default, localhost, 127.0.0.1, [::1], no-user) run 4 psql calls with `PGHOSTADDR` stripped; 9 refused with rc=1 and 0 psql calls (kforce-dev pooler DSN, `db.<ref>.supabase.co`, `?host=` override, `?y=@localhost:` trick, `localhost.evil.com`, multi-host, keyword conninfo, host-less `postgresql:///db`). Real psql against closed `localhost:59999`: new script prints the libpq error, old one exited 2 silently. **Not run against a live server** (Docker down, only libpq installed) → the `client_min_messages` line is unexercised.
- Verified (first cut): `bash -n`, the `:?` guard aborts with its message without the env var (replaced by the default + host guard in r1), ruff check + format clean on the seed script, grep for `user:pass@` / `PGPASSWORD=<literal>` in the touched files → none.

## Decisions
- Scope = exactly Alan's two findings. `tests/conftest.py` (`PostgresContainer(..., password="test")`) and `.env.copy` (`POSTGRES_PASSWORD=postgres`) also hold local test passwords but Sonar did not flag them, so they were left alone.
- r1: regex over Leo's suggested `case` glob (`*@localhost:*|...`): the glob still accepts `?host=` overrides, multi-host DSNs and `...@evil?x=@localhost:` shapes. Query strings are refused outright since a local clone never needs one. Host-less DSNs refused too (libpq would fall back to `PGHOST`).
- r1 Sonar nit on test fixtures (`postgres:pw@` in `tests/unit/test_seed_kforce_tenant_guards.py`, `password="test"` in `tests/conftest.py:122`): no code change; mark "Safe" in the Sonar dashboard if they show up after merge (Leo's call too).
- Placeholder style follows CLAUDE.md's psql guidance (password-less DSN + `PGPASSWORD`), not `<password>` inside the URL, so the secret-detection rule has nothing URL-shaped to match.

## Gotchas
- Sonar's table says "GitHub, not ADO" for this repo: the finding lives in the GitHub-side SonarQube project, not Azure DevOps.
- Reading Slack tables: `slack_read_thread` shows `Attachment: [no preview available]` and file search finds nothing; the web client (`app.slack.com/client/TDSJQ944T/C08ECBFTQJC`) renders the table and `get_page_text` returns it.
- Removing a hardcoded DSN can remove the only safety rail: in `reset_clone.sh` the fixed `localhost:5433` target was what kept `DROP SCHEMA ... CASCADE` off shared DBs. When parameterising a destructive script's target, add a host allowlist in the same change (precedent: `validate_target` / `LOCAL_HOSTS` in `scripts/seed_kforce_tenant.py`).
- libpq can move a connection away from the URI host: `?host=` in the query string overrides it, and `PGHOSTADDR` / a `PGSERVICE` entry with `hostaddr` connect elsewhere while `host` is only used for auth/SSL. A string check on the URI alone is not enough.
- The worktree-isolation hooks refuse compound shell commands (`&&`, loops, heredocs mentioning the VCS) inside a worktree session; put harnesses in a file inside the worktree (e.g. `.claude/tmp/`, deleted afterwards) and run them as one plain command.
- SSH push to github.com worked again today (it had timed out on 2026-10-19).

## Pending
- Post the r1 reply to Leo (drafted in session 2026-10-21) + his re-review → squash-merge to dev; qa/main promotion with the next release.
- After merge: if Sonar raises the test-fixture passwords, mark them Safe.
- Confirm on the next SonarQube scan of `dev` that both findings close; no reply to Alan requested (read-only thread).

## Related
- [[Map - Pentest 2026]] (Vanta/security hygiene) · [[Map - Kforce]] (Fase 6 convergence tooling the script belongs to)
