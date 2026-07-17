---
type: home
tags: [home]
---

# 🏠 Echo delivery memory

Personal vault: one note per delivered feature/bugfix (echo-backend + echo-frontend), so "what did we do 15 days ago and what was left pending?" takes one search instead of an archaeology session. Conventions: [[CLAUDE]] · Template: [[Delivery]].

**Maps**: [[Map - Contact Relationships]] · [[Map - Kforce]] · [[Map - TrackerRMS integration]] · [[Map - Pentest 2026]] · [[Map - Observability & Reliability]]

---

## 🚧 In flight (open PRs / gated work)

- [[Open Jobs 1-5 matching (US 23640)]] — **M1 (backend) PR [#1854](https://github.com/taller-projects/echo-backend/pull/1854) open → `dev`** (tasks 23641/42/43 in one PR; built vs mock; **merge gated on Data endpoint [US 23610](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23610)**). M2 (FE, [US 23644](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23644)) is frontend-owned (not backend scope) — its PR should note M1 must merge first.
- [[Case studies per-card management (US 23613)]] — QA/PROD promotion cherry-picks **open**: [#1852](https://github.com/taller-projects/echo-backend/pull/1852) → qa + [#1853](https://github.com/taller-projects/echo-backend/pull/1853) → main (merge with merge commit, main after qa)
- [[Interview assessment change history (US 22248)]] — Melina's [#1848](https://github.com/taller-projects/echo-backend/pull/1848) **open**; reviewed 2026-07-17 (READY WITH NITS, 0 blockers) + nit fixes pushed (`cd3c0c80`/`4cae3e48`); 3 open questions for Melina; FE [#2970](https://github.com/taller-projects/echo-frontend/pull/2970) merges after
- [[Pentest 4.1.7 input validation (23018)]] — PRs [#1625](https://github.com/taller-projects/echo-backend/pull/1625) (dev) + [#1626](https://github.com/taller-projects/echo-backend/pull/1626) (kforce-dev) **still open**
- [[Pentest 4.3.1 CORS allowlist (23024)]] — PRs [#1632](https://github.com/taller-projects/echo-backend/pull/1632) + [#1633](https://github.com/taller-projects/echo-backend/pull/1633) **still open**; live re-test pending post-merge
- OpenAPI 500 via `partial_model` (Sentry `7600828395`) — fix verified, **PRs to dev + kforce-dev not created yet** → [[Map - Observability & Reliability]]
- [[Kforce Last Contacted By filter (PR 1846)]] — round 2 [#1850](https://github.com/taller-projects/echo-backend/pull/1850) (kforce, [Bug 23638](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23638)) + Taller port [#1851](https://github.com/taller-projects/echo-backend/pull/1851) ([Bug 23639](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23639)) both **open**; #1851 review-fixed (alembic multi-head rebase onto dev head `3gufg5ykw01g` + concurrent index build), commit `fc5876cf`
- Kforce [Task 23375](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23375) — gated `last_relationship_type` column DROP → [[Kforce Contact Relationships port (US 23370)]]
- Taller QA/PROD matview gate for migration `mx7qkw9n2r4v` → [[Generic Contact Relationships (US 23240)]]
- Kforce group-hierarchy: 3 latent seed bugs + prod seed → [[Kforce multilevel groups (US 23339)]]
- Industry-agnostic: admin surface + prod `generic` gated on matching-products data promotion → [[Industry-agnostic Echo (PRD 398aedca)]]
- Outbox dispatcher prod deploy quantification (infra [#9981](https://dev.azure.com/TallerInternTools/Snapshot%20Exploration/_git/taller-ttit-kubernetes/pullrequest/9981)) → [[Map - TrackerRMS integration]]
- WeasyPrint: Taller proposal manual QA → [[WeasyPrint 62 to 68 upgrade (US 23479)]]

## 📌 Recent activity

- **2026-07-17** — [[Open Jobs 1-5 matching (US 23640)]] — **M1 backend implemented → PR [#1854](https://github.com/taller-projects/echo-backend/pull/1854) → `dev`** (open): sync client + per-call timeout/504 mapping (tasks 23641), `match_talents` re-impl to 1-5 + tenant-tagged JSONB + row-lock RMW + cap 30 + tenant-aware `highest_match_score` SQL + service read-filtering (23642), 502/504 error mapping + structured logs + unit/system tests (23643). 14 new unit tests + 2 system tests green, ruff clean; merge gated on Data US 23610. Earlier same day: feature resumed from [PRD](https://app.notion.com/p/39eaedca11f081ff95f4c0b20b6b3aab), tenancy risk confirmed, PRD §7 plan, Azure tickets created under Feature 23494 · [[Kforce Last Contacted By filter (PR 1846)]] — #1846 proved insufficient (pagination COUNT still timed out); round-2 fix [#1850](https://github.com/taller-projects/echo-backend/pull/1850) (nested EXISTS + `contact_last_interaction_id_idx`, >2min→201ms) + [Bug 23638](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23638) · Taller preventive port [#1851](https://github.com/taller-projects/echo-backend/pull/1851) ([Bug 23639](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23639): dev count already at 11.8s of the 20s budget → 41ms; **/pr-review caught a latent alembic multi-head** — migration cut off `q8vd3mzk7w2p` but dev head advanced to `3gufg5ykw01g`, would 2-head dev on merge; fixed by rebase onto dev head + concurrent index build + tenant/test nits, commit `fc5876cf`) · [[Case studies per-card management (US 23613)]] — dev e2e vs real TB **PASSED** (all 6 endpoints; Navitec-only QA, company-name dedup nuance); US → Ready to Test; then QA/PROD promotion cherry-picks opened ([#1852](https://github.com/taller-projects/echo-backend/pull/1852) → qa, [#1853](https://github.com/taller-projects/echo-backend/pull/1853) → main, byte-identical to dev, no migrations) · [[Interview assessment change history (US 22248)]] — fixed PR #1848 CI (polyfactory FK pins) + backfill-migration ordering no-op; full review (0 blockers) + nit fixes pushed (jsonb-null NULLIF, marker-collision skip, repo-level scoping)
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
