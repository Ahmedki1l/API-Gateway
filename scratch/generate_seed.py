"""
Generate seed.sql from the live damanat_pms database.
Run: .venv/bin/python scratch/generate_seed.py > sql/seed.sql
"""
import pymssql
import sys

conn = pymssql.connect(server='localhost', port=1433, user='sa', password='YourStrong!Pass1', database='damanat_pms')
cursor = conn.cursor(as_dict=True)

def q(val):
    """SQL-quote a value."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''")
    return f"N'{s}'"

def dt(val):
    """Format datetime for SQL."""
    if val is None:
        return "NULL"
    s = str(val)
    # Remove trailing zeros from microseconds
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return f"'{s}'"

# ── Header ──
print("""/* ============================================================================
   seed.sql — cloned from the live damanat_pms database

   Companion to bootstrap.sql, which is schema-only (DDL + additive ALTERs +
   FKs). Run this AFTER bootstrap.sql to populate the database.

   Tables seeded:
     1. parking_slots          (32 rows — B1 / B2 / Ground)
     2. cameras                (16-row canonical fleet, MERGE-style upsert,
                                Fernet-encrypted RTSP credentials)
     3. zone_occupancy         (3 rows: B1 / B2 / GARAGE-TOTAL)
     4. vehicles               (5 registered vehicles)
     5. slot_status            (32 rows — latest state per slot)
     6. entry_exit_log         (26 gate crossings from live ANPR)
     7. parking_sessions       (17 rows — real entry/exit/park sessions)
     8. alerts                 (32 rows — real alerts from live system)
     9. camera_feeds           (0 rows — table empty in live DB)
    10. Floor alias normalization

   Idempotent — every block is guarded by IF NOT EXISTS or by MERGE so
   re-running the file does nothing on a populated DB.

   IMPORTANT — cameras section:
     The encrypted passwords below were created with a specific
     CAMERAS_ENCRYPTION_KEY. If your gateway runs with a different key,
     decryption will fail at runtime (InvalidToken); re-seed by POSTing
     to /cameras/ with plaintext passwords so the gateway encrypts with
     your key.

   Run:
     sqlcmd -E -S localhost -d damanat_pms -i sql/seed.sql
     (or `-U sa -P "..."` for SQL auth)

   Data cloned from live DB on 2026-04-26.
   ============================================================================ */

SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

PRINT '──────────────────────────────────────────────';
PRINT '  Parking System — seed.sql (live DB clone)';
PRINT '──────────────────────────────────────────────';
""")

# ── 1. parking_slots ──
print("""/* ────────────────────────────────────────────────────────────────────────────
   1. parking_slots — 32 slots (B1 / B2 / Ground)
   ──────────────────────────────────────────────────────────────────────────── */""")

cursor.execute("SELECT slot_id, slot_name, floor, is_available, is_violation_zone FROM dbo.parking_slots ORDER BY slot_id")
slots = cursor.fetchall()

# Use first slot as guard
guard = slots[0]['slot_id']
print(f"IF NOT EXISTS (SELECT 1 FROM dbo.parking_slots WHERE slot_id = '{guard}')")
print("BEGIN")
print("    INSERT INTO dbo.parking_slots (slot_id, slot_name, floor, is_available, is_violation_zone) VALUES")
lines = []
for s in slots:
    avail = 1 if s['is_available'] else 0
    viol = 1 if s['is_violation_zone'] else 0
    lines.append(f"        ({q(s['slot_id'])}, {q(s['slot_name'])}, {q(s['floor'])}, {avail}, {viol})")
print(",\n".join(lines) + ";")
print(f"    PRINT '  Seeded {len(slots)} parking_slots';")
print("END;")

# Backfill floors
print("""
/* Backfill floors lookup from the slots we just seeded. */
INSERT INTO dbo.floors (name)
SELECT DISTINCT ps.floor FROM dbo.parking_slots ps
WHERE ps.floor IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = ps.floor);

IF COL_LENGTH(N'dbo.parking_slots', N'floor_id') IS NOT NULL
    UPDATE ps SET floor_id = f.id
    FROM dbo.parking_slots ps INNER JOIN dbo.floors f ON f.name = ps.floor
    WHERE ps.floor_id IS NULL;
