---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, documents, blob, sentry]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2110"
fe_prs: []
tickets: []
prd: ""
---

# Document upload 403 CloudFront special chars (PR 2110)

Prod incident (Sentry issue 7681042782, alert 2026-08-19): `POST /talents/{talent_id}/documents` 500ed with `ExternalApiException` — free-document-loader got **403 from CloudFront** downloading the just-uploaded CV, the document row rolled back and the CV was never parsed. 71+ events since 2026-08-18 ~21:00 UTC, all tenant `fe6b6db9-3edc-44cc-97e4-54ef1a9012f8`, bulk CV uploads with `C#`/`+` in filenames. Fixed the filename-normalization regex + percent-encoded the CDN URL.

## Azure / docs
- No ticket (incident-driven fix straight from the Sentry alert).
- Sentry: [issue 7681042782](https://taller-wn.sentry.io/issues/7681042782/) — prod, `component: api`, release `81a310c`.

## PRs
- [#2110](https://github.com/taller-projects/echo-backend/pull/2110) → dev — OPEN, in review (2026-08-19)

## How
- Root cause 1 — `app/blob/service.py::normalize_file_name` used `[^A-Za-z0-9. -_]+`: the ` -_` tail is an **accidental char range 0x20–0x5F** whitelisting `# + ( ) % ? & =` etc., so "normalize" was a no-op and those chars landed in S3 keys. Fixed to `r"[^A-Za-z0-9._ -]+"` (hyphen literal, last).
- Root cause 2 — `EchoDocument.file_url` (`app/services/echo_api_services.py`) built `CDN_URL/{file_id}` with no encoding. Unencoded `#` truncates the URL at the fragment; literal `+` is decoded as space by S3 → key mismatch → 403 AccessDenied (S3 hides 404 without ListBucket). Fixed with `urllib.parse.quote(self.file_id)`.
- New `tests/unit/test_document_file_name_sanitization.py` (5 tests: regex whitelist + file_url percent-encoding).

## Decisions
- Two-layer fix on purpose: the regex stops bad chars in NEW keys; `quote()` also repairs **legacy keys** already stored with `#`/`+` whenever they get re-pushed (e.g. `sync_talent` re-syncs). Either alone leaves a hole.
- Test fixtures anonymized (john/jane doe) — the real failing filenames were actual candidate names from prod; don't commit those.

## Gotchas
- The two 403s have different mechanisms: `#` breaks client-side (fragment truncation by httpx in the loader), `+` breaks server-side (S3 decodes `+` as space in paths). Both look identical in Sentry.
- Failed uploads persisted NO document row (tx rollback) but DID leave an orphaned S3 object; affected CVs just need re-upload after deploy.
- Sentry issues endpoints 403 with the current token — found the events by paginating `projects/taller-wn/echo-backend/events/?full=true` and filtering `groupID`.

## Pending
- Merge #2110 → dev; then evaluate qa/main promotion (prod incident — likely wanted soon).
- Kforce twin: `app/blob/service.py` predates the fork, kforce almost certainly has the same latent bug — evaluate copy of this fix to kforce-dev.
- Consider re-upload comms for the affected tenant's failed CVs (71+ events).

## Related
- [[Map - Observability & Reliability]]
