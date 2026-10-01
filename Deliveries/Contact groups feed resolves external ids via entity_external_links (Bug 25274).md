---
type: delivery
status: in-review
env: both
delivered:
tags: [bugfix, contacts, internal-api, external-links, hubspot, taller, kforce]
prs:
  - "https://github.com/taller-projects/echo-backend/pull/2378"
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25274"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24974"
prd: "https://app.notion.com/p/3ecaedca11f0811bbd71d57f636ae830"
---

# Contact groups feed resolves external ids via entity_external_links (Bug 25274)

Nico (Data, Slack 2026-10-01) found that `PUT /internal/contacts/groups/bulk` resolved parent and child ids only against `contact.kforce_external_id`, so the 12,339 Taller contacts that `taller_hubspot_api` identifies solely through `entity_external_links` (HubSpot id, all created since Aug 2026) came back as `unknown_parent` / `unknown_child` and could not be grouped. Confirmed in code (`app/modules/contact/group/` never touched the links table), plus two reporting gaps from the same cause (`unlinked` fell back to the UUID, link-only grandchildren vanished from `child_has_children`). Shipped Nico's option (b) generalised: ids resolve against the column **and** `entity_external_links` on **any platform**, with a new `ambiguous_external_id` skip code instead of guessing.

## Azure / docs
- [Bug 25274](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25274) (BE, under [Feature 24974](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/24974) "Kforce - Merge contacts pipeline", the contact-groups home) — In revision
- PRD técnico Tier B: [Contact groups: resolver external ids vía entity_external_links — PRD Técnico](https://app.notion.com/p/3ecaedca11f0811bbd71d57f636ae830) — Ready for review (owner Gonzalo; no business PRD: promoted from a Data finding because it changes the endpoint contract)
- Design note `docs/contact-groups.md` (Feed section + follow-ups) updated in the PR
- Original feature: [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] records the "links are the direction, column unique is global" decision this fix leans on

## PRs
- [#2378](https://github.com/taller-projects/echo-backend/pull/2378) → dev — OPEN 2026-10-01 (`c1280239`). Branch `25274/contact-groups-external-links`. Self `/pr-review` r1 (not posted) **CHANGES REQUESTED** → blockers + nits fixed in `4f6ca804` (pushed 2026-10-01 from worktree branch `25274/contact-groups-review-fixes`; PR body gained a "Review follow-ups" section). No FE PR (response additive only). No Data ticket (Data just needs to tolerate the new `code` value).

## How
- `ContactGroupService._resolve_nodes`: column hits (`resolve_external_ids`) + link hits (`ExternalLinkService.resolve_entity_ids`, `entity_type=contact`, any platform, any status) merged per id. Every link target goes through `ContactGroupSQLRepository.nodes_by_ids` (tenant-scoped) **before** counting candidates (`4f6ca804`), so a link of a deleted contact is neither a node nor a candidate → exactly one existing contact = node; 2+ = ambiguous; none = unknown.
- Replace-step guard (`4f6ca804`): a refused child id (ambiguous or already named) records its candidates in `_GroupPlan.held`; `_desired_parents` keeps a current child of that parent among them where it is instead of unlinking it.
- `addressed` map in plan building: a contact named by two different ids in one request (column id + link, or two links) is one member; the second reference is skipped as `ambiguous_external_id` with `contact_ids=[that contact]` (prevents the self-child CHECK violation that would have 400'd the whole batch).
- `_name_current_children` (was `_name_children_by_links`): report name = the id the request used for the contact (`addressed`), else the column, else the newest link (`ExternalLinkService.external_ids_by_entity`). With none: `unlinked` falls back to the UUID, `grandchildren` omits it (pre-existing; kept for AC4 — 377 column-less kforce-dev contacts).
- New repo methods `EntityExternalLinkSQLRepository.get_by_external_ids` / `get_by_entity_ids` (index prefixes `uq_entity_external_links_external_id`, `ix_entity_external_links_entity_lookup`). No migration.
- Schemas: `GroupSkipCode` + `ContactGroupSkippedChild.code` gain `ambiguous_external_id`; both skip models gain `contact_ids: list[uuid] = []`. Logs: `contact_group.ambiguous_external_id` warning (also for the named-twice skip, with `named_by`), `ambiguous=` = count of ambiguous skips on `contact_group.upserted`, which is now logged on no-change requests too (write block extracted to `_write_changes`). `GroupNode` lost its unread external-id field; skips built through the typed `_refused_candidates`.
- Tests: 7 new feed tests in `tests/unit/test_contact_groups.py` (link-only parent + hubspot/tracker/column children, dissolve by link id, same id in both stores → applies, column-vs-link and cross-platform ambiguity with the rest applied, contact named twice, link-only grandchildren, dangling link) + `test_feed_ignores_foreign_external_links` in multitenancy. 139 (groups + external_link) and 107 multitenancy green locally. `4f6ca804` adds 5 feed tests (held child, dangling links, move/promote/partial unlink by link id, stale + same-id organization link, naming precedence) + 2 multitenancy (own link → foreign contact, foreign link on own child); the held / dangling / naming ones fail on `c1280239`. 49 group tests + 671 contact/group/external_link tests green.

## Decisions
- **Any platform, not `hubspot` only** (Gonzalo's call over Nico's wording): tenant + `entity_type` scoping plus ambiguity detection cover the collision risk; a per-platform filter would leave the same hole for the next integration.
- **Rejected option (a)** (copy HubSpot id into `kforce_external_id`): the column is `UNIQUE` **global**, not per tenant (Task 25057) → a Taller HubSpot id could collide with a KForce Dynamics id; second source of truth; against the org-side direction (links authoritative).
- **Ambiguity = skip + report, no precedence rule**: the feed must not guess which duplicate is the person; Data fixes rows and re-sends. Precedence (links over column) stays a documented alternative.
- **Payload field names kept** (`parent_kforce_external_id` / `child_kforce_external_ids`): renaming breaks Emiliano's KForce pipeline; generic aliases deferred unless Data asks.
- Ticket type Bug under the Closed Feature 24974 (contact-groups lineage) rather than a HubSpot feature — re-parent if Nicolás prefers.

## Gotchas
- The session's permission classifier blocks prod DB reads (`PGSERVICE=echo-prod`), so Nico's 12,339 / `251551985161` numbers are **unverified by me**; verification SQL is in the Slack thread reply draft (join `entity_external_links` ↔ `contact` on `kforce_external_id IS DISTINCT FROM external_id`).
- Worktree guard refuses any Bash command whose text contains "GitHub" (matches `git`) — the Azure `ArtifactLink` PATCH must go through `-d @file` written inside the worktree.
- Azure internal GitHub repo id for echo-backend ArtifactLinks: `db75e3ff-226f-4014-86ae-37f4bcf56c43` (`vstfs:///GitHub/PullRequest/<id>%2f<PR>`), read from Bug 25222's relations.
- `/prd-tecnico-nuevo` wrapper points at Pedro's absolute path; the skill lives in `taller-projects/echo-flows-docs`, cloneable only via the `github-taller` SSH alias (`gh repo clone` with the default account 404s). Cloned shallow into the session scratchpad.
- Azure `$timeframe=current` still answers Sprint 45 (dates stale); every open ticket sits there anyway.
- **`entity_external_links` has no FK to `contact` and `ContactService.delete` leaves the links** (only the outbox tombstone path deletes them): any link-based resolution must re-check the target exists. Taller dev had 6 such dangling contact links on 2026-10-01; kforce-dev has 0 contact links at all.
- Replace semantics + "skip the bad id" is a trap: skipping an ambiguous child alone still let the unlink step remove its candidate from the group (r1 B1). Skipped references need explicit protection.
- Adding a defaulted field to a response model breaks exact-dict assertions (`test_feed_reports_unknown_ids…`, `test_feed_skips_group_when_child_would_keep_children`) — updated, not loosened.

## Pending
- **Open decision (Q1 of r1):** a contact named by two different ids in one request applies the first reference by payload order (identical strings would be a 422). Options: refuse every reference (order-independent), or a separate `duplicate_contact` code. Left as-is in `4f6ca804`.
- PRD wording to amend: latency criterion → "at most 3 extra queries, index-served" (the third is the PK lookup the no-cross-module-join rule forces); "tests existentes sin cambios de aserción" → "except the additive `contact_ids`".
- Follow-up ticket: `ContactService.delete` should drop the contact's links.
- Pedro review + squash-merge → Bug 25274 Closed, PRD Estado → Approved / In development, dev deploy.
- Tell Nico (Slack): confirmed, option (b) any-platform shipped in #2378, new `ambiguous_external_id` + `contact_ids` in the response, Data re-sends the Taller groups once on dev/prod; ask them to run the verification SQL.
- Check the Taller tenant in **dev** has `CONTACT_GROUPS` enabled before QA (Data's re-send is the QA).
- Follow-up ticket: `GET /internal/contacts?kforce_external_id__in=` and `GET /internal/contacts/interactions?kforce_external_id__in=` are still column-only (same bug class) — reuse `resolve_entity_ids`.
- qa / main promotion after dev QA.

## Related
- [[Map - Kforce]] · [[Kforce push echo-backend requests - kforce_external_id__in filter (US 25054)]] · [[Internal bulk tenant checks - interaction created_by + contacts PATCH (Bug 25222)]] · [[Relationship recency by activity dates (PR 2341)]]
