---
type: delivery
status: in-review
env: taller
delivered:
tags: [feature, kforce, unification, contacts, dashboard, contract-change]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2036"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24200"
prd: "https://app.notion.com/p/3b2aedca11f081f8a460f1c22f675ba8"
---

# Label-state dashboard contract convergence (Task 24200)

Fase 4 / paso 12 of the [[Kforce-main code unification (PRD 3b2aedca)]] program: `GET /contacts/dashboard/metrics` converges to the kforce M4 label×state shape (5 buckets: `active/past_clients_count`, `active/past_consultants_count`, `prospects_tracked_count`) **for ALL tenants, no flag** — decisión abierta 6 resolved 2026-08-07 (Pedro): standard contract change with a deprecation window, NOT a gated feature. The dev trio (`clients/consultants/alumni_tracked_count`) stays deprecated until both FEs migrate. Trigger: Pedro's Slack — Melina ported the active/past movida to Taller (#1962/#1963, tenure + company movement) and the dashboard was the piece left behind.

## Azure / docs
- [Task 24200](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24200) — created this session under umbrella US 24172 (the program US, where Leandro hangs the "Fase N - ..." tasks); In development.
- PRD ledger: `docs/unification-ledger.md` row **17** (added in the PR). Plan de ejecución paso 12 says "desbloqueado, falta aviso FE" — the PR's "Cambio de contrato" section (before/after JSON) is the input for that notice; the actual FE comms remain a human step.

