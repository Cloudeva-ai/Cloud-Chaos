# Cloud Chaos

A 90-second Cloudeva event challenge: six cloud governance scenarios, Right/Wrong decisions, results, and a live leaderboard. The interface keeps the navy/teal brand, original questions and external Cloudeva registration link.

## Run locally

Requires Python 3.12+. In PowerShell:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 -m streamlit run app.py
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` if you have not configured secrets. Fill `DATABASE_URL`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD`; see [live setup](docs/LIVE_TEST_SETUP.md). Never commit the real secrets file.

## Storage and gameplay

With `DATABASE_URL` configured, Supabase PostgreSQL stores players, attempts, answers, results, and admin throttling in the private `cloud_chaos` schema. Without it, local SQLite is used. A configured database outage never silently switches gameplay to SQLite.

Each attempt has a server-side deadline, sequential immutable answers, and one saved result. Refreshing resumes the same attempt from its URL; changing the browser clock cannot extend it. Repeat attempts remain allowed for testing. The Cloudeva signup button continues to redirect externally, without checking signup status.

The cool mascot floats above the starting form. The generated waving video appears at the post-quiz registration invitation. Animation can be paused, and reduced-motion preferences are respected.

## Development

```powershell
py -3.12 -m pytest -q
py -3.12 check_mobile_flow.py
```

Automated tests force an isolated SQLite database, even when live secrets exist. See [setup](docs/SETUP.md) and [architecture](docs/ARCHITECTURE.md). Runtime databases, exports, and secrets are ignored by Git. Local historical SQLite records are not automatically imported into Supabase.
