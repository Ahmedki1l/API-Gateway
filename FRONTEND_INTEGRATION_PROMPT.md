# Frontend integration prompt — production-level audit + adoption

**Purpose:** brief the Angular team (or an AI agent) with everything they need to consume the gateway at production quality. **Read top to bottom**, then execute the "Required tasks" list in order. The audit script `/tmp/pms_audit.py` (runs in the gateway venv against `localhost:8001`) is the canonical pass/fail gate for the gateway-side acceptance criteria; your equivalent for the frontend is the `yarn gen:api` codegen tripwire + the Cypress smoke run.

---

## 0. Context

The gateway (`http://<host>:8001`, FastAPI on Python 3.11) is the **only** API the frontend talks to. It sits between you and two private upstreams (PMS-AI on :8080, VideoAnalytics on :8000) and reads the shared SQL Server `damanat_pms` directly.

Recently shipped on the gateway main branch:

- PR 1 (housekeeping), PR 2 (bug fixes), PR 3 (breaking changes, "G-x" in audit doc)
- WS-A frontend-audit hotfix bundle (GA-1 to GA-4 + G-6 extension)
- WS-1 (VA centralized creds — transparent to FE), WS-2 (CI gate — infra), WS-7 (timezone setting + VA stalled-frame watchdog — transparent to FE), WS-7-doc (workspace `CLAUDE.md`)
- **WS-8 floor + slot-PK refactor — Phase 1 (additive)**: every endpoint that returns or accepts `floor` now also surfaces `floor_id` (integer). Both keys live side-by-side; integer wins when both are sent. Schemas extended with `id` on `SlotRef`/`FloorOccupancy` and `watches_floor_id` on `CameraRef`/`CameraCreate`/`CameraUpdate`. **No breaking change** — string `floor` keeps working.

Open issue you must work around:

- **GA-5** — `parking_sessions` has **no writer in any of the three services**. `/dashboard/kpis.active_now` and the `is_currently_parked` filter rely on it. In production data, both will read whatever stale rows are in the table (today: 15 seed rows). Treat both as "best-effort" until PMS-AI ships the missing `/internal/parking-sessions/{bind,unbind}-slot` endpoints. See §"Known issues" below for the recommended UI mitigation.

## 1. Required reading (in order)

1. `API-Gateway/GATEWAY_PROMPT_FROM_FRONTEND_AUDIT.md` — audit findings GA-1 to GA-5, plus the "hard constraints" list of locked-in shapes.
2. `API-Gateway/GATEWAY_MODIFICATIONS_REQUIRED.md` — the 22 G-x audit items and their resolution.
3. `EXECUTION_PLAN.md` (workspace root) — the cross-service sequencing of WS-A through WS-8, including the post-Phase-4C cleanup that strips temporary back-compat shims.
4. `DTO_REFACTOR_PLAN.md` (workspace root) — the target domain model (zones removed, only floors + slots).
5. `PHASE_4C_CLEANUP_CHECKLIST.md` (workspace root) — the list of validation_alias shims and deprecated routes that get removed after one production release of soak.

## 2. Hard constraints — DO NOT regress

If you change any of these you'll force a rollback:

- **`EntryExitKPIs.total_vehicles_today`** stays as-is (G-7 deferred-by-design — the `_today` suffix carries semantic weight).
- **`AlertStreamEventLite`** SSE schema is canonical: 12 fields, wire field is `triggered_at` (not `timestamp`). Don't add or remove fields. WS-8 added `floor_id` to it; that's the only addition.
- **Endpoint shapes shipped in PR 3 are locked**:
  - `GET /entry-exit/by-vehicle/{vehicle_id}` → `PagedResponse[VehicleEvent]`
  - `GET /entry-exit/{event_id}` → `VehicleEventDetail` (joined `vehicle`, `slot`, `entry_camera`, `exit_camera`, `alerts`)
  - `GET /occupancy/slots/by-floor` → `list[FloorSlotGroup]`
  - `GET /occupancy/slots/{slot_id}` → `SlotDetail`
  - `GET /vehicles/?is_currently_parked=true` → `PagedResponse[VehicleListItem]`
