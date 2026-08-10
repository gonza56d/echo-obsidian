---
type: delivery
status: merged
env: taller
delivered: 2026-08-10
tags: [bugfix, applications, jazzhr]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2026"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24165"
prd: ""
---

# Stamp last_status_update on status change (Bug 24165)

Patricio (FE) found while building the Jazz stage UI: `PATCH /applications/{id}` changes `status` but never writes `last_status_update` — the column's only writer was the ATS back-sync payload — so workflow-less (Jazz/legacy-status) applications have no "last stage change" date for the FE to show. Workflow tenants were fine (`last_step_update` derives from the step history). Fix: `ApplicationService.update` stamps it on real status changes, unless the caller sent the field explicitly.

## Azure / docs
- [Bug 24165](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24165) — created by Patricio 2026-08-10, assigned Gonzalo, In development. PR linked via comment.

## PRs
- [#2026](https://github.com/taller-projects/echo-backend/pull/2026) → dev — **MERGED 2026-08-10** (squash `fd15015a`; commits `c3efb502` + nits `f749d23f`; CI green, Pedro approved)

## Review (Pedro, 2026-08-10 — APPROVED, 0 blockers)
- Nit 1 → new `test_explicit_null_last_status_update_skips_stamp_and_clears`: explicit `last_status_update: null` + status change **skips the stamp AND clears the column** (pinned as contract). Fixing it exposed a latent duplicate-kwarg bug in the `make_application` helper (pinned default + `**overrides` collide) → dict-merge.
- Nit 2 → service comment now states the mechanics constraint: assignment registers the field in `model_fields_set` (what makes it survive `exclude_unset=True`); rebuilding `entity` before `super().update()` would silently drop the stamp.
- Q1 answered with dev data: back-sync does NOT always send the field — 3,949/26,152 (~15%) synced status-bearing rows have NULL `last_status_update`; omitted → we stamp Echo-now (better than NULL). Data-team heads-up owed.
- Q2: create-leaves-NULL confirmed intentional; "FE treats NULL as no stage change yet" passed to Patricio.

## How
- `app/modules/application/service.py` — in `update()`, right before `super().update()`: if `entity.status is not None and entity.status != old_status and "last_status_update" not in entity.model_fields_set` → `entity.last_status_update = datetime.now(tz=UTC)`. Mutating the pydantic entity registers the field in `model_fields_set`, so it rides `repo.update`'s `model_dump(exclude_unset=True)`.
- Covers the **promotion out of matching** (`NULL → first stage`, the Jazz path) because `old_status=None != entity.status`.
- `schemas.py`: replaced the ancient `# TODO modify automatically in update` on `ApplicationCreate.last_status_update` with a comment stating the behavior.
- `models.py`: updated the `last_activity_at()` docstring from [[Talent last_application recency (Bug 24149)]] — it claimed "nothing in the app ever writes last_status_update", now false; the GREATEST + `created_at` reasoning still holds (matching-only + pre-fix rows stay NULL).
- Tests: `TestLastStatusUpdateStamp` in `tests/unit/test_applications.py` (5 client-level cases): change stamps; promotion stamps; same-status PATCH doesn't; status-less PATCH doesn't; explicit value wins.

## Decisions
- **Explicit value always wins** (`model_fields_set` guard): the ATS back-sync PATCHes through the same code path (`internal_routers.py` PATCH `/applications/{id}`) sending the upstream change timestamp — stamping "now" over it would lie about the moment. If the back-sync ever PATCHes a status change *without* the field, we stamp now, which is still better than NULL.
- **Stamp only on actual change** (`!= old_status`), matching the gate used by `_handle_status_transition` / `_publish_status_changed_event` — a same-status PATCH is not a stage move (it still appends status history, as before).
- **No stamping on `create()`** — out of the ticket's scope; a fresh application's `created_at` covers "when did it enter this stage" and `last_activity_at()` GREATESTs it in anyway.
- Service layer, not schema validator: the stamp needs the pre-update DB state (old status), which a Pydantic validator can't see.

## Gotchas
- **`source scripts/venv.sh` before pytest = every client test 404s.** venv.sh does `set -o allexport && source .env` — the exported vars hijack the testcontainer (the known trap from [[reference_local_test_role_mismatch]], but presenting as 404s instead of role errors). Run plain `uv run pytest`; first run wasted a full triage cycle on this.
- The column is naive `timestamp` (migration `65758f5ebc54`) while `created_at` is `timestamptz`; writing `datetime.now(tz=UTC)` follows the existing precedent (`matched_on`, repository.py) and Postgres converts via session TZ (UTC).

## Pending
- ~~PR #2026 merge~~ **MERGED 2026-08-10**, Bug 24165 → **Ready to Test** (comment on ticket incl. FE note: created-with-status keeps NULL by design, treat as "no stage change yet").
- Data-team heads-up owed (from review Q1): back-sync omits `last_status_update` on ~15% of synced status-bearing rows (3,949/26,152 on dev) — post-fix those get Echo-now on their next change; confirm whether ER should always send it.
- FE consumption side is Patricio's — no FE ticket known; response shape unchanged, the field just starts being populated.
- qa/main promotion unrequested (rides normal release flow).

## Related
- [[Map - JazzHR integration]] · [[Push Applications Echo to JazzHR (Feature 24051)]] — the feature this surfaces from (stage moves for workflow-less tenants)
- [[Talent last_application recency (Bug 24149)]] — where "no writer for last_status_update" was first established; this fix retires that fact
