# Seed Data — Simulation Reference

> **Source:** `sql/seed.sql` · Cloned from the live `damanat_pms` database on 2026-04-26.
> Alerts section uses simulated data with relative timestamps.

---

## Facility Layout

The garage has **3 floors** and **32 parking slots**:

| Floor | Slots | Description |
|-------|-------|-------------|
| **Ground** | `G1` – `G6`, `V1_Violation_1`, `V2_Violation_2` | 6 standard + 2 violation slots |
| **B1** | `B1_CRO`, `B10_CTO`, `B11_CFO`, `B3_CEO`, `B13_COO`, `B6_Reserved`, `GMIA`, `B2`, `B8`, `B9`, `B12` | 11 slots — includes 7 executive/restricted |
| **B2** | `B14` – `B25`, `B27` | 13 standard numbered slots |

### Reserved / Restricted Slots (B1)

| Slot ID | Label | Assignment |
|---------|-------|------------|
| `B1_CRO` | Slot B1 CRO | Chief Revenue Officer |
| `B10_CTO` | Slot B10 CTO | Chief Technology Officer |
| `B11_CFO` | Slot B11 CFO | Chief Financial Officer |
| `B3_CEO` | Slot B3 CEO | Chief Executive Officer |
| `B13_COO` | Slot B13 COO | Chief Operating Officer |
| `B6_Reserved` | Slot B6 Reserved | Reserved |
| `GMIA` | GMIA | Restricted |

### Violation Slots (Ground)

| Slot ID | Label |
|---------|-------|
| `V1_Violation_1` | Violation Slot 1 — no parking permitted |
| `V2_Violation_2` | Violation Slot 2 — no parking permitted |

---

## Camera Fleet (16 cameras)

| Camera ID | Name | Floor | IP Address | Purpose |
|-----------|------|-------|------------|---------|
| `Cam_01` | GF-FRONT | Ground | 10.1.13.60 | Ground floor front |
| `Cam_02` | GF-FRONT | Ground | 10.1.13.61 | Ground floor front |
| `Cam_03` – `Cam_08` | B1-PARKING | B1 | 10.1.13.62 – .67 | B1 floor coverage |
| `Cam_09` – `Cam_14` | B2-PARKING | B2 | 10.1.13.68 – .73 | B2 floor coverage |
| `ANPR-Entry` | ENTRY-GATE | Ground | 10.1.13.100 | License plate reader — entry |
| `ANPR-Exit` | EXIT-GATE | Ground | 10.1.13.101 | License plate reader — exit |

> Credentials are Fernet-encrypted. If your `CAMERAS_ENCRYPTION_KEY` differs from the seed key, re-register cameras via `POST /cameras/`.

---

## Floor Capacity

| Floor | Total Slots | Max Capacity |
|-------|------------|--------------|
| B1 | 11 | 11 |
| B2 | 13 | 13 |
| **Garage Total** | **32** | **24** |

---

## Registered Vehicles (5)

| Plate | Owner | Type | Employee | Title |
|-------|-------|------|----------|-------|
| `ZXY-123` | Ahmed alaa | sedan | ✅ (452) | eng. |
| `cdf-123` | Mohamed Henaish | cross | ✅ (emp-2) | eng. |
| `kgh-587` | mohamed gamal | suv | ✅ (875) | eng. |
| `TEST-001` | Ahmed Test | sedan | ✅ | Mr |
| `asdr1234` | ahmed alaa 2 | sedan | ❌ | test |

---

## Simulated Alerts (24 rows)

Alerts use **relative timestamps** (`DATEADD(@now)`), so they always appear recent when the seed is run. They span the last **14 days** with a mix of active (unresolved) and resolved alerts.

### Alert Types

#### 1. `vehicle_violation` — Violation Slot Parking (5 alerts)

A vehicle has been detected parked in a designated violation slot where parking is not permitted.

| # | Slot | Plate | Severity | Status | When |
|---|------|-------|----------|--------|------|
| 1 | V1_Violation_1 | SHR-1198 | 🔴 critical | **Active** | 35 min ago |
| 2 | V2_Violation_2 | AAD-2560 | 🔴 critical | **Active** | 20 min ago |
| 3 | V1_Violation_1 | HGD-2926 | 🔴 critical | Resolved | 3 days ago |
| 4 | V2_Violation_2 | NXR-2727 | 🔴 critical | Resolved | 7 days ago |
| 5 | V1_Violation_1 | TTB-8627 | 🟡 warning | Resolved | 12 days ago |

