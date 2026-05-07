# Damanat PMS — Lifecycle Simulator

## What this is

Reproduces the full vehicle lifecycle (entry → park → move floors → exit) by
hitting the same APIs the cameras hit, end-to-end against running PMS-AI +
VideoAnalytics + Gateway services and a seeded SQL Server. Use it to validate
fixes before deploy: every script ends with a `PASS` / `FAIL` token on stdout
so you can grep an entire run.

## Prerequisites

- Python 3.10+ (3.11 tested) with `pip install requests pyodbc`.
- All three services running locally:
  - PMS-AI on `:8080` (`/api/v1/health`)
  - VideoAnalytics on `:8000`
  - API Gateway on `:8001` (`/dashboard/health`)
- SQL Server reachable (default `localhost:1433`, db `damanat_pms`) and
  seeded:
  ```
  sql/bootstrap.sql      # schema
  sql/seed.sql           # cameras, slots, sample data
  ```
- `cleanup_test_data.py` needs the `ODBC Driver 18 for SQL Server` (or pass
  `--db-driver "ODBC Driver 17 for SQL Server"`).

## Quick start

```bash
# Full lifecycle (default plate TEST-LIFE01)
python scripts/simulate/run_full_lifecycle.py

# Single step
python scripts/simulate/01_car_enters_garage.py --plate TEST-A001

# Wipe TEST-* rows from the DB
python scripts/simulate/cleanup_test_data.py --plate-prefix TEST-
```

Override service URLs with `--pms-ai http://...` and `--gateway http://...`
on every script.

## Scripts

| Script | What it does | Typical invocation |
| --- | --- | --- |
| `_common.py` | Shared helpers (HTTP, builders, color, polling). Not directly executable. | — |
| `01_car_enters_garage.py` | Posts a Hikvision ANPR XML entry event; verifies `entry_exit_log` row, vehicle parked, KPI bumped. | `python 01_car_enters_garage.py --plate TEST-A001` |
| `02_car_parks_in_slot.py` | Calls PMS-AI internal `bind-slot`; verifies `vehicle.current_slot_id` and `current_event.slot_id` agree (three-way invariant). | `python 02_car_parks_in_slot.py --plate TEST-A001 --slot-id B11_CFO --zone-id B1-PARKING` |
| `03_car_leaves_slot.py` | Calls PMS-AI internal `unbind-slot`; verifies slot cleared but session stays open. | `python 03_car_leaves_slot.py --plate TEST-A001 --slot-id B11_CFO` |
| `04_car_moves_b1_to_b2.py` | Composite (03 → optional linedetection → 02). | `python 04_car_moves_b1_to_b2.py --plate TEST-A001 --from-slot B11_CFO --to-slot B16 --with-line-events` |
| `05_car_moves_b2_to_b1.py` | Mirror of 04. | `python 05_car_moves_b2_to_b1.py --plate TEST-A001 --from-slot B16 --to-slot B11_CFO` |
| `06_car_exits_garage.py` | Posts an ANPR XML exit event; verifies session closed + vehicle unparked. | `python 06_car_exits_garage.py --plate TEST-A001` |
| `run_full_lifecycle.py` | Orchestrator: 01 → 02 → 04 → 05 → 06. Short-circuits on first FAIL. | `python run_full_lifecycle.py --plate TEST-LIFE01` |
| `cleanup_test_data.py` | Direct `pyodbc` DELETE of all `plate_number LIKE 'TEST-%'` rows. | `python cleanup_test_data.py --plate-prefix TEST- --dry-run` |

## Conventions

- Final stdout line of every leaf script is exactly `PASS` or `FAIL`
  (uppercase, no colon, no trailing whitespace). Grep that, not the body.
- Exit code `0` ↔ `PASS`, exit code `1` ↔ `FAIL` or HTTP/connection error.
- Test plates always start with `TEST-` so cleanup can target them safely.
  Single-script default: `TEST-A001`. Orchestrator default: `TEST-LIFE01`.
- Test slots: `B11_CFO` (B1) and `B16` (B2). Defaults in 04/05 use these.
  (Note: per `seed.sql`, `B12` is on B1 — do NOT use `B12` for B2-side
  defaults. See Troubleshooting if 04/05 fail floor checks.)
- All times use facility offset `+03:00` (matches `_common.now_facility_iso`).
- `--pms-ai` and `--gateway` flags pass through every layer of the suite.

## Troubleshooting

- **"vehicle not found" in 02/03/04/05** — run `01_car_enters_garage.py`
  first (or `run_full_lifecycle.py` which orders steps for you).
- **"slot not on B1/B2" / floor mismatch in 04/05** — `seed.sql` ships
  `B12` on `B1` (line 55). If your B1↔B2 move script asserts the new
  floor differs, point `--to-slot` at a real B2 slot (e.g. `B14`, `B15`,
  `B16`, …, `B27`).
- **HTTP timeout** — confirm services are up:
  ```
  curl http://localhost:8080/api/v1/health
  curl http://localhost:8001/dashboard/health
  ```
- **PASS line mismatch** — re-run the script and look at the FINAL line
  of stdout manually. The orchestrator splits on lines and matches
  `["PASS"]` exactly; trailing whitespace or accidental extra prints
  break the check. Common culprit: `print(green("PASS"))` instead of
  `print("PASS")` (the helper prints to stdout AND returns None).
- **`cleanup_test_data.py` connection failure** — try `--db-driver
  "ODBC Driver 17 for SQL Server"`, or `--trusted` if you're using
  Windows Auth. Mirrors the connection rules in `app/config.py`.

## What this does NOT test

- VideoAnalytics' CV pipeline. We do not write to `slot_status` — that's
  VA's table. The `/occupancy/slots/{id}` snapshot in script 02 is
  informational only.
- The camera-server HLS proxy (`/cameras/{id}/feed`).
- Live SSE alert-stream timing (`/alerts/stream`). Use
  `/alerts/test/start` for that.

## Cleanup

```bash
# Dry-run first to see what would be deleted
python scripts/simulate/cleanup_test_data.py --plate-prefix TEST- --dry-run

# Actually delete
python scripts/simulate/cleanup_test_data.py --plate-prefix TEST-

# Windows auth variant
python scripts/simulate/cleanup_test_data.py --plate-prefix TEST- --trusted
```

`run_full_lifecycle.py` calls cleanup automatically before AND after each
run unless you pass `--no-cleanup-first` / `--no-cleanup-after`.
