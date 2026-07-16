---
type: delivery
status: merged
env: taller
delivered: 2026-07-16
tags: [feature, case-studies, ai]
prs: [1842, 1843]
tickets: [23613, 23619, 23620, 23621, 23622, 23623, 23624]
prd: "Notion 39daedca — Case Studies edit/regenerate (In Development)"
---

# Case studies per-card management (US 23613)

Per-item management for generated case-study cards: edit, delete, regenerate, and find-similar — replacing the all-or-nothing regeneration flow.

## Azure / docs
- US 23613 → tasks 23619–23624 (were "In revision" pre-merge)
- PRD: Notion `39daedca…`

## PRs (both → dev, merged 2026-07-16)
- [#1842](https://github.com/taller-projects/echo-backend/pull/1842) **M1** (23619/23620) — per-card **edit (PATCH)** and **delete** endpoints (head `f2ccdbb9`)
- [#1843](https://github.com/taller-projects/echo-backend/pull/1843) **M2** (23621–23624) — per-card **regenerate** and **find-similar** endpoints (head `56232772`; approved by Pedro, review nits addressed)

## Key decisions
- **Forma B** API shape (chosen during PRD review).
- **null-vs-soft-fail** semantics: a failed regeneration doesn't destroy the existing card.
- **`position` computed in the INSERT** (no read-modify-write race for card ordering).

## Merge coordination note
- #1843 stacked on #1842 — the rule was: merge #1842 first; re-merge into #1843 if #1842 moved. Both landed 2026-07-16 in order.
