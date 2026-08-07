---
type: delivery
status: in-review
env: taller
delivered:
tags: [bugfix, talent, applications, jazzhr, sql]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2018"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24149"
prd: ""
---

# Talent last_application recency (Bug 24149)

The candidate overlay stopped showing the active application: add a candidate to a role from Matched, `PATCH /applications/{id}` with `status: "New"`, refresh, and the overlay resolved an *older* application. Root cause was the recency key behind `Talent.last_application` — it ranked by a column (`last_status_update`) that **no code path in Echo ever writes**, so every UI-created application sorted last forever. Fixed by ranking on `GREATEST(step-history, last_status_update, created_at)` through a shared helper, applied to all three places that independently reimplemented "the talent's latest application".

## Azure / docs
- [Bug 24149](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24149) — reported by Patricio (FE), assigned to me, state **In development**.
- Surfaced while working the JazzHR push feature → [[Push Applications Echo to JazzHR (Feature 24051)]].

## PRs
- [#2018](https://github.com/taller-projects/echo-backend/pull/2018) → dev — **open, in review** (branch `24149/last-application-most-recent`, commit `5ab2796c`)
- FE: none. Contract is unchanged — same fields, same shapes; only *which* application `last_application` points at changes.

## How
- **`app/modules/application/models.py`** — new module-level `last_activity_at(application_id, last_status_update, created_at)` returning `GREATEST(max(step_history.created_at), last_status_update, created_at)`. Also hoisted the `application_workflow_step_history` `table()` alias to module level (it existed in three copies).
- **`app/modules/talent/models.py`** — `Talent.last_application` and the nine `last_application_*` column_properties share one subquery, so fixing its `ORDER BY` fixed all of them at once. Added `desc(Application.id)` as tie-break.
- **`app/modules/role/models.py`** — the same ordering was duplicated in `Role.active_candidates_count` and in `roles_with_active_candidates_subquery` (the `active_candidates_count__gte` filter). Both now call the helper.
- **Tests** — new `tests/unit/test_talent_last_application.py` (6 cases) + a role-side regression in `test_active_candidates_count.py`. **5 of them fail on `dev` and pass on the branch** — verified by stashing the `app/` changes and re-running.

## Decisions
- **`GREATEST`, not `COALESCE(..., created_at)`.** ATS-synced rows routinely carry a `last_status_update` *older than the Echo row itself* (real example: app created 2024-10-13 with `last_status_update` 2024-01-25). With `COALESCE` such a row would rank by the stale date and could still lose. `GREATEST` ignores NULLs and `created_at` is NOT NULL, so the key is never NULL and `NULLS LAST` became moot.
- **Fixed all three sites, not just talent.** They currently agree (all three wrong); fixing only `Talent.last_application` would have made the roles' active-candidate count and filter disagree with the talent overlay. `roles_with_active_candidates_subquery`'s own docstring already declared it must match `active_candidates_count`.
- **Added a deterministic tie-break** (`application.id DESC`). `LIMIT 1` over tied rows picked arbitrarily, so the same talent could report different "last" applications across queries — not just "the old one", genuinely unstable.
- **Implemented "most recent", not "active".** That is what the ticket asks for. See Pending — they are not the same thing.

## Gotchas
- **`last_status_update` is dead weight in app code.** No assignment anywhere under `app/`, no DB trigger. It only arrives via `ApplicationCreate.last_status_update` on ATS sync payloads. Any future ranking/filtering that leans on it will silently exclude every UI-created row. Dev spread: Taller 13.9% of eligible applications have a NULL ordering key; Synthesis Technologies, Cortez Group and Taller Dev are at **100%**; Navitec at 0% (its TrackerRMS sync populates it).
- **The ticket's original diagnosis was wrong and I proved it before coding.** It claimed `GET /talents/{id}` omitted `id`/`talent_id` inside `last_application` while the list returned them. Both endpoints emit the identical shape with `id` present (verified on a local backend against the dev DB *and* on deployed dev). `talent_id` is absent from `TalentLastApplication` — but from both endpoints, so it never explained a difference. Patricio retracted it in rev 5; I rewrote the title, description and **Repro Steps** (he had updated the description but left the stale root cause in the repro field, so the ticket contradicted itself).
- **"Terminal stage" is a red herring.** The corrected ticket initially framed the bug as "when the previous application is in a terminal stage". Status plays no part in the ordering: of 2587 affected talents on dev, **891 have a non-terminal winner**. Cleanest case: talent `85addf80-…`, two applications both in `New` created 80 seconds apart, returns the older.
- **Tests are order-sensitive by construction now.** `created_at` participates in the key and is set by the model default at insert, so in tests "created later" wins. `ApplicationCreate` has no `created_at` field, so to pin an exact tie you must pass it through `create_entity(extra_fields={"created_at": ...})`.
- Local repro recipe that worked well: run the app locally against the dev DB (`ENFORCE_SESSION_LIVENESS=false uv run uvicorn app.main:create_app --factory --port 8011`) and hit it with a real dev JWT. Minting a JWT is blocked by the tool classifier — ask for a real one instead.

## Pending
- Merge [#2018](https://github.com/taller-projects/echo-backend/pull/2018) → dev, then Bug 24149 → Ready to Test.
- **Open product question, flagged on the ticket and in the PR: "most recent" ≠ "active".** Some talents' newest application is terminal (e.g. `08cdd075-…`, whose latest is `HIRED - Contract signed`), so the overlay will now receive a terminal application in those cases. If the overlay always needs the *active* one, that needs a separate field rather than changing `last_application` semantics. Needs Patricio/producto.
- qa/main promotion not started.
- Behaviour change to expect after merge: on dev the `active_candidates_count__gte` filter moves from 1746 to 1759 roles — talents get re-attributed to the role holding their genuinely-newest application. Worth a heads-up if anyone reads those counts as stable.

## Related
- [[Push Applications Echo to JazzHR (Feature 24051)]] · [[Roles listing NULL-row hardening (Bug 24132)]] · [[Map - JazzHR integration]]
