---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, jazzhr, outbox, applications, entity-resolution]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1986"
  - "https://github.com/taller-projects/echo-backend/pull/1987"
  - "https://github.com/taller-projects/echo-backend/pull/1988"
  - "https://github.com/taller-projects/echo-backend/pull/1989"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24051"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24052"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24053"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24054"
prd: "https://app.notion.com/p/3b2aedca11f081318531c144c63d72e7"
---

# Push Applications Echo → JazzHR (Feature 24051)

Inverts the sync direction for **Taller** applications: today they are born in JazzHR and mirrored into Echo by the data team's back-sync (Echo = espejo); stage changes happen in Jazz. This feature makes **Echo the origin** — the application is created in Echo (`POST /applications`, status `New`) and the event rides the **existing outbox/dispatcher** (same infra as TrackerRMS/Navitec) to a new `jazz_hr` delivery handler that calls **entity-resolution**: `application.created` → create-or-get, `application.updated` → `change_stage`. Taller status names match the Jazz workflow **637230** steps 1:1 (raw, no mapping table). **No schema changes, no new public endpoints.** M1 (create path) shipped as PR [#1986](https://github.com/taller-projects/echo-backend/pull/1986) → `dev` (open, full `tests/unit` suite green: 3292).

## Azure / docs
- Epic [23305](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23305) Taller - Jazz (Application stages)
- Feature [24051](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24051) — this delivery
  - [US 24052](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24052) — **M1** Create path (emission rule + `jazz_hr` create-or-get handler + link persistence)
  - [US 24053](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24053) — **M2** Status path (`change_stage` + ordering + freshness guards)
  - [US 24054](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24054) — **M3** FE + cutover (DELETE restriction, `tenant_integrations` enablement, back-sync adaptation, prod)
