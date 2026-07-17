---
type: delivery
status: merged
env: kforce
delivered: 2026-07-16
tags: [bugfix, kforce, filters, performance, contact]
prs: [1846]
tickets: []
---

# Kforce "Last Contacted By" filter 500s (PR 1846)

FE reported the contacts "Last Contacted By" dropdown showing "No options found" on kforce — `GET /users?...&has_contact_interaction=true` returned **500 after ~20.7s**. Root cause was **dual** (the FE dev's missing-cherry-pick theory was only half right):

1. **Dropdown 500** — `User.has_contact_interaction` ranked EVERY `contact_interaction` row with `row_number() OVER (PARTITION BY contact_id)` → full-table window scan → statement timeout at Kforce volume. Rewritten to resolve via the denormalized **`Contact.last_interaction_id` pointer** (same join the applied filter uses, maintained by the contact summary refresh). Benchmark at 600k contacts / 3M interactions: old **>120s timeout** → new **0.26s**.
2. **Latent applied-filter 500** — dev commit `00fdc79e` ([[UUID typing for id__in filters (23253)]]) was never ported; malformed `last_interaction__created_by_id__in` → `InvalidTextRepresentation` 500. Ported copy+adapt (kforce `OrganizationInternalFilter` has no `id__in`; `OrganizationJob.id` is a str PK so its `List[str]` is correct).

## PRs
- [#1846](https://github.com/taller-projects/echo-backend/pull/1846) → kforce-dev — merged 2026-07-16 (branch `fix/last_contacted_by_filter_kforce`)

## FE contract (both envs)
- Dropdown options: `GET /users?has_contact_interaction=true(&organization_id&full_name__ilike)`; applied filter: `last_interaction__created_by_id__in`; hydration: per-id `GET /users/{id}`.

## Pending — IMPORTANT
- **Taller dev/main still run the row_number() implementation** of `has_contact_interaction` — survives only on smaller volume. **Port the pointer rewrite to dev.**

## Related
- [[Map - Kforce]]