- **`FloorOccupancy`** retains every existing field. WS-8 added `id: int` and `floor_id: int` (same value, intentional symmetry); the legacy fields (`floor`, `max_capacity`, `current_count`, `available`, `utilization`, `data_source`, `last_updated`, `camera_id`, `slot_occupancy_count`, `slot_occupancy_source`, `reconciled`) all stay.
- **`/dashboard/active-vehicles`** is `deprecated=True` but **must keep working** until you re-migrate off it (per GA-2 + WS-5 in `EXECUTION_PLAN.md`).
- **Canonical wire field names** the gateway emits: `snapshot_url` (not `snapshot_path`), `slot_name` (not `zone_name`), `triggered_at` (not `timestamp`).

## 3. Required tasks — release blockers

Order matters. Each task has a one-line acceptance criterion you can plug into Cypress / your codegen tripwire.

### T1. Adopt the new `floor_id` field on every list/detail screen

WS-8 just shipped. Every response with `"floor": "B1"` now also includes `"floor_id": 1`. Every endpoint that accepts `?floor=B1` also accepts `?floor_id=1`.

**Action:** in your shared `FloorPickerService` (or equivalent), cache the `id ↔ name` mapping at boot from `GET /occupancy/floors`. From this point forward:

- Use `floor_id` as the **stable key** (cache invalidation, query params, route params where you control them).
- Keep `floor` (string) as the **display label** ("B1", "B2").
- All `?floor=B1` query params can migrate to `?floor_id=N` at your pace; both ship for one release.
- `SlotRef` now has `id: int` and `floor_id: int`. Use `id` for cache keys; render `slot_id` ("B1-001") to the user.

**Acceptance:** open `/openapi.json`, confirm `floor_id: integer` appears under `components.schemas.FloorOccupancy.properties` and on every floor-bearing schema. Codegen regenerates without errors.

### T2. SSE listener — read `triggered_at` (not `timestamp`)

Already a known migration. The wire payload is `AlertStreamEventLite` with 12 fields. The `connection_established` keep-alive frame uses the same shape (with all values null except `is_alert: false` and `source_system: "gateway"`).

**Acceptance:** opening EventSource against `/alerts/stream`, the first event is `connection_established`, and every subsequent event has a `triggered_at` field (or null). No `timestamp` field in the payload at all.

### T3. Slots grid — switch `?grouped=true` calls to `/occupancy/slots/by-floor`

Plain `/occupancy/slots` is now strictly paginated (`PagedResponse[SlotListItem]`); the `?grouped=` query param was removed in PR 3. The grouped shape lives at `GET /occupancy/slots/by-floor` → `list[FloorSlotGroup]`.

**Acceptance:** `grep -rn 'grouped=true' src/` returns zero. The slots-by-floor view fetches from `/occupancy/slots/by-floor` and renders one card per `FloorSlotGroup`.

### T4. Dashboard active-vehicles card

Per WS-A.GA-2 + the dashboard redesign:

```typescript
// Replace any single call to /dashboard/active-vehicles with:
const { active_now } = await api.dashboard.kpis();           // headline number
const { items } = await api.vehicles.list({                  // preview list
    is_currently_parked: true,
    page_size: 20,
});
```

The deprecated endpoint stays serving for now (per hard-constraints), but new code should use the pair above. **Don't remove the fallback** to `/dashboard/active-vehicles` until GA-5 (`parking_sessions` has-no-writer) is resolved upstream — see §"Known issues".

**Acceptance:** Cypress test for the dashboard card mounts both endpoints, asserts `total_count` from the second call equals `active_now` from the first (within 1s of each other).

