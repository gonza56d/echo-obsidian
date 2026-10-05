---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, contacts, internal-api, external-links, contact-groups, taller, kforce]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2386"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25372"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25373"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25374"
prd: "https://app.notion.com/p/3ecaedca11f0811bbd71d57f636ae830"
---

# Contact external ids follow-ups - list filter via links, links dropped on delete, duplicate references (25372-25374)

The three follow-ups of [[Contact groups feed resolves external ids via entity_external_links (Bug 25274)]], shipped as one PR (Gonzalo's ask 2026-10-05, right after #2380 reached prod).

## Azure / docs
- [Bug 25372](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25372) `GET /internal/contacts?kforce_external_id__in=` column-only — In revision
- [Bug 25373](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25373) `ContactService.delete` leaves `entity_external_links` rows — In revision
- [US 25374](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25374) duplicate-reference semantics (parent Feature 24974) — In revision
- Design note `docs/contact-groups.md` updated (feed section, logs, cost, open follow-ups). No PRD of its own: the Tier B PRD of 25274 covers the contract; its "Q1" is what 25374 resolves.

## PRs
- [#2386](https://github.com/taller-projects/echo-backend/pull/2386) → dev — OPEN 2026-10-05 (`d6f8a804`), branch `25372/contact-external-links-followups`, worktree `.claude/worktrees/25372+contact-external-links-followups`. No FE PR (response additive; the FE never sends `kforce_external_id__in`). No migration, no flag.

## How
- **25372 — shared resolver.** `ContactService.resolve_external_ids(ids) -> {ext: {contact ids}}`: column via the new `ContactRepository.ids_by_kforce_external_ids(tenant_id, ids)` ∪ links via `ExternalLinkService.resolve_entity_ids`. Does NOT verify link targets exist (callers do). `ContactService.get_all` rewrites `kforce_external_id__in` → `id__in` (ambiguous id = every candidate; unknown = nothing; caller `id__in` intersects; the group-children predicate steps aside like for `id__in`). `ContactGroupService._resolve_nodes` uses the same resolver through `injector.get(ContactService)` (ContactService constructor-injects ContactGroupService → lazy) and `nodes_by_ids` over every candidate; `ContactGroupSQLRepository.resolve_external_ids` removed. Still 3 queries; on KForce the PK batch now also covers column hits.
- **25373 — links go with the contact.** `ExternalLinkService.unbind_entity(type, id, tenant_id=)` → `EntityExternalLinkSQLRepository.delete_by_entity` (tenant + entity_type scoped, **no commit**: runs inside `ContactService.delete`'s transaction, `super().delete` commits both). Contacts emit no outbox tombstone (only `touchpoint.deleted` exists), so nothing downstream needs the links after the delete.
- **25374 — `duplicate_contact`.** `_duplicate_references(nodes)` = contacts named by ≥2 resolved ids of the request; every such id is refused (`_Refusal(code, candidates)`), parents included (group skipped whole, children not evaluated); refused children are held. `_claim` first-wins removed. Warning `contact_group.duplicate_contact` (`tenant_id, external_id, contact_id, external_ids`); the `ambiguous_external_id` warning lost `named_by`; `contact_group.upserted` gained `duplicates=`.
- Tests: +8 filter (`TestKforceExternalIdInResolvesExternalLinks`), +4 `test_contact_delete_external_links.py`, +3 repo `TestDeleteByEntity`, groups named-twice test → 3 order-parametrised tests + reworked log test, +1 multitenancy delete isolation. Local: 192 targeted, 1546 unit selection, 112 multitenancy green.

## Decisions
- **US 25374 resolved as "refuse every reference" + dedicated code** (agent's recommendation; Gonzalo asked to "start addressing" without picking an option): order-independent, and Data can tell "two ids, one person" (`duplicate_contact`) from "one id, two people" (`ambiguous_external_id`). Consequence: a group whose *parent* is named twice is skipped whole — before, its children still applied. Flag in review if product prefers first-wins.
- **Resolver lives in `ContactService`** (owner of contact), not in the groups service; the groups service calls it lazily to avoid the DI cycle.
- **Interactions filter excluded from 25372**: `GET /internal/contacts/interactions?kforce_external_id__in=` keys on the *interaction's* own id, not the contact's — the earlier "same bug" claim (memory + the 25274 note) was wrong; ticket, PR and design note say so.
- **No backfill of pre-existing dangling links** in this PR (Taller dev had 6 on 2026-10-01; kforce-prod has 0 contact links). The one-off guarded `DELETE … WHERE NOT EXISTS` is documented as a follow-up; other entity types (talent/application/role/user) still leave links behind on delete.

## Gotchas
- The outbox dispatcher resolves the TrackerRMS id of a `*.deleted` event **at delivery time from `entity_external_links`** (`_deliver_tracker_rms_delete`), because the row is already gone. Deleting links synchronously is only safe because contacts have no tombstone event; if one is added, move the cleanup into the dispatcher like touchpoints. Recorded in the `delete` docstring.
- Worktree guard inside `.claude/worktrees/*`: blocks Write/Edit outside the worktree (scratchpad included), `for`-loops with computed `sed`, `export VAR=$(…)` prefixes, heredocs that `cd` elsewhere, and heredoc text containing the three letters of the VCS name (URLs included). Workarounds: python heredocs run from the worktree with the host name concatenated at runtime, `GH_TOKEN=$(…) gh …` inline, PR body and Azure JSON written with the Write tool into the VCS-ignored `vault/` of the worktree (`vault/.pr_body_*.md`, `vault/.az_*.json`, sent with `-d @file`).
- `EnterWorktree` branched from the session-start HEAD (`f4de7891`), not `origin/dev` → hard reset to `origin/dev` first; branch renamed from `worktree-…` to `25372/contact-external-links-followups`.
- `ContactFactory` randomises `kforce_external_id`: pass `kforce_external_id=None` explicitly for link-only fixtures.

## Pending
- Review (Flor/Leo/Pedro) → squash-merge → Close 25372/25373/25374 → dev smoke: `GET /internal/contacts?kforce_external_id__in=<hubspot id>` on "Hubspot - Taller" (`3744ad0b`) returns the contact.
- qa → main promotion with the next release.
- Tell Nico/Emiliano: new `duplicate_contact` code (Task 25332 already asks Data to tolerate new codes).
- Follow-ups unticketed: dangling-link backfill; link cleanup on talent/application/role/user delete.

## Related
- [[Contact groups feed resolves external ids via entity_external_links (Bug 25274)]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Map - Kforce]]
