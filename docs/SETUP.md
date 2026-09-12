# Cloud Chaos setup

## Prerequisites

- Python 3.12 or newer
- Git
- Optional: Docker Desktop
- A free Streamlit Community Cloud account for hosting
- A free Supabase project when durable hosted storage is required

## Local setup

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
streamlit run app.py
```

The app uses Supabase when `DATABASE_URL` is configured, otherwise SQLite. Runtime exports and local SQLite files go to `.cloud_chaos_data/`, which is ignored by Git. Tests explicitly select isolated SQLite.

For a fast local timeout test, set `CLOUD_CHAOS_GAME_DURATION=3` before starting the app. The production default is 90 seconds.

## Secrets

For the Supabase connection and deployment steps, follow [LIVE_TEST_SETUP.md](LIVE_TEST_SETUP.md).

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill the database URL and admin credentials. Do not overwrite an existing configured file. Never commit `secrets.toml`.

The application fails closed when admin credentials are not configured. The development fallback credentials were deliberately removed.

## Validation

```powershell
python -m pytest
python check_mobile_flow.py
python -m py_compile app.py frontend/app.py backend/database.py backend/game_data.py backend/game_engine.py
```

## Disposable Docker setup

Docker is optional. It gives you a clean local environment without changing the host Python installation:

```powershell
$env:ADMIN_USERNAME = "choose-an-admin-name"
$env:ADMIN_PASSWORD = "use-a-new-local-password"
docker compose up --build
```

Open `http://localhost:8501`. Stop and remove the local container and volume with:

```powershell
docker compose down -v
```

## Hosting decision

Streamlit is the free public quiz host. GitHub stores source code and deploys it to Streamlit Community Cloud. GitHub Pages is not used because it cannot run Streamlit or protect server-side secrets.

Supabase is integrated through the server-side `DATABASE_URL`. Set it in the host Secrets panel to retain event data across app restarts. CSV and XLSX are exports, not the authoritative live store.
