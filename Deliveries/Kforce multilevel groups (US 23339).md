---
type: delivery
status: merged
env: kforce
delivered: 2026-07-03
tags: [feature, kforce, groups, reporting]
prs: [1673, 1675, 1678, 1713, 1714]
tickets: [23287, 23339, 23340, 23341, 23342]
prd: "Notion 38eaedca…daca24 — Echo Usage multilevel groups (Kforce)"
---

# Kforce multilevel groups / group hierarchy (US 23339)

Echo Usage reporting needed **DAG layers (Region → Market → Office)** over the flat `user_group` table on Kforce. New `group_hierarchy` module: hierarchy nodes + edges, node→leaf resolution, metrics aggregation per node.

## Azure / docs
- Feature 23287 → US 23339 → Tasks 23340 (M1) / 23341 (M2) / 23342 (M3). M4 (FE) skipped.

## PRs (all → kforce-dev)
- [#1673](https://github.com/taller-projects/echo-backend/pull/1673) **M1** — hierarchy model + node→leaf resolution + levels endpoint (merged 2026-06-30)
- [#1675](https://github.com/taller-projects/echo-backend/pull/1675) **M2** — `/nodes` metrics aggregation + `group_node_id` filter (2026-06-30)
- [#1678](https://github.com/taller-projects/echo-backend/pull/1678) **M3 (partial)** — idempotent seed script + tests (2026-06-30)
- [#1713](https://github.com/taller-projects/echo-backend/pull/1713) — make the M3 seed runnable standalone against the Supabase pooler (2026-07-03)
- [#1714](https://github.com/taller-projects/echo-backend/pull/1714) — expose leaf `user_group_id` in `NodeSummary` (2026-07-02)

## Status
- **Seed APPLIED to kforce-dev 2026-07-02**: 147 nodes / 134 edges / 62 departments / 699 members (idempotent).

## Pending
- Seed script has **3 known latent bugs** → needs a follow-up PR before reuse.
- **PROD seed still pending.**

## Related
- [[Map - Kforce]]
