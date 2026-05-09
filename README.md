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

### Prerequisites

- Python 3.11 or 3.12
- SQL Server reachable (local SSMS, Docker, or Azure SQL Edge — see below)
- Microsoft ODBC Driver 17 or 18 for SQL Server installed on the host

### Steps

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd "API Gateway"

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example env and fill in your values
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
# Key variables to set:
#   DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD  (or DB_TRUSTED_CONNECTION=True for Windows Auth)
#   SYSTEM1_BASE_URL  (PMS-AI, default http://localhost:8080)
#   SYSTEM2_BASE_URL  (VideoAnalytics, default http://localhost:8000)

# 5. Generate the two required secrets and paste them into .env
python -c "from cryptography.fernet import Fernet; print('CAMERAS_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "import secrets; print('CAMERAS_INTERNAL_TOKEN=' + secrets.token_urlsafe(32))"
# CAMERAS_ENCRYPTION_KEY  — encrypts RTSP passwords stored in the cameras table
# CAMERAS_INTERNAL_TOKEN  — shared secret for /cameras/internal/all (used by VideoAnalytics)

# 6. Set up the database (run ONCE, in this order, in SSMS or sqlcmd)
#
#    a. Create the database if it doesn't exist:
#       CREATE DATABASE damanat_pms;
#
#    b. Apply the full schema (idempotent — safe to re-run):
sqlcmd -E -S localhost -d damanat_pms -i sql/bootstrap.sql
#
#    c. Load seed data — 32 parking slots, 16 cameras, zone_occupancy rows,
#       sample vehicles / alerts / sessions (idempotent):
sqlcmd -E -S localhost -d damanat_pms -i sql/seed.sql

# 7. Start the gateway
python run.py
# → API:     http://localhost:8001
# → Swagger: http://localhost:8001/docs
```

> **Windows Auth shortcut (step 6):** if you set `DB_TRUSTED_CONNECTION=True` in `.env`
> you can skip `DB_USER` / `DB_PASSWORD`. Open SSMS, connect to your instance, and run
> `sql/bootstrap.sql` then `sql/seed.sql` from the query window instead of sqlcmd.

> **Disable camera monitor during local dev** (no cameras wired up):  
> set `CAMERA_MONITOR_ENABLED=false` in `.env` to silence TCP-probe timeouts on startup.

---

## First-time setup — Docker SQL Server (macOS / Linux, no SSMS)

```bash
# 1. Start Azure SQL Edge (ARM-native, works on Apple Silicon without Rosetta)
docker run -d --name pms-mssql \
  -e "ACCEPT_EULA=Y" \
  -e "MSSQL_SA_PASSWORD=YourStrong!Pass1" \
  -p 1433:1433 \
  -v pms-mssql-data:/var/opt/mssql \
  mcr.microsoft.com/azure-sql-edge:latest

# 2. Create the database and apply schema + seed via the mssql-tools sidecar
SQLCMD="docker run --rm --network host -v $(pwd):/sql \
  mcr.microsoft.com/mssql-tools /opt/mssql-tools/bin/sqlcmd \
  -S localhost,1433 -U sa -P 'YourStrong!Pass1' -C"

$SQLCMD -Q "IF DB_ID('damanat_pms') IS NULL CREATE DATABASE damanat_pms"
$SQLCMD -d damanat_pms -i /sql/sql/bootstrap.sql
$SQLCMD -d damanat_pms -i /sql/sql/seed.sql

# 3. Set DB_DRIVER=ODBC Driver 18 for SQL Server in .env, then:
python run.py
```

### DB driver choice

| Setting | Transport | When to use |
|---|---|---|
| `DB_DRIVER=ODBC Driver 18 for SQL Server` | pyodbc | Default — production and most dev environments |
| `DB_DRIVER=ODBC Driver 17 for SQL Server` | pyodbc | Older host installs |
| `DB_DRIVER=pymssql` | FreeTDS | macOS dev when ODBC driver unavailable (`pip install pymssql && brew install freetds`) |

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
| Method | Path                          | Query Params                                                  |
|--------|-------------------------------|---------------------------------------------------------------|
| GET    | `/occupancy/kpis`             | —                                                             |
| GET    | `/occupancy/totals`           | —                                                             |
| GET    | `/occupancy/floors`           | page, page_size                                               |
| GET    | `/occupancy/floors/{floor}`   | —                                                             |
| GET    | `/occupancy/slots`            | page, page_size, floor, floor_id, is_available, reservation_type |
| GET    | `/occupancy/slots/by-floor`   | floor, floor_id                                               |
| GET    | `/occupancy/slots/{slot_id}`  | —                                                             |
| GET    | `/occupancy/export`           | floor, floor_id, search                                       |
| GET    | `/occupancy/zones`            | page, page_size, search, floor (**deprecated** — use `/floors`) |

> Violation-zone slots (`is_violation_zone = 1`) are excluded from every count and list.  
> Reserved slots can be filtered with `?reservation_type=SPECIAL`.  
> Each slot row now includes `reservation_type` and `reserved_for` fields.

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
API Gateway/
├── run.py                          # uvicorn entry point (python run.py)
├── requirements.txt
├── .env.example
├── sql/
│   ├── bootstrap.sql               # full schema — idempotent, run first
│   ├── seed.sql                    # 32 slots, 16 cameras, sample data — run after bootstrap
│   └── legacy_migrations/          # destructive scripts for pre-Phase-2 databases only
└── app/
    ├── main.py                     # FastAPI app, CORS, router registration
    ├── config.py                   # pydantic-settings → .env
    ├── database.py                 # SQLAlchemy engine, scalar()/rows() helpers
    ├── shared.py                   # build_paged() envelope, stream_csv()
    ├── schemas.py                  # all Pydantic response models
    ├── services/
    │   ├── upstream.py             # httpx clients for System 1 & 2 + SSE iterators
    │   ├── auth.py                 # require_internal_token FastAPI dependency
    │   ├── crypto.py               # Fernet encrypt/decrypt for camera passwords
    │   ├── camera_monitor.py       # background TCP-probe task
    │   ├── snapshots.py            # resolve_snapshot_url() — local path → CDN URL
    │   └── bus.py                  # in-process SSE broadcaster for /alerts/stream
    └── routers/
        ├── _helpers.py             # _floor_schema() probe cache + floor-resolve helpers
        ├── dashboard.py
        ├── alerts.py
        ├── entry_exit.py
        ├── vehicles.py
        ├── occupancy.py
        ├── cameras.py
        └── camera_feeds.py
```

---

## What Each Router Reads

| Router        | SQL Server tables used                                                    | Upstream calls                         |
|---------------|---------------------------------------------------------------------------|----------------------------------------|
| dashboard     | `vehicles`, `entry_exit_log`, `alerts`, `parking_sessions`                | Sys1 /health, Sys2 /health, Sys2 /vehicles |
| alerts        | `alerts`, `vehicles`, `parking_slots`                                     | Sys1 SSE, Sys2 SSE (stream multiplex)  |
| entry_exit    | `entry_exit_log`, `parking_sessions`, `vehicles`                          | none                                   |
| vehicles      | `vehicles`, `parking_sessions`, `alerts`                                  | none                                   |
| occupancy     | `parking_slots`, `slot_status`, `zone_occupancy`, `parking_sessions`      | Sys2 /slots (live overlay on /zones)   |
| cameras       | `cameras`                                                                 | none                                   |
| camera_feeds  | `camera_feeds`                                                            | none                                   |

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
