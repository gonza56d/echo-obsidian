---
type: delivery
status: merged
env: taller
delivered: 2026-07-09
tags: [bugfix, outbox, sentry, resilience]
prs: [1799]
tickets: [23522]
---

# Outbox dispatcher poll backoff + Sentry dedupe (Bug 23522)

Sentry `7600853881`: the dev DB went read-only for ~6 minutes (2026-07-08) and the outbox dispatcher **flooded 170 Sentry events** retrying its poll at the fixed 2s cadence.

## PRs
- [#1799](https://github.com/taller-projects/echo-backend/pull/1799) → dev — merged 2026-07-09. Azure Bug 23522 Closed. **Taller-only** (kforce has no outbox dispatcher).

## How
- **Exponential backoff** on poll failure, capped at the lease TTL (so a recovered dispatcher can't hold stale leases).
- **First-of-streak Sentry capture** — one event per failure streak, not one per retry.
- Sleep waits on the **stop event** (clean shutdown during backoff).

## Related
- [[Sentry observability rollout (US 22295)]] — the tooling that surfaced it
- [[Outbox flat payload fix (PR 1838)]] · [[Map - TrackerRMS integration]]