GO
""")

# ── 2. cameras ──
print("""/* ────────────────────────────────────────────────────────────────────────────
   2. cameras — canonical 16-camera fleet (Fernet-encrypted credentials)
   ────────────────────────────────────────────────────────────────────────────
   MERGE so re-running updates fields without inserting duplicates.
   ──────────────────────────────────────────────────────────────────────────── */""")

cursor.execute("SELECT camera_id, name, floor, ip_address, rtsp_port, rtsp_path, username, password_encrypted, enabled, notes FROM dbo.cameras ORDER BY camera_id")
cams = cursor.fetchall()

print("IF OBJECT_ID(N'dbo.cameras', 'U') IS NOT NULL")
print("BEGIN")
print("    MERGE INTO dbo.cameras AS Target")
print("    USING (VALUES")
lines = []
for c in cams:
    en = 1 if c['enabled'] else 0
    lines.append(f"        ({q(c['camera_id'])}, {q(c['name'])}, {q(c['floor'])}, {q(c['ip_address'])}, {c['rtsp_port']}, {q(c['rtsp_path'])}, {q(c['username'])}, {q(c['password_encrypted'])}, {en}, {q(c['notes'])})")
print(",\n".join(lines))
print("""    ) AS Source (camera_id, name, floor, ip_address, rtsp_port, rtsp_path, username, password_encrypted, enabled, notes)
    ON Target.camera_id = Source.camera_id
    WHEN MATCHED THEN
        UPDATE SET
            name = Source.name,
            floor = Source.floor,
            ip_address = Source.ip_address,
            rtsp_port = Source.rtsp_port,
            rtsp_path = Source.rtsp_path,
            username = Source.username,
            password_encrypted = Source.password_encrypted,
            enabled = Source.enabled,
            notes = Source.notes,
            updated_at = GETUTCDATE()
    WHEN NOT MATCHED THEN
        INSERT (camera_id, name, floor, ip_address, rtsp_port, rtsp_path, username, password_encrypted, enabled, notes)
        VALUES (Source.camera_id, Source.name, Source.floor, Source.ip_address, Source.rtsp_port, Source.rtsp_path, Source.username, Source.password_encrypted, Source.enabled, Source.notes);""")
print(f"    PRINT '  Seeded {len(cams)} cameras (canonical fleet).';")
print("END")
print("GO")

# Cameras floor backfill
print("""
/* Ensure new camera floor names exist in floors lookup, then backfill
   cameras.floor_id and cameras.watches_floor_id for the inserted rows. */
INSERT INTO dbo.floors (name)
SELECT DISTINCT t.floor FROM dbo.cameras t
WHERE t.floor IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = t.floor);

IF COL_LENGTH(N'dbo.cameras', N'floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.cameras', N'floor') IS NOT NULL
    UPDATE t SET floor_id = f.id
    FROM dbo.cameras t INNER JOIN dbo.floors f ON f.name = t.floor
    WHERE t.floor_id IS NULL;

IF COL_LENGTH(N'dbo.cameras', N'watches_floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.cameras', N'watches_floor') IS NOT NULL
    UPDATE t SET watches_floor_id = f.id
    FROM dbo.cameras t INNER JOIN dbo.floors f ON f.name = t.watches_floor
    WHERE t.watches_floor_id IS NULL;
