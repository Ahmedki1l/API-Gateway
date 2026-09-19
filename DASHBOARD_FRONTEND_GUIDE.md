# Dashboard — Frontend Integration Guide

Last updated: 2026-09-19. Covers the redesigned Dashboard page. Every endpoint
below is served by the API Gateway (System 3); the frontend never calls PMS-AI
or VideoAnalytics directly.

**Base URL:** `{GATEWAY}` plus the optional `PREFIX` from the gateway `.env`
(e.g. `https://host/api`). Paths below are relative to it.

**Timestamps** are facility-local (UTC+3) and **naive** — no `Z`, no offset.
Display them as-is; do not convert from UTC.

---

## Page layout → endpoint map

| # | Widget | Endpoint | Update |
|---|---|---|---|
| 0 | AI system health banner | `GET /dashboard/ai-status` | poll 30 s |
| 1 | KPI row (5 cards) | `GET /dashboard/kpis` | poll 30 s |
| 2 | Occupancy Overview (floor bars + donut) | `GET /occupancy/floors` | poll 30 s |
| 3 | Entry / Exit Activity | `GET /entry-exit/` | poll 30 s |
| 4 | Occupancy Trend | `GET /occupancy/history/trend` | on load + on range change |
| 5 | Alerts Summary | `GET /alerts/` + `GET /alerts/stream` (SSE) | live |

**Removed from the design:**
- Header date-range picker, "Last 24 Hours" dropdown, and Export Report button.
- "Top Parkings by Occupancy" card — replaced by a sort icon on the Occupancy
  Overview card (see §2).

**"Real-time"** means polling for widgets 0–3. Only alerts are pushed over SSE.
Pause polling while the browser tab is hidden (`document.visibilityState`).

---

## 0. AI system health banner

`GET /dashboard/ai-status`

```json
{
  "overall_health": "degraded",
  "issues": [
    { "system": "VideoAnalytics", "reason": "stream CAM-23 frozen for 94s" }
  ],
  "systems": [
    { "name": "PMS-AI", "health": "healthy", "timestamp": "2026-09-19T09:12:03", "last_connected_at": "2026-09-19T09:12:03" },
    { "name": "VideoAnalytics", "health": "degraded", "timestamp": "2026-09-19T09:12:03", "last_connected_at": "2026-09-19T09:11:30" }
  ]
}
```

| Field | Values | UI |
|---|---|---|
| `overall_health` | `healthy` · `degraded` · `down` | `healthy` → hide banner (or show a green dot). `degraded` → amber. `down` → red. |
| `systems[].health` | `healthy` · `unreachable` · any other string (e.g. `degraded`) passed through from the upstream | Treat any value that is not `healthy` / `unreachable` as a warning. |
| `issues[]` | `{system, reason}` — one entry per reason | List the reasons in the banner. They are human-readable; show them verbatim. |
| `last_connected_at` | datetime or `null` | "Last seen 3 min ago". `null` = never reached since the gateway started. |

`overall_health` is `down` only when **both** systems are unhealthy.

---

## 1. KPI row

`GET /dashboard/kpis`

```json
{
  "total_slots": 35,
  "floors_count": 3,
  "free_slots": 33,
  "occupied_slots": 2,
  "occupancy_pct": 5.7,
  "parked_vehicles": 2,
  "critical_alerts": 0,
  "entries_today": 0,
  "exits_today": 0,
  "overstays_today": 2
}
```

| Card | Main value | Subtitle | Meaning |
|---|---|---|---|
| Total Capacity | `total_slots` | "Across `floors_count` Parkings" | Every parking slot, including ones cameras can't see. Violation zones / ROI excluded. `floors_count` = active floors = number of bars in §2. |
| Current Occupancy | `occupied_slots` | "`occupancy_pct`% Occupied" | Slots the cameras currently see a car in. `occupancy_pct` is already rounded to 1 decimal. |
| Entries | `entries_today` | — | Every car that entered since **local midnight**, including ones that already left. |
| Exits | `exits_today` | — | Every session **closed since local midnight**, including cars that entered yesterday. When an overnight car leaves, Exits goes **+1** and Overstays goes **−1** on the same refresh. |
| Overstays | `overstays_today` | — | Cars still inside that entered **before today's midnight** (i.e. stayed past midnight). Distinct plates. |

