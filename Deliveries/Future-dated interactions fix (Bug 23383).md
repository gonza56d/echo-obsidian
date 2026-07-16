---
type: delivery
status: merged
env: taller
delivered: 2026-07-02
tags: [bugfix, contact, navitec]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/1711"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/23383"
---

# Future-dated interactions excluded from last_interaction (Bug 23383)

Navitec logs **future-dated interactions on purpose** (follow-ups: "call back on Jul 6"). The `ROW_NUMBER() OVER (ORDER BY date DESC)` subquery in `refresh_contact_attributes_bulk` had no upper bound, so the future follow-up won as `last_interaction` → FE renders "Today", ordering breaks.

## PRs
- [#1711](https://github.com/taller-projects/echo-backend/pull/1711) → dev — merged 2026-07-02

## How
- Bound latest-interaction subquery + interaction-count aggregation to `Interaction.date <= func.now()` (shared `interaction_has_occurred` expr). `hot_lead`, `relationship_state`, sort columns all read the denormalized value → corrected automatically.
- **Backfill migration** `k7n3wq9x2rmp`: denormalized columns only recompute on write, so affected contacts don't self-heal — recompute `last_interaction_id`/`last_interaction_date`/`client_visits_count` for every contact with ≥1 future-dated interaction (future-only contacts get nulled). Scoped by data condition, not tenant.
- Creating future-dated interactions stays unrestricted — follow-ups keep working.

## Decisions
- Cutoff is timestamp `<= now()` (consistent with `hot_lead`/`relationship_state`), not end-of-day.
- Future interactions also excluded from `client_visits_count` for consistency.

## Related
- [[Map - Contact Relationships]] · Navitec client context in [[Map - TrackerRMS integration]]