GO
""")

# ── 3. zone_occupancy ──
print("""/* ────────────────────────────────────────────────────────────────────────────
   3. zone_occupancy — line-crossing counters (B1, B2, GARAGE-TOTAL)
   ──────────────────────────────────────────────────────────────────────────── */""")

cursor.execute("SELECT zone_id, camera_id, current_count, max_capacity, zone_name, floor FROM dbo.zone_occupancy ORDER BY zone_id")
zones = cursor.fetchall()

print("IF NOT EXISTS (SELECT 1 FROM dbo.zone_occupancy WHERE zone_id = 'B1-PARKING')")
print("BEGIN")
print("    INSERT INTO dbo.zone_occupancy (zone_id, camera_id, current_count, max_capacity, last_updated, zone_name, floor) VALUES")
lines = []
for z in zones:
    lines.append(f"        ({q(z['zone_id'])}, {q(z['camera_id'])}, {z['current_count']}, {z['max_capacity']}, GETUTCDATE(), {q(z['zone_name'])}, {q(z['floor'])})")
print(",\n".join(lines) + ";")
print(f"    PRINT '  Seeded {len(zones)} zone_occupancy rows';")
print("END;")
print("GO")

# ── 4. vehicles ──
print("""
/* ────────────────────────────────────────────────────────────────────────────
   4. vehicles — 5 registered vehicles from live DB
   ──────────────────────────────────────────────────────────────────────────── */""")

cursor.execute("SELECT plate_number, owner_name, vehicle_type, employee_id, is_registered, registered_at, notes, title, is_employee, phone, email FROM dbo.vehicles ORDER BY id")
vehicles = cursor.fetchall()

guard_plate = vehicles[0]['plate_number']
print(f"IF NOT EXISTS (SELECT 1 FROM dbo.vehicles WHERE plate_number = {q(guard_plate)})")
print("BEGIN")
print("    INSERT INTO dbo.vehicles")
print("        (plate_number, owner_name, vehicle_type, employee_id, is_registered, registered_at, notes, title, is_employee, phone, email)")
print("    VALUES")
lines = []
for v in vehicles:
    reg = 1 if v['is_registered'] else 0
    emp = 1 if v['is_employee'] else 0
    lines.append(f"        ({q(v['plate_number'])}, {q(v['owner_name'])}, {q(v['vehicle_type'])}, {q(v['employee_id'])}, {reg}, {dt(v['registered_at'])}, {q(v['notes'])}, {q(v['title'])}, {emp}, {q(v['phone'])}, {q(v['email'])})")
print(",\n".join(lines) + ";")
print(f"    PRINT '  Seeded {len(vehicles)} vehicles';")
print("END;")
print("GO")

# ── 5. slot_status — latest per slot ──
print("""
/* ────────────────────────────────────────────────────────────────────────────
   5. slot_status — latest state per slot (32 rows)
   ──────────────────────────────────────────────────────────────────────────── */""")

cursor.execute("""
    SELECT ss.slot_id, ss.plate_number, ss.status, ss.time
    FROM dbo.slot_status ss
    INNER JOIN (SELECT slot_id, MAX(id) as max_id FROM dbo.slot_status GROUP BY slot_id) latest
    ON ss.id = latest.max_id
    ORDER BY ss.slot_id
""")
statuses = cursor.fetchall()

guard_slot = statuses[0]['slot_id']
print(f"IF NOT EXISTS (SELECT 1 FROM dbo.slot_status WHERE slot_id = {q(guard_slot)})")
print("BEGIN")
print("    INSERT INTO dbo.slot_status (slot_id, plate_number, status, time) VALUES")
lines = []
for s in statuses:
    pn = q(s['plate_number']) if s['plate_number'] else "NULL"
    lines.append(f"        ({q(s['slot_id'])}, {pn}, {q(s['status'])}, {dt(s['time'])})")
print(",\n".join(lines) + ";")
print(f"    PRINT '  Seeded {len(statuses)} slot_status rows (latest per slot)';")
print("END;")
print("""
/* Backfill parking_slot_id (INT FK partner) for the new rows. */
IF COL_LENGTH(N'dbo.slot_status', N'parking_slot_id') IS NOT NULL
    UPDATE t SET parking_slot_id = ps.id
    FROM dbo.slot_status t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
    WHERE t.parking_slot_id IS NULL;
GO
""")

# ── 6. entry_exit_log ──
print("""/* ────────────────────────────────────────────────────────────────────────────
   6. entry_exit_log — 26 gate crossings from live ANPR
   ──────────────────────────────────────────────────────────────────────────── */""")

cursor.execute("SELECT plate_number, vehicle_type, gate, camera_id, event_time, parking_duration, snapshot_path, is_test FROM dbo.entry_exit_log ORDER BY id")
eels = cursor.fetchall()

print(f"IF NOT EXISTS (SELECT 1 FROM dbo.entry_exit_log WHERE plate_number = {q(eels[0]['plate_number'])} AND event_time = {dt(eels[0]['event_time'])})")
print("BEGIN")
print("    INSERT INTO dbo.entry_exit_log")
print("        (plate_number, vehicle_type, gate, camera_id, event_time, parking_duration, snapshot_path, is_test)")
print("    VALUES")
lines = []
for e in eels:
    test = 1 if e['is_test'] else 0
    lines.append(f"        ({q(e['plate_number'])}, {q(e['vehicle_type'])}, {q(e['gate'])}, {q(e['camera_id'])}, {dt(e['event_time'])}, {q(e['parking_duration'])}, {q(e['snapshot_path'])}, {test})")
print(",\n".join(lines) + ";")
print(f"    PRINT '  Seeded {len(eels)} entry_exit_log rows';")
print("END;")
print("GO")

# ── 7. parking_sessions ──
print("""
/* ────────────────────────────────────────────────────────────────────────────
   7. parking_sessions — 17 real sessions from live DB
   ──────────────────────────────────────────────────────────────────────────── */""")

cursor.execute("""SELECT plate_number, vehicle_type, is_employee, entry_time, exit_time, duration_seconds,
       entry_camera_id, exit_camera_id, entry_snapshot_path, exit_snapshot_path,
       floor, zone_id, zone_name, slot_id, slot_number, parked_at, slot_left_at,
       slot_camera_id, slot_snapshot_path, status
