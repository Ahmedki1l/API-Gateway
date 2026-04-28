"""
Populate the database with realistic demo simulation data.
Covers: entry_exit_log, parking_sessions, slot_status, alerts.

Run: .venv/bin/python scratch/simulate_demo.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pymssql
import random
from datetime import datetime, timedelta
from app.config import settings

conn = pymssql.connect(
    server=settings.db_server,
    port=settings.db_port,
    user=settings.db_user,
    password=settings.db_password,
    database=settings.db_name,
)
cursor = conn.cursor(as_dict=True)

NOW = datetime.utcnow()

# ── Known plates (registered + unknown) ─────────────────────────────────
REGISTERED = ['ZXY-123', 'cdf-123', 'kgh-587', 'TEST-001', 'asdr1234']
UNKNOWN = [
    'SHR-1198', 'AAD-2560', 'HGD-2926', 'KKR-2994', 'TTB-8627',
    'NDD-4141', 'RTB-2016', 'RGR-6466', 'SDD-6707', 'NXR-2727',
    'EEB-80', 'RDJ-9640', 'HBR-4920', 'UEU-777', 'ZRS-6511',
    'BGD-7593', 'NJS-7894', 'HVA-77', 'TRS-9117', 'HDU-7',
]
ALL_PLATES = REGISTERED + UNKNOWN

# ── Slot layout ──────────────────────────────────────────────────────────
B1_SLOTS = ['B1_CRO','B10_CTO','B11_CFO','B12','B13_COO','B2','B3_CEO','B6_Reserved','B8','B9','GMIA']
B2_SLOTS = ['B14','B15','B16','B17','B18','B19','B20','B21','B22','B23','B24','B25','B27']
GF_SLOTS = ['G1','G2','G3','G4','G5','G6']
VIOLATION_SLOTS = ['V1_Violation_1', 'V2_Violation_2']
RESTRICTED_SLOTS = ['B1_CRO','B10_CTO','B11_CFO','B3_CEO','B13_COO','B6_Reserved','GMIA']
ALL_NORMAL = B1_SLOTS + B2_SLOTS + GF_SLOTS
SLOT_FLOOR = {}
for s in B1_SLOTS: SLOT_FLOOR[s] = 'B1'
for s in B2_SLOTS: SLOT_FLOOR[s] = 'B2'
for s in GF_SLOTS + VIOLATION_SLOTS: SLOT_FLOOR[s] = 'Ground'

# ── Helper ───────────────────────────────────────────────────────────────
def dt(d): return d.strftime('%Y-%m-%d %H:%M:%S.') + f'{d.microsecond // 1000:03d}'
def run(sql, params=None):
    cursor.execute(sql, params or {})

# ── Step 0: Clear volatile tables ────────────────────────────────────────
print("Clearing volatile tables...")
for t in ['intrusions', 'alerts', 'slot_status', 'entry_exit_log', 'parking_sessions']:
    run(f'DELETE FROM dbo.{t}')
    print(f"  Cleared {t}")
conn.commit()

# ── Decide currently parked vehicles FIRST ───────────────────────────────
# This determines everything else (slot_status, zone_occupancy, entry_exit)
NUM_PARKED = random.randint(10, 14)
currently_parked_slots = random.sample(ALL_NORMAL, NUM_PARKED)
currently_parked_plates = random.sample(ALL_PLATES, NUM_PARKED)
parked_map = dict(zip(currently_parked_plates, currently_parked_slots))
# Also park one car in violation slot V1 for the demo
violation_plate = random.choice([p for p in UNKNOWN if p not in currently_parked_plates])
parked_map[violation_plate] = 'V1_Violation_1'

print(f"\n  {len(parked_map)} vehicles currently parked (incl. 1 in violation slot)")

# ── Step 1: entry_exit_log — 14 days of gate events ─────────────────────
print("\nGenerating entry_exit_log...")
entry_exit_rows = []

for day_offset in range(14, 0, -1):  # 14 days ago .. yesterday
    day_start = (NOW - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
    n_entries = random.randint(6, 12)
    n_exits = random.randint(4, 8)
    
    for _ in range(n_entries):
        t = day_start + timedelta(hours=random.randint(5, 19), minutes=random.randint(0, 59), seconds=random.randint(0, 59))
        plate = random.choice(ALL_PLATES)
        entry_exit_rows.append((plate, 'unknown', 'entry', 'CAM-ENTRY', t, None, None, 0))
    
    for _ in range(n_exits):
        t = day_start + timedelta(hours=random.randint(10, 22), minutes=random.randint(0, 59), seconds=random.randint(0, 59))
        plate = random.choice(ALL_PLATES)
        entry_exit_rows.append((plate, 'unknown', 'exit', 'CAM-EXIT', t, None, None, 0))

# Today: ensure all currently-parked plates have an entry event today
today_start = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
for plate in parked_map.keys():
    entry_t = today_start + timedelta(hours=random.randint(5, int(NOW.hour) or 6), minutes=random.randint(0, 59))
    if entry_t > NOW:
        entry_t = NOW - timedelta(minutes=random.randint(30, 180))
    entry_exit_rows.append((plate, 'unknown', 'entry', 'CAM-ENTRY', entry_t, None, None, 0))

# Additional random entries/exits today
for _ in range(random.randint(4, 8)):
    t = today_start + timedelta(hours=random.randint(5, max(int(NOW.hour), 6)), minutes=random.randint(0, 59))
    if t > NOW: t = NOW - timedelta(minutes=random.randint(5, 60))
    plate = random.choice(ALL_PLATES)
    entry_exit_rows.append((plate, 'unknown', 'entry', 'CAM-ENTRY', t, None, None, 0))

for _ in range(random.randint(2, 5)):
    t = today_start + timedelta(hours=random.randint(8, max(int(NOW.hour), 9)), minutes=random.randint(0, 59))
    if t > NOW: t = NOW - timedelta(minutes=random.randint(5, 60))
    plate = random.choice([p for p in ALL_PLATES if p not in parked_map])
    entry_exit_rows.append((plate, 'unknown', 'exit', 'CAM-EXIT', t, None, None, 0))

entry_exit_rows.sort(key=lambda r: r[4])

for r in entry_exit_rows:
    run("""INSERT INTO dbo.entry_exit_log 
           (plate_number, vehicle_type, gate, camera_id, event_time, parking_duration, snapshot_path, is_test)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", r)
