# SLO Combine — Setup & Reference

## Firebase Project

- **Project ID:** `code-8-performance`
- **Service account key:** `code8-vue-app/service-account.json` (local only — do not commit)
- **Admin SDK scripts** at repo root use this key:
  - `actions.py` — upload base athletes to Firestore
  - `create_live_admin.py` — provision admin users in Firebase Auth
  - `seed_percentiles.py` — seed percentile lookup collections
  - `restore_summaries.py` — backfill legacy athlete summaries

### Firestore collections
- `athlete_info` — athlete roster keyed by auto-ID, `Name` field used for lookups
- `athlete_summaries` — rich-text summaries (HTML), read-public, write restricted to `admin` / `coach` custom claims (see `code8-vue-app/firestore.rules`)
- Percentile collections seeded by `seed_percentiles.py`

### Auth
Custom claims drive authorization:
- `role: "admin"` — full write access
- `role: "coach"` — write access to summaries
Set via `auth.set_custom_user_claims(uid, {"role": "..."})` (see `create_live_admin.py`).

## Vue App (`code8-vue-app/`)

Vue 3 + TypeScript + Vite + Pinia + Firebase SDK + Tailwind.

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
`functions/.env` holds runtime secrets (HD_TOKEN, Bookeo creds, etc.) — not committed.

### Emulators
Configured in `code8-vue-app/firebase.json`:
- Auth: `localhost:9099`
- Functions: `localhost:5001`
- Emulator UI enabled

```bash
cd code8-vue-app
firebase emulators:start
```

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

- **Hawkin Dynamics** — force plate / jump analysis (`hdforce` SDK, `HD_TOKEN` env var)
- **Valor** — movement screening, JWT auth handled by the Python functions
- **Swift** — speed/agility timing (CSV ingest)
- **Bookeo** — scheduling / customer sync (see below)

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
- **productId**: '415536EXT7W19C6381813B',
- **productCode**: '415536EXT7W19C6381813B',

SLO Combine Bookings Request: `https://api.bookeo.com/v2/bookings?productId=415536EXT7W19C6381813B&startTime=2026-05-09T01:00:00-07:00&endTime=2026-05-09T23:00:00-07:00&apiKey=A397HJ9EPYRALT4TH7NPU41553ERWJH719C637CA92D&secretKey=aaHWtJwuVkvTey2cc1wviAercth68Asg`
## Repo layout

```
slo-combine/
├── code8-vue-app/              # Vue 3 + Firebase app (primary)
│   ├── src/                    # Vue components, stores, views
│   ├── functions/              # Python Firebase Cloud Functions
│   ├── firestore.rules         # Firestore security rules
│   ├── firebase.json           # Firebase project config
│   └── service-account.json    # Local-only admin key
├── data/                       # CSV data (percentiles, rosters)
├── assets/                     # Images / logos
├── actions.py                  # Admin: upload athletes
├── create_live_admin.py        # Admin: create admin user
├── seed_percentiles.py         # Admin: seed percentile tables
└── restore_summaries.py        # Admin: migrate legacy summaries
```