FROM dbo.parking_sessions ORDER BY id""")
sessions = cursor.fetchall()

print(f"IF NOT EXISTS (SELECT 1 FROM dbo.parking_sessions WHERE plate_number = {q(sessions[0]['plate_number'])} AND entry_time = {dt(sessions[0]['entry_time'])})")
print("BEGIN")
print("    INSERT INTO dbo.parking_sessions")
print("        (plate_number, vehicle_type, is_employee, entry_time, exit_time, duration_seconds,")
print("         entry_camera_id, exit_camera_id, entry_snapshot_path, exit_snapshot_path,")
print("         floor, zone_id, zone_name, slot_id, slot_number, parked_at, slot_left_at,")
print("         slot_camera_id, slot_snapshot_path, status)")
print("    VALUES")
lines = []
for s in sessions:
    emp = 1 if s['is_employee'] else 0
    lines.append(f"        ({q(s['plate_number'])}, {q(s['vehicle_type'])}, {emp}, {dt(s['entry_time'])}, {dt(s['exit_time'])}, {q(s['duration_seconds'])}, {q(s['entry_camera_id'])}, {q(s['exit_camera_id'])}, {q(s['entry_snapshot_path'])}, {q(s['exit_snapshot_path'])}, {q(s['floor'])}, {q(s['zone_id'])}, {q(s['zone_name'])}, {q(s['slot_id'])}, {q(s['slot_number'])}, {dt(s['parked_at'])}, {dt(s['slot_left_at'])}, {q(s['slot_camera_id'])}, {q(s['slot_snapshot_path'])}, {q(s['status'])})")
print(",\n".join(lines) + ";")
print(f"    PRINT '  Seeded {len(sessions)} parking_sessions rows';")
print("END;")
print("""
/* Backfill floor_id / parking_slot_id integer FK partners. */
IF COL_LENGTH(N'dbo.parking_sessions', N'floor_id') IS NOT NULL
    UPDATE t SET floor_id = f.id
    FROM dbo.parking_sessions t INNER JOIN dbo.floors f ON f.name = t.floor
    WHERE t.floor_id IS NULL;

IF COL_LENGTH(N'dbo.parking_sessions', N'parking_slot_id') IS NOT NULL
    UPDATE t SET parking_slot_id = ps.id
    FROM dbo.parking_sessions t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
    WHERE t.parking_slot_id IS NULL;
GO
""")

# ── 8. alerts ──
print("""/* ────────────────────────────────────────────────────────────────────────────
   8. alerts — 32 real alerts from live system
   ──────────────────────────────────────────────────────────────────────────── */""")

cursor.execute("""SELECT alert_type, camera_id, zone_id, zone_name, slot_id, slot_number, event_type,
       description, snapshot_path, is_test, is_resolved, triggered_at, resolved_at,
       plate_number, severity, location_display
FROM dbo.alerts ORDER BY id""")
alerts = cursor.fetchall()

print(f"IF NOT EXISTS (SELECT 1 FROM dbo.alerts WHERE alert_type = {q(alerts[0]['alert_type'])} AND triggered_at = {dt(alerts[0]['triggered_at'])})")
print("BEGIN")
print("    INSERT INTO dbo.alerts")
print("        (alert_type, camera_id, zone_id, zone_name, slot_id, slot_number, event_type,")
print("         description, snapshot_path, is_test, is_resolved, triggered_at, resolved_at,")
print("         plate_number, severity, location_display)")
print("    VALUES")
lines = []
for a in alerts:
    test = 1 if a['is_test'] else 0
    resolved = 1 if a['is_resolved'] else 0
    lines.append(f"        ({q(a['alert_type'])}, {q(a['camera_id'])}, {q(a['zone_id'])}, {q(a['zone_name'])}, {q(a['slot_id'])}, {q(a['slot_number'])}, {q(a['event_type'])}, {q(a['description'])}, {q(a['snapshot_path'])}, {test}, {resolved}, {dt(a['triggered_at'])}, {dt(a['resolved_at'])}, {q(a['plate_number'])}, {q(a['severity'])}, {q(a['location_display'])})")
print(",\n".join(lines) + ";")
print(f"    PRINT '  Seeded {len(alerts)} alerts rows';")
print("END;")
print("""
/* Backfill parking_slot_id integer FK partner for the new alerts. */
IF COL_LENGTH(N'dbo.alerts', N'parking_slot_id') IS NOT NULL
    UPDATE t SET parking_slot_id = ps.id
    FROM dbo.alerts t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
    WHERE t.parking_slot_id IS NULL;