- PRD: [Push de Applications Echo → JazzHR (tenant Taller)](https://app.notion.com/p/3b2aedca11f081318531c144c63d72e7) — owner @pedro.rocha, Tier C
- Sibling exploratory line (different approach): Feature [23306](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23306) "Explore ↔ sync echo→jazz on stages", US [23688](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23688) (Ready to Test), US [24026](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24026) (FE hardcoded-stages dropdown for Taller).

## PRs
- [#1986](https://github.com/taller-projects/echo-backend/pull/1986) → `dev` — **open** (M1 create path): emission rule in `ApplicationService` + `jazz_hr` create-or-get handler + dual-write link persistence + no-op for unsupported event types. Commit `ce12c492`. Also fixes the active Navitec `matching_diff` → TrackerRMS shortlist leak. Branch `24052/jazz-hr-application-push-m1` (worktree).
  - **Conflict fix 2026-08-04**: `dev` merged the touchpoints reverse-push PRs (#1978/#1979) which appended test classes at the same EOF as mine → merged `origin/dev` into the branch (merge `f7b3ea1a`, no rebase/force per no-force-push rule); resolved both test-file conflicts (kept my emission tests + `TestDeliverJazzHr`, kept dev's touchpoint tests, dropped dev's stale stage-change assertion superseded by my M1 change). 266 outbox/application/touchpoint tests green, ruff clean. PR #1986 now MERGEABLE.

## How (implementation shape across milestones)
- **Emission rule — all in `ApplicationService`** (`app/modules/application/service.py`), zero changes to dispatcher/writer/repos/schema. Verified against `dev` before ticketing:
  - Helper `_in_matching(status, workflow_step_id)` = `status is None and workflow_step_id is None` — extracts the canonical predicate today duplicated in `_snapshot_owner_if_leaving_matching` (`service.py:515`) and the `category==MATCHED` branch (`models.py:361`).
  - `create()`: emit `APPLICATION_CREATED` only when the app is born **outside** matching (defensive gate); payload gains `status`.
  - `update()`: three branches on the **effective post-update** state (incoming value wins over pre-update snapshot, same as the existing `effective_step_id` block at `service.py:444-448`) — **(a)** matching→non-matching = promotion → `APPLICATION_CREATED` with the new status (never `updated`); **(b)** already in-process → `APPLICATION_UPDATED`; **(c)** still matching → emit nothing. Emission stays **before** `super().update()` (same transaction).
- **`jazz_hr` handler** in the dispatcher (`app/modules/outbox/dispatcher.py`): new `_deliver_jazz_hr` branch registered in the `_deliver()` if/else. `created` → `POST /applications/sync_data` (v2, create-or-get, `X-Echo-internal`); `updated` → `POST /applications/change_stage`. Identity/linkage resolved **fresh per delivery by SQL** (`jazz_job_id`←`role.external_id`, `jazz_candidate_id`/`talent_email`/`echo_source`←talent row, `jazz_application_id`←`entity_external_links`/`application.external_id`); payload freezes only what describes the event (`status_from`/`status_to`/`updated_by_id`/`occurred_at`).
- **Guards**: ordering (`updated` without link → **retryable**, never fallback-create — raise a non-`DeliveryError` à la `LinkPersistError`) and freshness (`status_to` ≠ current Echo status → no-op `superseded`; new `OutboxRepository.get_application_status`, one SELECT/PK).
- **Dual-write** jazz id → `entity_external_links` (`jazz_hr`) + `application.external_id`, patrón `persist_sync_result`.

## Decisions
- **Matching emission rule (the crux).** Verified in code 2026-08-04: the matching engine already does **not** emit `created` (bulk INSERT in `ApplicationRepository.create_match_applications`, no outbox). The real leak is `update()` emitting `APPLICATION_UPDATED` **unconditionally** — including `POST /applications/{id}/matching_diff` (`service.py:198-200`, called by the FE after each match), which for a matched app has no external link, so the **tracker handler falls back to POST and creates a shortlist in TrackerRMS off a single match**. This is an **active Navitec bug** the "silence while in matching" branch fixes for free. Promotion→`created` makes the invariant "every processable `updated` has a prior `created`" true, which is what makes M2's "retry, never create" ordering guard safe from permanent dead-letters.
- **409 on `POST /applications` vs an existing matching row** (candidate already matched to the role) → BE just raises `DuplicateError` (409), **FE handles it** (confirmed with Gonzalo). No promotion-on-conflict logic in the backend.
- **Cross-platform emission is uniform.** The emission rule is not platform-aware (the emitter is agnostic; consumers decide). Today Taller↔`jazz_hr` and Navitec↔`tracker_rms` is 1↔1, but the schema is 1↔N (`tenant_integrations` PK `(tenant_id, external_platform)`, one delivery row per enabled platform), so the emitter must not condition on platform. Hence the `jazz_hr` handler no-ops unsupported event types (talent.*, role.*, org.*, contact.*, user.*).
- **DELETE contract change** (M3): `DELETE /applications/{id}` → 204 only while in matching, **409** once in-process (exit is a terminal status via `change_stage`). Prevents Jazz orphans and back-sync resurrections. Global-vs-jazz-only scope = PRD open question #6, to close with product.

## Gotchas
- **`get_external_id` / `persist_sync_result` are tracker-shaped.** For `application` the scalar path **ignores `external_platform`** and returns `application.external_id` (`repository.py:393-404`); `persist_sync_result` hardcodes the `tracker_rms_id` response key (`dispatcher.py:470`). The `jazz_hr` handler needs **platform-aware** lookup/persist or it will read/write TrackerRMS ids. Ties into PRD open question #1 (how `application.external_id` is populated in prod).
- **Deploy order is load-bearing**: the handler must be deployed **before** the `tenant_integrations` INSERT — enabling `jazz_hr` today dead-letters every event of the tenant (`"No delivery handler for platform: jazz_hr"`, already asserted by `tests/unit/test_outbox_dispatcher.py:370`).
- **Fine ordering assumes a single dispatcher replica** — current deploy invariant, made explicit in the PRD.
- QA case to confirm: `On Hold` vs `ON HOLD` case-sensitivity in ER's stage-name match (the Echo enum has both variants) — ties to [[On Hold candidates invisible in pipeline buckets (Bug 24010)]].

## Pending
- **System tests DONE** (#1989) — the PRD's testcontainers plan is covered.
- **Blocked on data team** (does not block starting M1's emission rule / handler skeleton): open q#2 (final `/applications/sync_data` v2 shape — today returns 200-on-failure), q#4 (`jazz_candidate_id`: `ats_external_ids` vs `jazz_person_id`), q#5 (`user_id` of `change_stage`: Echo id vs `jazz_user_id` + fallback). **Do not enable delivery in dev without the v2 contract.**
- **Blocked on data team for cutover (M3)**: back-sync → upsert/skip when the app already exists in Echo.
- **Infra**: INSERT `tenant_integrations` (Taller, `jazz_hr`) per env + dispatcher ER env vars (URL + `X-Echo-internal` key).
- Prod verification for open q#1 (`application.external_id` format) → backfill decision for `entity_external_links`. Gonzalo can run the prod query when needed.
- **QA hours + estimate**: PENDING (sprint planning) before `Ready for review`.
- **M1 (#1986) reviewed 2026-08-04 → READY WITH NITS (0 blockers)**; actionable test nits closed in `3a11bf52` (7 unit + 3 system, test-only — jazz_hr handler error branches + `get_talent_jazz_person_id` cross-tenant). Merge to dev FIRST. M3/US 24054 gates before enabling delivery: `talent_email`+`echo_source` in the ER body (ticket named 5 fields, PR sends 3), platform-aware role read, collapse `_JAZZ_APPLICATION_ID_KEYS`. **M2 (#1987) in review, stacked on M1** → rebase onto dev after M1 merges, then merge. **M3 backend (#1988) in review** (DELETE 409 restriction, global scope). Remaining M3 (NOT backend-coded here): FE apply-branch + hide delete for in-process (FE team); back-sync → upsert/skip (data team); `tenant_integrations` INSERT (handler BEFORE INSERT) + prod enablement (infra). Whole feature QA-gated before prod; `jazz_hr` disabled until then.
- Open q#5 (`change_stage` `user_id`: Echo id vs `jazz_user_id`) flagged in M2 handler comment — needs data-team answer before enabling.
- FE work tracked as a section inside US 24054 (per team decision — no separate FE ticket).

## Related
- [[Map - JazzHR integration]] · [[Map - TrackerRMS integration]] (shared outbox/dispatcher; the emission rule change touches Navitec — regression must stay green)
- [[Outbox skips internal-originated emits (Bug 23656)]] — `is_internal` suppression this feature relies on
- [[External links writeback (US 23126)]] — the `entity_external_links` dual-write pattern reused here
- [[Outbox flat payload fix (PR 1838)]] · [[Outbox poll backoff (Bug 23522)]] — dispatcher behavior context
