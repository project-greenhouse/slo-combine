# Hawkin Dynamics API Reference

API portal: https://connect.hawkindynamics.com/api

## Authentication

- Env var: `HD_TOKEN` (stored in `code8-vue-app/functions/.env`)
- Python SDK: `hdforce` package
- Auth: `AuthManager(region="Americas", authToken=HD_TOKEN)`

## Endpoints currently used

All via the `hdforce` Python SDK in `code8-vue-app/functions/main.py`:

| SDK call | Purpose | Where |
|----------|---------|-------|
| `GetAthletes()` | Fetch full athlete roster | `get_roster()` — merged with Valor + Firestore |
| `GetTests(typeId="CMJ", from_=..., to_=...)` | Countermovement jump tests | `get_athlete_metrics()` |
| `GetTests(typeId="MR", from_=..., to_=...)` | Multi-rebound tests | `get_athlete_metrics()` |

## Caching

Global in-memory cache per function instance:
- `hd_cache["CMJ"]` / `hd_cache["MR"]` — populated on first call, reused for duration of function cold start.

## Athlete creation

HD supports athlete creation via API (confirmed by user).
- Method TBD: check `hdforce` SDK for `CreateAthlete()` or equivalent.
- Will be used by `sync_bookeo_roster` to auto-create Bookeo athletes not yet in HD.
- Required fields: firstName, lastName, DOB, height, weight, gender (mapped from Bookeo registration data).

## Athlete schema (HD side)

Key fields returned by `GetAthletes()`:
- `id` — HD athlete ID (stored as `HawkinID` in Firestore `athlete_info`)
- `name` — full name (used for cross-system matching)
- Additional fields: teams, groups, position, etc.