All three definitions are identical to `GET /entry-exit/kpis`, so the Dashboard
and the Entry/Exit page always show the same numbers.

Drill-downs:

| Card | List URL |
|---|---|
| Entries | `/entry-exit/?date_from=<today>&date_to=<today>` (entry date) |
| Exits | `/entry-exit/?status=closed&exit_date_from=<today>&exit_date_to=<today>` (**exit** date) |
| Overstays | `/entry-exit/?status=overstay` |

`date_from`/`date_to` filter on the day the car **entered**; the new
`exit_date_from`/`exit_date_to` filter on the day it **left**. Never pair the
Exits card with `date_from` — that silently drops the overnight cars.
The same two filter pairs exist on `/entry-exit/export/csv` and
`/entry-exit/by-vehicle/{id}`.

Other fields:
- `free_slots` — used by the donut in §2.
- `parked_vehicles` — cars inside by gate count. Not shown on this design.
- `critical_alerts` — today's unresolved critical alerts. Not shown on this design.

---

## 2. Occupancy Overview

`GET /occupancy/floors?sort=default`

| Query param | Values | Default |
|---|---|---|
| `sort` | `default` (layout order) · `most_occupied` · `least_occupied` | `default` |
| `page`, `page_size` | ints (`page_size` ≤ 100) | `1`, `20` — one page is enough (3 floors) |

The sort icon on the card header cycles `default → most_occupied →
least_occupied` and re-fetches. Ranking is by `utilization`, then `current_count`.

```json
{
  "total_count": 3, "page": 1, "page_size": 20,
  "items": [
    {
      "floor_id": 3, "floor": "Ground",
      "max_capacity": 8, "current_count": 1, "available": 7, "utilization": 12.5,
      "monitored_capacity": 8, "unmonitored_count": 0,
      "cars_in_floor": 1, "slots_occupied": 1, "cars_unparked": 0, "reconciled": true,
      "last_updated": null, "camera_id": null,
      "data_source": "slot_aggregation", "slot_occupancy_count": 1, "slot_occupancy_source": "va_cv",
      "coverage_note": "Counts cover monitored slots only — uncovered slots are excluded."
    }
  ]
}
```

**Floor bar row:** label `floor`, text `current_count / max_capacity`, bar and
percentage from `utilization`. Take all three from the **same item** and do not
compute the percentage client-side. Mixing sources is how a "1/16 — 6.7%" row
happens.

**Donut (right side):**
- Centre value: `occupancy_pct` from §1.
- "N Occupied": `occupied_slots` from §1.
- "N Available": `free_slots` from §1.

Available = monitored slots − occupied, the same rule as `available` per floor.
With every slot monitored, occupied + available = total. If `unmonitored_count
> 0` on any floor, show the gap as "N uncovered" rather than silently dropping it.

"View All" → Occupancy page.

---

## 3. Entry / Exit Activity

`GET /entry-exit/?page=1&page_size=10`

```json
{
  "total_count": 1544, "page": 1, "page_size": 10,
  "items": [
    {
      "id": 1612, "plate_number": "ABC1234", "owner_name": null, "vehicle_type": null,
      "is_employee": false, "status": "closed", "is_overstay": false,
      "entry": { "direction": "entry", "event_time": "2026-09-18T08:02:11", "camera_id": "ANPR-IN", "snapshot_url": "…", "plate_confidence": 0.93 },
      "exit":  { "direction": "exit",  "event_time": "2026-09-18T11:40:05", "camera_id": "ANPR-OUT", "snapshot_url": "…" },
      "duration_seconds": 13074, "floor": "B1", "slot_name": "B1-07"
    }
  ]
}
```

Each item is one **parking session**, with an `entry` and (if the car left) an
`exit`. Render each item as:
- `exit != null` → "⟵ ABC1234 exited · 11:40" (use `exit.event_time`).
- otherwise → "⟶ ABC1234 entered · 08:02" (use `entry.event_time`).

