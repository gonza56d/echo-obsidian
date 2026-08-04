---
type: map
tags: [map, jazzhr, outbox, entity-resolution, taller]
---

# Map — JazzHR integration (Taller)

Syncing Echo ↔ **JazzHR** for the **Taller** tenant, via **entity-resolution** (the `taller_entity_resolution` service, auth `X-Echo-internal`) and the JazzHR workflow **637230** (Taller status names = workflow step names, 1:1, raw). Distinct from Navitec/TrackerRMS ([[Map - TrackerRMS integration]]) but shares the **same outbox/dispatcher** infrastructure.

## Object mapping
Role→Jazz job (`role.external_id`) · Application→Jazz application/projob reference (`application.external_id` + `entity_external_links` platform `jazz_hr`) · Talent→Jazz candidate. Application status name → Jazz workflow step name (raw match against workflow 637230).

## Direction inversion (the saga)
Historically Taller applications are **born in JazzHR** and mirrored into Echo by the data team's back-sync (`POST /internal/applications`); stage moves happen in Jazz. Echo is a mirror. The push feature makes **Echo the origin** for applications: created in Echo → outbox event → `jazz_hr` handler → entity-resolution.

## Downstream contracts (entity-resolution)
- `POST /applications/sync_data` **v2** (data-team dependency) — create-or-get idempotent; must return the jazz application id; real 4xx/5xx (today 200-on-failure).
- `POST /applications/change_stage` (deployed) — idempotent; advisory (not compare-and-swap); 404 returns available stages; 409 = ambiguous (send `jazz_application_id`).
- `POST /candidates/sync_data` (unchanged) — still called by the synchronous candidate sync before the `POST /applications`.

## Deliveries
- [[Push Applications Echo to JazzHR (Feature 24051)]] — **in progress** (tickets written 2026-08-04; M1 create / M2 change_stage / M3 FE+cutover). First delivery of this saga.

## Key decisions / invariants
- **Emission rule** lives entirely in `ApplicationService` and is **platform-agnostic** (emitter describes domain facts; handlers decide): silence while in matching, promotion→`created`, defensive create gate. Invariant: every processable `updated` has a prior `created` → makes the `jazz_hr` "retry, never create" ordering guard safe.
- **Freshness guard** (convergencia al último estado): `status_to` ≠ current Echo status → no-op `superseded`. Local anti-regression because `change_stage` is advisory. Assumes a single dispatcher replica.
- **Deploy order**: handler deployed **before** the `tenant_integrations` INSERT, else every tenant event dead-letters.

## Cross-saga note
The emission-rule change also fixes an **active Navitec bug**: `matching_diff` today emits an `updated` per matched app → tracker fallback-POST → shortlist created in TrackerRMS off a single match. The "silence while in matching" branch closes it. Navitec regression must stay green → [[Map - TrackerRMS integration]].

## Reference
- Shared outbox/dispatcher architecture, MockServer-in-dev, POST-vs-PATCH routing: [[Map - TrackerRMS integration]].
- `entity_external_links` enum already includes `jazz_hr`; `entity_type=application` already dual-written today.
