# API Gateway — Parking System 3

The **only** API the frontend talks to.  
Reads historical data from SQL Server and calls System 1 / System 2 for live state.

---

## Architecture

```
Frontend
   │
   ▼
API Gateway  (this project — FastAPI, port 8001)
   ├── SQL Server          ← history, vehicles, alerts, occupancy capacities
   ├── System 1 :8001      ← Damanat-PMS-AI  (health check only from gateway)
   └── System 2 :8002      ← Damanat-PMS-VideoAnalytics (live slots & vehicles)
```

**Rule:**
- Paginated / filterable / exportable / historical → read SQL directly
- "Live right now" → call upstream API from gateway
- Frontend never knows which system the data came from

---

## Quick Start

```bash
# 1. Create and activate a Python virtual environment (Python 3.11 recommended; 3.12 also works)
python3.11 -m venv .venv
source .venv/bin/activate          # (Windows: .venv\Scripts\activate)

# 2. Copy and fill in env
cp .env.example .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate the camera-credentials encryption key + internal token (REQUIRED)
python -c "from cryptography.fernet import Fernet; print('CAMERAS_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "import secrets; print('CAMERAS_INTERNAL_TOKEN=' + secrets.token_urlsafe(32))"
# Paste both into .env. The gateway refuses to boot without them.

# 5. Run the SQL migrations (once, in order)
#    - migrations/fix_system1_schema.sql   (existing System-1 compatibility patches)
#    - migrations/add_cameras_table.sql    (new cameras configurator table)
# Open both in SSMS or run via sqlcmd / docker exec — see the macOS quickstart below.

# 6. Start the gateway
python run.py
# → http://localhost:8001
# → http://localhost:8001/docs  (Swagger UI)
```

## First-time setup on macOS (no SQL Server installed)

If you don't already have a SQL Server reachable, the fastest path is Azure SQL Edge in Docker (ARM-native — runs cleanly on Apple Silicon, unlike `mssql/server` which requires Rosetta and crashes under it).

```bash
# 1. Start the DB
docker run -d --name pms-mssql \
  -e "ACCEPT_EULA=Y" \
  -e "MSSQL_SA_PASSWORD=YourStrong!Pass1" \
  -p 1433:1433 \
  -v pms-mssql-data:/var/opt/mssql \
  mcr.microsoft.com/azure-sql-edge:latest

# 2. Load schema + migrations using a sidecar tools container
#    (avoids needing host-side mssql-tools / msodbcsql)
TOOLS="docker run --rm --network host -v $(pwd):/sql mcr.microsoft.com/mssql-tools \
  /opt/mssql-tools/bin/sqlcmd -S localhost,1433 -U sa -P 'YourStrong!Pass1' -C"
$TOOLS -Q "IF DB_ID('damanat_pms') IS NULL CREATE DATABASE damanat_pms"
$TOOLS -d damanat_pms -i /sql/damanat_pms_full_script_portable.sql
$TOOLS -d damanat_pms -i /sql/migrations/fix_system1_schema.sql
$TOOLS -d damanat_pms -i /sql/migrations/add_cameras_table.sql
```

### DB driver choice (pyodbc vs pymssql)

`config.py` accepts two drivers:

- **`DB_DRIVER=ODBC Driver 18 for SQL Server`** (default) — uses pyodbc. Requires the Microsoft ODBC driver installed on the host: `brew tap microsoft/mssql-release ; brew install msodbcsql18 mssql-tools18`. Production deploys should use this.
- **`DB_DRIVER=pymssql`** — uses pymssql (FreeTDS-based). Useful for local dev when host msodbcsql is unavailable (e.g. macOS Command Line Tools update pending). `pip install pymssql` and `brew install freetds`. Same SQL Server, different transport — no other code changes needed.

---

## System 1 Schema Fixes Required

Before starting the gateway, apply `migrations/fix_system1_schema.sql`.

The script is idempotent and now does two jobs:

1. Adds the compatibility columns the gateway expects on `alerts`, `zone_occupancy`,
   `vehicles`, and `entry_exit_log`.
2. Creates `parking_sessions` if it is missing and hardens the real foreign-key links
   that already exist conceptually in PMS-AI:
   - `entry_exit_log.vehicle_id -> vehicles.id`
   - `entry_exit_log.matched_entry_id -> entry_exit_log.id`
   - `parking_sessions.vehicle_id -> vehicles.id`

