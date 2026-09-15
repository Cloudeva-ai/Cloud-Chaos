# Cloud Chaos live redesign implementation plan

**Goal:** Connect the existing event game to Supabase and rebuild its complete presentation while preserving its colors, questions, text, and external registration destination.

**Architecture:** Keep Streamlit as the public host and SQLAlchemy as the persistence boundary. Separate durable game attempts and authentication from presentation; use one coherent stylesheet and reusable screen components. Keep SQLite for isolated local tests.

**Constraints:** Repeat attempts remain allowed. Never expose credentials or answer keys to the browser. Keep the Cloudeva redirect unchanged. No claims of live deployment without a hosted URL. Do not overwrite existing user edits or runtime data. The cool mascot stays the original raster artwork. The post-quiz waving clip uses generated animation frames encoded into a transparent 30fps video.

- [x] Database and game integrity: introduce validated PostgreSQL configuration, dialect-safe startup and queries, private hosted tables, durable attempt IDs/deadlines, atomic answer saves, canonical scoring and idempotent finalization. Preserve existing exports. Test duplicate retries, expiry, canonical answers and PostgreSQL operation.
- [x] Admin protection: persistent attempt throttling, constant-time credential comparison, generic failures, authenticated export guard and logout. Test lockout across independent login sessions and cooldown.
- [x] Visual specification: create a coordinated image concept for registration, question, results and leaderboard, using the existing navy/teal palette, mascot and exact content. Extract typography, spacing, component and motion rules before frontend changes.
- [x] Presentation: replace layered legacy CSS with a cohesive responsive interface; implement navigation, answer transitions, accessible focus states, reduced motion and stable browser timer rendering. Integrate server-owned attempt state and fixed saved result times.
- [x] Verification: run isolated regression tests, exercise actual Supabase writes/reads using identified QA records, and inspect Playwright desktop/mobile screenshots and the complete game/admin flow. Record any limits honestly and update setup documentation.
