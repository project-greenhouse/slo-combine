# SLO Combine — Athlete Performance Dashboard

Vue 3 + Firebase app for managing and visualizing athlete performance data from the San Luis Obispo County Combine.

## Stack

- **Frontend:** Vue 3, TypeScript, Vite, Pinia, Tailwind, ECharts — see [code8-vue-app/](code8-vue-app/)
- **Backend:** Firebase (Auth, Firestore, Hosting, Cloud Functions in Python)
- **Data integrations:** Hawkin Dynamics, Valor, Swift, Bookeo

## Quick start

```bash
cd code8-vue-app
npm install
npm run dev
```

For Firebase emulators, functions setup, deploy commands, collection schema, and API credentials see [SUMMARY_SETUP.md](SUMMARY_SETUP.md).

For Vue app structure, Cloud Function endpoints, and role permissions see [code8-vue-app/README.md](code8-vue-app/README.md).

## Repo layout

```
slo-combine/
├── code8-vue-app/              # Vue 3 + Firebase app (primary)
│   ├── src/                    # Vue components, stores, views
│   │   └── views/entry/        # Testing station data entry screens
│   ├── functions/              # Python Firebase Cloud Functions
│   ├── firestore.rules         # Firestore security rules
│   └── firebase.json           # Firebase project config
├── data/                       # CSV data (percentiles, rosters)
├── assets/                     # Images / logos
├── actions.py                  # Admin: upload athletes to Firestore
├── create_live_admin.py        # Admin: create admin user
├── seed_percentiles.py         # Admin: seed percentile tables
├── restore_summaries.py        # Admin: migrate legacy summaries
└── dedup_athletes.py           # Admin: one-off duplicate athlete merge
```

Admin Python scripts at the repo root use `code8-vue-app/service-account.json` for Firebase Admin SDK access.

## Architecture

**Athlete identity:** Firestore `athlete_info` is the single source of truth for athlete profiles. External systems (Hawkin Dynamics, Valor) are linked via stored foreign keys (`HawkinID`, `ValorID`), not by name matching. Bookeo registration feeds athlete creation; the matching UI links Valor profiles post-creation.

**Data flow:** Bookeo → `athlete_info` (via sync) → HD/Valor matched by FK → metrics fetched by FK at display time.

## License

Proprietary — Code 8 Performance and Greenhouse Performance.