If old orphan rows exist, the script prints a warning and skips that foreign key instead
of failing halfway through.

---

## Endpoint Reference

### Gateway Health
| Method | Path      | Description        |
|--------|-----------|--------------------|
| GET    | `/health` | Gateway liveness   |

### Dashboard
| Method | Path                         | Description                                      |
|--------|------------------------------|--------------------------------------------------|
| GET    | `/dashboard/ai-status`       | Combined System 1 + System 2 health              |
| GET    | `/dashboard/kpis`            | total_unique_plates, active_now, open_alerts     |
| GET    | `/dashboard/active-vehicles` | Live parked vehicles merged with SQL metadata    |

### Alerts
| Method | Path                   | Query Params                                          |
|--------|------------------------|-------------------------------------------------------|
| GET    | `/alerts/stats`        | —                                                     |
| GET    | `/alerts/stream`       | — (Server-Sent Events)                                |
| GET    | `/alerts/`             | page, page_size, search, severity, alert_type, resolved, date_from, date_to |
| PATCH  | `/alerts/{id}/resolve` | —                                                     |
| DELETE | `/alerts/{id}`         | —                                                     |
| GET    | `/alerts/export/csv`   | same filters as list                                  |

# Test Alerts
| Method | Path                   | Query Params                                          |
|--------|------------------------|-------------------------------------------------------|
| GET    | `/alerts/test/start`   | interval (sec, default 1.0) — start continuous stream |
| GET    | `/alerts/test/stop`    | — (stop continuous stream)                            |

### Entry / Exit
| Method | Path                      | Query Params                                          |
|--------|---------------------------|-------------------------------------------------------|
| GET    | `/entry-exit/kpis`        | target_date (ISO, optional — for yesterday compare)   |
| GET    | `/entry-exit/traffic`     | period = daily \| weekly \| monthly                   |
| GET    | `/entry-exit/`            | page, page_size, search, floor, is_employee, date_from, date_to |
| GET    | `/entry-exit/export/csv`  | same filters as list                                  |

### Vehicles
| Method | Path                    | Query Params                                  |
|--------|-------------------------|-----------------------------------------------|
| POST   | `/vehicles/`            | body: VehicleCreate                           |
| GET    | `/vehicles/kpis`        | —                                             |
| GET    | `/vehicles/`            | page, page_size, search, is_employee, vehicle_type |
| PUT    | `/vehicles/{id}`        | body: VehicleUpdate                           |
| DELETE | `/vehicles/{id}`        | —                                             |
| GET    | `/vehicles/export/csv`  | same filters as list                          |

### Occupancy
| Method | Path                 | Query Params                        |
|--------|----------------------|-------------------------------------|
| GET    | `/occupancy/kpis`    | —                                   |
| GET    | `/occupancy/zones`   | page, page_size, search, floor      |

### Cameras
| Method | Path                                | Query Params / Body                                                        |
|--------|-------------------------------------|----------------------------------------------------------------------------|
| GET    | `/cameras/kpis`                     | — (returns total, enabled, disabled, online, offline, by_floor, by_status) |
| GET    | `/cameras/`                         | page, page_size, search, floor, enabled, is_online, last_status            |
| GET    | `/cameras/{camera_id}`              | —                                                                          |
| POST   | `/cameras/`                         | body: CameraCreate (camera_id, ip_address, username?, password?, …)        |
| PUT    | `/cameras/{camera_id}`              | body: CameraUpdate — only provided fields update; password=None is no-op   |
| DELETE | `/cameras/{camera_id}`              | —                                                                          |
| POST   | `/cameras/{camera_id}/check-now`    | one-off TCP probe; returns is_online, last_status, last_check_at, last_seen_at |
| GET    | `/cameras/export/csv`               | search, floor, enabled — **password column intentionally absent**          |
| GET    | `/cameras/{camera_id}/credentials`  | header `X-Internal-Token` required → returns plaintext password + assembled rtsp_url |
| GET    | `/cameras/internal/all`             | header `X-Internal-Token` required → bulk decrypted list for upstream consumers (VideoAnalytics). `?enabled=true` (default), `?include_disabled=true` for diagnostic mode. **Unpaginated by design.** |

The RTSP URL is **never stored** — it's assembled on demand from `ip_address`/`rtsp_port`/`rtsp_path`/`username`/decrypted-`password`. List/show responses include `rtsp_url_masked` (password → `***`) and `is_online` (derived from `last_seen_at` + the monitor interval).

