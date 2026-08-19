---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, hotfix, export, observability]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2111"
fe_prs: []
tickets: []
prd: ""
---

# Export talent 500 on newline filename (PR 2111)

Prod incident fix (Sentry [7680867336](https://taller-wn.sentry.io/issues/7680867336/), 18 events 2026-08-18/19, tenant `01df2012-…`, caller = curl script): `POST /export/talent` 500'd for any talent whose `title` contains newlines (multi-line list of job titles, e.g. "data engineer\ndata architect\n…"). The download filename is built as `first_name_last_name_title` and leaked the control chars into the `Content-Disposition` header; h11 rejected it (`LocalProtocolError: Illegal header value`) when the StreamingResponse started — **after** the PDF had already been generated. No ticket (Sentry-alert-driven, same flow as PR 2110 the same week).

## Azure / docs
- No ticket — direct Sentry alert triage.
- Sentry issue: https://taller-wn.sentry.io/issues/7680867336/

## PRs
- [#2111](https://github.com/taller-projects/echo-backend/pull/2111) → dev — OPEN (review r1 addressed 2026-08-19). Branch `fix/export_filename_header_sanitization`, commits `cb9c2b09` + `f393b65e` (review fixes).
- No FE PR. FE contract impact: none breaking — the filename is now emitted as a quoted-string; FE's `extractFilename` regex (`echo-frontend/src/lib/utils.ts:38`) already handles quoted + unquoted and strips quotes.

## How
- `sanitize_download_filename()` (r1 rename from `encode_download_filename`) in `app/modules/export/schemas.py`, shared by `DownloadableFileResponse` **and** `ZipFileResponse` (they had duplicated inline logic): collapse control chars (`[\x00-\x1f\x7f-\x9f]+` — C0 + DEL + C1 windows-1252 mojibake) to a single space → keep the legacy figure-dash → `-` replacement and latin-1 `errors="ignore"` filter → drop `"` and `\` (value goes inside a quoted-string) → strip → truncate to 150 chars → fall back to `"export"` if nothing survives (no hidden-dotfile `.pdf` downloads).
- Header now `attachment; filename="<name>.<ext>"` (quoted, RFC-compliant) in both classes.
- Covers all 6 routers that use these response classes: export, role, project, interview, snapshot (public + auth).
- Tests: `tests/unit/export/test_download_responses.py` — 15 tests incl. an **h11 round-trip regression** (builds the response with the incident's filename shape and feeds `raw_headers` to `h11.Response`; also proves the unsanitized form raises `LocalProtocolError`), truncation boundary (150/151), C1 pin, and fallback pins.

## Review (r1, 2026-08-19 — /pr-review, 2 agents, lightweight mode)
- **CHANGES REQUESTED — 1 blocker**: the test fixture committed the REAL prod talent's name + verbatim job-title list from the Sentry incident (PII into permanent git history; repo access ≫ prod-data access). Fixed in `f393b65e`: synthetic `jane_doe_…` name — only the newline structure matters for the regression.
- Nits applied in the same commit: collapse C1 control chars (`\x80-\x9f`) too; `"export"` fallback for names that sanitize to empty (was `filename=".pdf"`); rename to `sanitize_download_filename` (nothing is encoded); boundary/degenerate test pins.
- Security verification from the review (empirical vs h11 0.16.0): CR/LF splitting closed; quoted-string breakout impossible (`"`/`\` dropped, nothing later reintroduces them); sanitization ordering sound; FE parser verified — quoting actually FIXES a latent FE truncation for `;`-containing names.
- PR body updated via `gh api` PATCH (rename + additions).

## Decisions
- **Sanitize, don't reject**: the newline lives in stored talent data, not in a user-supplied filename; a 422 would make those talents permanently un-exportable. Export succeeds with a cleaned filename; document content untouched.
- Fixed at the **response layer**, not input validation — dirty data already exists in the DB and filenames are built from many sources (talent, role, project names).
- Quoting verified safe against the FE parser before adopting it (regex handles both forms).
- Empty-sanitizing names fall back to `"export"` rather than shipping a hidden dotfile (r1 nit).

## Gotchas
- **Never commit real prod names into fixtures** — r1 blocker: the incident talent's real name was in `INCIDENT_FILENAME`; squash-merge would have baked it into `dev` history permanently. Synthetic names, always.
- `ruff format app/` reformats the untouched `app/modules/reporting_dashboard/repository.py` (pre-existing drift on dev) — reverted to keep the diff scoped. Same scope-creep trap as the PR 2107 session. r1 fixes linted per-file to dodge it.
- The failure fires **after** `http.response.start`, so the client sees a dropped connection, and the export cost (PDF render, LLM tailoring) is already paid — every retry burns it again.
- Adoption CSV export (`app/modules/adoption/routers.py:375`) already quoted its filename — untouched; reviewer flagged it as a candidate to adopt the shared helper later (it builds its own via `_slugify`, safe today).

## Pending
- CI green on `f393b65e` → merge #2111 → dev; qa/main promotion (prod is where the incident lives — promote promptly).
- **Kforce twin**: `origin/kforce-dev` has the same unsanitized duplicated logic in its `export/schemas.py` (verified 2026-08-19) — needs a copy+adapt twin PR.
- Optional data cleanup: talents with control chars in `title` (the export now tolerates them, so not urgent).
- Reviewer follow-up candidates (unticketed): adoption CSV filename builder → shared helper; RFC 5987 `filename*` UTF-8 form for non-latin-1 names.

## Related
- [[Map - Observability & Reliability]] · [[Document upload 403 CloudFront special chars (PR 2110)]] (same week, same shape: prod incident in the talent-file pipeline, fix + regression tests, no ticket)
