# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the gateway (port from settings.gateway_port, default 8001)
python run.py

# One-time DB setup before first run — execute against SQL Server in SSMS.
# bootstrap.sql is SCHEMA ONLY: tables, FKs, additive ALTERs, alembic
# version pin. It inserts no display data. Idempotent.
sql/bootstrap.sql

# Run AFTER bootstrap.sql to load every row the gateway expects:
# the canonical 16-camera fleet (Fernet-encrypted credentials), 30 parking
# slots, zone_occupancy, plus sample vehicles / alerts / entry-exit /
# sessions / camera_feeds for a populated dashboard. Idempotent.
sql/seed.sql

# Legacy migrations (only run on databases that pre-date Phase 2 — destructive,
# drops zone_occupancy and zone_id/zone_name columns):
sql/legacy_migrations/drop_zones_v2_destructive.sql

# Manual verification scripts (no real test suite — these are ad-hoc checks
# against a running DB / running gateway, not pytest)
python scratch/check_db.py
python scratch/verify_alerts_fix.py
python scratch/verify_continuous_alerts.py
python scratch/verify_occupancy_fix.py
```

There is no linter, formatter, or test runner configured. Dependencies are pinned in `requirements.txt` (FastAPI 0.111, SQLAlchemy 2.0, pyodbc 5.1, httpx 0.27, pydantic 2.7).

## Architecture

This service is **System 3** — the only API the frontend calls. It sits between the frontend and two upstream services it does **not own**:

- **System 1 — Damanat-PMS-AI** (`SYSTEM1_BASE_URL`, default `:8080`): owns the SQL Server database (`damanat_pms`). The gateway reads its tables directly via SQLAlchemy.
- **System 2 — Damanat-PMS-VideoAnalytics** (`SYSTEM2_BASE_URL`, default `:8000`): provides live slot/vehicle state via HTTP + SSE.

The routing rule, applied per endpoint:

- **Paginated / filterable / exportable / historical** → query SQL Server directly.
- **"Live right now"** → `await` an upstream HTTP call (`app/services/upstream.py`).
- **Real-time push** → SSE multiplex (see `routers/alerts.py:stream_alerts`).

The frontend must never know which system supplied the data — endpoints merge both sources before returning.

### Layering

```
app/main.py             FastAPI app, CORS, includes 7 routers
  ├─ config.py          pydantic-settings → reads .env, builds DB connection string
  ├─ database.py        engine + SessionLocal + scalar()/rows() raw-SQL helpers
  │                     + _BOOL_COLUMNS bool-coercion frozenset
  ├─ shared.py          build_paged() envelope + stream_csv() helper
  ├─ schemas.py         Pydantic response models — wired to response_model= on
  │                     most endpoints; SuccessResponse / EntityActionResponse
  │                     for write endpoints, PagedResponse[T] for list endpoints
  ├─ services/
  │   ├─ auth.py        require_internal_token dependency — gates the
  │   │                 X-Internal-Token-protected camera-credentials and
  │   │                 alerts-test-stream endpoints
  │   ├─ camera_monitor.py  background TCP poller that updates
  │   │                 cameras.last_check_at / last_seen_at / last_status
  │   ├─ crypto.py      Fernet wrapper around CAMERAS_ENCRYPTION_KEY for
  │   │                 reading/writing cameras.password_encrypted
  │   ├─ upstream.py    Two long-lived httpx.AsyncClient instances + SSE iterators
  │   │                 + module-level _system{1,2}_last_connected_at trackers
  │   │                 surfaced on /dashboard/ai-status
  │   └─ bus.py         alerts_bus: in-process Broadcaster fan-out for /alerts/stream
  │                     + start_test_stream() that loops fake alerts for demo
  └─ routers/           One file per tab — dashboard, alerts, entry_exit, vehicles,
                        occupancy, camera_feeds, cameras
