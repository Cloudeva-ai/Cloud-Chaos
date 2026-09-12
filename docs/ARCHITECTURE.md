# Architecture

```text
app.py                  Thin Streamlit deployment entrypoint
backend/
  config.py             Environment and ignored TOML configuration
  database.py           SQLAlchemy models, storage, reporting and exports
  attempts.py           Durable deadline, sequential answers, atomic finalization
  admin_auth.py         Shared database-backed admin login throttle
  game_data.py          Original six scenarios and game constants
  game_engine.py        Canonical scoring and result copy
frontend/
  app.py                Registration, game, results, leaderboard and admin screens
  components.py         Branding, mascot media, timer and external signup CTA
  ui.py                 Legacy helpers retained for compatibility
static/                 Theme, local fonts, media and browser interaction scripts
tests/                  Isolated backend and Streamlit flow checks
```

Backend services do not render HTML. The frontend owns presentation and Streamlit session state, while PostgreSQL/SQLite owns durable game state. Supabase access uses psycopg and SQLAlchemy on the server; no database key or answer key is sent to the browser.

## Storage

`DATABASE_URL` enables PostgreSQL with TLS, a bounded connection pool and a private `cloud_chaos` schema. Startup creates missing tables and revokes schema access from PUBLIC, anon and authenticated roles. Do not expose this schema through Supabase's Data API. The database connection account needs schema/table creation privileges at startup.

An empty URL selects SQLite in the writable data directory. `CLOUD_CHAOS_DATABASE_URL` is an explicit environment override, including an empty value for isolated tests. Configured hosted failures remain visible; hosted leaderboard and admin reads do not fall back to local backups. Exports are generated on demand and are not the authoritative store. Excel timestamps are converted to UTC without timezone metadata because Excel cannot store timezone-aware dates.

## Attempt lifecycle

Registration creates a player and a separate UUID attempt with a fixed deadline and shuffled card order. Each answer is accepted only for the current card and before that deadline. Answer keys, elapsed time and scores are derived on the server. Database row locks serialize answers and finalization; SQLite uses an immediate transaction. Finalization stores the result, six selections, player totals and attempt result pointer together. Retrying returns that same result, including after an optional audit log failure.

The attempt URL acts as a resume link. Keep it private: anyone possessing it can resume that attempt. Refreshing and reconnecting preserve answers/deadline. If a browser closes, expiry is enforced on its next request; there is no background worker finalizing disconnected attempts. New attempts remain intentionally permitted, so this is not verified participant identity or a one-entry prize enforcement system.

The timer display uses performance.now against server-supplied remaining time. A one-second Streamlit fragment triggers timeout submission. The backend checks expiry independently of JavaScript, so display modification cannot extend acceptance of answers. Saved result time does not keep increasing on refresh.

## Admin and presentation

Five failed admin logins within 60 seconds cause a shared 60-second cooldown. New sessions/usernames cannot reset it. This account-wide throttle can temporarily block the legitimate admin too. Missing credentials/database failures deny login. Admin sessions expire after 30 minutes; logout clears the prepared export.

CSS handles layout and brief transitions. Original artwork floats above the starting form; a transparent 30fps VP9 video of generated artwork waves in the post-quiz signup panel. A global pause control and reduced-motion preference stop both. Browser scripts bind once and dispose obsolete timer intervals. Static media/font files ship with the application.
