# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the gateway (port from settings.gateway_port, default 8001)
python run.py

# One-time DB setup before first run — execute against SQL Server in SSMS
# (idempotent; adds compatibility columns + relationships on System 1's tables)
migrations/fix_system1_schema.sql

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
app/main.py             FastAPI app, CORS, includes 6 routers
  ├─ config.py          pydantic-settings → reads .env, builds DB connection string
  ├─ database.py        engine + SessionLocal + scalar()/rows() raw-SQL helpers
  ├─ shared.py          build_paged() envelope + stream_csv() helper
  ├─ schemas.py         Pydantic response models (defined but not wired to response_model=)
  ├─ services/
  │   ├─ upstream.py    Two long-lived httpx.AsyncClient instances (one per upstream)
  │   │                 + SSE iterators iter_system1_alert_events / iter_system2_alert_events
  │   └─ bus.py         alerts_bus: in-process Broadcaster fan-out for /alerts/stream subscribers
  │                     + start_test_stream() that loops fake alerts for demo/testing
  └─ routers/           One file per tab — dashboard, alerts, entry_exit, vehicles, occupancy, camera_feeds
```

### Conventions every router follows

- **Raw SQL via `text()`**, never ORM models. Use `scalar(db, sql, params)` for single values and `rows(db, sql, params)` for lists; both come from `app/database.py` and return primitives / list-of-dicts.
- **Each tab exposes the trio**: `GET /kpis` (flat object, no nesting), `GET /` (paged list), `GET /export/csv` (same filters as the list). Wrap list responses with `build_paged(items, total, page, page_size)`.
- **SQL Server pagination idiom**: `OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY`.

### Schema-compatibility shim (important — easy to miss)

The gateway runs against **System 1's database**, which may or may not have had `migrations/fix_system1_schema.sql` applied. Several routers therefore probe `INFORMATION_SCHEMA.COLUMNS` at runtime to decide which columns to reference:

- `routers/alerts.py:_alerts_extra_cols()` (cached via `lru_cache`) → `severity`, `location_display`, `slot_id`. `_alert_query_bits()` then synthesizes expressions: when `severity` column is missing it derives the value from `alert_type` via a `CASE`; when `slot_id` is missing it falls back to `zone_id` for joins.
- `routers/vehicles.py:_vehicle_extra_cols()` (per-request) → `is_employee`, `phone`, `email`. Missing columns are emitted as `NULL AS col` in `SELECT`s, and `PUT /vehicles/{id}` filters out post-migration fields when the columns don't exist.

**When adding columns or filters, branch on these helpers rather than assuming the column exists** — the gateway is meant to keep working before and after the migration runs.

### Live SSE alert stream (`/alerts/stream`)

`routers/alerts.py:stream_alerts` fans in three sources into one client SSE response, normalising each event through `_normalize_stream_event`:

1. `iter_system1_alert_events()` — SSE from PMS-AI (`/api/v1/alerts/stream`), tagged `pms_ai`.
2. `iter_system2_alert_events()` — SSE from VideoAnalytics (`/api/alerts/stream`), tagged `video_analytics`.
3. `alerts_bus` (the in-process `Broadcaster` from `services/bus.py`) — receives synthetic alerts when `/alerts/test/start` is called, tagged `test_system`.

Plus a 15s `: keep-alive` heartbeat. On client disconnect every pump task is cancelled and the bus subscription removed. The first message sent to a new client is always a `connection_established` event (`is_alert: false`) so the frontend can confirm the pipe is up.

### Time-zone handling (heads up)

Local time is hard-coded to **UTC+2 (Arab Standard Time)** in `routers/alerts.py:alert_stats` and `routers/entry_exit.py:entry_exit_kpis`. "Resolved today" / "today's KPIs" / "since local midnight" all derive from `timezone(timedelta(hours=2))` and convert to UTC before comparing against DB columns (which store UTC). If the deployment moves regions, this needs to change in both files — there is no central setting for it.

### Occupancy capacity sync (side effect)

`GET /occupancy/zones` is **not read-only**: on every call it recomputes `B1`/`B2`/total slot counts from `parking_slots` and writes them back into `zone_occupancy.max_capacity` for `B1-PARKING` / `B2-PARKING` / `GARAGE-TOTAL` rows, then commits, before returning the page. Edits to slot counts in `parking_slots` propagate to zone capacity automatically through this endpoint.

## Tables this gateway touches

`vehicles`, `parking_sessions`, `entry_exit_log`, `alerts`, `zone_occupancy`, `parking_slots`, `slot_status`, `camera_feeds`. Schemas live in `damanat_pms_full_script.sql` / `damanat_pms_full_script_portable.sql` (System 1's authoritative dump) — read those, do not invent column names. Real column lists are also commented at the top of `routers/entry_exit.py` and `routers/occupancy.py` for the most-touched tables.

## Configuration

`app/config.py` (`Settings`, pydantic-settings) loads `.env`. Notable defaults differ from `.env.example`: code defaults assume `pms-mssql:1433` / driver 18 (container deploy), while the example file targets `localhost` / driver 17 (local SSMS). Always copy `.env.example` → `.env` and override before running locally.