## PRs
- [#2036](https://github.com/taller-projects/echo-backend/pull/2036) → dev — open. Branch `unif/dashboard-label-state` (unif/ style like #2023's `unif/contact-totals-widgets`).

## How
- `repository.py`: ported kforce's `_label_state_count` (kwargs signature kept so 4 of 5 call sites are kforce-identical) + `relationship_state` added to the dashboard `tracked_contacts`/`contact_info` CTEs; 5 FILTER aggregates lead the SELECT; legacy trio still computed behind them.
- **Semantic adaptation (the load-bearing detail)**: kforce's on-read label derives `Alumni` for every ended Consultant, dev retired that label (Task 23264) — so kforce's `past_consultants_count` = label=Alumni becomes dev's (Consultant, Past). Same humans, different data shape. Legacy persisted `Alumni`-typed rows (enum still accepted on write; dev DB has 0, prod unmeasured — psql to prod got blocked this session) are ORed in via `include_alumni_label=True`, keeping the 5 buckets an exact partition under any data.
- `prospects_tracked_count`: was a `@computed_field` subtraction (total − clients − consultants − alumni), now the real label-keyed bucket. Value-identical (alumni≡0; subtraction ≡ label=Prospect because state=Prospect ⇔ no relationships ⇔ label coalesces to Prospect). Old `test_alumni_dashboard_response.py` deleted; equality pinned in the new test instead.
- Cost (EXPLAIN vs dev DB, compiled the real query via a literal-binds capture script): same single statement, 0 extra queries; heaviest real user (198 tracked) 6.5→9ms warm; synthetic 40k-tracked stress (NULL-user tracker rows, unreachable via endpoint) 686→748ms (+9%). No mitigation needed — cost scales with the JWT user's tracked set, not tenant size.
- Tests `tests/unit/test_dashboard_label_state_counts.py` (6): bucket classification incl. Prospect-typed guard (label-keyed bucket catches label=Prospect+state=Past, kforce regression) + legacy Alumni row; exact partition; deprecated-trio consistency; golden-snapshot scenario replication (loads `contacts_dashboard_metrics.json` and asserts its exact values after rebuilding the C2/C4 data shapes); empty tracked set all-zeros; key-order contract (5 kforce keys first — FastAPI serializes in field order). Suite: 3642 passed. Repo-level via `background_request_context(RequestContext(tenant_id=...))` — `get_tenant_id()` returns None outside request context and the CTE would match nothing.

## Decisions
- `include_alumni_label` flag over a generic conds signature: keeps the kforce helper shape (dev is the surviving codebase post-cutover, but reviewers diff against kforce today).
- Waiver `[contacts_dashboard_metrics]` covers ONLY the 3 legacy keys. The tracked-set VALUE diff is deliberately NOT waived — it's the `tracked_by_id__in` param gap (see Pending) and waiving values would mask real classification regressions.
- `TenantFeature.LABEL_STATE_DASHBOARD` (#1993) left in place unused — post-program cleanup, per the PRD.

## Gotchas
- The golden replay can't fully MATCH this snapshot yet no matter what: the baseline was recorded via kforce's `tracked_by_id__in=U1` param and dev scopes to the JWT user (`0322865c…`), whose seed tracked set is different. The param superset ("acepta y devuelve tanto tracked_by_id como tracking_by_ids") is its own PRD contract line — separate port.
- kforce's dashboard repo takes `tenant_id`/`tracking_by_ids` args; dev derives both (RLS context / single user). Don't copy the kforce signature when porting around this endpoint.
- The ledger has a pending renumbering chore (two rows "12", collision on "13"); row 17 was the next free number.
- `docs/` matches a .gitignore rule — the ledger file is tracked anyway; `git add` the file path works, adding the dir errors.

## Pending
- Squash-merge #2036 to dev (review DONE 2026-08-11 — see Review & follow-up below).
- FE contract-change notice to both FE TLs (PR section is the input; paso 12 note says "falta aviso FE").
- `tracked_by_id__in`/`tracking_by_ids` param superset port (closes the replay VALUE gap; unticketed).
- Re-run classification tests under `kforce_tenant` fixture when #2029 merges (paso 12 commitment, same as #2023's).
- Legacy trio removal PR once both FEs migrate (end of deprecation window).
- Prod check for persisted `Alumni`-typed relationship rows (defensive OR covers them either way).
- Post-program: delete `TenantFeature.LABEL_STATE_DASHBOARD`.

## Review & follow-up (2026-08-11)

Ran the 3-agent `/pr-review` (architecture + tests-security + prd) on #2036.
**Verdict: READY WITH NITS — 0 blockers.** Arch 11 PASS / 0 FAIL / 3 N/A;
Tests&Security 12 PASS / 0 FAIL / 4 N/A; PRD 6/7 fully + 1 defensible warning
(cost measured on dev, not a large prod tenant — but the endpoint scopes to the
JWT user's tracked set, so tenant size isn't the cost driver).

Independently confirmed the load-bearing claims: the **exact-partition invariant**
holds under every data shape (state=Prospect iff no relationships, so a
Client/Consultant contact always lands in a bucket; legacy `Alumni`-typed rows
caught explicitly; the four types are mutually exclusive so no double-count),
`prospects_tracked_count` computed->real has **no other consumer**
(`reporting_dashboard` is an unrelated `ReportingDashboardResponse`, not a missed
site), and the golden replay is a **standalone ops script** (not pytest) so the
waiver honestly covers only the 3 legacy keys and does not mask bucket values.

Addressed the 2 test-coverage nits in follow-up commit `61d8e9f4` (pushed to the PR):
- **HTTP-layer test** `test_dashboard_metrics_endpoint_projects_label_state_buckets`
  — end-to-end through `GET /contacts/dashboard/metrics`, asserts the 5 buckets
  serialize via the response_model over the authenticated router path (one contact
  per bucket tracked to `mocked_user`).
- **Latest-relationship-wins test** `test_latest_relationship_wins_single_bucket`
  — an ended Consultant superseded by a newer still-open Client lands in exactly
  one bucket (open relationship wins via `end_date DESC NULLS FIRST`); partition
  still holds, no double-count.
- Nit #3 (factories over raw ORM) **skipped with justification**: no
  `RelationshipFactory` exists and the sibling `test_alumni_regression.py` uses the
  identical raw-ORM `Relationship(...)` pattern; a new factory would be scope creep.

**Gotcha (new):** the dashboard endpoint **404s in an isolated TestClient run**
because `.env` sets `ENABLE_ACCESS_CONTROL=True` and the authenticated DB-role path
in `app/database/base.py` (read **per request**) makes it unreachable; the full CI
suite only passes it because `test_alumni_regression.py` force-disables the flag at
import time. I scoped a **per-request toggle fixture** (`_access_control_off`)
around the single HTTP call instead of flipping the global module-wide — a second
import-time flipper would add a collection-order "who-restores-last" footgun. File
green in isolation (7 tests) and alongside the sibling + `test_relationship_state`
(50 tests).
