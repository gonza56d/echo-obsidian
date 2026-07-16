---
type: map
tags: [map, contact, relationships]
---

# Map — Contact Relationships

The longest-running saga: generalizing the contact relationship model to **label (Client/Consultant) ⟂ state (Active/Past)**, computed on-read, on both environments — then iterating on the Client Active semantics as real prod data (mostly Navitec) exposed edge cases.

## Timeline

### Foundation (Taller)
- [[Generic Contact Relationships (US 23240)]] — the core refactor: on-read model, column DROP, view-shape guard (Jun 25–30)
- [[Alumni label removal (PR 1742)]] — kill the legacy "Alumni" label backend-side (Jul 7)

### Kforce port + net-new
- [[Kforce Contact Relationships port (US 23370)]] — M1–M4 copy+adapt + Re-Engage/tenure/expanded-view/dashboard (Jul 2–7)
- [[Kforce relationship aggregates M6 (US 23424)]] — People Involved + contact-level totals (Jul 8)

### Client Active semantics iterations (order matters!)
1. [[Client Active gate relaxation (PR 1745)]] — don't punish contacts with no scraped history (Jul 7)
2. [[Moved-away Client contacts Past (Bug 23519)]] — unless the scrape proves they left (Jul 9)
3. [[Client Active significant activity (US 23536)]] — 12-month significant activity, null end_date ≠ vigencia; kforce-first, then Taller (Jul 10)
4. [[Kforce Client Active no-job gate (Bug 23545)]] — port of 1+2 to kforce (Jul 10)

### Adjacent contact-module fixes
- [[Contact bulk_track IntegrityError (Bug 23251)]] · [[Future-dated interactions fix (Bug 23383)]] · [[Kforce contacts custom sorts (23546)]] · [[Kforce Last Contacted By filter (PR 1846)]]

## Standing gotchas for this area
- Smart-search views/matviews (`view_smart_search_contacts_info`, `mv_smart_search_*`) are **owner-managed out-of-band** ([ticket 19757](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/19757)) on BOTH envs — never `CREATE OR REPLACE` them without the `_view_is_repo_shaped` guard.
- The Client Active rule lives in `_relationship_is_active_expr` (contact/models.py) on both envs, but the **implementations have drifted differently** — always verify against the branch you're on.
- `current_company_id` / `current_relationship` feed the TrackerRMS outbox — do not break when touching relationship logic.

## Still pending in this saga
- Taller: QA/PROD matview recreation gate for migration `mx7qkw9n2r4v`; dashboard counts reshape (#4); FE [US 23259](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23259) (Alumni chrome).
- Kforce: [Task 23375](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23375) physical column DROP (per-env owner gate); M5 FE (Alumni flip + dashboard key rename).
- Moved-away `company_id`-exact edge case.
