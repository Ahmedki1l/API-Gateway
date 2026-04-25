# Gateway service: modifications required

> **Revision history**
> - v1 (initial audit): 17 findings across the gateway routers + schemas.
> - v2 (this revision, 2026-04-25): re-validated against the current source after the recent Frontend Enhancements + DTO refactor work. Each finding is now stamped **OPEN / RESOLVED / PARTIAL / OUTDATED**. New findings discovered during the re-audit appear at the bottom (G-18 onward). A concrete execution plan is included as Part B.

---

## Context

The API Gateway (System 3, FastAPI on `:8001`) is the only API the Angular frontend talks to. An audit of the live OpenAPI surface against the gateway source — `app/routers/*.py`, `app/schemas.py`, `app/database.py` — turned up a set of contract bugs and quality issues that are independent of any one consumer. This document is the gateway team's punch list.

Findings are bucketed by severity. Each item names the file, line range, the exact problem, the fix, and the acceptance check.

A companion document covering the Angular client's integration drift lives at `Synitera.PS/angular/INTEGRATION_AUDIT.md`.

---

## Part A — Audit Findings (re-validated)

### P0 — release blockers

#### G-1. `GET /occupancy/zones` mutates the database on every read — **OPEN**
**File:** `app/routers/occupancy.py:95-125`
**What it does:** recomputes B1/B2/total slot counts from `parking_slots` and writes them back into `zone_occupancy.max_capacity` for `B1-PARKING` / `B2-PARKING` / `GARAGE-TOTAL`, then commits, then returns the page.
**Why it's broken:**
- HTTP GET is required to be idempotent. This isn't.
- Two concurrent calls race on the UPDATE.
- A CDN, a `fastapi-cache` decorator, or even browser back-forward cache silently breaks the sync.
- The new `/occupancy/floors` endpoint already computes these counts on the fly via `_build_floor_occupancy()` — the GET-side write is now strictly redundant.

