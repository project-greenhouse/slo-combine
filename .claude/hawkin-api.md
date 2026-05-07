# Hawkin Dynamics API Reference

OpenAPI spec: `hawkin-api-v1.13.json` in repo root
Live API portal: https://connect.hawkindynamics.com/api

## Base URLs

- **Americas (default):** `https://cloud.hawkindynamics.com`
- **Europe:** `https://eu.cloud.hawkindynamics.com`
- **Asia-Pacific:** `https://apac.cloud.hawkindynamics.com`

## Authentication

Two-step Bearer auth:

1. **Refresh Token** — generated in HD dashboard → Settings → Integrations. Stored as `HD_TOKEN` in `code8-vue-app/functions/.env`. Long-lived.
2. **Access Token** — exchange refresh token via `GET /api/token`. 1-hour expiry. Used as `Authorization: Bearer {AccessToken}` for all other endpoints.

Our client (`code8-vue-app/functions/hawkin_client.py`) handles the exchange and caches the access token until ~1 minute before expiry.

## Endpoints we use

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/token` | Exchange refresh token → access token |
| `GET`  | `/api/v1/athletes` | List athletes (params: `includeInactive`) |
| `POST` | `/api/v1/athletes` | Create single athlete |
| `POST` | `/api/v1/athletes/bulk` | Create up to 500 athletes |
| `PUT`  | `/api/v1/athletes/{id}` | Update single athlete (partial) |
| `PUT`  | `/api/v1/athletes/bulk` | Bulk update up to 500 athletes |
| `GET`  | `/api/v1/test_types` | List test types (cached per client instance) |
| `GET`  | `/api/v1` | Get tests (params: `from`, `to`, `syncFrom`, `syncTo`, `athleteId`, `testTypeId`, ...) |

## Test Type Resolution

`GET /api/v1`'s `testTypeId` param expects the org-specific test type ID (not the canonical ID).

The `HawkinClient.find_test_type_id(hint)` helper resolves common shortcuts:
- `"CMJ"` → matches "Countermovement Jump"
- `"MR"` → matches "Multi Rebound"
- `"SJ"` → matches "Squat Jump"
- `"DJ"` → matches "Drop Jump"

Or pass any name substring; matching is case-insensitive.

## Test Object Shape

Each test from `GET /api/v1` has:
```jsonc
{
  "id": "...",
  "testType": { "id": "...", "name": "Countermovement Jump", "canonicalId": "..." },
  "athlete": { "id": "...", "name": "..." },
  "timestamp": 1551301560,
  "segment": "Countermovement Jump:5",
  "Jump Height(m)": 0.42,
  "mRSI": 0.55,
  "Peak Relative Propulsive Power(W/kg)": 38.2,
  // ...other metric keys
}
```

`HawkinClient.get_tests()` flattens these into a single-level dict with snake_case metric keys, e.g. `jump_height_m`, `mrsi`, `peak_relative_propulsive_power_w_kg`. The transformation: lowercase, replace `(`, `)`, ` `, `/` with `_`, strip non-alphanumeric, collapse repeats.

## Caching

- **Access token:** cached in `HawkinClient._access_token`, invalidated 1 minute before `expires_at`.
- **Test types:** cached in `HawkinClient._test_type_cache` for the client's lifetime.
- **Test results (CMJ, MR):** cached in `main.py` `hd_cache` dict at module level — survives across function invocations within a single Cloud Function instance.

## Bulk failures

Bulk create/update returns:
```jsonc
{
  "data": [/* successful Athletes */],
  "hasFailures": true,
  "failures": [
    { "reason": "...", "data": { /* original input */ } }
  ]
}
```
Always check `hasFailures` before assuming success.

## External Properties Gotcha

When `PUT`'ing athletes with an `external` field, **any keys NOT in the request will be removed** from the stored record. Always send the full `external` map.

## Rate Limiting

Hawkin recommends `from`/`to` for bulk historical export and `syncFrom`/`syncTo` for incremental sync (every 5 min). Responses exceeding the memory limit will fail — keep windows narrow.

## Athlete Schema (Firestore Side)

`athlete_info.HawkinID` is the foreign key to HD's athlete `id`. Set automatically by:
- `link_hd_athlete` (matching UI links roster → HD)
- `create_hd_athlete` (creates in HD then stores ID)
- `sync_bookeo_roster` (cross-refs new Bookeo athletes against HD by name match)