```

### Cameras subsystem (Phase 2/4A)

`cameras` is a Gateway-owned table introduced after Phase 4A's
`schema_v2_additive.sql` migration. Columns: `id`, `camera_id` (business
key), `name`, `floor`, `role` (`entry`/`exit`/`floor_counting`/
`slot_detection`/`other`), `watches_floor`, `watches_slots_json`,
`ip_address`, `rtsp_port`, `rtsp_path`, `username`, `password_encrypted`,
`enabled`, plus liveness columns (`last_check_at`, `last_seen_at`,
`last_status`).

Two encryption / auth pieces:

1. **Credentials encryption.** `services/crypto.py` wraps `cryptography.Fernet`
   keyed by `CAMERAS_ENCRYPTION_KEY` (Base64-encoded, generate with
   `Fernet.generate_key()`). The plaintext password is never stored — only
   `password_encrypted`. Two endpoints decrypt on-demand:
   `GET /cameras/{id}/credentials` and `GET /cameras/internal/all`. Both
   require the `X-Internal-Token` header.
2. **Internal token.** `services/auth.py:require_internal_token` is a
   FastAPI `Depends`. It gates the credential endpoints (so VideoAnalytics
   can fetch decrypted RTSP URLs) and the `/alerts/test/start|stop` simulators
   (so a public `/docs` page can't flood the dashboard). The token lives in
   `CAMERAS_INTERNAL_TOKEN`. Empty token → 503 ("not configured").

### Camera liveness monitor

`services/camera_monitor.py` runs a background asyncio task during the
FastAPI lifespan. Every `CAMERA_MONITOR_INTERVAL_SECONDS` (default 60), it
TCP-probes every enabled camera in parallel (concurrency
`CAMERA_MONITOR_CONCURRENCY`) with timeout `CAMERA_MONITOR_TCP_TIMEOUT_SECONDS`
and updates `cameras.last_check_at` / `last_seen_at` / `last_status`. Set
`CAMERA_MONITOR_ENABLED=false` for first-boot when no cameras are wired up.

### Occupancy: two data sources

- `/occupancy/floors`, `/occupancy/floors/{floor}`, `/occupancy/totals` are
  the canonical, current endpoints. They aggregate live `parking_slots` +
  `slot_status` (VA computer-vision counts) and `zone_occupancy.current_count`
  (PMS-AI line-crossing counts) and report both:
    - `current_count` — the line-crossing total (primary)
    - `slot_occupancy_count` — the VA total (secondary)
    - `reconciled: bool` — whether the two agree
  `/occupancy/kpis` exposes the same dual-source signal as
  `occupied_spots` (line-crossing) + `slot_occupied_spots` (VA).
- `/occupancy/zones` is **deprecated** (kept for one release of frontend
  back-compat). Same data shape as `/occupancy/floors` but uses the legacy
  `ZoneItem` schema. Removed in Phase 4C.
- `/occupancy/slots` is paginated; `/occupancy/slots/by-floor` returns the
  same data grouped by floor; `/occupancy/slots/{slot_id}` returns
  `SlotDetail` (single slot + current occupancy + last_occupant + recent
  events + recent alerts).

### Conventions every router follows

- **Raw SQL via `text()`**, never ORM models. Use `scalar(db, sql, params)` for single values and `rows(db, sql, params)` for lists; both come from `app/database.py` and return primitives / list-of-dicts. `rows()` auto-coerces SQL Server `BIT` columns whose names appear in `_BOOL_COLUMNS` (e.g. `is_employee`, `enabled`, `is_online`) to Python `bool` — when adding a new boolean column to a SELECT, also add it to that frozenset.
- **Each tab exposes the trio**: `GET /kpis` (flat object, no nesting), `GET /` (paged list), `GET /export/csv` (same filters as the list). Wrap list responses with `build_paged(items, total, page, page_size)`.
- **SQL Server pagination idiom**: `OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY`.
- **Every endpoint declares `response_model=`.** Write endpoints use either the full entity schema (`VehicleListItem`, `CameraItem`) or `EntityActionResponse{success: bool, id: int|str}` for DELETE/PATCH. The two simple shapes live in `schemas.py` so both routers and the OpenAPI spec stay honest.

### Schema-compatibility shim (important — easy to miss)

The gateway runs against **System 1's database**, which may or may not have had `sql/bootstrap.sql` applied. Several routers therefore probe `INFORMATION_SCHEMA.COLUMNS` at runtime to decide which columns to reference:

- `routers/alerts.py:_alerts_extra_cols()` (cached via `lru_cache`) → `severity`, `location_display`, `slot_id`. `_alert_query_bits()` then synthesizes expressions: when `severity` column is missing it derives the value from `alert_type` via a `CASE`; when `slot_id` is missing it falls back to `zone_id` for joins.
- `routers/vehicles.py:_vehicle_extra_cols()` (per-request) → `is_employee`, `phone`, `email`. Missing columns are emitted as `NULL AS col` in `SELECT`s, and `PUT /vehicles/{id}` filters out post-migration fields when the columns don't exist.
- `routers/camera_feeds.py:_camera_feeds_introspect()` (cached for the process) → returns `{exists, has_id, has_camera_id}`. When the table is missing the endpoint returns an empty paged response instead of 500ing. When the table has a partial shape (no `id`/`camera_id`), the SELECT emits `NULL AS …` placeholders.

**When adding columns or filters, branch on these helpers rather than assuming the column exists** — the gateway is meant to keep working before and after the migration runs.

### Live SSE alert stream (`/alerts/stream`)

`routers/alerts.py:stream_alerts` fans in three sources into one client SSE response, normalising each event through `_normalize_stream_event`:

1. `iter_system1_alert_events()` — SSE from PMS-AI (`/api/v1/alerts/stream`), tagged `pms_ai`.
2. `iter_system2_alert_events()` — SSE from VideoAnalytics (`/api/alerts/stream`), tagged `video_analytics`.
3. `alerts_bus` (the in-process `Broadcaster` from `services/bus.py`) — receives synthetic alerts when `/alerts/test/start` is called, tagged `test_system`.

Plus a 15s `: keep-alive` heartbeat. On client disconnect every pump task is cancelled and the bus subscription removed. The first message sent to a new client is always a `connection_established` event (`is_alert: false`) so the frontend can confirm the pipe is up.

### Time-zone handling (heads up)

Local time is hard-coded to **UTC+2 (Arab Standard Time)** in `routers/alerts.py:alert_stats` and `routers/entry_exit.py:entry_exit_kpis`. "Resolved today" / "today's KPIs" / "since local midnight" all derive from `timezone(timedelta(hours=2))` and convert to UTC before comparing against DB columns (which store UTC). If the deployment moves regions, this needs to change in both files — there is no central setting for it.

### Occupancy capacity sync (side effect — scheduled for removal)

`GET /occupancy/zones` is **not read-only** (yet): on every call it recomputes `B1`/`B2`/total slot counts from `parking_slots` and writes them back into `zone_occupancy.max_capacity` for `B1-PARKING` / `B2-PARKING` / `GARAGE-TOTAL` rows, then commits, before returning the page. This is item **G-1** in `GATEWAY_MODIFICATIONS_REQUIRED.md` PR 2 — after that PR, the GET will be strictly read-only. The computation moves to `_build_floor_occupancy()` (`routers/occupancy.py`) which is already used by `/occupancy/floors` and `/occupancy/totals`.

## Tables this gateway touches

`vehicles`, `parking_sessions`, `entry_exit_log`, `alerts`, `zone_occupancy`, `parking_slots`, `slot_status`, `camera_feeds`, `cameras`. Schemas live in `sql/bootstrap.sql` (the consolidated source of truth, idempotent) — read that, do not invent column names. Real column lists are also commented at the top of `routers/entry_exit.py` and `routers/occupancy.py` for the most-touched tables.

## Configuration

`app/config.py` (`Settings`, pydantic-settings) loads `.env`. Notable defaults differ from `.env.example`: code defaults assume `pms-mssql:1433` / driver 18 (container deploy), while the example file targets `localhost` / driver 17 (local SSMS). Always copy `.env.example` → `.env` and override before running locally.

### DB connection — Trusted_Connection (Windows Auth)

When `DB_TRUSTED_CONNECTION=True` the connection string becomes
`mssql+pyodbc://@{host}:{port}/{db}?driver={d}&Trusted_Connection=Yes&TrustServerCertificate=Yes`.
Two non-obvious bits:

1. The empty `@` between scheme and host is **required** so SQLAlchemy/pyodbc
   doesn't try SQL auth with a blank user. Without it pyodbc 5+ raises
   "Login failed for user ''".
2. The parameter is `Trusted_Connection=Yes` — capital T/C, value `Yes`. The
   ODBC driver is case-sensitive on some Windows builds.

`DB_USER` / `DB_PASSWORD` are ignored when `DB_TRUSTED_CONNECTION=True`.

### CORS — localhost any-port

`app/main.py` configures `CORSMiddleware` with both `allow_origins=settings.origins_list` (from `ALLOWED_ORIGINS`) **and** `allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?"`. The regex is the safety net: any localhost dev port (3000, 4200, 5173, 8080, …) is accepted without having to maintain the `.env` list. In production, only `ALLOWED_ORIGINS` matters — set it to your real frontend domain(s).
