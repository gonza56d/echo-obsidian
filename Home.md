---
type: home
tags: [home]
---

# 🏠 Echo delivery memory

Personal vault: one note per delivered feature/bugfix (echo-backend + echo-frontend), so "what did we do 15 days ago and what was left pending?" takes one search instead of an archaeology session. Conventions: [[CLAUDE]] · Template: [[Delivery]].

**Maps**: [[Map - Contact Relationships]] · [[Map - Kforce]] · [[Map - TrackerRMS integration]] · [[Map - Pentest 2026]] · [[Map - Observability & Reliability]]

---

## 🚧 In flight (open PRs / gated work)

- [[Pentest 4.1.7 input validation (23018)]] — PRs [#1625](https://github.com/taller-projects/echo-backend/pull/1625) (dev) + [#1626](https://github.com/taller-projects/echo-backend/pull/1626) (kforce-dev) **still open**
- [[Pentest 4.3.1 CORS allowlist (23024)]] — PRs [#1632](https://github.com/taller-projects/echo-backend/pull/1632) + [#1633](https://github.com/taller-projects/echo-backend/pull/1633) **still open**; live re-test pending post-merge
- OpenAPI 500 via `partial_model` (Sentry `7600828395`) — fix verified, **PRs to dev + kforce-dev not created yet** → [[Map - Observability & Reliability]]
- Taller port of the `has_contact_interaction` pointer rewrite → [[Kforce Last Contacted By filter (PR 1846)]]
- Kforce [Task 23375](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23375) — gated `last_relationship_type` column DROP → [[Kforce Contact Relationships port (US 23370)]]
- Taller QA/PROD matview gate for migration `mx7qkw9n2r4v` → [[Generic Contact Relationships (US 23240)]]
- Kforce group-hierarchy: 3 latent seed bugs + prod seed → [[Kforce multilevel groups (US 23339)]]
- Industry-agnostic: admin surface + prod `generic` gated on matching-products data promotion → [[Industry-agnostic Echo (PRD 398aedca)]]
- Outbox dispatcher prod deploy quantification (infra [#9981](https://dev.azure.com/TallerInternTools/Snapshot%20Exploration/_git/taller-ttit-kubernetes/pullrequest/9981)) → [[Map - TrackerRMS integration]]
- WeasyPrint: Taller proposal manual QA → [[WeasyPrint 62 to 68 upgrade (US 23479)]]

## 📌 Recent activity

- **2026-07-16** — [[Case studies per-card management (US 23613)]] merged ([#1842](https://github.com/taller-projects/echo-backend/pull/1842) + [#1843](https://github.com/taller-projects/echo-backend/pull/1843)) · [[Kforce Last Contacted By filter (PR 1846)]] merged
- **2026-07-15** — [[Outbox flat payload fix (PR 1838)]] → dev/qa/main
- **2026-07-13/14** — [[Industry-agnostic Echo (PRD 398aedca)]] M1–M5 + /users/me merged; dev QA passed · [[Deep pagination selectin fix (23553)]] both envs · [[Project creation consumer_id 422 (Bug 23571)]]
- **2026-07-10** — [[Client Active significant activity (US 23536)]] both envs · [[Kforce Client Active no-job gate (Bug 23545)]] · [[Kforce contacts custom sorts (23546)]] · [[Inactive vendor notifications (US 23531)]]
- **2026-07-09** — [[Moved-away Client contacts Past (Bug 23519)]] → prod · [[ATS deep-links Open in ATS (US 23507)]] logo slice · [[Outbox poll backoff (Bug 23522)]]
- **2026-07-07/08** — [[Client Active gate relaxation (PR 1745)]] → prod · [[Alumni label removal (PR 1742)]] → prod · [[WeasyPrint 62 to 68 upgrade (US 23479)]] · [[Kforce relationship aggregates M6 (US 23424)]] · ATS deep-links M1+M2
- **2026-07-02/03** — [[Kforce Contact Relationships port (US 23370)]] M1–M4 merged · [[Kforce multilevel groups (US 23339)]] seed applied · [[Future-dated interactions fix (Bug 23383)]]
- **2026-07-01** — [[similar_role null-vector 500 (Bug 23362)]] hotfixed to prod
- **2026-06-25/30** — [[Generic Contact Relationships (US 23240)]] M1→DROP+hotfix · [[Contact bulk_track IntegrityError (Bug 23251)]] · [[UUID typing for id__in filters (23253)]]
- **2026-06-22/24** — [[Pentest 4.1.3 session-liveness (23014)]] · [[Pentest 4.1.5 no-store headers (23016)]] · [[Roles statement timeout fix (PR 1600)]] · [[Pending interview notifications (US 23321)]] step 1
- **2026-06-18/19** — [[External links writeback (US 23126)]] · [[Sentry observability rollout (US 22295)]] · [[Upload file-type validation (23013)]]

## 🗂 All deliveries

Browse `Deliveries/` (33 notes, 2026-06-18 → 2026-07-16), or start from a Map above.
