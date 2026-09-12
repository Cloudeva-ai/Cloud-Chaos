# Live test setup

## Fill the local secrets file

Open `.streamlit/secrets.toml` and fill these three values inside the quotes:

| Setting | What to enter |
| --- | --- |
| `DATABASE_URL` | The full PostgreSQL connection string from your Supabase project, using **Connect > Session pooler**. |
| `ADMIN_USERNAME` | Your chosen admin username. |
| `ADMIN_PASSWORD` | A long, unique admin password. This is separate from your Supabase database password. |

Create a Supabase project if you do not have one. Copy the pooler connection
string exactly, including its host, username, and port. Replace
`[YOUR-PASSWORD]` with the database password you chose for the project.
Percent-encode reserved characters in the password, such as `@` as `%40`,
`#` as `%23`, and `%` as `%25`. Encode the password portion only, not the
whole connection string.

The connection string is not the Supabase project URL, anon key, publishable
key, or service-role key. No image-generation key is needed for this setup.

Reference: [Supabase database connection instructions](https://supabase.com/docs/guides/database/connecting-to-postgres).

The local secrets file is ignored by Git. Keep real credentials out of chat,
screenshots, the example template, and documentation.

## Hosting

If using Streamlit Community Cloud, enter the same three settings in the app's
Secrets panel. The ignored local file will not be deployed through Git.

Reference: [Streamlit hosting secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Implemented and verified locally against Supabase

The configured database connection has been tested over TLS. The app creates its private `cloud_chaos` schema and stores registrations, attempts, answers and results there. Browser checks covered a complete quiz, refresh/resume, fixed deadlines, duplicate finalization, automatic timeout, leaderboard reads, admin lockout, successful admin login and Excel download.

The secrets already entered locally are sufficient. No Supabase anon/service-role key or animation API key is needed. Restart Streamlit after changing secrets. Select `cloud_chaos` in Supabase's table editor to inspect event tables; do not add it to the exposed API schemas.

Repeat attempts remain allowed for testing. The existing Cloudeva registration redirect remains unchanged. Local historical SQLite data is not automatically uploaded. Live integration checks create clearly named `Live QA` test players; these are test entries, not event participants.

## Publish for shared testing

1. Put this source repository on GitHub, with secrets/runtime data excluded.
2. In Streamlit Community Cloud create an app for this repository and branch, using `app.py` and Python 3.12.
3. Paste the three settings from the local secrets file into the app's Secrets panel. Do not put them in repository files.
4. Deploy, open the resulting HTTPS URL, and run a full quiz plus admin login from a second device.
5. Share the live URL and expected simultaneous player count for public-host and load testing.

This implementation has been tested from a local Streamlit server connected to Supabase. It has not been publicly deployed or load-tested for an event audience.

[Streamlit Community Cloud](https://streamlit.io/cloud) offers free hosting. The [Supabase free plan](https://supabase.com/pricing) has usage limits and can pause inactive projects; open and check the project before the event. Do not assume free hosting guarantees uninterrupted event availability. No paid service is required by this implementation.