#### Liveness monitor

A background asyncio task TCP-probes every enabled camera every `CAMERA_MONITOR_INTERVAL_SECONDS` (default 60s) and writes `last_check_at` / `last_seen_at` / `last_status` (`online`, `timeout`, `connection_refused`, `dns_error`, `unreachable`). Toggle off with `CAMERA_MONITOR_ENABLED=false` for local dev when cameras aren't reachable.

#### Migrating an upstream `.env` into the cameras table

For sites where camera credentials currently live in System 2 (VideoAnalytics) `.env` files, use the one-shot ingest script:

```bash
# Dry-run (default — prints what would change, makes no DB writes)
python scripts/migrate_cameras_from_env.py --source /path/to/upstream/.env

# Actually write
python scripts/migrate_cameras_from_env.py --source /path/to/upstream/.env --commit

# Rotate passwords (re-imports CAM<N>_PASS values for existing rows)
python scripts/migrate_cameras_from_env.py --source /path/to/upstream/.env --commit --overwrite-passwords

# Custom prefix if upstream uses CAMERA<N>_ instead of CAM<N>_
python scripts/migrate_cameras_from_env.py --source ... --prefix CAMERA --commit
```

Expected key shape (default prefix `CAM`): `CAM01_NAME`, `CAM01_FLOOR`, `CAM01_IP`, `CAM01_RTSP_PORT`, `CAM01_RTSP_PATH`, `CAM01_USER`, `CAM01_PASS`, `CAM01_ENABLED`, `CAM01_NOTES`. See `scripts/sample_upstream_cameras.env` for a complete annotated example. The script also accepts a full `CAM01_RTSP=rtsp://user:pass@host:port/path` line and decomposes it via `urllib.parse.urlsplit` for backwards compatibility with upstream configs that already store the assembled URL.

After running once, point System 2 (VideoAnalytics) at `GET /cameras/internal/all` (with the shared `X-Internal-Token` header) on its own startup + on a periodic refresh, and remove the `CAM<N>_*` lines from its `.env`. Camera changes from then on happen via the gateway's CRUD endpoints.

---

## Uniform Response Contracts

**Paged list** (every list endpoint):
```json
{
  "total_count": 150,
  "page": 1,
  "page_size": 20,
  "items": [ ... ]
}
```

**CSV export** — every tab has `/export/csv` accepting the same filters as its list endpoint. Returns a `Content-Disposition: attachment` stream.

**KPIs** — every tab has `/kpis` returning a flat object. No nesting.

---

## Project Structure

```
api_gateway/
├── run.py                        # uvicorn entry point
├── requirements.txt
├── .env.example
├── migrations/
│   └── fix_system1_schema.sql    # run once on SQL Server
└── app/
    ├── main.py                   # FastAPI app + middleware
    ├── config.py                 # Settings from .env
    ├── database.py               # SQLAlchemy engine + helpers
    ├── shared.py                 # PagedResponse + stream_csv
    ├── schemas.py                # Pydantic response models
    ├── services/
    │   └── upstream.py           # httpx clients for System 1 & 2
    └── routers/
        ├── dashboard.py
        ├── alerts.py
        ├── entry_exit.py
        ├── vehicles.py
        └── occupancy.py
```

---

## What Each Router Reads

| Router       | SQL Server tables used                        | Upstream calls              |
|--------------|-----------------------------------------------|-----------------------------|
| dashboard    | Vehicles, EntryExit, Alerts                   | Sys1 /health, Sys2 /health, Sys2 /vehicles |
| alerts       | Alerts, Vehicles                              | none                        |
| entry_exit   | EntryExit, Vehicles                           | none                        |
| vehicles     | Vehicles, EntryExit                           | none                        |
| occupancy    | ZoneOccupancy                                 | Sys2 /slots, Sys2 /stats    |

---

## Next Steps (after this scaffold works)

1. **SSE pass-through** — if the frontend needs real-time slot updates, add a  
   `GET /live/slots` endpoint that proxies System 2's SSE stream.

2. **Auth middleware** — add JWT/API-key verification as a FastAPI dependency  
   injected globally in `main.py`.

3. **Response caching** — wrap KPI queries in a short TTL cache (e.g. `fastapi-cache2`)  
   to avoid hammering SQL on every dashboard refresh.

4. **Typed return annotations** — wire `schemas.py` into each router's  
   `response_model=` parameter for automatic OpenAPI docs generation.
