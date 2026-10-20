---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, export, interviews, assessments, frontend]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2441"
fe_prs:
  - "https://github.com/taller-projects/echo-frontend/pull/3564"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25607"
prd: ""
---

# Assessment zip resume comes out blank (Bug 25607)

Paloma (CSR, Sprint 45, 2026-10-20): **Download Assessment** on the public assessment preview returns a ZIP whose `{name}_resume.pdf` only shows the Taller logo, the name and the seniority, while the Resume tab download on the same page is complete. Root cause: the zip rendered its own `snapshot_resume.jinja` from `snapshot.content.talent`, a JSON the FE writes at preview creation by copying the interview response's `talent`, whose backend schema is `TalentInfo` (id, full_name, phone, links, owner) and never carried summary / skills / job history. Every section of the template was skipped. Fix: the zip resume now reuses `export_talent_by_id` (live talent, same pipeline as the direct download) and honours `include_resume_on_export`. Second ask in the same ticket: a hint on the preview for Safari / browsers without a PDF viewer (FE).

## Azure / docs
- [Bug 25607](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25607) — In revision, PR linked (GitHub Pull Request relation), attachments: blank Valeria / Willie / Carlos resumes vs the complete `export_talent` one.
- No PRD (bug). Flow docs: `echo-flows-docs/06-interviews.md` Flow 11 + `help/interviews.md` "Share an assessment preview" (to update when the PRs land in dev).

## PRs
- [#2441](https://github.com/taller-projects/echo-backend/pull/2441) → dev — **OPEN** 2026-10-20 (branch `25607/assessment-zip-resume`, head `0216602a`). No FE contract change: same route, same zip, same filenames.
- FE: [#3564](https://github.com/taller-projects/echo-frontend/pull/3564) → dev — **DRAFT** 2026-10-20 (branch `assessment-preview-resume-hint`, head `5de612c45`). Hint above the embedded resume on the public preview ("If the resume doesn't display in your browser, use Open in new tab or Download Assessment."), `fallbackHint` prop on `BaseResume`, constant in `constants/interviewPreviews.ts`, `Resume.test.js` + `PreviewTabs.test.js`. No API change. Verified in Chrome against the dev API (screenshot attached to the Bug).
- Docs: `echo-flows-docs` branch `assessment-preview-resume-hint` (`67933d4`, pushed, no PR): Flow 11 + endpoints table + "For the chat" Q in `06-interviews.md`, `help/interviews.md` preview paragraph. Merge to `main` once both PRs are in `dev`.

## How
- `FileExportService.export_snapshot_zip(snapshot, tenant_id, talent_id)`: resume = `export_talent_by_id(talent_id, PDF)` (tenant logo + custom CV template when the tenant has one); resume file skipped when `snapshot.include_resume_on_export` is false (FE already hides the Resume tab in that case). Router passes `snapshot.talent_id` (deferred column_property through the interview).
- `snapshot_resume.jinja` deleted; `snapshot_base.jinja` kept for the assessment + challenge PDFs.
- Tests: `tests/unit/export/test_snapshot_zip_resume.py` (resume bytes are the talent export; opt-out skips it); badge test updated for the new signature.

## Decisions
- Live talent, not frozen at snapshot time: the preview's Resume tab and the direct download already behave that way, and the stored snapshot talent has no resume data to freeze. Storing a full `TalentExport` in the snapshot would need an FE change plus a backfill for 3,321 prod snapshots, all blank.
- All tenants, no flag: shared endpoint, pure bug fix.

## Gotchas
- `snapshot.content` is FE-authored JSON (`GeneratePreviewModal.tsx`): the backend never shaped it. Any export reading `content.talent` beyond `full_name` is reading `TalentInfo`.
- Prod evidence (read-only, 2026-10-20): 3,321 snapshots, 0 with summary or jobs; Valeria's live talent has a 1,072-char summary + 12 experiences. Broken since the zip export landed (`8405afdf`, 2025-12-02), never a regression.
- Ruff over `tests/unit/export` rewrites 5 unrelated test files (CI only lints `app/`): revert them before committing.

## Pending
- Review + squash-merge #2441; FE #3564 out of draft + review + merge (independent, no merge-order constraint); qa / main promotion of both; close Bug 25607; reply to Paloma (resume in the zip = live talent data, same as the direct download).
- Merge the `echo-flows-docs` branch into `main` after both land in `dev`.
- Out of scope, worth a ticket: the "Candidate's Resume" checkbox in Generate Preview is still not sent by the FE (`GeneratePreviewModal.tsx` keeps `includeResume` in state only; docs Known limitations 2). The BE now honours `include_resume_on_export: false` in the ZIP, so wiring the checkbox is an FE-only change.
- `corepack enable pnpm` was run on this machine (pre-commit hook needs `pnpm` on PATH; the FE CLAUDE.md documents it).

## Related
- Same export path, earlier fix: [[Assessment download showed every skill as Expert (Bug 23775)]] (badge weight bug, `e688b998`).
