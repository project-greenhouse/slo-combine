# SLO Combine — Setup & Reference

## Firebase Project

- **Project ID:** `code-8-performance`
- **Service account key:** `code8-vue-app/service-account.json` (local only — do not commit)
- **Admin SDK scripts** at repo root use this key:
  - `actions.py` — upload base athletes to Firestore
  - `create_live_admin.py` — provision admin users in Firebase Auth
  - `seed_percentiles.py` — seed percentile lookup collections
  - `restore_summaries.py` — backfill legacy athlete summaries
  - `dedup_athletes.py` — one-off duplicate athlete merge (`--dry-run` supported)

### Firestore collections

| Collection | Key | Purpose | Write access |
|------------|-----|---------|--------------|
| `athlete_info` | auto-ID (`athlete_uid`) | Canonical athlete roster. Source of truth for profiles. Linked to HD/Valor via `HawkinID`/`ValorID` foreign keys. | admin/coach |
| `athlete_summaries` | auto-ID | Rich-text evaluation notes (HTML) | admin/coach |
| `standing_reach` | `athlete_uid` | Standing reach measurement (1 value per athlete) | admin/coach |
| `standing_vert` | auto-ID | Vertical jump entries (MaxTouch, computed Vert) | admin/coach |
| `broad_jump` | auto-ID | Broad jump entries (2 attempts + best) | admin/coach |
| `sprint40` | auto-ID | 40-yard dash times (Swift CSV import) | admin |
| `pro_agility` | auto-ID | Pro agility times (Swift CSV import) | admin |
| `combine_percentiles` | Percentile | Percentile lookup for combine ranking | admin (seeded) |
| `fp_percentiles` | Percentile | Force plate percentile lookup | admin (seeded) |

### Athlete identity model

`athlete_info` is the single source of truth. External systems are linked by stored foreign keys:
- `HawkinID` — links to Hawkin Dynamics athlete ID
- `ValorID` — links to Valor athlete ID
- `bookeo_person_id` — links to Bookeo participant ID (set by Bookeo sync)
- `bookeo_customer_id` — parent/guardian Bookeo customer ID

Roster and metrics are joined by these FKs, not by name. The matching UI (`/match-athletes`) and Bookeo sync establish these links.

### Auth

Custom claims drive authorization:
- `role: "admin"` — full write access, user management, Bookeo sync
- `role: "coach"` — write access to summaries, metrics entry, athlete edits, matching
- `role: "athlete"` (default) — read-only presentation view

Set via `auth.set_custom_user_claims(uid, {"role": "..."})` (see `create_live_admin.py`).

## Vue App (`code8-vue-app/`)

Vue 3 + TypeScript + Vite + Pinia + Firebase SDK + Tailwind.

See [code8-vue-app/README.md](code8-vue-app/README.md) for project structure, Cloud Function endpoints, and role matrix.

### Local dev
```bash
cd code8-vue-app
npm install
npm run dev          # Vite dev server
npm run build        # type-check + production build into dist/
npm run preview      # preview built dist/
```

### Firebase Functions (Python)
Cloud Functions live in `code8-vue-app/functions/` (Python, `firebase-functions` SDK).
```bash
cd code8-vue-app/functions
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```
`functions/.env` holds runtime secrets (HD_TOKEN, Valor creds, Bookeo creds) — not committed.

### Emulators
Configured in `code8-vue-app/firebase.json`:
- Auth: `localhost:9099`
- Functions: `localhost:5001`
- Emulator UI enabled

```bash
cd code8-vue-app
firebase emulators:start
```

Note: Firestore emulator requires Java 21+. Use `--only auth,functions` to skip it (writes hit production Firestore via service account).

### Deploy
```bash
cd code8-vue-app
npm run build
firebase deploy                        # hosting + functions + rules
firebase deploy --only hosting         # SPA only
firebase deploy --only functions       # Python functions only
firebase deploy --only firestore:rules # rules only
```
Hosting serves `code8-vue-app/dist/` with SPA rewrite to `index.html`.

## Data Sources

- **Hawkin Dynamics** — force plate / jump analysis (`hdforce` SDK, `HD_TOKEN` env var). Linked by `HawkinID` FK.
- **Valor** — movement screening, JWT auth via AWS Cognito. Linked by `ValorID` FK. Athletes must be created manually in Valor; use Match Athletes UI to link.
- **Swift** — speed/agility timing (CSV ingest into `sprint40`/`pro_agility` collections)
- **Bookeo** — event registration, source of truth for athlete profiles (see below)

## Bookeo API

- **Application Id:** `YRALT4TH7NPU`
- **Secret Key:** `aaHWtJwuVkvTey2cc1wviAercth68Asg`
- **API Key:** `A397HJ9EPYRALT4TH7NPU41553ERWJH719C637CA92D`
- **Authorization URL:** https://signin.bookeo.com/?authappid=YRALT4TH7NPU&permissions=customers_rw_all,bookings_rw_all,blocks_rwd_all,availability_r

### SLO County Combine Bookeo Data

All URIs are relative to https://api.bookeo.com/v2
All requests must provide a `secretKey` and an `apiKey` as parameters

Example request for all Code8 Bookeo products: `https://api.bookeo.com/v2/settings/products?apiKey=A397HJ9EPYRALT4TH7NPU41553ERWJH719C637CA92D&secretKey=aaHWtJwuVkvTey2cc1wviAercth68Asg`

The SLO County Combine is product:
- **productId**: `415536EXT7W19C6381813B`
- **productCode**: `415536EXT7W19C6381813B`

SLO Combine Bookings Request: `https://api.bookeo.com/v2/bookings?productId=415536EXT7W19C6381813B&startTime=2026-05-09T01:00:00-07:00&endTime=2026-05-09T23:00:00-07:00&apiKey=A397HJ9EPYRALT4TH7NPU41553ERWJH719C637CA92D&secretKey=aaHWtJwuVkvTey2cc1wviAercth68Asg`

## Repo layout

```
slo-combine/
├── code8-vue-app/              # Vue 3 + Firebase app (primary)
│   ├── src/                    # Vue components, stores, views
│   │   └── views/entry/        # Testing station data entry screens
│   ├── functions/              # Python Firebase Cloud Functions
│   │   ├── main.py             # All callable endpoints
│   │   └── func_bookeo.py      # Bookeo API client
│   ├── firestore.rules         # Firestore security rules
│   ├── firebase.json           # Firebase project config
│   └── service-account.json    # Local-only admin key
├── data/                       # CSV data (percentiles, rosters)
├── assets/                     # Images / logos
├── actions.py                  # Admin: upload athletes
├── create_live_admin.py        # Admin: create admin user
├── seed_percentiles.py         # Admin: seed percentile tables
├── restore_summaries.py        # Admin: migrate legacy summaries
└── dedup_athletes.py           # Admin: one-off duplicate merge
```