**Known limitation — ordering.** The list is sorted by **entry time**, newest
first. A car that entered 3 hours ago and exits now stays at its entry
position; it does not jump to the top. For a strictly chronological event feed
the gateway needs a new event-level endpoint (not built yet). Until then, label
the card "Recent sessions" or accept this ordering.

Empty state: "No recent activity". "View All" → Entry/Exit page.

---

## 4. Occupancy Trend

`GET /occupancy/history/trend?grain=hour&start_time=…&end_time=…&business_hours=false`

| Query param | Value for the dashboard |
|---|---|
| `grain` | `hour` (for ranges ≤ 3 days); `day` for longer ranges |
| `start_time` | `now − 24h`, facility-local, format `YYYY-MM-DDTHH:mm:ss`, no `Z` |
| `end_time` | now, same format (exclusive) |
| `business_hours` | **always send `false`**. If omitted, the server's `.env` decides; when business hours are on, overnight points come back `null` and the 24 h chart gets holes. |

Other grains: `week`, `month`, `weekday` (7 Mon–Sun bars). The server returns
**400** if the range yields more than 2000 points, or if `start_time >= end_time`.

```json
{
  "grain": "hour",
  "start_time": "2026-09-18T10:00:00", "end_time": "2026-09-19T10:00:00",
  "total_capacity": 35,
  "business_hours_applied": false, "business_hour_from": null, "business_hour_to": null,
  "business_days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
  "points": [
    { "label": "2026-09-18 10:00", "index": 0, "bucket_start": "2026-09-18T10:00:00", "bucket_end": "2026-09-18T11:00:00", "occupancy": 5.7, "days_sampled": 1, "weekday": null, "weekday_index": null }
  ]
}
```

- Y axis = `occupancy` (0–100 %). X axis = `bucket_start` formatted `HH:mm` (e.g. `13:00`).
- `occupancy: null` means "not measured" → draw a **gap**, not zero.
- Values are time-weighted averages per hour, so they will not exactly equal the live KPI.
- The range button defaults to "Last 24 Hours". This is the only widget that
  takes a range, and it only affects this chart.

---

## 5. Alerts Summary

### List (card body)

`GET /alerts/?resolved=false&page=1&page_size=5`

Returns `PagedResponse<AlertItem>`, newest first. Useful fields:
- `id`, `alert_type`, `severity` (`critical` · `warning` · `info`)
- `description`, `location`, `floor`, `slot_name`, `plate_number`
- `snapshot_url`, `triggered_at`

Empty state: "No active alerts". "View All" → Alerts page.
The badge count is `total_count`.

### Optional per-type breakdown

`GET /alerts/summary` (defaults to active alerts):

```json
{ "total": 3, "by_type": [ { "alert_type": "overstay", "count": 2, "severity": "warning" }, … ] }
```

`by_type` includes every known type, even at `count: 0`, so filter to
`count > 0` before rendering.

### Live updates — SSE

`GET /alerts/stream` (`text/event-stream`, use `EventSource`).

- The first frame has `alert_type: "connection_established"` and `is_alert: false`. Ignore it (or use it to mark the stream connected).
- Keep-alive comment frames arrive every 15 s.
- Every alert frame has `is_alert: true` and the fields `id, source_system,
  alert_type, severity, slot_id, slot_name, zone_id, plate_number, camera_id,
  floor, floor_id, snapshot_url, triggered_at`.

On an alert frame, **re-fetch** the list, rather than splicing the frame in,
because the frame is a lighter shape than `AlertItem`. `EventSource`
reconnects on its own after a drop; re-fetch the list on reconnect as well.

---

## Error handling (all widgets)

- Every widget loads and fails **independently**. One failed call must not blank the page.
- On error, keep the last good value, add a subtle "stale" marker, and retry on the next poll.
- `/dashboard/ai-status` never fails because an upstream is down. It reports the outage as data (`unreachable`, plus an `issues[]` entry).
