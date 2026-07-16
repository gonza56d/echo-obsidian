---
type: delivery
status: shipped-prod
env: taller
delivered: 2026-07-15
tags: [bugfix, outbox, trackerrms]
prs: [1838, 1839, 1840]
tickets: []
---

# Outbox dispatcher: flat TrackerRMS payload, not an envelope (PR 1838)

After the outbox dispatcher was **enabled in prod** (infra PR #9981 in taller-ttit-kubernetes), every delivery to the TrackerRMS sync service failed `HTTP 422` and was **dead-lettered immediately** (422 = client error). The dispatcher sent the event envelope (`{event_id, event_type, data: {…}}`) but the sync service validates the **flat entity at the body root** — the contract the manual-sync `TrackerRMSHttpClient` already used.

**Why dev never caught it**: dev points at MockServer, which matches on path only and reads the id from either shape (`b.data.id ?? b.id`) → canned 200 regardless of body. Classic mock-too-lenient trap.

## PRs
- [#1838](https://github.com/taller-projects/echo-backend/pull/1838) → dev · [#1839](https://github.com/taller-projects/echo-backend/pull/1839) → qa · [#1840](https://github.com/taller-projects/echo-backend/pull/1840) → main — merged 2026-07-15

## How
- `_deliver_tracker_rms` now sends `event.payload` directly (flat), for both POST and PATCH (remember: dispatcher must route POST vs PATCH like manual sync — never always-POST).
- New setting `OUTBOX_DISPATCHER_SKIP_WRITEBACK` (default `True`) controls the `skip_writeback` flag per env — `true` in dev, `false` in prod.

## Related
- [[Outbox poll backoff (Bug 23522)]] · [[Map - TrackerRMS integration]]
- Dev MockServer expectations live in a taller-ttit-kubernetes ConfigMap (separate copy from the repo's init.json)
