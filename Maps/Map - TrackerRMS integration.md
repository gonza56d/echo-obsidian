---
type: map
tags: [map, trackerrms, outbox, navitec]
---

# Map — TrackerRMS integration (Navitec)

Everything around syncing Echo ↔ TrackerRMS for **Navitec** (active client: TrackerRMS ATS, custom CV/JD generation; team notes in echo-backend `vault/Echo/Navitec/`).

## Object mapping
Role→Opportunity · Talent→Resource · Application→OpportunityResource · Organization→Client. Linked by TrackerRMS id in `entity_external_links`.

## Architecture
- **Outbox pattern**: `integration_outbox` rows enqueued per entity action (org=track, role=update-if-linked, user=create-only), drained by a background **dispatcher** that POST/PATCHes the sync service (must route POST vs PATCH like manual sync — never always-POST).
- Dev talks to a **MockServer** whose expectations live in a taller-ttit-kubernetes ConfigMap (separate copy from the repo's init.json) — it matches on path only, which is how [[Outbox flat payload fix (PR 1838)]] escaped to prod.

## Deliveries (pre-window context)
- [US 22995](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/22995) (T1–T8) — outbox for Contact/Org, merged to dev (T8 dropped)
- User entity outbox ([23084](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23084), PR [#1563](https://github.com/taller-projects/echo-backend/pull/1563)) + link-persist silent-drop fix ([23089](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23089), PR [#1564](https://github.com/taller-projects/echo-backend/pull/1564))

## Deliveries (this vault's window)
- [[External links writeback (US 23126)]] — application + talent ids into `entity_external_links` (Jun 18)
- [[ATS deep-links Open in ATS (US 23507)]] — expose links + logo for the FE button (Jul 8–9)
- [[Outbox poll backoff (Bug 23522)]] — dispatcher resilience under DB outage (Jul 9)
- [[Outbox flat payload fix (PR 1838)]] — first prod-enablement bug: envelope vs flat body (Jul 15)

## Prod rollout state
- Dispatcher enabled in prod via infra PR **[#9981](https://dev.azure.com/TallerInternTools/Snapshot%20Exploration/_git/taller-ttit-kubernetes/pullrequest/9981)** (values-prod dispatcher block; prereqs: Vault `OUTBOX_DISPATCHER_ENABLED` + role migration `du9q74zf53x9`). ~8 weeks of prod backlog drains safely (bounded; no-op for non-integrated tenants).

## Reference
- TrackerRMS API: swagger + object mapping notes in auto-memory `reference_trackerrms_api`.
- Local sync system tests: need Docker; run with `TRACKER_RMS_ENABLED_TENANT_IDS=""` to dodge 403.
