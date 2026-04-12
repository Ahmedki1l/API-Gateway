# API Gateway — Parking System 3

The **only** API the frontend talks to.  
Reads historical data from SQL Server and calls System 1 / System 2 for live state.

---

## Architecture

```
Frontend
   │
   ▼
API Gateway  (this project — FastAPI, port 8000)
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
# 1. Copy and fill in env
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the schema migration on SQL Server (once)
#    Open migrations/fix_system1_schema.sql in SSMS and execute

# 4. Start the gateway
python run.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

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
| GET    | `/alerts/`             | page, page_size, search, severity, alert_type, resolved, date_from, date_to |
| PATCH  | `/alerts/{id}/resolve` | —                                                     |
| DELETE | `/alerts/{id}`         | —                                                     |
| GET    | `/alerts/export/csv`   | same filters as list                                  |

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
| GET    | `/vehicles/kpis`        | —                                             |
| GET    | `/vehicles/`            | page, page_size, search, is_employee, vehicle_type |
| PUT    | `/vehicles/{id}`        | body: VehicleUpdate                           |
| GET    | `/vehicles/export/csv`  | same filters as list                          |

### Occupancy
| Method | Path                 | Query Params                        |
|--------|----------------------|-------------------------------------|
| GET    | `/occupancy/kpis`    | —                                   |
| GET    | `/occupancy/zones`   | page, page_size, search, floor      |

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