**Fix:** delete the `UPDATE zone_occupancy SET max_capacity = ...` statements from `get_zones`. If max_capacity needs to be persisted (it doesn't — `_build_floor_occupancy` reads `parking_slots` live), do it via a background task or an explicit `POST /occupancy/sync-capacity` admin endpoint. The GET handler does only a read. `/occupancy/zones` itself is already deprecated in favor of `/occupancy/floors` (Phase 4C removes it).

**Accept:** wrap the route in a read-only DB session for one release; observe the logs for blocked-write attempts; confirm none.

---

#### G-2. `GET /alerts/stream` payload contradicts its declared schema — **OPEN**
**File:** `app/routers/alerts.py:156-175` (`_normalize_stream_event`), `app/schemas.py:207-210` (`AlertStreamEvent`).

**What's wrong:** `AlertStreamEvent` extends `AlertItem` (22 fields). `_normalize_stream_event` emits 12: `id, source_system, alert_type, severity, slot_id, slot_name, plate_number, camera_id, floor, snapshot_url, timestamp, is_alert`. The other 10 (`event_type, vehicle_id, vehicle_event_id, triggering_camera_event_id, owner_name, vehicle_type, description, location, resolved_at, is_resolved, resolved_by, resolution_notes`) are documented as part of the stream but never sent. Also: schema has `triggered_at`; stream sends `timestamp`.

**Fix:** keep the lean stream event and create a dedicated `AlertStreamEventLite` schema with the actual 12 fields. Reserve `AlertStreamEvent` for an enriched stream variant only if/when needed. Rename the wire field from `timestamp` → `triggered_at` so it matches `AlertItem.triggered_at`.

**Accept:** an `EventSource` consumer that destructures every field on `AlertStreamEventLite` finds no `undefined`s.

---

#### G-3. Endpoints with no `response_model=` — **PARTIAL** (8 of 21 are real gaps)
**Total endpoints lacking `response_model`:** 21. Of those, 13 are legitimately schema-less (CSV downloads, SSE stream, OpenAPI/docs internals, `/health`, test endpoints). **8 real gaps remain:**

| Method | Path | File:line |
|---|---|---|
| POST | `/vehicles/` | `vehicles.py:96` |
| PUT | `/vehicles/{vehicle_id}` | `vehicles.py:298` |
| DELETE | `/vehicles/{vehicle_id}` | `vehicles.py:331` |
| PATCH | `/alerts/{alert_id}/resolve` | `alerts.py:512` |
| DELETE | `/alerts/{alert_id}` | `alerts.py:524` |
| DELETE | `/cameras/{camera_id}` | `cameras.py:310` |
| GET | `/occupancy/slots` | `occupancy.py:208` |
| GET | `/occupancy/slots/by-floor` | `occupancy.py:553` |

**Fix:** introduce two trivial schemas:
```python
class SuccessResponse(BaseModel):
    success: bool = True

class EntityActionResponse(BaseModel):
    """For DELETE/PATCH that return the entity ID alongside the success flag."""
    success: bool = True
    id: int | str
```
- `POST /vehicles/` and `PUT /vehicles/{id}`: return the full entity (`response_model=VehicleListItem`). **Stop returning a hybrid** — currently each branches between `created[0]` (raw dict) and `{"success": True}`. Pick one shape.
- `DELETE` and `PATCH /resolve` endpoints: `response_model=EntityActionResponse`.
- `GET /occupancy/slots`: `response_model=PagedResponse[SlotDetail]`.
- `GET /occupancy/slots/by-floor`: define a small `FloorSlotGroup{floor: str, slots: list[SlotDetail]}` and return `list[FloorSlotGroup]`.

**Accept:** `/openapi.json` shows a non-empty `responses["200"].content` for every CRUD route.

---

#### G-4. `GET /occupancy/slots` is two endpoints in one URL — **OPEN**
**File:** `app/routers/occupancy.py:208-292` (the `grouped` parameter at line 214).

**What it does:** when `?grouped=true` returns `list[{"floor": str, "slots": list[dict]}]`; when `?grouped=false` returns `PagedResponse[dict]`. No `response_model=`.

**Why it's broken:**
- OpenAPI cannot represent the union; clients see no response schema.
- TypeScript codegen produces `any | any[]`.
- `/occupancy/slots/by-floor` already exists at line 553 with the grouped shape — `/slots?grouped=true` duplicates it.

**Fix:** delete the `grouped` query param. Direct grouped consumers to `/occupancy/slots/by-floor`. `/occupancy/slots` becomes strictly paginated and gets `response_model=PagedResponse[SlotDetail]` (item G-3 covers this part).

**Accept:** `?grouped=true` returns 422; `/occupancy/slots/by-floor` is still the way to get the grouped form.

---

#### G-5. `GET /cameras` `total_count` lies when filters are used — **OPEN**
**File:** `app/routers/cameras.py:148-204` (Python-side filtering at lines 198-202).

**What it does:** `role`, `watches_floor`, `is_online` filters are applied in Python *after* the SQL `OFFSET / FETCH NEXT`. The page returns `total_count` from the DB query (un-filtered) and `items` filtered. Result: page 1 shows 2 items but the UI displays "1-2 of 100".

**Fix:**
- `role` and `watches_floor` are now real DB columns after Phase 4A's `schema_v2_additive.sql` ran. Push them into the SQL `WHERE` clause.
- `is_online` is computed from `last_seen_at` and the monitor interval; encode the same threshold as a SQL `CASE WHEN last_seen_at >= DATEADD(SECOND, -:threshold, GETUTCDATE()) THEN 1 ELSE 0 END` so it's filterable. If the threshold is dynamic from settings, pass it as a parameter.

**Accept:** `total_count == sum(items.length over all pages)` for any filter combination.

---

### P1 — credibility

#### G-6. `AlertItem` declares 8 fields the SQL never selects — **OPEN**
**File:** `app/schemas.py:180-204` (declares 22 fields), `app/routers/alerts.py:240-262` (the list query).

**The gap:** declared on `AlertItem`, never selected in `/alerts/`: `event_type`, `camera_id`, `vehicle_id`, `vehicle_event_id`, `triggering_camera_event_id`, `floor`, `resolved_by`, `resolution_notes`. All `Optional`, so they return `null`.

**Fix:** decide per field — populate (extend the SELECT) or remove. Recommended:
- **Populate:** `camera_id` (already on the row), `event_type`, `floor` (via parking_slots join). All user-visible.
- **Populate via Phase 4A audit columns:** `vehicle_id`, `vehicle_event_id`, `triggering_camera_event_id`, `resolved_by`, `resolution_notes` if Phase 4A migration has run on the target DB. Otherwise fall back to NULL (the columns may not exist yet).

**Accept:** `AlertItem` in `schemas.py` lists only fields actually present in the SELECT; or, equivalently, every nullable field has an SQL source.

---

#### G-7. `EntryExitKPIs.total_vehicles_today` field name — **DEFERRED** (intentionally renamed in last cycle)
**File:** `app/schemas.py:228-232`.

**Original audit recommendation:** rename `total_vehicles_today` → `total_vehicles` for consistency with the other 3 KPI endpoints.

**Recent decision:** during the Frontend Enhancements work (Item 2 in the latest user request set), this field was deliberately renamed *to* `total_vehicles_today` to match the actual response key. Reverting it now would cause yet another break.

**Resolution:** **defer** the rename. If consistency across the four KPI endpoints is the goal, rename the field on the OTHER three KPIs (`VehicleKPIs.total_vehicles`, `OccupancyKPIs.total_vehicles`) to `total_vehicles_today` *if* they are also "in the date window" semantics. Otherwise leave as-is — the suffix is documenting a real semantic difference.

**Accept:** N/A this cycle.

---

#### G-8. `VehicleEvent.slot_number` declared but never populated — **RESOLVED** (verified)
**File:** `app/schemas.py:165` (declared), `app/routers/entry_exit.py:289-290` (the SELECT).

**Current state:** the SELECT now includes BOTH `COALESCE(pk.slot_name, ps.slot_number) AS slot_name` AND `ps.slot_number` as separate columns. `_event_from_row` (line 63) populates `slot_number` from the dict.

**Action:** none.

---

#### G-9. `SlotOccupancy.snapshot_url` declared, never populated — **OPEN**
**File:** `app/schemas.py:363` (declared `snapshot_url: Optional[str]`), `app/routers/occupancy.py:614-645` (the dict-build).

**Current state:** the `current` dict in `get_slot_detail` sets `state, plate_number, vehicle_id, vehicle_event_id, since, last_seen_at` — no `snapshot_url`.

**Fix:** in the open-event lookup (line 622), additionally `SELECT TOP 1 entry_snapshot_path` from `parking_sessions` (or `slot_snapshot_path` if more relevant) and add it to the `current` dict as `snapshot_url`. Or remove `snapshot_url` from the `SlotOccupancy` schema.

**Accept:** the slot detail page shows a thumbnail when a vehicle is currently in the slot.

---

#### G-10. Inline DTO `VehicleEventDetail` in router — **OPEN**
**File:** `app/routers/entry_exit.py:479-486`.

**Why:** the only inline DTO in the gateway codebase. Limits `from app.schemas import VehicleEventDetail` for downstream callers and OpenAPI codegen consumers.

**Fix:** move the class to `schemas.py` (next to `VehicleEvent`).

**Accept:** `from app.schemas import VehicleEventDetail` works.

---

#### G-11. Test endpoints reachable in production — **OPEN**
**File:** `app/routers/alerts.py:354-365` — `/alerts/test/start`, `/alerts/test/stop`.

**Why:** anyone who finds `/docs` can flood the dashboard with synthetic alerts.

**Fix:** gate behind the `X-Internal-Token` header (the same one `/cameras/internal/all` and `/cameras/{id}/credentials` already use). One line: add `_: None = Depends(require_internal_token)` to both endpoints.

**Accept:** prod build returns 401 on these URLs without the header; dev build with the token still serves.

---

#### G-12. Dead schemas — **OPEN**
**File:** `app/schemas.py` — `FloorDetail` (line 383), `CameraDetail` (line 427), `VehicleWithEvents` (line 241).

**Why:** never wired to any endpoint. Adds noise to OpenAPI; misleads consumers.

**Fix per class:**
- `VehicleWithEvents`: removed from `entry_exit.py` imports (verified). Schema class can be deleted unless slated for the (proposed) `GET /entry-exit/by-vehicle/{id}/grouped` endpoint — but that endpoint isn't planned.
- `FloorDetail`: extends `FloorOccupancy` with `slots[]`, `current_vehicles[]`, `recent_alerts[]`. Wire it as the response model for `GET /occupancy/floors/{floor}` (currently returns `FloorOccupancy`). Add the `slots[]` join in the handler.
- `CameraDetail`: extends `CameraItem` with `recent_events[]`, `stats`. Wire as the response model for `GET /cameras/{camera_id}` if those enrichments are wanted; otherwise delete.

**Accept:** a grep for the type name in `app/` returns at least one non-definition reference, OR the class is deleted.

---

#### G-13. Field-aliasing inconsistencies — **OUTDATED** for the Gateway side
**Locations:** `validation_alias=` was a Phase 3 transitional shim in PMS-AI / VA — confirmed zero `validation_alias` usages in `API-Gateway/app/`. Per `PHASE_4C_CLEANUP_CHECKLIST.md`, these come out of the upstream services in Phase 4C.

**The remaining concern in Gateway:** the `snapshot_path` → `snapshot_url` rename is done via SQL `AS snapshot_url` aliases (already centralized; see `routers/alerts.py:250` and `routers/camera_feeds.py:80`). Other column renames are done in the Python dict-build layer. **One pattern, applied consistently** would be cleaner. Low priority — the SQL-alias approach works.

**Action:** none this cycle. Track in `PHASE_4C_CLEANUP_CHECKLIST.md`.

---

### P2 — quality of life

#### G-14. `_BOOL_COLUMNS` coercion is centralized — **RESOLVED** (document the pattern)
**File:** `app/database.py:37-50`.

**Current state:** good pattern (frozenset of column names → bool coercion in `rows()`). Already used for `is_employee, is_resolved, is_violation_zone, is_available, enabled, is_online, has_password, is_test, is_currently_parked, is_alert, is_registered`.

**Action:** add a 3-line module docstring at the top of `database.py` explaining the pattern so future contributors don't reinvent it elsewhere.

---

#### G-15. Boolean coercion list completeness — **OPEN** (verify on schedule)
**Action:** when adding a new boolean SELECT column, also add it to `_BOOL_COLUMNS`. Add a CI check (or a pre-commit grep): for every `is_*` or `enabled`/`has_*` column referenced in `app/routers/*.py`, confirm it's in `database.py:_BOOL_COLUMNS`.

---

#### G-16. Documentation lag — **OPEN**
**File:** `CLAUDE.md`.

**Missing topics:**
- The `cameras` table (Phase 4A) and its `role` / `watches_floor` / `watches_slots_json` columns.
- The credentials encryption (`CAMERAS_ENCRYPTION_KEY`) + `X-Internal-Token` system.
- The camera liveness monitor (`camera_monitor.py` + the four `CAMERA_MONITOR_*` env vars).
- The canonical `/occupancy/floors`, `/occupancy/floors/{floor}`, `/occupancy/totals`, `/occupancy/slots/{slot_id}`, `/occupancy/slots/by-floor` endpoints.
- The `slot_occupied_spots` dual-source signal in `OccupancyKPIs`.
- The DB connection's `Trusted_Connection=Yes` Windows-Auth fix (`config.py:38-49`) and the localhost-regex CORS allowance (`main.py:30`).
- The `camera_feeds` table introspection fallback (`camera_feeds.py:13`).

**Fix:** one PR-sized update to `CLAUDE.md`. Match the structure of the existing file.

---

#### G-17. CSV export endpoints accept different filter sets than the list endpoints — **OPEN** (audit)
**Files:** the four `/x/export/csv` routes (alerts, vehicles, entry-exit, occupancy) and one `/x/export` (occupancy).

**Action:** for each, list the params the list endpoint accepts vs the CSV endpoint, and either align them or document the divergence. Drift produces CSVs that don't match the on-screen filtered view.

---

### New findings discovered during re-audit

#### G-18. `VehicleEvent` has the slot's snapshot but not VA's CV-derived per-slot snapshot — **NEW, P2**
**File:** `app/schemas.py:140-170`, `app/routers/entry_exit.py:25-67`.

**The gap:** `VehicleEvent.slot_snapshot_url` is populated from `parking_sessions.slot_snapshot_path` — the snapshot taken when the vehicle parked. There's no field for *the most recent* slot snapshot (which is what the dashboard wants to display in the "currently in slot" tile). They're different images: parked-at vs. live-now.

**Action:** if needed, add `current_slot_snapshot_url` to `SlotOccupancy` (not `VehicleEvent`) — populated from the slot's most recent `slot_status` row's image URL. Defer until the frontend asks.

---

#### G-19. `/cameras/{id}/check-now` ignores cached `is_online` — **NEW, P2**
**File:** `app/routers/cameras.py:286-291`.

**Current:** the endpoint always performs a fresh TCP probe even if the camera was checked < 1s ago. Fine for one-off use, but if a frontend dashboard maps "refresh all cameras" → loops over this endpoint, it can swamp the gateway and the cameras.

**Action:** add a `?force=false` default; only re-probe if `now - last_check_at > camera_monitor_interval_seconds`. Frontend that needs an immediate fresh probe passes `?force=true`.

---

#### G-20. `/dashboard/active-vehicles` is now redundant with `/vehicles/?is_currently_parked=true` — **NEW, P1**
**File:** `app/routers/dashboard.py:60-103`, `app/routers/vehicles.py:135-225`.

**Current state:** after Item 6 of the recent enhancements, `/vehicles/?is_currently_parked=true` returns the same logical set as `/dashboard/active-vehicles` — and *more accurately*, because it includes unregistered plates (the dashboard endpoint silently misses them when there's no `vehicles` row).

**Action:**
- **Option A:** mark `/dashboard/active-vehicles` deprecated (`@router.get(..., deprecated=True)`); keep it serving for one release; remove later. Update the frontend to call `/vehicles/?is_currently_parked=true&page_size=N`.
- **Option B:** keep the endpoint but change its body to internally call the `/vehicles/` query, so both endpoints emit the same row count.

Recommendation: **A**.

---

#### G-21. CTE in `/vehicles/` list query may need SQL Server `WITH` qualifier — **NEW, P1** (verify on real DB)
**File:** `app/routers/vehicles.py:172-187` (the new `WITH all_plates AS ...` CTE).

**Concern:** SQL Server requires CTEs to be the FIRST statement in a batch, and previous statements in the same batch (e.g. a SET option) must end with `;`. The `text(...)` block is the only statement, so this should be fine — but verify on a live SQL Server and pymssql/pyodbc + SQLAlchemy combo. If broken, rewrite as a derived table inline.

**Action:** smoke-test against the user's running DB; if it errors, refactor to:
```sql
SELECT v.id, ap.plate_number, ...
FROM (
    SELECT plate_number FROM dbo.vehicles
    UNION
    SELECT DISTINCT plate_number FROM dbo.parking_sessions WHERE plate_number IS NOT NULL
) ap
LEFT JOIN dbo.vehicles v ON v.plate_number = ap.plate_number
...
```

**Accept:** `GET /vehicles/` returns 200 with both registered and unregistered plates against a live DB.

---

#### G-22. SSE stream re-subscribes leak when the client doesn't gracefully close — **NEW, P2**
**Symptom in the user's logs:** repeated `Bus sub: 1 total` / `Bus unsub: 0 remains` cycles, and several `[upstream] SSE stream ended for /api/alerts/stream` log lines per minute. The pump tasks are getting cancelled correctly, but each new SSE subscription opens TWO upstream SSE connections (one to PMS-AI, one to VA), neither of which is reachable in the user's dev setup, so they retry-fail in a tight loop.

**Action:** add an upstream-side circuit breaker. If an upstream SSE pump fails 5 times in 30s, back off for 60s before re-trying. Today the failure is silent and the gateway does ~20 connection attempts/minute against unreachable hosts.

---

## Part B — Execution Plan

Three PRs, sequenced. Each is independently shippable; PR boundaries are chosen so the frontend coordinates only on PR 3.

### PR 1 — Housekeeping (no frontend coordination)

| # | Item | Effort | Risk |
|---|---|---|---|
| G-3 | Add `SuccessResponse` / `EntityActionResponse` schemas; wire `response_model=` on the 8 missing CRUD endpoints | 2h | Low |
| G-10 | Move `VehicleEventDetail` from `entry_exit.py` into `schemas.py` | 10m | Low |
| G-11 | Gate `/alerts/test/{start,stop}` behind `X-Internal-Token` | 15m | Low |
| G-12 | Either wire `FloorDetail` / `CameraDetail` into their detail endpoints, or delete; delete `VehicleWithEvents` | 1h | Low |
| G-14 | Add a docstring to `app/database.py` documenting the `_BOOL_COLUMNS` pattern | 5m | Low |
| G-16 | Update `CLAUDE.md` with the missing topics | 1h | Low |
| G-21 | Smoke-test the new `/vehicles/` CTE against the live DB; rewrite as derived table if it errors | 30m | Low–Med |

**Total:** ~5h. Ships first.

### PR 2 — Bug fixes (additive, non-breaking)

| # | Item | Effort | Risk |
|---|---|---|---|
| G-1 | Remove the `UPDATE zone_occupancy` writes from `GET /occupancy/zones`; let `_build_floor_occupancy` compute live | 1h | Med (verify nothing depends on persisted max_capacity) |
| G-5 | Push `role` / `watches_floor` filters into SQL; encode `is_online` as a SQL CASE; restore correct `total_count` | 1h | Low |
| G-6 | Extend `/alerts/` SELECT to populate `camera_id`, `event_type`, `floor`, audit columns; or remove dead schema fields | 1.5h | Low |
| G-9 | Populate `SlotOccupancy.snapshot_url` from the open vehicle event | 30m | Low |
| G-15 | CI check that every `is_*`/`enabled`/`has_*` column reference is in `_BOOL_COLUMNS` | 30m | Low |
| G-17 | Audit + align CSV export filter parity | 1h | Low |
| G-19 | Add `?force=false` default to `/cameras/{id}/check-now` | 15m | Low |
| G-22 | Upstream SSE backoff (5 failures / 30s → 60s pause) | 1h | Low |

**Total:** ~7h. Ships after PR 1 has been verified.

### PR 3 — Breaking changes (frontend coordinates)

| # | Item | Effort | Risk | Frontend impact |
|---|---|---|---|---|
| G-2 | Introduce `AlertStreamEventLite`; rename `timestamp` → `triggered_at` in the SSE wire payload | 1h | High | UI listener must update field names |
| G-4 | Delete `?grouped` query param from `/occupancy/slots`; `/occupancy/slots/by-floor` is the canonical grouped endpoint | 30m | High | UI must switch URLs |
| G-20 | Mark `/dashboard/active-vehicles` deprecated; the dashboard card switches to `/vehicles/?is_currently_parked=true` | 30m | High | UI must switch URLs |

**Total:** ~2h gateway work + frontend pairing. Ships after PR 2 verification.

### Verification (gateway-side, after each PR)

1. `python run.py` from `API-Gateway/` → `/openapi.json` resolves; `/docs` is reachable.
2. **For every newly-wired `response_model=`**, the OpenAPI spec's `responses["200"].content` is non-empty.
3. `curl http://localhost:8001/cameras?role=ENTRY` returns a `total_count` consistent with the items the user can paginate through (G-5).
4. `curl http://localhost:8001/occupancy/zones` against SQL Server's audit log: zero `UPDATE zone_occupancy` rows in the last call (G-1).
5. `curl -N http://localhost:8001/alerts/stream` from a connected EventSource client: every emitted event's keys match `AlertStreamEventLite` exactly (G-2).
6. `curl http://localhost:8001/vehicles/?is_currently_parked=true` returns the same plate set as `/dashboard/active-vehicles` (or `/vehicles/?is_currently_parked=true` returns a *superset* including unregistered plates — see G-20).
7. The `TestClient`-based harness (see `scratch/`) passes with no exceptions and no 5xx.

---

## Part C — Files referenced

- `app/main.py:27-37` (CORS), `app/database.py:37-50` (bool coercion), `app/schemas.py` (full)
- `app/routers/dashboard.py:60`
- `app/routers/alerts.py:156-175, 240-262, 354, 365, 512, 524`
- `app/routers/entry_exit.py:25-67, 220, 280-310, 390, 479-486, 590`
- `app/routers/occupancy.py:95-125, 208-292, 488-555, 588-645`
- `app/routers/vehicles.py:96, 135, 172-225, 298, 331, 348-440`
- `app/routers/cameras.py:148-204, 270, 286, 310`
- `app/routers/camera_feeds.py:13, 36`
- `sql/bootstrap.sql`
- Existing companion docs at the workspace root: `DTO_CATALOG.md`, `DTO_ALIGNMENT.md`, `DTO_REFACTOR_PLAN.md`, `PHASE_4C_CLEANUP_CHECKLIST.md`, `GATEWAY_FRONTEND_ISSUES.md`. Several P1/P2 items overlap with cleanup work already scheduled there — the issues here are *additional*, not duplicates.

---

## Status snapshot

PR 1 (G-3, G-10, G-11, G-12, G-14, G-16, G-21), PR 2 (G-1, G-5, G-6, G-9,
G-13, G-15, G-17, G-18, G-19, G-22), and PR 3 (G-2, G-4, G-20) have been
landed in the gateway. G-7 and G-8 were already resolved before this audit.

| Severity | Open | Resolved | Outdated | Deferred | Total |
|---|---|---|---|---|---|
| **P0** | 0 | 5 (G-1, G-2, G-3, G-4, G-5) | 0 | 0 | 5 |
| **P1** | 0 | 7 (G-6, G-8, G-9, G-10, G-11, G-12, G-20) | 1 (G-13) | 1 (G-7) | 9 |
| **P2** | 0 | 8 (G-14, G-15, G-16, G-17, G-18, G-19, G-21, G-22) | 0 | 0 | 8 |
| **Total** | **0** | **20** | **1** | **1** | **22** |

**Time estimate (original):** 14 engineer-hours total across 3 PRs. **Actual:**
all 3 PRs landed in this session. Frontend now needs to coordinate PR 3's
breaking changes — see "PR 3 frontend changes required" below.

### PR 3 frontend changes required

After deploying this gateway, the frontend must:

1. **Alerts SSE consumer** — read `evt.triggered_at` instead of `evt.timestamp`
   (the JSON SSE payload renamed the field; the backing schema is now
   `AlertStreamEventLite`). The `connection_established` keep-alive frame
   uses the same field.
2. **Slots grid** — if the UI used `GET /occupancy/slots?grouped=true`, switch
   to `GET /occupancy/slots/by-floor` (returns `list[FloorSlotGroup]`). The
   plain `GET /occupancy/slots` is now always paginated
   (`PagedResponse[SlotListItem]`); the `grouped` query param is no longer
   read.
3. **Active-vehicles dashboard card** — `GET /dashboard/active-vehicles` is
   marked deprecated. Switch to `GET /vehicles/?is_currently_parked=true`,
   which returns the same vehicles in the canonical paged envelope with
   filter and CSV-export support. The deprecated endpoint will be removed
   in Phase 4C.