> **Camera:** `Cam_01` (GF-FRONT) · **Floor:** Ground

---

#### 2. `vehicle_intrusion` — Restricted Slot Intrusion (6 alerts)

An unauthorized vehicle has parked in a reserved/restricted executive slot.

| # | Slot | Plate | Severity | Status | When |
|---|------|-------|----------|--------|------|
| 1 | B3_CEO | KKR-2994 | 🔴 critical | **Active** | 50 min ago |
| 2 | B1_CRO | RGR-6466 | 🔴 critical | **Active** | 2 hours ago |
| 3 | B10_CTO | RTB-2016 | 🔴 critical | Resolved | 1 day ago |
| 4 | B6_Reserved | SDD-6707 | 🟡 warning | Resolved | 4 days ago |
| 5 | GMIA | EEB-80 | 🟡 warning | Resolved | 6 days ago |
| 6 | B13_COO | NDD-4141 | 🔴 critical | Resolved | 10 days ago |

> **Cameras:** `Cam_03` – `Cam_06` (B1-PARKING) · **Floor:** B1

---

#### 3. `capacity_exceeded` — Capacity Exceeded (6 alerts)

A floor has reached or exceeded its maximum number of available parking slots.

| # | Floor | Message | Severity | Status | When |
|---|-------|---------|----------|--------|------|
| 1 | B2 | Full: 100% (13/13 slots occupied) | 🟡 warning | **Active** | 1 hour ago |
| 2 | B2 | Exceeded: 108% (14/13 slots occupied) | 🔴 critical | **Active** | 45 min ago |
| 3 | B1 | Nearly full: 91% (10/11 slots occupied) | 🟡 warning | Resolved | 2 days ago |
| 4 | B2 | Exceeded: 115% (15/13 slots occupied) | 🔴 critical | Resolved | 5 days ago |
| 5 | B1 | Full: 100% (11/11 slots occupied) | 🟡 warning | Resolved | 8 days ago |
| 6 | B2 | Nearly full: 92% (12/13 slots occupied) | 🟡 warning | Resolved | 11 days ago |

> **Cameras:** `Cam_03` (B1), `Cam_09` (B2)

---

#### 4. `unknown_vehicle` — Unknown Vehicle (7 alerts)

An unregistered license plate was detected at the entry or exit gate.

| # | Gate | Plate | Severity | Status | When |
|---|------|-------|----------|--------|------|
| 1 | Entry | SHR-1198 | 🔴 critical | **Active** | 15 min ago |
| 2 | Entry | AAD-2560 | 🔴 critical | **Active** | 3 hours ago |
| 3 | Exit | HBR-4920 | 🔴 critical | **Active** | 5 hours ago |
| 4 | Entry | BGD-7593 | 🔴 critical | Resolved | 1 day ago |
| 5 | Entry | NJS-7894 | 🟡 warning | Resolved | 3 days ago |
| 6 | Entry | HVA-77 | 🟡 warning | Resolved | 6 days ago |
| 7 | Entry | RDJ-9640 | 🟡 warning | Resolved | 9 days ago |

> **Cameras:** `ANPR-Entry`, `ANPR-Exit` · **Floor:** Ground (gates)

---

## Severity Distribution

| Severity | Active | Resolved | Total |
|----------|--------|----------|-------|
| 🔴 `critical` | 8 | 7 | **15** |
| 🟡 `warning` | 1 | 8 | **9** |
| **Total** | **9** | **15** | **24** |

---

## Timestamps

| Table | Strategy | Notes |
|-------|----------|-------|
| parking_slots | Static | Cloned from live DB |
| cameras | Static | Cloned from live DB — encrypted creds |
| vehicles | Static | Real registration dates from live DB |
| slot_status | Static | Latest state per slot from live DB |
| entry_exit_log | Static | Real ANPR events from live DB |
| parking_sessions | Static | Real sessions from live DB |
| **alerts** | **`DATEADD(@now)`** | **Relative — always appears recent** |
| camera_feeds | — | Empty (no rows) |

---

## Running the Seed

```bash
# After bootstrap.sql creates the schema:
sqlcmd -E -S localhost -d damanat_pms -i sql/seed.sql

# Or with SQL authentication:
sqlcmd -U sa -P "YourStrong!Pass1" -S localhost -d damanat_pms -i sql/seed.sql
```

The seed is **idempotent** — every block is guarded by `IF NOT EXISTS` or `MERGE`, so re-running on a populated database is safe and does nothing.
