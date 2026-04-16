# Code 8 Performance — SLO Combine Vue App

Vue 3 + TypeScript + Vite + Pinia + Tailwind frontend with Firebase backend (Auth, Firestore, Hosting, Cloud Functions in Python).

## Local dev

```bash
npm install
npm run dev          # Vite dev server (http://localhost:5173)
npm run build        # type-check + production build → dist/
npm run preview      # preview built dist/
```

## Firebase emulators

Requires [Firebase CLI](https://firebase.google.com/docs/cli) and Java 21+ for Firestore emulator.

```bash
firebase emulators:start                  # Auth (9099) + Functions (5001) + Firestore
firebase emulators:start --only auth,functions   # skip Firestore (no Java needed)
```

In dev mode the Vue app auto-connects to local Auth and Functions emulators (see `src/firebase/config.ts`).

## Cloud Functions (Python)

```bash
cd functions
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

`functions/.env` holds runtime secrets — not committed. Required vars:
- `HD_TOKEN` — Hawkin Dynamics refresh token
- `VALOR_URL`, `VALOR_USER`, `VALOR_PASSWORD`, `VALOR_CLIENT_ID`, `VALOR_TOKEN_URL` — Valor API
- `BOOKEO_API_KEY`, `BOOKEO_SECRET`, `BOOKEO_PRODUCT_ID` — Bookeo API

## Deploy

```bash
npm run build
firebase deploy                        # hosting + functions + rules
firebase deploy --only hosting         # SPA only
firebase deploy --only functions       # Python functions only
firebase deploy --only firestore:rules # rules only
```

## Project structure

```
code8-vue-app/
├── src/
│   ├── firebase/config.ts          # Firebase SDK init + emulator connections
│   ├── stores/
│   │   ├── authStore.ts            # Auth state, roles, login/logout
│   │   └── athleteStore.ts         # Roster, metrics, athlete selection, sync
│   ├── views/
│   │   ├── HomeView.vue            # Public landing page
│   │   ├── LoginView.vue           # Auth (login + athlete registration)
│   │   ├── DashboardView.vue       # Roster + athlete detail + system integrations
│   │   ├── EvaluationHubView.vue   # Coach evaluation notes (rich text)
│   │   ├── PresentationView.vue    # Athlete-facing data sheet
│   │   ├── AdminView.vue           # User management, CSV upload, Bookeo sync
│   │   ├── AthleteMatchingView.vue # Bulk Valor ↔ roster matching
│   │   └── entry/
│   │       ├── StandingReachEntry.vue   # Station: standing reach (1 value)
│   │       ├── VerticalJumpEntry.vue    # Station: max touch → computed vertical
│   │       └── BroadJumpEntry.vue       # Station: 2 attempts, highlight best
│   └── router/index.ts             # Routes + auth/role guards
├── functions/
│   ├── main.py                     # All Cloud Function endpoints
│   ├── func_bookeo.py              # Bookeo API client
│   ├── data.py, viz.py, utility.py # Legacy helper modules
│   └── requirements.txt            # Python deps
├── firestore.rules                 # Security rules
├── firebase.json                   # Emulator + hosting + functions config
└── tailwind.config.js              # Custom colors (code8-gold, code8-dark, etc.)
```

## Cloud Function endpoints

| Function | Auth | Purpose |
|----------|------|---------|
| `get_roster` | any | Fetch merged roster from athlete_info (FK joins to HD/Valor) |
| `get_athlete_metrics` | any | Fetch metrics for one athlete (Firestore + HD + Valor) |
| `get_valor_athletes` | admin/coach | List Valor athletes with assignment status |
| `update_athlete_info` | admin/coach | Edit athlete profile (including ValorID/HawkinID) |
| `upload_roster_csv` | admin | Batch upsert athletes from CSV |
| `set_user_role` | admin | Assign roles + athlete linkage |
| `admin_create_user` | admin | Create new user account |
| `register_athlete` | public | Athlete self-registration |
| `submit_standing_reach` | admin/coach | Write standing reach measurement |
| `get_standing_reach` | any | Read standing reach for vertical calc |
| `submit_vertical_jump` | admin/coach | Write vertical jump (auto-computes from reach) |
| `submit_broad_jump` | admin/coach | Write broad jump (2 attempts, best computed) |
| `sync_bookeo_roster` | admin | Pull Bookeo bookings → upsert athlete_info, cross-ref HD/Valor |

## Roles

| Role | Nav access | Write access |
|------|-----------|--------------|
| `admin` | All views | All collections + user management + Bookeo sync |
| `coach` | Dashboard, Evaluation, Testing Stations, Match Athletes | Summaries, metrics entry, athlete profile edits |
| `athlete` | Presentation only | None |
