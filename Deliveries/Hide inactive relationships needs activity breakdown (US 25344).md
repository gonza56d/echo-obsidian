---
type: delivery
status: merged-dev
env: both
delivered: 2026-10-02
tags: [frontend, contacts, contact-groups, feature-flags, kforce, taller]
prs: []
fe_prs:
  - "https://github.com/taller-projects/echo-frontend/pull/3484"
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25344"
prd:
---

# Hide inactive relationships needs activity breakdown (US 25344)

Found on 2026-10-02 while checking what enabling `TenantFeature.CONTACT_GROUPS` (`"contact_groups"`) for Taller would involve.

US 25071 (KForce post-demo) made the FE hide relationship sub-rows with no activity on two surfaces: the Contacts table and the company → Contacts tab. It tied that hiding to `CONTACT_GROUPS` alone (`hideInactiveRelationships={hasContactGroups}`).

"Activity" = `client_visits_count` / `job_orders_count` / `send_outs_count` / `placements_count` > 0 (`hasRelationshipActivity`, `CONTACT_ACTIVITY_COUNT_METRICS`). Those are KForce staffing counters. On Taller dev, 0/562 (Taller) and 0/770 (Hubspot - Taller) relationships have any of them, while Navitec has 537/660.

So turning `contact_groups` on for any non-KForce tenant would hide every sub-row and kill the expand control. This was an FE blocker for that.

## Azure
- [US 25344](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25344): Web Team, In revision, assigned to Gonzalo, Related to 25071 + 24986.

## PRs
- [echo-frontend #3484](https://github.com/taller-projects/echo-frontend/pull/3484) → dev, **draft**, opened 2026-10-02.
  - Branch `hide-inactive-relationships-by-activity-breakdown`, commit `b778ee018`, from worktree `~/.superset/worktrees/echo-frontend/hide-inactive-relationships-by-activity-breakdown`.
  - No BE PR.
- Docs: echo-flows-docs `03-contacts.md` (`1299bba`, pushed straight to `main` as the repo does).

- **Review r1 (2026-10-02), Flor + Patricio, both COMMENTED, no blockers.** All addressed in `8c177880b` (pre-push: 208 + 1456 tests green). I replied on all 6 threads.
  - **AND vs. replace** (AC1 said "no longer depends on CONTACT_GROUPS"): kept the AND, because it's Gonzalo's no-behavior-change requirement. With a replace, a tenant with the breakdown but no groups would start hiding. US 25344 Decision section + AC1 rewritten (rev 5), plus a comment.
  - **Hook comment removed:** FE CLAUDE.md says "No comments — no comments, JSDoc, or inline annotations".
  - **Tab-wiring tests added:**
    - company tab in `companies/tabs/contacts/Contacts.test.js`;
    - contacts list in `__pagesTests__/contacts/index.test.js`;
    - both use a pass-through `AccessControlEnforcement` mock for `contacts.activity`, because the default `/users/me` mock only grants `talents` / `companies`;
    - each case fails if its `Table` prop goes back to `hasContactGroups`.
  - Gotcha: mocking `usePermissions` with a fresh `hasPermission` per render hung jest (render loop). Mock `AccessControlEnforcement` instead.
- **`build` check is red.** The preview's ACM certificate rejects `hide-inactive-relationships-by-activity-breakdown.preview…` (> 64 chars). It's not required; the merge is only blocked by REVIEW_REQUIRED. Use FE branch names of ≤ ~40 chars if the preview is wanted.

- **MERGED to dev 2026-10-02 19:29 UTC (`d47b03e3`, by gonza-taller).** US 25344 moved to Developed via the FE pipeline; it goes to Ready to Test at the next QA release. Merge-info comment added on the ticket.

## How
- New hook `src/components/contacts/table/useHideInactiveRelationships.ts` = `CONTACT_GROUPS && CONTACTS_ACTIVITY_BREAKDOWN`. It's a separate module built on `useTenantFeature`, so the existing `jest.mock('@/hooks/useTenantFeatures', () => ({ useTenantFeature }))` mocks keep working.
- Used by:
  - `useExpandableTableControls` (row expand / "Expand All");
  - both tabs (`Table` prop `hideInactiveRelationships`);
  - a new `getContactsTableColumns` option `hideInactiveRelationships` for `ActionCell`.
- `hasContactGroups` still gates the rest of the groups UI.

## Decisions
- **AND, not a swap to `contacts_activity_breakdown`.** A swap could start hiding for a Taller tenant that has the breakdown but not groups. AND keeps every current tenant identical.
- kforce-prod verified read-only on 2026-10-02: `Kforce Inc` has both `contact_groups` and `contacts_activity_breakdown`, so KForce is unchanged.
- No new flag. The FE has many FE-only flags that are just strings in `tenant.available_features`, not in the BE `TenantFeature` enum (`contacts_activity_breakdown` is one).

## Gotchas
- **echo-frontend `origin` remote (`git@github.com:`) can't fetch with the default SSH key.** `git fetch` failed silently and `origin/dev` was 3 days stale. Use `git@github-taller:taller-projects/echo-frontend.git` explicitly for fetch and push (remote config left untouched).
- **FE repo + the fresh echo-flows-docs clone have the personal git identity** (`gonza56d@gmail.com`). The FE CI check `check-commit-emails.yml` only allows `@tallertechnologies.net/.com`.
  - Commit FE with `git -c user.name=gonza-taller -c user.email=gonzalo.garcia@tallertechnologies.com`.
  - The docs commit `1299bba` went out with the gmail address before I noticed; no force push. The docs clone now has the work identity set locally.
- **Local Node is 24, but the repo pins 20.19 (`.nvmrc`).** Under Node 24 every nock-based suite fails, on clean `origin/dev` too: 41 page tests and 5 company Contacts tab tests. Under Node 20.19 (`npx -y node@20.19.0 …`) everything passes.
- `pnpm` isn't on PATH; use `corepack pnpm`. The husky hooks call `pnpm` and `node`, so commit/push with `PATH=<shim dir with pnpm→corepack and node→node20>:$PATH`.

## Pending
- FE CI on #3484 → mark ready for review → FE reviewer.
- After merge: QA per the PR's QA note (KForce unchanged; Taller tables unchanged).
- This only removes the FE blocker. Enabling `contact_groups` for Taller still needs:
  - a Data grouping source;
  - product OK;
  - measuring the BE company-scoped sort on echo-clon-prod.

## Related
- [[Contact groups feed resolves external ids via entity_external_links (Bug 25274)]]
