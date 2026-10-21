---
type: delivery
status: in-review
env: both
delivered:
tags: [security, chore, auth, dependencies]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2444"
fe_prs: []
tickets: []
prd: ""
---

# Replace python-jose with PyJWT and transitive CVE bumps (PR 2444)

Alan's security findings ([Slack 2026-10-20](https://taller-tech.slack.com/archives/C0CA5AVE162/p1792525352941939)) flagged four dependency advisories with due dates: python-jose <= 3.5.0 CVE-2026-85394 (algorithm confusion, **critical, due Nov 4**), aiohttp <= 3.14.3 via `realtime` (2 high + 1 low), Mako <= 1.4.1 via `alembic`, Werkzeug < 3.1.9 via `sendgrid`. python-jose has no patched release, so the only way to close it is to drop the package: both JWT decode sites (Supabase HS256 in `auth.py`, Entra RS256 in `entra.py`) moved to PyJWT (already in the lock through `gotrue`), and the transitive packages were bumped. Echo was never exploitable (both sites pin `algorithms`).

## Azure / docs
- No Azure ticket; source is Alan's Slack thread above.

## PRs
- [#2444](https://github.com/taller-projects/echo-backend/pull/2444) → dev **OPEN** (branch `chore/replace-python-jose-with-pyjwt`). First cut `78093429` 2026-10-20; Leo r1 CHANGES REQUESTED 2026-10-21 (1 blocker + 6 nits) → all addressed in `6f43ef4a` 2026-10-21, PR body refreshed, [reply posted](https://github.com/taller-projects/echo-backend/pull/2444#issuecomment-6322188813).
- No FE PR: no endpoint, schema or permission changes.

## How
- `pyproject.toml`: `pyjwt[crypto]>=2.15.1,<3` (2.15.1 = locked + reviewed version); `cryptography>=42.0.0` kept as a version floor only (comment says so, do not delete as redundant).
- `app/core/permissions/auth.py`: `jwt.decode(..., algorithms=["HS256"], audience="authenticated", options={"verify_iat": False})`; `PyJWTError` → 401 `WWW-Authenticate: Bearer`. Missing / non-UUID `sub` → `InvalidTokenError` → 401 (was a 500, pre-existing).
- `app/core/permissions/entra.py`: JWKS entry → key via `jwt.PyJWK(jwk).key`; unverified `tid` via `decode(..., options={"verify_signature": False})`; `leeway=60`. `UserService.exchange_teams_token` catches `PyJWTError` → 401 (covers `PyJWK` key errors too).
- Lock bumps via `uv lock --upgrade-package`: aiohttp 3.14.3 → 3.14.5, Mako 1.3.12 → 1.4.3, Werkzeug 3.1.8 → 3.1.9, yarl 1.20.0 → 1.25.1, certifi 2025.4.26 → 2026.10.19 (GHSA-6q48-6c7w-9gw2, from pip-audit).
- Tests: new `tests/unit/test_auth_jwt.py` (Supabase path had no direct coverage: valid, iat +5 accepted, wrong secret / expired / wrong or missing aud / missing or non-UUID sub / alg none / RS256 / garbage / no bearer → 401 + header); `test_entra_token.py` serves a real JWK and covers unsupported `kty` → `PyJWTError`. Unit + multitenancy 6409 passed after r1.

## Decisions
- **iat: parity over leeway** (Leo r1 blocker). PyJWT 2.15.1 raises `ImmatureSignatureError` when `iat > now + leeway`; python-jose never checked `iat`. A pod clock a second behind Supabase Auth would 401 every fresh token, and a 401 on `users/me` sends the FE to `/account-deactivated` with no retry. Leo offered `leeway=30` or `verify_iat: False`; chose the latter because leeway also accepts tokens up to 30 s past `exp`, which python-jose never did. `exp` stays strict.
- **Missing `aud` now rejected** (accepted tightening): PyJWT refuses a token without `aud` when an audience is expected; Supabase always stamps `aud: authenticated`.
- Bad `sub`: only the `uuid.UUID(...)` parse is wrapped and re-raised as `InvalidTokenError`, instead of widening the outer `except` with `TypeError`/`ValueError` (the auto-mode classifier refused the broad version; the narrow one is cleaner anyway).

## Gotchas
- `jwt.InvalidSubjectError` is NOT exported at the `jwt` package top level in 2.15.1 (only `jwt.exceptions`); used `InvalidTokenError` instead.
- Worktree sessions: the worktree-guard blocks Edit/Write in the scratchpad too, so PR body / reply drafts went to an untracked `.pr-drafts/` inside the worktree.
- The first-cut worktree `security-pyjwt` belongs to the earlier session (read-only for others); review fixes were made in `.claude/worktrees/pyjwt-review-r1` (local branch `chore/pyjwt-review-r1`) and pushed with `HEAD:chore/replace-python-jose-with-pyjwt`.

## Pending
- Leo re-review → squash-merge to dev.
- qa → main promotion before the **Nov 4** python-jose due date (aiohttp Nov 19; Mako / Werkzeug Dec 4). Dependabot evaluates `main`, so alerts stay open until then.
- Out of scope, no fix released: `ecdsa 0.19.2` (PYSEC-2026-1325) via `sendgrid`; `rsa` / `pyasn1` stay via `google-auth`.
- Tell Alan once on main.

## Related
- [[Map - Pentest 2026]] · [[Dependabot Oct 2026 lock bump (US 25361)]] (PyJWT 2.13.0 → 2.15.1) · [[SonarQube hardcoded local DB passwords (PR 2438)]] (same Alan security stream)
