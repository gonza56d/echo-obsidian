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
- [#2111](https://github.com/taller-projects/echo-backend/pull/2111) → dev — OPEN (in review, 2026-08-19). Branch `fix/export_filename_header_sanitization`, commit `cb9c2b09`.
- No FE PR. FE contract impact: none breaking — the filename is now emitted as a quoted-string; FE's `extractFilename` regex (`echo-frontend/src/lib/utils.ts:38`) already handles quoted + unquoted and strips quotes.

## How
- New `encode_download_filename()` in `app/modules/export/schemas.py`, shared by `DownloadableFileResponse` **and** `ZipFileResponse` (they had duplicated inline logic): collapse ASCII control chars (`[\x00-\x1f\x7f]+`) to a single space → keep the legacy figure-dash → `-` replacement and latin-1 `errors="ignore"` filter → drop `"` and `\` (value goes inside a quoted-string) → strip → truncate to 150 chars.
- Header now `attachment; filename="<name>.<ext>"` (quoted, RFC-compliant) in both classes.
- Covers all 6 routers that use these response classes: export, role, project, interview, snapshot (public + auth).
- Tests: `tests/unit/export/test_download_responses.py` — 11 tests incl. an **h11 round-trip regression** (builds the response with the exact incident filename and feeds `raw_headers` to `h11.Response`; also proves the unsanitized form raises `LocalProtocolError`).

## Decisions
- **Sanitize, don't reject**: the newline lives in stored talent data, not in a user-supplied filename; a 422 would make those talents permanently un-exportable. Export succeeds with a cleaned filename; document content untouched.
- Fixed at the **response layer**, not input validation — dirty data already exists in the DB and filenames are built from many sources (talent, role, project names).
- Quoting verified safe against the FE parser before adopting it (regex handles both forms).

## Gotchas
- `ruff format app/` reformats the untouched `app/modules/reporting_dashboard/repository.py` (pre-existing drift on dev) — reverted to keep the diff scoped. Same scope-creep trap as the PR 2107 session.
- The failure fires **after** `http.response.start`, so the client sees a dropped connection, and the export cost (PDF render, LLM tailoring) is already paid — every retry burns it again.
- Adoption CSV export (`app/modules/adoption/routers.py:375`) already quoted its filename — untouched, and its tests don't collide.

## Pending
- Merge #2111 → dev; qa/main promotion (prod is where the incident lives — promote promptly).
- **Kforce twin**: `origin/kforce-dev` has the same unsanitized duplicated logic in its `export/schemas.py` (verified 2026-08-19) — needs a copy+adapt twin PR.
- Optional data cleanup: talents with control chars in `title` (the export now tolerates them, so not urgent).

## Related
- [[Map - Observability & Reliability]] · [[Document upload 403 CloudFront special chars (PR 2110)]] (same week, same shape: prod incident in the talent-file pipeline, fix + regression tests, no ticket)
