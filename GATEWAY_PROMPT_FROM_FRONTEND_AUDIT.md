# Gateway prompt — frontend live-audit findings (handoff to gateway team / next session)

**Status (2026-04-25):** all five gateway-side items below have shipped on
the gateway main branch. Verification gates remain to run against a live
gateway + DB (the `/tmp/pms_audit.py` script). Per-item resolution:

| Item | Status | Resolution |
|---|---|---|
| GA-2 | ✅ shipped | `app/routers/vehicles.py` — filter switched from `ps.parked_at IS NOT NULL` to `ps.plate_number IS NOT NULL`. The `ps` subquery already constrains `WHERE status = 'open'`, so a non-null match means an open session exists for that plate. Aligns with `/dashboard/kpis.active_now`. |
| GA-1 | ✅ shipped | `app/routers/dashboard.py` — `total_unique_plates` now reads `vehicles` registry (option #3). Added `plates_seen_today: int` (`entry_exit_log` since local midnight). `DashboardKPIs` schema gained the new field. |
| GA-3 | ✅ shipped | `app/routers/occupancy.py` — `/occupancy/kpis` now uses the same slot-status SQL as `/occupancy/totals`. `slot_occupied_spots` retained as the explicit secondary signal (equals `occupied_spots` after fix). |
| GA-4 | ✅ shipped | `app/routers/cameras.py` — `online` now reads from `by_status.get("online", 0)`; both `online` and `by_status` are enabled-only and key off `last_status`. By construction `online == by_status['online']`. |
| G-6  | ✅ shipped | `app/routers/alerts.py` — list and detail queries now `LEFT JOIN cameras` (for `floor` fall-through via `watches_floor`); list also COALESCEs `vehicle_id` from the existing vehicles join. Detail handler now builds the `camera` and `vehicle_event` nested objects from the joined columns. |
| GA-5 | 🔴 upstream bug | `parking_sessions` has **no writer in any of the three services**. PMS-AI's camera webhook only writes `entry_exit_log`; VideoAnalytics POSTs to a phantom `/api/v1/internal/parking-sessions/bind-slot` endpoint that does not exist in PMS-AI. The 15 "active_now" rows are stale or seed/manual data. Not gateway-fixable — owners of System 1 must implement the missing endpoint. Gateway-side mitigation options listed below. |

**Context for the gateway-side worker:** the Angular team just finished a live end-to-end audit (probing every endpoint at `http://localhost:8001` and cross-checking against the `damanat_pms` SQL Server). Six issues surfaced that produce wrong-looking numbers in the UI. Five of them are gateway-side. This document is the brief — paste it into the next Claude session on the gateway repo, or hand it to whoever is doing the work.

The full audit data lives at `Synitera.PS/angular/INTEGRATION_AUDIT_LIVE.md`. The frontend rollout that depends on these fixes is in `Synitera.PS/angular/INTEGRATION_PLAN_LIVE.md`. The gateway team's existing punch list is `API-Gateway/GATEWAY_MODIFICATIONS_REQUIRED.md` — items below either map to its existing G-x or extend it as GA-x ("audit-derived").

---

## Hard constraints — DO NOT change these (frontend has aligned to them)

If you rename or reshape any of the following, you will force the Angular team to redo recently-shipped work. Don't.

- **`EntryExitKPIs.total_vehicles_today`** stays as-is (G-7 was already resolved as deferred-by-design — the `_today` suffix carries semantic weight). Frontend reads this field by this exact name.
- **`AlertStreamEventLite`** SSE schema is the canonical wire shape (G-2 RESOLVED). The wire field is `triggered_at` (not `timestamp`). Don't add or remove fields from this schema without notice.
- **The new endpoints exposed in the recent gateway PR** must keep their shapes:
  - `GET /entry-exit/by-vehicle/{vehicle_id}` → `PagedResponse[VehicleEvent]`
  - `GET /entry-exit/{event_id}` → `VehicleEventDetail` (with `vehicle`, `slot`, `entry_camera`, `exit_camera`, `alerts` joined)
  - `GET /occupancy/slots/by-floor` → `list[FloorSlotGroup]`
  - `GET /occupancy/slots/{slot_id}` → `SlotDetail`
  - `GET /vehicles/?is_currently_parked=true` → `PagedResponse[VehicleListItem]` (the **filter** needs fixing per GA-2 below; the **shape** stays)
- **`FloorOccupancy`** keeps its current fields: `floor`, `max_capacity`, `current_count`, `available`, `utilization`, `data_source`, `last_updated`, `camera_id`, `slot_occupancy_count`, `slot_occupancy_source`, `reconciled`. Frontend consumes `reconciled` and `slot_occupancy_count` to render a drift badge per floor.
- **`/dashboard/active-vehicles`** can be marked deprecated but **MUST NOT BE REMOVED** until GA-2 ships. The frontend just reverted to it as a fallback because GA-2 is broken. Once GA-2 lands, the frontend will re-migrate and you can drop the route after that release cycle.
- **The two CSV-aliasing fields the frontend has settled on**: `snapshot_url` (not `snapshot_path`), `slot_name` (not `zone_name`). Whichever endpoint emits these, keep these names.

If any of the above MUST change for a good reason, say so out loud in the PR description so the Angular team can pre-empt the rollback cycle.

---

## Required fixes — five items, ranked by user-visible impact

### GA-2 — RELEASE BLOCKER — `/vehicles/?is_currently_parked=true` returns 0

**File:** `app/routers/vehicles.py` — wherever `is_currently_parked` filter is applied. Likely a `JOIN parking_sessions ON parking_sessions.vehicle_id = vehicles.id WHERE parking_sessions.exit_time IS NULL`.

**The problem:** all 17 rows in `parking_sessions` have `vehicle_id IS NULL` — the data is plate-keyed only. The INNER JOIN therefore matches nothing, returning `total_count=0` even though `/dashboard/kpis.active_now` correctly counts 15. The dashboard's "Active Vehicles" panel renders empty.

**Direct DB confirmation:**
```sql
SELECT COUNT(*) AS total,
       SUM(CASE WHEN vehicle_id IS NOT NULL THEN 1 ELSE 0 END) AS linked,
       SUM(CASE WHEN exit_time IS NULL THEN 1 ELSE 0 END) AS active
FROM parking_sessions;
-- total=17 linked_to_vehicle=0 active(no_exit)=15
```

**Required fix — pick one (in order of preference):**

1. **Plate-join** (preferred, no data migration): change the filter to `LEFT JOIN parking_sessions ON parking_sessions.plate_number = vehicles.plate_number WHERE parking_sessions.exit_time IS NULL`. For unregistered plates (rows in `parking_sessions` with no matching `vehicles` row), synthesize a "ghost vehicle" item: `id=null, plate_number=<from session>, owner_name=null, vehicle_type=null, is_employee=null, is_registered=false`, and populate `current_event` from the session.

2. **Backfill `parking_sessions.vehicle_id` at ingest**: when a new session is opened, INSERT-or-SELECT into `vehicles` first to ensure a row exists, then set `parking_sessions.vehicle_id`. One-time backfill SQL for the existing 17 rows: `UPDATE ps SET vehicle_id = v.id FROM parking_sessions ps INNER JOIN vehicles v ON v.plate_number = ps.plate_number WHERE ps.vehicle_id IS NULL;`. This works only for plates already in `vehicles` (4 of 15) — the other 11 still need the plate-join behavior or auto-promotion.

3. **Auto-promote plates into `vehicles` at session-open**: similar to #2 but creates the `vehicles` row inline.

#1 is the smallest-blast-radius change. The frontend is OK with `id: null` items as long as `plate_number` and `current_event.entry.{camera_id, snapshot_url}` are populated.

**Acceptance:**
```sql
-- Should equal /vehicles/?is_currently_parked=true total_count
SELECT COUNT(DISTINCT COALESCE(v.id, CAST(ps.id AS BIGINT) * -1)) AS expected
FROM parking_sessions ps
LEFT JOIN vehicles v ON v.plate_number = ps.plate_number
WHERE ps.exit_time IS NULL;
```

After fix, the Angular team un-reverts `loadActiveVehicles` to call `getActiveParkedVehicles({page_size: 20})` (their Phase 20).

---

### GA-1 — `/dashboard/kpis.total_unique_plates` reads from the wrong table

**File:** `app/routers/dashboard.py` — kpis SQL.

**The problem:** the field returns `15` (which is `COUNT(DISTINCT plate_number) FROM parking_sessions`). The dashboard tile is labeled "Total Unique Plates" — operators reading it assume it's the registered-vehicle count, which is `4`. The field name + SQL + UI label are not aligned.

**Direct DB confirmation:**
```sql
SELECT COUNT(DISTINCT plate_number) FROM vehicles;          -- 4
SELECT COUNT(DISTINCT plate_number) FROM parking_sessions;  -- 15  ← this is what the gateway returns
SELECT COUNT(DISTINCT plate_number) FROM entry_exit_log;    -- 20
```

**Required fix — pick one:**

1. **Change the SQL to read from `vehicles`** (registry-based reading). Field name unchanged. Numbers go down sharply but are trustworthy.

2. **Rename the field to match the SQL** (history-based reading). Suggested: `plates_seen_today` (today-window from `entry_exit_log`) or `plates_seen_total` (lifetime from `parking_sessions`). The Angular team will relabel the dashboard tile to match the new name.

3. **Two fields, two meanings** (most informative): keep both. `total_unique_plates: int` from `vehicles`, plus `plates_seen_today: int` from `entry_exit_log` filtered to today. Frontend can render both as separate tiles or pick one.

Recommendation: **#3** (both fields). Removes the ambiguity entirely and lets product decide which to show.

**Acceptance:** `dashboard/kpis.total_unique_plates` matches `SELECT COUNT(DISTINCT plate_number) FROM vehicles` exactly.

---

### GA-3 — `/occupancy/kpis` and `/occupancy/totals` disagree

**Files:** `app/routers/occupancy.py` — the two SQL queries.

**The problem:** same garage, two endpoints, three-spot discrepancy:
- `/occupancy/kpis: total=32, available=14, occupied=18` (line-crossing source via `zone_occupancy.current_count`)
- `/occupancy/totals: total=32, available=17, occupied=15` (slot-status source via `parking_slots.is_available`)

The dashboard reads one, the Occupancy page reads the other. Adjacent UI tiles report different numbers.

**Required fix — pick one canonical source for the headline counts** (the `total_spots / occupied_spots / available_spots` triplet). Keep `OccupancyKPIs.slot_occupied_spots` as the explicit secondary signal — that's already the right pattern. Either:

1. **Make `/occupancy/kpis` use the same SQL as `/occupancy/totals`** (slot-status driven). The line-crossing reading remains exposed only via `/occupancy/floors[*].current_count` per floor.

2. **Or keep `/occupancy/kpis` line-crossing-driven and remove the contradicting fields from `/occupancy/totals`** — `/occupancy/totals` would just be a per-source breakdown card, not a drop-in replacement.

Recommendation: **#1** — slot-status is the more direct ground truth (a slot is or isn't occupied; line-crossing accumulates errors over time). The frontend has tentatively planned for `/occupancy/totals` to be the canonical headline source, so this aligns.

**Acceptance:** `/occupancy/kpis.occupied_spots == /occupancy/totals.occupied_slots` for every dataset.

---

### GA-4 — `/cameras/kpis.online` vs `by_status.online` disagree in the same response

**File:** `app/routers/cameras.py` — kpis SQL.

**The problem:** within one response body:
```json
{ "online": 0, "offline": 5, "by_status": {"unknown": 4, "online": 1} }
```
The headline says zero cameras online; the breakdown says one. DB direct: 1 camera has `last_status='online'`, 4 have `last_status IS NULL`.

**Required fix:** compute both from a single CASE expression. The likely current code uses two different SQL fragments — one is hitting an extra `is_online IS TRUE` derived check that's not catching the camera. Verify using:

```sql
SELECT
  SUM(CASE WHEN last_status = 'online' THEN 1 ELSE 0 END) AS by_status_online,
  SUM(CASE WHEN last_seen_at >= DATEADD(SECOND, -:online_threshold, GETUTCDATE())
           THEN 1 ELSE 0 END) AS is_online_threshold
FROM cameras;
```

If `by_status_online` and `is_online_threshold` differ, document which one drives the headline. Recommendation: align them — either drop the threshold check (let `last_status` be the source of truth) or recompute `last_status` whenever the threshold says offline.

**Acceptance:** `cameras/kpis.online == cameras/kpis.by_status.online` for every dataset.

---

### G-6 (extending the gateway's existing item) — populate `AlertItem` joined fields

**Files:** `app/routers/alerts.py:240-262` (list query) and any additional joins for `/alerts/{id}` detail.

**The problem (from a 20-row sample):** of 22 declared fields on `AlertItem`, these have null rates:

| Null rate | Fields |
|---|---|
| 100% | `vehicle_id`, `owner_name`, `vehicle_type`, `vehicle_event_id`, `triggering_camera_event_id`, `resolved_by`, `resolution_notes` |
| 95% | `slot_id`, `slot_name`, `floor`, `resolved_at` |
| 85% | `snapshot_url` |
| 40% | `plate_number` |

Plus on `/alerts/{id}` all five nested join objects (`vehicle`, `slot`, `camera`, `vehicle_event`, `related_alerts`) are returned as null/empty.

**Required fix:** extend the list query with `LEFT JOIN`s into:
- `vehicles` on `alerts.plate_number = vehicles.plate_number` → populate `vehicle_id`, `owner_name`, `vehicle_type`
- `parking_slots` on `alerts.slot_id = parking_slots.slot_id` (if alerts already carry `slot_id`) OR via `cameras → camera-floor → slot` lookup → populate `slot_name`, `floor`
- `cameras` is already on the row; `floor` can fall through from `cameras.watches_floor`

For `/alerts/{id}` detail, populate the five nested objects from the same joins.

**Note:** several of the fields (e.g. `resolved_by`, `resolution_notes`) presumably stay null until alerts are actually resolved with a note. That's fine — they're populated post-resolution. The 100%-null-pre-resolution rate is acceptable. The 95%-null fields are the real bug.

**Frontend impact:** alerts list's *Location* column reads `slot_name || floor || location || camera_id`. With G-6 populated, `slot_name` and `floor` will fire for the 95% of rows currently falling through to `location`/`camera_id`. The `/alerts/{id}` detail modal (Phase 7) will start showing real joined data instead of duplicating the list row.

**Acceptance:** rerun `/tmp/pms_audit.py` (the existing audit script, already in the venv-runnable form). The `null/empty fields (NN)` line for `/alerts/{id}` should drop from 19 to ≤5 (audit fields only).

---

### GA-5 — `entry_exit_log` and `parking_sessions` are written by **disjoint** code paths; the latter has no writer at all

**Files:**
- `Damanat-PMS-AI/app/routers/events.py:22-91` — the `/api/v1/events/camera` webhook, the only camera ingest path. Writes `entry_exit_log` (via `entry_exit_service.handle_anpr_event`) + `camera_events` + `floor_occupancy`. Never touches `parking_sessions`.
- `Damanat-PMS-AI/app/services/entry_exit_service.py:88-164` — the sole `EntryExitLog(...)` insert. No `parking_sessions` mention; the model isn't even imported.
- `Damanat-PMS-VideoAnalytics/src/services/slot_status_service.py:62-81` — when VA detects a slot transition it calls `pms_api_client.bind_slot_session(...)` / `unbind_slot_session(...)`.
- `Damanat-PMS-VideoAnalytics/src/services/pms_api_client.py:29-66` — those helpers POST to `/api/v1/internal/parking-sessions/bind-slot` and `/unbind-slot` on `PMS_API_URL`.
- `Damanat-PMS-AI/app/main.py:86-94` — registered routers: `events, occupancy, health, alerts, vehicles, entry_exit, parking_stats`. **There is no `parking_sessions` router.** Grep across the entire PMS-AI tree for `parking_sessions` finds it only in column comments on `app/models/entry_exit_log.py:25` and `app/models/alert.py:23`. There is **no `ParkingSession` SQLAlchemy model, no `INSERT INTO parking_sessions`, no router that maps to bind-slot/unbind-slot**. The VA POST hits a 404 and the URL-error is swallowed by `pms_api_client.py:25-26` (`print(...)` only).

**The problem:** the dashboard's `active_now = COUNT(*) FROM parking_sessions WHERE status='open'` and `plates_seen_today = COUNT(DISTINCT plate_number) FROM entry_exit_log WHERE event_time >= today_local_midnight_utc` (`API-Gateway/app/routers/dashboard.py:102-114`) are reading **two tables that are populated by zero overlapping code**. `entry_exit_log` is written by gate ANPR events; `parking_sessions` has no writer in source — the 15 rows visible are seed/manual data or were inserted by a tool that no longer exists. Schema confirms: `entry_exit_log.event_time` is `DATETIME2` UTC (`sql/bootstrap.sql:175`, written via `datetime.utcnow()` at `entry_exit_service.py:34,96`), so the dashboard SQL is correct — the data is stale.

This explains the audit numbers exactly: `plates_seen_today=0` (no ANPR webhook has fired today), `active_now=15` (legacy `parking_sessions` rows from before — not overnight stays, just orphaned). The two columns will diverge forever until someone implements the bind/unbind endpoints **or** rewires `entry_exit_service` to also open/close `parking_sessions` rows in the same transaction.

**Direct DB confirmation:**
```sql
-- 1. Are the parking_sessions rows actually fresh? (expected: oldest entry_time is days+ old)
SELECT MIN(entry_time) AS oldest_open, MAX(entry_time) AS newest_open, COUNT(*) AS open_n
FROM parking_sessions WHERE status = 'open';

-- 2. Has entry_exit_log received anything today? (expected: 0 today, plenty historical)
SELECT COUNT(*) AS today_n,
       (SELECT COUNT(*) FROM entry_exit_log) AS total_n,
       MAX(event_time) AS last_event
FROM entry_exit_log
WHERE event_time >= CAST(GETUTCDATE() AS DATE);

-- 3. Cross-check: do the 15 "active" plates have any matching entry_exit_log row? (expected: most don't)
SELECT ps.plate_number,
       (SELECT COUNT(*) FROM entry_exit_log e
         WHERE e.plate_number = ps.plate_number AND e.gate = 'entry') AS entry_log_count
FROM parking_sessions ps
WHERE ps.status = 'open';
```

**Required fix — pick one (in order of preference):**

1. **Owner action — implement the missing endpoint in PMS-AI** (correct fix, blast radius outside the gateway). Add a `parking_sessions` router on `/api/v1/internal/parking-sessions/{bind-slot,unbind-slot}` that opens/updates a session row when VA reports a slot transition. Same router should be called from `entry_exit_service.handle_anpr_event` so a gate-entry event also opens an unbound session that VA later attaches a slot to. Wrap both writes in the same `db` transaction the existing webhook already manages (`events.py:78`). Until this ships, the dashboard `active_now` is unreliable.

2. **Gateway-side defensive read — derive `active_now` from `entry_exit_log` instead** (workaround, no PMS-AI change). Replace the dashboard SQL with `COUNT(DISTINCT plate_number) FROM entry_exit_log WHERE id IN (latest entry per plate AND gate='entry' AND no later exit)`. Same logic the frontend already wants for `is_currently_parked` per GA-2. Aligns the two KPIs against a single, actively-written table.

3. **Stop reading `parking_sessions` for any KPI until it has a writer** (escalation). Mark `active_now` as deprecated, fall back to `/occupancy/totals.occupied_slots` for the headline, and document that "active vehicles" = "currently-occupied slots" until session tracking is wired up.

Recommendation: **#1** (real fix) tracked in PMS-AI; **#2** (gateway workaround) shipped immediately so the dashboard becomes self-consistent today.

**Acceptance:**
- After #1: a freshly-fired ANPR entry event causes `plates_seen_today` to increment within 1s, and a VA slot-occupied event causes `active_now` to increment within 1s. Both tables stay in lock-step.
- After #2 (interim): `dashboard/kpis.active_now == COUNT(DISTINCT plate_number) FROM entry_exit_log e WHERE e.gate='entry' AND NOT EXISTS (SELECT 1 FROM entry_exit_log x WHERE x.plate_number=e.plate_number AND x.gate='exit' AND x.event_time > e.event_time)`.

---

## Verification — the audit script

The Angular team uses `/tmp/pms_audit.py` (runnable from the gateway's venv) to detect drift end-to-end. After your fixes, run it and confirm:

```bash
"/Users/ahmedalaa/Work/Spectech/Projects/Parking System/API-Gateway/.venv/bin/python" /tmp/pms_audit.py
```

Pass criteria:
- `total_unique_plates`: **OK** (was DRIFT 15 vs 4) — GA-1
- `/vehicles/?is_currently_parked=true total_count > 0` — GA-2
- `/occupancy/kpis.occupied_spots == /occupancy/totals.occupied_slots` — GA-3
- `cameras/kpis.online == cameras/kpis.by_status.online` — GA-4
- `/alerts/{id}` null fields ≤ 5 (down from 19) — G-6

The audit script is fine as-is — don't move it into the repo unless you want to; it's a working scratch tool.

---

## What the frontend will do after each fix

| Gateway fix | Frontend follow-up |
|---|---|
| GA-2 | Un-revert `loadActiveVehicles` to call `getActiveParkedVehicles({page_size: 20})` (Phase 20). |
| GA-1 | If you go with option #3 (two fields), Angular adds a second tile or picks one to show. If you go with #1/#2, frontend keeps the existing tile binding. |
| GA-3 | Frontend may drop one of `/occupancy/kpis` or `/occupancy/totals` calls if they become redundant. Until then both are read for resilience. |
| GA-4 | No frontend change — the headline `online` field starts being correct. |
| G-6 | Phase 7's alert detail modal lights up. Frontend will *also* trim the `slot_name || floor || location || camera_id` fallback chain since `slot_name`/`floor` will start being populated. |

---

## Order of operations the Angular team prefers

1. **GA-2 first** (release blocker). Frontend can then un-revert Phase 15.
2. **GA-3** + **GA-4** (internal contradictions). Both are quick SQL fixes; together they remove the two "same screen, different numbers" bugs.
3. **GA-1** (semantics decision). Needs product input; can come last.
4. **G-6** (alert joins). Already on your existing punch list; ship at your pace.

---

## Out of scope for the gateway team

The frontend is handling these without gateway help:
- Alerts list *Location* fallback chain extension (uses your existing `location` field).
- Reconciliation drift badge per floor (uses your existing `reconciled` + `slot_occupancy_count` fields).
- Standardizing on one occupancy source (frontend picks `/occupancy/totals` regardless of GA-3's outcome — the GA-3 fix just removes the contradiction at the source).

---

## Anything you find that I missed

If during the work you find related issues — e.g. another field with confused semantics, another endpoint with internally-contradictory fields — flag it in the PR description. The Angular team's `yarn gen:api` codegen tripwire will catch any contract surprise on the next `ng build`, so we'll see it eventually, but a heads-up is appreciated.
