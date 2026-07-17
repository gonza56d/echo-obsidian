---
type: delivery
status: merged
env: taller
delivered: 2026-06-19
tags: [security, pentest]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1582"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23013"
---

# Upload file-type validation (23013)

Security-assessment finding (CWE-434, unrestricted upload of dangerous file types): upload endpoints had **no server-side file-type validation**. `POST /blobs` only enforced PNG/JPG client-side; a forged request could upload `.html`/`.exe`, and since blobs are served unauthenticated via CloudFront with extension-inferred Content-Type, an uploaded HTML file rendered in the browser → phishing hosted on our domain.

## PRs
- [#1582](https://github.com/taller-projects/echo-backend/pull/1582) → dev — merged 2026-06-19

## How
- New `app/core/file_validation.py`: dependency-free validator = extension allowlist **plus magic-byte content checks** (client Content-Type/filename never trusted). SVG/GIF excluded (SVG can carry script).
- Signatures anchored at offset 0; PDF tolerates BOM/leading bytes; signature-less text (CSV) uses a denylist (MZ/ELF/shebang/markup, incl. markup behind whitespace or UTF-8 BOM).
- Wired `validate_upload(...)` at the router boundary: `POST /blobs` (images; covers public/internal/admin mounts via shared router), org/project/talent document uploads (pdf/doc/docx/xls/xlsx/csv), `POST /talents/resume` (pdf/doc/docx).
- Rejections → `400` with the standard `{"detail": ...}` shape. Allowlists match what the FE already restricts → no FE change.

## Related
- [[Map - Pentest 2026]]