### T5. Dashboard AI-status card — new shape

Old shape: `{ online: bool, issues: [...], system1: {...}, system2: {...} }`.
New shape: `{ overall_health: "healthy"|"degraded"|"down", issues: [...], systems: [{name, health, timestamp, last_connected_at}, ...] }`.

**Action:** iterate `systems[]`; render `name` as the row label, `health` (string enum: `healthy`/`degraded`/`unreachable`) drives the badge color. Use `overall_health` for the umbrella status.

**Acceptance:** the card renders 2 rows ("PMS-AI", "VideoAnalytics") even when both are unreachable. The umbrella badge reads "down" / "degraded" / "healthy" — never "online: true/false".

### T6. Dashboard KPIs — render both plate counts

`DashboardKPIs` now has 4 fields:

```ts
interface DashboardKPIs {
  total_unique_plates: number;   // registered plates (from `vehicles` table)
  plates_seen_today: number;     // distinct plates that crossed a gate today (from entry_exit_log)
  active_now: number;            // currently parked (from parking_sessions — see GA-5 caveat)
  open_alerts: number;
}
```

Add a separate tile (or footnote) for `plates_seen_today`. Don't conflate with `total_unique_plates`.

**Acceptance:** the dashboard renders both numbers with distinct labels.

## 4. Recommended tasks — defensive improvements

Not blockers; do them when convenient.

- **Alerts table — trim the location fallback chain.** Per G-6 ext, `slot_name` and `floor` are now populated 95%+ of the time on `AlertItem`. The chain `slot_name || floor || location || camera_id` can drop the last two fallbacks for most rows.
- **Reconciliation drift badge per floor.** `FloorOccupancy.reconciled: bool` and `slot_occupancy_count` (vs `current_count`) are already in the contract — surface a small warning indicator when the line-crossing and slot-status counts disagree.
- **CSV downloads** — every list endpoint with filters has a matching `/export/csv` that takes the same filters. Make sure the export buttons pass the current filter state.
- **Pagination defaults** — every paged endpoint accepts `page_size` 1-100. Default 20 is fine; use 50 for table views with virtual scrolling.
- **Camera role rendering** — `CameraRef.role` is one of `entry`/`exit`/`floor_counting`/`slot_detection`/`other`. WS-8 wires `watches_floor_id` directly so role can render a "watching: B1" badge from the integer when present.

## 5. Field-by-field new fields cheat sheet (post-WS-8)

| Schema | New fields | Old field still present? |
|---|---|---|
| `SlotRef`, `SlotListItem`, `SlotDetail` | `id: int`, `floor_id: int` | Yes (`slot_id`, `floor`) |
| `FloorOccupancy`, `FloorDetail` | `id: int`, `floor_id: int` | Yes (`floor`) |
| `FloorSlotGroup` | `floor_id: int` | Yes (`floor`) |
| `CameraRef`, `CameraItem`, `CameraCreate`, `CameraUpdate` | `floor_id: int`, `watches_floor_id: int` | Yes (`floor`, `watches_floor`) |
| `ActiveVehicle`, `VehicleEvent`, `VehicleListItem` | `floor_id: int` | Yes (`floor`) |
| `AlertItem`, `AlertDetail`, `AlertStreamEventLite` | `floor_id: int` | Yes (`floor`) |
| `ZoneItem` (deprecated) | `floor_id: int` | Yes (`floor`) |
| `DashboardKPIs` | `plates_seen_today: int` | (already covered in T6) |

All new fields are `Optional[int] | null` during the additive phase. After Phase 4C cleanup they become non-nullable; until then, treat them as nullable and fall back to the string field when absent.

## 6. Known issues / workarounds

### GA-5 — `parking_sessions` has no writer

PMS-AI's webhook only writes `entry_exit_log`. VideoAnalytics POSTs to a phantom `/api/v1/internal/parking-sessions/bind-slot` endpoint that doesn't exist; the 404 is swallowed silently. Effect on the frontend:

