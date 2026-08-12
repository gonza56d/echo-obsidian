---
type: delivery
status: in-review
env: taller
delivered:
tags: [security, pentest, uploads]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2043"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24219"
prd: ""
---

# Allow csv/json blob uploads for data team (Task 24219)

Follow-up to the CWE-434 pentest lock-down ([[Upload file-type validation (23013)]] / [#1582](https://github.com/taller-projects/echo-backend/pull/1582)). That PR restricted the generic `POST /blobs` endpoint to an **images-only** allowlist. The data team uploads `.csv`/`.json` data files through that same endpoint, so they started getting `400 Unsupported file type`. This widens the blob allowlist to also accept `.csv` and `.json` — without reopening the render/phishing vector.

## Azure / docs
- [Task 24219](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24219) — created for this change (Task, tagged Security).

## PRs
- [#2043](https://github.com/taller-projects/echo-backend/pull/2043) → dev — **OPEN** (2026-08-11). Leo review **APPROVED — READY WITH NITS** (2026-08-12): all 6 AC met, no blockers; confirmed the widened allowlist does not reopen CWE-434 (no extension maps to a renderable Content-Type; `.json` shares the same signature-less denylist branch as `.csv`). Folded both nits in commit `ac01ddcd` (2026-08-12).

## How
- `app/core/file_validation.py`: new signature-less `JSON` type (mirrors `CSV`); renamed `IMAGE_POLICY` → `BLOB_POLICY` (its only consumer is the now-generic `/blobs` endpoint) and extended it to `PNG, JPEG, CSV, JSON`.
- `app/blob/routers.py`: `POST /blobs` validates against `BLOB_POLICY`.
- `DOCUMENT_POLICY` / `RESUME_POLICY` untouched: CSV was already allowed on the org/project/talent document uploads; JSON stays blob-only.
- Tests: unit `test_file_validation.py` (accepted csv/json incl. whitespace/empty; forged `.json` HTML/SVG/SVG_XML/EXE/ELF/SHEBANG/BOM rejected; json rejected on document/resume to pin scope) → 57 pass. System `test_blob_upload_validation.py` parametrized over png/csv/json 201 + forged-json 400 → 6 pass.

## Decisions
- **Endpoint = `POST /blobs` only** (confirmed with requester). CSV already worked on the document endpoints; the "both csv AND json blocked" framing pointed at the images-only blob policy, which is the sole policy that blocked both.
- **Why it's safe / does not reopen 4.1.2 (CWE-434).** S3 sets `ContentType` via `mimetypes` from the key extension → `.csv`=`text/csv`, `.json`=`application/json`. Neither renders as HTML in a browser, so the CloudFront inline-render phishing vector the pentest closed is not reintroduced. JSON is signature-less, so like CSV it runs the best-effort denylist: leading `MZ`/`ELF`/`#!` or browser-renderable markup (`<html`,`<script`,`<svg`,`<?xml`…, incl. behind whitespace/UTF-8 BOM) → 400.
- Renamed the policy rather than adding a second one, because `IMAGE_POLICY` had exactly one consumer and leaving it around would be dead code / a misnomer.
- **Nit fixes (review round 1, `ac01ddcd`).** (1) Added explicit `.json` forbidden rows (`SVG_XML`/`ELF`/`SHEBANG`) — behaviour was already covered by the shared signature-less branch (via `.csv`), these pin it per-extension for regression clarity. (2) Made the leading-whitespace/BOM strip **idempotent**: the old `lstrip().lstrip(BOM).lstrip()` single pass missed markup behind a *double* BOM (BOM + whitespace + BOM) and non-UTF-8 BOMs. Replaced with `_strip_leading_noise()` that loops until stable and strips UTF-8/16/32 marks (longest-prefix-first so UTF-32 LE isn't half-eaten by the UTF-16 LE mark). No real exploit (blobs served non-renderable + upload authenticated) — defense-in-depth. Pinned by new rows `DOUBLE_BOM_HTML` (`.json`) and `UTF16_BOM_HTML` (`.csv`).

## Gotchas
- CSV was **already** in `DOCUMENT_POLICY` from #1582 — only JSON is genuinely new to the codebase; the blob endpoint is where both were blocked.
- The blob endpoint is shared across the public / internal / admin mounts, so this one policy change relaxes all three.

## Pending
- Merge #2043 to dev (Taller-only; no qa/main cherry-pick requested).
- No FE change (FE already restricts client-side; server-side only). No migration.
- Kforce twin: not requested. `POST /blobs` + `file_validation.py` exist on kforce too — port only if the kforce data team hits the same block.

## Related
- [[Map - Pentest 2026]] · [[Upload file-type validation (23013)]]