GO
""")

# ── 9. camera_feeds — empty in live ──
print("""/* ────────────────────────────────────────────────────────────────────────────
   9. camera_feeds — empty in live DB, nothing to seed
   ──────────────────────────────────────────────────────────────────────────── */
/* No rows to seed — camera_feeds table is empty in the live database. */
GO
""")

# ── 10. Floor alias normalization ──
print("""/* ────────────────────────────────────────────────────────────────────────────
   10. Floor-name alias normalization (idempotent; safe to re-run)
   ────────────────────────────────────────────────────────────────────────────
   Cameras seed introduces floor='Ground'; PMS-AI may at some point write
   floor='Ground Floor' for the same physical floor. Without normalization
   the dashboard splits them into separate buckets. This block:
     1. re-points integer FK columns from "Ground Floor" → "Ground";
     2. rewrites legacy `floor` string columns on every source table;
     3. deletes the now-empty "Ground Floor" row from `floors`.
   Append rows to @aliases to add more name → canonical mappings.
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @aliases TABLE (alias NVARCHAR(50), canonical NVARCHAR(50));
INSERT INTO @aliases (alias, canonical) VALUES
    ('Ground Floor', 'Ground');
    -- additional aliases here, e.g. ('GF', 'Ground'), ('Basement 1', 'B1')

DECLARE @alias NVARCHAR(50), @canonical NVARCHAR(50), @from_id INT, @to_id INT;
DECLARE alias_cur CURSOR LOCAL FAST_FORWARD FOR SELECT alias, canonical FROM @aliases;
OPEN alias_cur;
FETCH NEXT FROM alias_cur INTO @alias, @canonical;
WHILE @@FETCH_STATUS = 0
BEGIN
    SELECT @from_id = id FROM dbo.floors WHERE name = @alias;
    SELECT @to_id   = id FROM dbo.floors WHERE name = @canonical;

    IF @from_id IS NOT NULL AND @to_id IS NOT NULL AND @from_id <> @to_id
    BEGIN
        IF COL_LENGTH(N'dbo.parking_slots', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.parking_slots   SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF COL_LENGTH(N'dbo.parking_sessions', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.parking_sessions SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF COL_LENGTH(N'dbo.cameras', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.cameras SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF COL_LENGTH(N'dbo.cameras', N'watches_floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.cameras SET watches_floor_id = @t WHERE watches_floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF COL_LENGTH(N'dbo.alerts', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.alerts SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF OBJECT_ID(N'dbo.floor_occupancy', N'U') IS NOT NULL
           AND COL_LENGTH(N'dbo.floor_occupancy', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.floor_occupancy SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;

        IF COL_LENGTH(N'dbo.parking_slots', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.parking_slots   SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF COL_LENGTH(N'dbo.parking_sessions', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.parking_sessions SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF COL_LENGTH(N'dbo.cameras', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.cameras SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF COL_LENGTH(N'dbo.cameras', N'watches_floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.cameras SET watches_floor = @t WHERE watches_floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF COL_LENGTH(N'dbo.alerts', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.alerts SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF OBJECT_ID(N'dbo.floor_occupancy', N'U') IS NOT NULL
           AND COL_LENGTH(N'dbo.floor_occupancy', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.floor_occupancy SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;

        DELETE FROM dbo.floors WHERE id = @from_id;
        PRINT '  Normalized floor alias: ' + @alias + ' -> ' + @canonical;
    END

    FETCH NEXT FROM alias_cur INTO @alias, @canonical;
END
CLOSE alias_cur;
DEALLOCATE alias_cur;
GO

/* Re-apply contiguous sort_order on floors (0..n-1). */
;WITH ordered AS (
    SELECT id, DENSE_RANK() OVER (ORDER BY name) - 1 AS new_order FROM dbo.floors
)
UPDATE f SET sort_order = o.new_order
FROM dbo.floors f INNER JOIN ordered o ON o.id = f.id
WHERE f.sort_order != o.new_order;
GO

PRINT '──────────────────────────────────────────────';
PRINT '  seed.sql finished';
PRINT '──────────────────────────────────────────────';
GO
""")

conn.close()
print("-- Generated from live database", file=sys.stderr)
