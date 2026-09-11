# Cloud Chaos Theme

## Runtime storage

The app reads media assets from the repo, but writes runtime data to a writable
data directory:

- SQLite database
- registration backup Excel export
- registration backup CSV export
- snapshot backups

Resolution order for the writable data directory:

1. `CLOUD_CHAOS_DATA_DIR` from environment or `st.secrets`
2. `./.cloud_chaos_data` if the repo is writable
3. system temp directory fallback

This keeps local development simple and prevents write failures on Streamlit
Cloud. If you need stable persistence across restarts on Streamlit Cloud, point
`CLOUD_CHAOS_DATA_DIR` to a persistent mounted location or move the app to an
external database/storage setup.