conn.commit()
print(f"  Inserted {len(entry_exit_rows)} entry/exit events")

# ── Step 2: parking_sessions — mix of open and closed ────────────────────
print("\nGenerating parking_sessions...")
session_count = 0

# Closed sessions over the last 14 days
for day_offset in range(14, 0, -1):
    day = (NOW - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
    n = random.randint(4, 8)
    for _ in range(n):
        plate = random.choice(ALL_PLATES)
        is_emp = plate in REGISTERED
        vtype = 'sedan' if is_emp else 'unknown'
        slot = random.choice(ALL_NORMAL)
        floor = SLOT_FLOOR[slot]
        duration = random.randint(1800, 28800)
        entry_t = day + timedelta(hours=random.randint(5, 14), minutes=random.randint(0, 59))
        exit_t = entry_t + timedelta(seconds=duration)
        run("""INSERT INTO dbo.parking_sessions
               (plate_number, vehicle_type, is_employee, entry_time, exit_time, duration_seconds,
                entry_camera_id, exit_camera_id, floor, slot_id, slot_number, status, created_at, updated_at)
               VALUES (%s,%s,%d,%s,%s,%d,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (plate, vtype, 1 if is_emp else 0, dt(entry_t), dt(exit_t), duration,
             'CAM-ENTRY', 'CAM-EXIT', floor, slot, slot, 'closed', dt(entry_t), dt(exit_t)))
        session_count += 1

# Currently open sessions
for plate, slot in parked_map.items():
    is_emp = plate in REGISTERED
    vtype = 'sedan' if is_emp else 'unknown'
    floor = SLOT_FLOOR[slot]
    # Stagger entry times: some arrived early morning, some recently
    hours_ago = random.choice([1, 2, 3, 4, 5, 6, 7, 8])
    mins_ago = random.randint(0, 59)
    entry_t = NOW - timedelta(hours=hours_ago, minutes=mins_ago)
    run("""INSERT INTO dbo.parking_sessions
           (plate_number, vehicle_type, is_employee, entry_time, entry_camera_id,
            floor, slot_id, slot_number, status, created_at, updated_at)
           VALUES (%s,%s,%d,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (plate, vtype, 1 if is_emp else 0, dt(entry_t), 'CAM-ENTRY',
         floor, slot, slot, 'open', dt(entry_t), dt(entry_t)))
    session_count += 1

conn.commit()
print(f"  Inserted {session_count} sessions ({len(parked_map)} currently open)")

# ── Step 3: slot_status — realistic current state + history ──────────────
print("\nGenerating slot_status...")
status_count = 0
all_slots = B1_SLOTS + B2_SLOTS + GF_SLOTS + VIOLATION_SLOTS

# Historical status changes over last 7 days
for day_offset in range(7, 0, -1):
    day = (NOW - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
    for slot in all_slots:
        n_changes = random.randint(2, 5)
        for _ in range(n_changes):
            t = day + timedelta(hours=random.randint(5, 22), minutes=random.randint(0, 59), seconds=random.randint(0, 59))
            status = random.choice(['occupied', 'available', 'available'])  # more available
            plate = random.choice(ALL_PLATES) if status == 'occupied' else ''
            run("""INSERT INTO dbo.slot_status (slot_id, plate_number, status, time)
                   VALUES (%s, %s, %s, %s)""", (slot, plate, status, dt(t)))
            status_count += 1

# Current state: must match parked_map exactly
occupied_slots = set(parked_map.values())
for slot in all_slots:
    if slot in occupied_slots:
        status = 'occupied'
        # Find which plate is in this slot
        plate = [p for p, s in parked_map.items() if s == slot][0]
    else:
        status = 'available'
        plate = ''
    # Stagger the "current" timestamps slightly
    t = NOW - timedelta(minutes=random.randint(1, 20), seconds=random.randint(0, 59))
    run("""INSERT INTO dbo.slot_status (slot_id, plate_number, status, time)
           VALUES (%s, %s, %s, %s)""", (slot, plate, status, dt(t)))
    status_count += 1

conn.commit()
print(f"  Inserted {status_count} slot_status rows")

# ── Step 4: alerts — all 4 types, natural spread ─────────────────────────
print("\nGenerating alerts...")
alert_count = 0

def rand_time(day_offset, min_hours=1, max_hours=12):
    """Unique timestamp with minute-level variation."""
    return NOW - timedelta(days=day_offset, hours=random.randint(min_hours, max_hours),
                            minutes=random.randint(0, 59), seconds=random.randint(0, 59))

# vehicle_violation — someone parked in V1/V2
for day_offset in [0, 1, 3, 5, 8, 12]:
    t = rand_time(day_offset, 0, 8)
    slot = random.choice(VIOLATION_SLOTS)
    plate = random.choice(UNKNOWN)
    resolved = day_offset > 0
    resolved_at = dt(t + timedelta(hours=random.randint(1, 3), minutes=random.randint(5, 55))) if resolved else None
    run("""INSERT INTO dbo.alerts
           (alert_type, camera_id, zone_id, zone_name, slot_id, slot_number,
            event_type, description, is_test, is_resolved, triggered_at, resolved_at,
            plate_number, severity, location_display)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,%d,%s,%s,%s,%s,%s)""",
        ('vehicle_violation', 'Cam_01', 'GF-FRONT', 'GF Front',
         slot, f'Slot {slot.replace("_"," ")}',
         'vehicle_detected', f'Vehicle parked in violation slot {slot.split("_")[0]}',
         1 if resolved else 0, dt(t), resolved_at,
         plate, 'critical', f'Ground / {slot.replace("_"," ")}'))
    alert_count += 1

# vehicle_intrusion — someone in a reserved slot
for day_offset in [0, 2, 4, 7, 10, 13]:
    t = rand_time(day_offset, 1, 10)
    slot = random.choice(RESTRICTED_SLOTS)
    plate = random.choice(UNKNOWN)
    resolved = day_offset > 1
    resolved_at = dt(t + timedelta(hours=random.randint(1, 4), minutes=random.randint(10, 50))) if resolved else None
    label = slot.replace('_', ' ')
    run("""INSERT INTO dbo.alerts
           (alert_type, camera_id, zone_id, zone_name, slot_id, slot_number,
            event_type, description, is_test, is_resolved, triggered_at, resolved_at,
            plate_number, severity, location_display)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,%d,%s,%s,%s,%s,%s)""",
        ('vehicle_intrusion', 'Cam_03', 'B1-PARKING', 'B1 Parking',
         slot, f'Slot {label}',
         'vehicle_detected', f'Unauthorized vehicle in reserved {label} slot',
         1 if resolved else 0, dt(t), resolved_at,
         plate, 'critical' if day_offset < 3 else 'warning', f'B1 / Slot {label}'))
    alert_count += 1

# capacity_exceeded — floor at/over capacity
for day_offset in [0, 1, 3, 6, 9, 11]:
    t = rand_time(day_offset, 0, 6)
    floor = random.choice(['B1', 'B2'])
    cap = 11 if floor == 'B1' else 13
    occ = cap + random.randint(0, 3)
    pct = round(occ / cap * 100)
    cam = 'Cam_03' if floor == 'B1' else 'Cam_09'
    resolved = day_offset > 0
    resolved_at = dt(t + timedelta(hours=random.randint(1, 3), minutes=random.randint(5, 45))) if resolved else None
    run("""INSERT INTO dbo.alerts
           (alert_type, camera_id, zone_id, zone_name,
            event_type, description, is_test, is_resolved, triggered_at, resolved_at,
            severity, location_display)
           VALUES (%s,%s,%s,%s,%s,%s,0,%d,%s,%s,%s,%s)""",
        ('capacity_exceeded', cam, f'{floor}-PARKING', f'{floor} Parking',
         'occupancy_update', f'Floor {floor} capacity: {pct}% ({occ}/{cap} slots occupied)',
         1 if resolved else 0, dt(t), resolved_at,
         'critical' if occ > cap else 'warning', f'{floor} Parking'))
    alert_count += 1

# unknown_vehicle — unregistered plate at gate
for day_offset in [0, 0, 1, 2, 4, 5, 7, 9, 12, 14]:
    t = rand_time(day_offset, 0, 10)
    plate = random.choice(UNKNOWN)
    gate = random.choice(['entry', 'entry', 'entry', 'exit'])
    cam = 'ANPR-Entry' if gate == 'entry' else 'ANPR-Exit'
    gate_name = 'Entry Gate' if gate == 'entry' else 'Exit Gate'
    resolved = day_offset > 1
    resolved_at = dt(t + timedelta(hours=random.randint(2, 8), minutes=random.randint(10, 55))) if resolved else None
    run("""INSERT INTO dbo.alerts
           (alert_type, camera_id, zone_id, zone_name,
            event_type, description, is_test, is_resolved, triggered_at, resolved_at,
            plate_number, severity, location_display)
           VALUES (%s,%s,%s,%s,%s,%s,0,%d,%s,%s,%s,%s,%s)""",
        ('unknown_vehicle', cam, gate, gate_name,
         'AccessControllerEvent', f'Unregistered vehicle at {gate} gate: plate {plate}',
         1 if resolved else 0, dt(t), resolved_at,
         plate, 'critical' if day_offset < 2 else 'warning', gate_name))
    alert_count += 1

conn.commit()
print(f"  Inserted {alert_count} alerts")

# ── Step 5: Update zone_occupancy to match actual slot_status ────────────
print("\nUpdating zone_occupancy...")
b1_occ = sum(1 for s in occupied_slots if SLOT_FLOOR.get(s) == 'B1')
b2_occ = sum(1 for s in occupied_slots if SLOT_FLOOR.get(s) == 'B2')
gf_occ = sum(1 for s in occupied_slots if SLOT_FLOOR.get(s) == 'Ground')
total_occ = b1_occ + b2_occ + gf_occ

run("UPDATE dbo.zone_occupancy SET current_count=%d, last_updated=%s WHERE zone_id='B1-PARKING'", (b1_occ, dt(NOW)))
run("UPDATE dbo.zone_occupancy SET current_count=%d, last_updated=%s WHERE zone_id='B2-PARKING'", (b2_occ, dt(NOW)))
run("UPDATE dbo.zone_occupancy SET current_count=%d, last_updated=%s WHERE zone_id='GARAGE-TOTAL'", (total_occ, dt(NOW)))
conn.commit()
print(f"  B1: {b1_occ}/11, B2: {b2_occ}/13, Ground: {gf_occ}/8, Total: {total_occ}/32")

# ── Summary ──────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("  DEMO SIMULATION COMPLETE")
print("="*50)

cursor.execute("SELECT COUNT(*) as c FROM dbo.entry_exit_log")
print(f"  entry_exit_log:    {cursor.fetchone()['c']} rows")

cursor.execute("SELECT COUNT(*) as c FROM dbo.entry_exit_log WHERE event_time >= CAST(GETUTCDATE() AS DATE)")
print(f"    today:           {cursor.fetchone()['c']}")

cursor.execute("SELECT COUNT(*) as c FROM dbo.parking_sessions")
print(f"  parking_sessions:  {cursor.fetchone()['c']} rows")
cursor.execute("SELECT COUNT(*) as c FROM dbo.parking_sessions WHERE status='open'")
print(f"    currently parked: {cursor.fetchone()['c']}")

cursor.execute("SELECT COUNT(*) as c FROM dbo.slot_status")
print(f"  slot_status:       {cursor.fetchone()['c']} rows")

cursor.execute("SELECT COUNT(*) as c FROM dbo.alerts")
print(f"  alerts:            {cursor.fetchone()['c']} rows")
cursor.execute("SELECT alert_type, COUNT(*) as c FROM dbo.alerts GROUP BY alert_type ORDER BY alert_type")
for r in cursor.fetchall():
    print(f"    {r['alert_type']:25s} {r['c']}")
cursor.execute("SELECT COUNT(*) as c FROM dbo.alerts WHERE is_resolved=0")
print(f"    active (unresolved):    {cursor.fetchone()['c']}")

conn.close()
print("\nDone! Dashboard should now show rich data.")
