---
type: delivery
status: merged
env: both
delivered: 2026-07-07
tags: [chore, security, dependencies]
prs: [1750, 1751]
tickets: [23479, 23480, 23481]
---

# WeasyPrint 62.3 → 68.1 upgrade (US 23479)

Dependency bump driven by an **SSRF CVE** in WeasyPrint (PDF generation: proposals, CV exports).

## Azure
- US 23479 → M1 Task 23480 (Taller) · M2 Task 23481 (Kforce). Tickets → Ready to Test.

## PRs
- [#1750](https://github.com/taller-projects/echo-backend/pull/1750) → dev · [#1751](https://github.com/taller-projects/echo-backend/pull/1751) → kforce-dev — both merged 2026-07-07

## Gotchas (export golden tests, macOS)
- `SAVE_GOLDEN` won't overwrite existing goldens — `rm` first.
- Remote `TEST_LOGO_URL` SIGABRTs pytest on macOS → dead-proxy workaround; 5% pixel threshold on comparisons.

## Pending
- Taller **proposal PDF manual QA** was still pending after merge.

## Related
- [[Map - Observability & Reliability]] (CVE hygiene)