- `/dashboard/kpis.active_now` reads `parking_sessions` → likely returns the count of **stale seed rows**, not the real number.
- `/vehicles/?is_currently_parked=true` joins `parking_sessions` → may return seed rows that don't reflect today's reality.
- `/dashboard/active-vehicles` (the deprecated endpoint) — same.

**UI mitigation until PMS-AI ships the writer:**

1. **Don't trust `active_now` literally.** Show it with a "(approximate)" footer or add a small "data freshness" indicator that reads `MAX(entry_time)` from the active list and warns if older than 24h.
2. **Cross-check against `entry_exit_log` if you have access.** A more honest "currently parked" count: `entries_today - exits_today` from `/entry-exit/`.
3. **When GA-5 ships server-side**, all three endpoints become accurate without frontend changes.

Track resolution in `EXECUTION_PLAN.md` "GA-5 finding" section.

## 7. Verification — how to confirm production readiness

Run these in order. Stop and fix at the first failure.

1. **Codegen:** `yarn gen:api` produces no warnings, no `any` types on response bodies, all new fields appear in generated TypeScript interfaces.
2. **Type-check:** `yarn ng build --configuration=production` passes.
3. **Cypress smoke:**
   - Dashboard loads with all 5 cards: AI-status, KPIs (4 numbers including `plates_seen_today`), Active Vehicles card, occupancy summary, alerts feed.
   - SSE stream shows `connection_established` within 2s; the `triggered_at` field exists on each event.
   - Alerts list — filtering by floor uses `?floor_id=`; the request URL contains the integer.
   - Slots grid — `/occupancy/slots/by-floor` returns one group per floor; clicking a slot opens `/occupancy/slots/{slot_id}` detail.
   - Camera list — filter by `?floor_id=1` returns only B1 cameras; total_count matches the rendered row count.
4. **Contract tripwire:** any field your code reads that's marked nullable in the OpenAPI spec must have an `?? defaultValue` or `if (!field) return early` path. Don't unwrap with `!` (non-null assertion) — the gateway is allowed to return null.
5. **Browser DevTools network tab — sanity check on a real session:** every paginated response has `total_count`, `page`, `page_size`, `items`. Every floor field has its `floor_id` sibling. No 500s on any endpoint.
6. **Run `/tmp/pms_audit.py` from the gateway venv** against your dev gateway. Confirm pass on all 5 GA-x lines: `total_unique_plates` OK, `is_currently_parked total_count > 0`, `occupancy/kpis == /occupancy/totals`, `cameras/kpis online == by_status`, `/alerts/{id}` null fields ≤ 5.

## 8. Order of operations (suggested sprint plan)

| Day | Task |
|---|---|
| 1 | T2 (SSE rename) + T6 (new dashboard KPI tile). Both small, low risk. |
| 1 | T5 (AI-status reshape). The component changes; props drop in cleanly. |
| 2 | T1 (floor_id adoption — service-layer caching + query-param swap one tab at a time). |
| 2-3 | T3 (slots-by-floor migration) + T4 (active-vehicles card pair). |
| 3 | Recommended tasks (location fallback trim, reconciliation drift badge). |
| 4 | Verification §7 end-to-end. |

If anything in this prompt conflicts with what `INTEGRATION_PLAN_LIVE.md` says, the **gateway main branch** is the truth source — `OpenAPI` at `/openapi.json` is canonical; if your generated client disagrees, regenerate.

## 9. Where to ask

- Gateway behavior questions → grep `API-Gateway/CLAUDE.md` first; then the audit doc; then file an issue.
- Cross-service contract questions → `DTO_REFACTOR_PLAN.md` + `EXECUTION_PLAN.md` are authoritative.
- Anything you find that this doc missed → flag it in the PR description; the gateway team will roll it into the next audit cycle.
