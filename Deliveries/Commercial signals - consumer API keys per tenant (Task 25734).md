---
type: delivery
status: shipped-prod
env: both
delivered: 2026-11-11
tags: [chore, internal-api, data-team, kforce, api-keys]
prs: []
fe_prs: []
tickets:
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25734"
  - "https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728"
prd: "https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C"
---

# Commercial signals - consumer API keys per tenant (Task 25734)

Juani's `tenant_commercial_profile_api` calls `/internal/commercial-signals/*` with one `X-Echo-Api-Key` per tenant, and the key's tenant decides whose data comes back. Task 25734 planned to mint consumer-named internal keys per tenant on dev, kforce-dev, prod and kforce-prod. Closed 2026-11-11 without minting anything: Echo already provisions one internal key per tenant into a shared Vault secret that external consumers read. Verified read-only against echo-prod.

## Azure / docs
- [Task 25734](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25734) **Closed** 2026-11-11 (rev 5); comment 29314704 (edited once: entry count 77 → 79 + verification results).
- Parent [Feature 25728](https://dev.azure.com/TallerInternTools/Echo%20Core/_workitems/edit/25728); request doc [echo-backend: endpoints commercial-signals](https://claude.ai/artifact/S6sUfQRS4KdYvbWKvzmq7C) (Juani, rev 34).

## PRs
- None (no code change).

## How (the mechanism that already existed)
- Tenant creation, both in workspace setup (`app/modules/workspace_setup/service.py`, steps 12-13) and in the super-admin service (`app/modules/super_admin/service.py`), creates a "Default API Key" (`APIKeyCreate` defaults: surface `internal`, no scopes) and calls `VaultService.upsert_tenant_api_key(tenant_id, raw_key)`.
- `app/services/vault_service.py`: CAS read-modify-write of the dict `ECHO_API_KEYS_BY_TENANT` (`{tenant_id: raw_key}`) at `secret-echo-api-keys-by-tenant-{dev,prod}` on mount `secret-ttit`. `kforce-development` maps to dev and `kforce-production` to prod: KForce shares the per-env dict because consumers inject it under one fixed env var. `scripts/organization_migrations/migrate_tenant_api_keys.py` backfilled older tenants.
- Raw key = `echo_` + 48 hex; `api_key.suffix` = its last 6 chars; `hashed_key` = argon2id. The DB never holds the raw key, only Vault does.
- Minting by hand, if ever needed: super-admin `POST /admin/tenants/{tenant_id}/api-keys`, or `POST /internal/api-keys` with a key of that tenant (creates for the caller's tenant). The raw key is returned once.

## Verification (echo-prod, 2026-11-11, read-only)
- The user pasted the prod dict: **79 entries**. Each key verified with argon2 against its tenant's `api_key.hashed_key`; keys never written to disk.
- **63/63** entries whose tenant exists in echo-prod match their tenant, all surface `internal`.
- Needed tenants OK: Taller `01df2012` (suffix `6d4d71`), Navitec `2445fa20` (`6de3ea`), Battle Tested `458fa9aa` (`0e0c0a`).
- KForce `c44b03e3` is in the dict but lives on kforce-prod: expected suffix `518649`, not yet checked.
- 15 entries point to tenants deleted from echo-prod: their `api_key` rows cascaded, so the keys are dead. `VaultService` has upsert only, nothing removes an entry on tenant delete.
- 4 echo-prod tenants have no entry: Cardinal Group Companies, Experis, SKYE TECH and an echo-prod tenant named "Kforce Inc" (`f2cc1fab`, 0 keys, NOT the real KForce). Not needed by this consumer.
- Four Taller-named tenants hold valid keys: `Taller` `01df2012` (4 keys, presumably the real one), `taller` `6d0e50a8`, `Taller QA` `dc7053cd`, `Taller Technologies` `e5d72b54`.

## Decisions
- No consumer-named keys (user, 2026-11-11): the auto-provisioned dict already covers dev + prod on both instances. The task's "name the keys for the consumer" and "hand over through a secure channel" steps were dropped.

## Gotchas
- The echo-prod direct host `db.hixqbnaslefvbxstwoog.supabase.co:5432` times out from this machine; the session pooler (`aws-0-us-east-1.pooler.supabase.com:5432`, user `postgres.hixqbnaslefvbxstwoog`) with the same password works. Read-only via `PGOPTIONS='-c default_transaction_read_only=on'` (the `postgres` login itself is a superuser).
- kforce-prod has no psql path from here: Supabase SQL editor only.
- I first counted 77 entries by eye; it is 79. Count such lists with code.
- The full prod key dict and the `postgres` password were pasted into the Claude session on 2026-11-11.

## Pending
- [ ] KForce key on kforce-prod (Supabase SQL editor): `select name, suffix, surface from api_key where tenant_id = 'c44b03e3-95f7-4b8d-9298-ede3d5067c26';` → expect suffix `518649`, `internal`.
- [ ] Alan / Juani: confirm the consumer's prod deploy injects `ECHO_API_KEYS_BY_TENANT` from `secret-echo-api-keys-by-tenant-prod` (their prod DAG has not run since October; the first run proves it), and that they use Taller `01df2012`.
- [ ] Rotate the pasted keys / `postgres` password: user's call.
- [ ] Optional: prune the 15 stale Vault entries.

## Related
- [[Map - Commercial signals]] · [[Commercial signals M1 - activities aggregates for the commercial profile API (US 25729)]] · [[Map - Kforce]]
