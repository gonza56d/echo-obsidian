---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, documents, talent, battle-tested]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2127"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24143"
prd: "https://app.notion.com/p/3c3aedca11f081ad974ff672582238a2"
---

# Retain original resume file (US 24143)

Battle Tested customer request (Jake Gomez, Aug 2026): opening the "original" resume showed the Echo-regenerated PDF because the internal upload flow (`POST /talents/resume`) is parse-only — the file was never persisted. M1 (backend) formalizes the resume Document tag convention so the FE can retain and retrieve the true original via the existing talent documents endpoints.

## Azure / docs
- [US 24143](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24143) — In development, assigned Gonzalo
- PRD: [Retener el CV original subido (US 24143) — PRD Técnico](https://app.notion.com/p/3c3aedca11f081ad974ff672582238a2) — Tier B, **In development**; Opción A decidida 2026-08-21

## PRs
- [#2127](https://github.com/taller-projects/echo-backend/pull/2127) → dev — OPEN (2026-08-21). M1: tag convention constants + first-ever route tests for `/talents/{id}/documents`.

## How
- **Option A** (decided): FE re-uploads the original to the existing `POST /talents/{talent_id}/documents` after talent create/patch; backend contract = tag convention only. Option B (multipart on `POST/PATCH /talents`, public-API parity) documented in the PRD as fallback if hard server-side retention is ever required.
- `app/modules/document/schemas.py`: `RESUME_TAG="resume"` + `RESUME_SOURCE_API/SELF_APPLIED/APP` constants; "current original" = most recent `resume`-tagged document (default `-created_at` ordering of `DocumentFilter`).
- Constants applied at the two pre-existing public-API producers (`PublicTalentWriteService._attach_resume`, apply flow) — zero behavior change.
- New `tests/unit/test_talent_documents.py` (5 tests): upload persists convention tags/tenant/created_by, upload policy 400, `tags__array_overlap=resume` latest-first, literal tag values pinned (renaming would orphan stored docs).
- No schema change, no migration, no OpenAPI surface change.

## Decisions
- Option A over B: reuses shipped infra, no content-type migration on core endpoints; soft-fail orchestration pattern already accepted for public API. Recorded in PRD (pre-Approved, so no changelog entry needed).
- Tag source for internal flow = `app` (public producers already use `api` / `self-applied`).
- No backfill: historical originals don't exist anywhere.

## Gotchas
- Documents are downloaded via raw S3 `key` → **unauthenticated CloudFront URL** (no presigned URLs); pre-existing PII exposure, deliberately OUT of scope — needs a separate security ticket (unfiled).
- No server-side max file size anywhere (5MB is FE-only) — hardening left as PRD open question 5.
- `document` table has NO Postgres RLS (app-level `TenantScopedRepository` only).
- `DocumentService.create_document` latent crashes for programmatic callers: `Path(None).suffix` and `",".join(None)` when tags omitted.
- Deleting a document never deletes the S3 object.
- Ticket description said `POST /talent/resume` — actual route is `POST /talents/resume`, and it has no `talent_id` (corrected via ticket comment).

## Pending
- Merge #2127 (CI + review).
- M2 (FE-owned): upload original with tags `resume,app` on add-candidate + replace-resume; expose view/download distinct from Echo export. No FE ticket filed yet.
- PRD open questions 2–5 (history vs latest-only, UI placement, doc title, size hardening) + Capa 1 formalization.
- Security follow-up ticket for unauthenticated CloudFront document access (unfiled).
- qa/main promotion after dev QA; Kforce port OUT unless requested.

## Related
- [[Generic proposal template & case studies (US 23670)]] (Battle Tested driving client) · Battle Tested rollout epic 23300
