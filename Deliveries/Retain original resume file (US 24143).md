---
type: delivery
status: merged
env: taller
delivered: 2026-08-21
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
- [#2127](https://github.com/taller-projects/echo-backend/pull/2127) → dev — **MERGED 2026-08-21** (squash `3f133298`; Leo approved (review r1 `5c15a511`: RESUME_SOURCE_APP renamed `app`→`echo-app`, `-id` tie-break on DocumentFilter.order_by, file renamed test_talent_documents_routes.py; r2 nits `83bc9e25`: direct same-created_at tie-break test + cross-tenant upload rejection test; nit 2 = order_by default now `-created_at,-id` for org/project listings too — FE radar, no change). 10/10 file tests green. /pr-review r1 (full, 3 reviewers): READY WITH NITS, 0 blockers; nits landed in `5c15a511`.

## How
- **Option A** (decided): FE re-uploads the original to the existing `POST /talents/{talent_id}/documents` after talent create/patch; backend contract = tag convention only. Option B (multipart on `POST/PATCH /talents`, public-API parity) documented in the PRD as fallback if hard server-side retention is ever required.
- `app/modules/document/schemas.py`: `RESUME_TAG="resume"` + `RESUME_SOURCE_API/SELF_APPLIED/APP` constants (`APP="echo-app"`); "current original" = most recent `resume`-tagged document (default `-created_at,-id` ordering of `DocumentFilter` — `-id` tie-break added post-review for determinism).
- Constants applied at the two pre-existing public-API producers (`PublicTalentWriteService._attach_resume`, apply flow) — zero behavior change.
- `tests/unit/test_talent_documents_routes.py` (8 tests; renamed from `test_talent_documents.py` — basename collided with the public_api sibling): upload persists convention tags/tenant/created_by, upload policy 400, nonexistent talent → translated 400 (composite-FK violation → `ReferencedError`, not 500), tagless upload → `tags=[]`, `tags__array_overlap=resume` latest-first, cross-tenant isolation of the listing, literal tag values pinned (renaming would orphan stored docs).
- No schema change, no migration, no OpenAPI surface change.

## Decisions
- Option A over B: reuses shipped infra, no content-type migration on core endpoints; soft-fail orchestration pattern already accepted for public API. Recorded in PRD (pre-Approved, so no changelog entry needed).
- Tag source for internal flow = `echo-app` (renamed from `app` post-review — ambiguous vs the `Application` entity; zero rows persisted so the rename was free; PR body, US comment, FE Task 24461 and PRD annex all updated).
- `DocumentFilter` default order gained `-id` tie-break (affects talent/org/project document lists; only OpenAPI delta is the param default).
- No backfill: historical originals don't exist anywhere.

## Gotchas
- Documents are downloaded via raw S3 `key` → **unauthenticated CloudFront URL** (no presigned URLs); pre-existing PII exposure, deliberately OUT of scope — needs a separate security ticket (unfiled).
- No server-side max file size anywhere (5MB is FE-only) — hardening left as PRD open question 5.
- `document` table has NO Postgres RLS (app-level `TenantScopedRepository` only).
- `DocumentService.create_document` latent crashes for programmatic callers: `Path(None).suffix` and `",".join(None)` when tags omitted.
- Deleting a document never deletes the S3 object.
- Ticket description said `POST /talent/resume` — actual route is `POST /talents/resume`, and it has no `talent_id` (corrected via ticket comment).

## Pending
- M2 (FE-owned): [Task 24461](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24461) filed 2026-08-21 (child of the US, unassigned) — upload original with tags `resume,echo-app` on add-candidate + replace-resume; expose view/download distinct from Echo export.
- PRD open questions 3–5 (UI placement, doc title, size hardening) + Capa 1 formalization. **Q2 RESOLVED 2026-08-21: full history retained — replace never deletes the prior original (PRD changelog row; Task 24461 updated).** Review also flagged two PRD wording fixes still pending: annex says `RESUME_POLICY` but the endpoint enforces `DOCUMENT_POLICY` (XLSX/CSV could become "the original"), and the soft-fail warning-log criterion has no backend home under Option A (re-home to M2/FE).
- Security follow-up ticket for unauthenticated CloudFront document access (unfiled).
- qa/main promotion after dev QA; Kforce port OUT unless requested.

## Related
- [[Generic proposal template & case studies (US 23670)]] (Battle Tested driving client) · Battle Tested rollout epic 23300
