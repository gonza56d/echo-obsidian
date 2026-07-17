---
type: delivery
status: in-review
env: kforce
delivered: 2026-07-16
tags: [bugfix, kforce, filters, performance, contact]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1846"
  - "https://github.com/taller-projects/echo-backend/pull/1850"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23638"
---

# Kforce "Last Contacted By" filter 500s (PR 1846 + PR 1850)

FE reported the contacts "Last Contacted By" dropdown showing "No options found" on kforce — `GET /users?...&has_contact_interaction=true` returned **500 after ~20.7s**. Took TWO rounds to actually fix.

## Round 1 — [#1846](https://github.com/taller-projects/echo-backend/pull/1846) (merged 2026-07-16, insufficient)

Root cause was dual:

1. **Dropdown 500** — `User.has_contact_interaction` ranked EVERY `contact_interaction` row with `row_number() OVER (PARTITION BY contact_id)` → full-table window scan → statement timeout. Rewritten to `id IN (SELECT ...)` via the denormalized **`Contact.last_interaction_id` pointer**.
2. **Latent applied-filter 500** — dev commit `00fdc79e` ([[UUID typing for id__in filters (23253)]]) was never ported; malformed `last_interaction__created_by_id__in` → `InvalidTextRepresentation` 500. Ported copy+adapt.

**Why it wasn't enough**: the 0.26s benchmark only covered the **page query** (LIMIT 50 → ~67 user rows evaluated). fastapi-pagination also runs a **count query over all 11,393 org users**; the planner estimates the IN subquery at ~1.5M rows (contact count), refuses a hashed subplan (`work_mem`), and rescans a materialized subplan per user row → count exceeds even a 2-min timeout. The `(expr) = true` wrapper emitted by `fastapi_filter` also blocks semi-join conversion. Confirmed live post-deploy (build `24619_kforce-dev`): still 500 at ~20.5s, Grafana traceback dies in `fastapi_pagination ... _total_flow`.

## Round 2 — [#1850](https://github.com/taller-projects/echo-backend/pull/1850) → kforce-dev ([Bug 23638](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23638), in review)

- `has_contact_interaction` reshaped to **nested EXISTS** (`EXISTS(ci WHERE created_by_id=u.id AND EXISTS(contact WHERE last_interaction_id=ci.id))`) → planner keeps per-user index probes.
- New index **`contact_last_interaction_id_idx`** on `contact(last_interaction_id)` (migration `d829nrzr6hik`) — the existing composite `(tenant_id, last_interaction_id)` leads with `tenant_id` and can't serve the probe.
- Validated on real kforce-dev data with `BEGIN; CREATE INDEX; EXPLAIN ANALYZE <exact ORM-compiled SQL>; ROLLBACK`: count **>2min timeout → 201ms**.

## Decisions

- **Rejected set-based shapes** (all recompute the 1.5M×2.2M contact↔interaction join per request): `IN (SELECT DISTINCT ...)` 5.9s, de-correlated `EXISTS` 4.0s. Only per-user index probes are ms-class. Volumes: 1.52M contacts / 2.2M interactions / 11,393 org users / only ~4.4k distinct "last contacted by" creators.
- **Plain index over reusing the tenant_id composite**: kforce's vestigial single-valued `contact.tenant_id` could have served the probe via `tenant_id = user.organization_id`, but that couples the filter to a vestige a future cleanup may drop. Explicit index is 1 cheap migration (~2s build at 1.5M rows).
- EXISTS is inherently immune to the NULL three-valued-logic trap the IN form needed a `created_by_id IS NOT NULL` guard for.

## Gotchas

- **Always benchmark the pagination COUNT query, not just the page query** — `paginate()` runs both; LIMIT hides per-row subplan disasters.
- Kforce DB **retains `tenant_id` columns/indexes** on `contact` (schema vestige of the fork) even though kforce code is single-tenant — don't trust CLAUDE.md's "no tenant_id anywhere" for the DB layer.
- Local pytest "role `test` does not exist" = exported `POSTGRES_*` vars from `set -a; source .env` hijack the testcontainer login role. Use `.env` as a FILE in cwd, never export it.

## FE contract (both envs)

- Dropdown options: `GET /users?has_contact_interaction=true(&organization_id&full_name__ilike)`; applied filter: `last_interaction__created_by_id__in`; hydration: per-id `GET /users/{id}`. Unchanged by both rounds.

## Pending

- **[#1850](https://github.com/taller-projects/echo-backend/pull/1850) merge + kforce-dev deploy + live re-test** of the dropdown.
- **Taller port**: dev/main still run the original `row_number()` implementation — survives only on volume (82k contacts / 544k interactions / 830 users on dev). Port the **round-2 shape** (nested EXISTS + `last_interaction_id` index), not the round-1 IN form.
- kforce-master promotion via normal release flow.

## Related

- [[Map - Kforce]]
- [[UUID typing for id__in filters (23253)]]
