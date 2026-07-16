---
type: delivery
status: merged
env: taller
delivered: 2026-06-19
tags: [observability, sentry]
prs: [1578, 1579, 1590, 1595, 1597]
tickets: [22295, 23141]
---

# Sentry observability rollout (US 22295)

Full Sentry hardening for echo-backend. The SDK was already live before this (DSN required); this work added everything that makes issues actionable.

## Azure / docs
- US 22295 — Sentry observability (echo-backend slice; sibling stories 22296/97/98 for other services were left pending)
- Ticket 23141 — dispatcher errors to Sentry
- Sentry org: `taller-wn` (token in `~/.zshrc`, `/sentry` skill)

## PRs (all → dev, merged 2026-06-19)
- [#1578](https://github.com/taller-projects/echo-backend/pull/1578) — send outbox **dispatcher** errors to Sentry (23141)
- [#1579](https://github.com/taller-projects/echo-backend/pull/1579) — **release tracking** (git short SHA via Docker build-arg), request context, dispatcher coverage
- [#1590](https://github.com/taller-projects/echo-backend/pull/1590) — review follow-ups consolidated into ONE PR (#1583/#1587 closed in its favor — see the "single PR for related nits" rule)
- [#1595](https://github.com/taller-projects/echo-backend/pull/1595) — tag events with `component` (api / dispatcher)
- [#1597](https://github.com/taller-projects/echo-backend/pull/1597) — register `/debug/sentry` in ENV `development`, not `dev` (env-name gotcha)

## Gotchas
- Environment names: local is `development`, deployed envs are `dev`/`qa`/`prod` — an env-gated route registered under `"dev"` silently ships to the cluster.
- Release = git short SHA injected at image build; if a Sentry event has no release, the build-arg wiring broke.

## Related
- [[Map - Observability & Reliability]]
- [[similar_role null-vector 500 (Bug 23362)]] · [[Outbox poll backoff (Bug 23522)]] — first bugs diagnosed through this tooling
