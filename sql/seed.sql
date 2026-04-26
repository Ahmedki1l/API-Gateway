/* ============================================================================
   seed.sql — sample data for the Parking System database

   Optional companion to bootstrap.sql. Run this AFTER bootstrap.sql to
   populate the dashboard with enough realistic rows that every tab
   (Dashboard, Alerts, Vehicles, Entry/Exit, Occupancy) shows non-empty
   content on a freshly bootstrapped database.

   Idempotent — every block is guarded by IF NOT EXISTS / WHERE ... NOT IN
   so re-running the file does nothing on a populated DB.

   What is intentionally NOT in this file:
     - cameras            — bootstrap.sql already seeds the canonical 16-camera
                            fleet with encrypted credentials.
     - alembic_version    — bootstrap.sql pins it to a specific head.
     - real plate numbers, names, phone numbers — every value below is
                            obviously synthetic.
     - secrets / tokens / passwords of any kind.

   Run:
     sqlcmd -E -S localhost -d damanat_pms -i sql/seed.sql
     (or `-U sa -P "..."` for SQL auth)

   Dates are anchored to SYSUTCDATETIME() so the data stays "recent" no
   matter when the script runs.
   ============================================================================ */

SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

PRINT '──────────────────────────────────────────────';
PRINT '  Parking System — seed.sql (sample data)';
PRINT '──────────────────────────────────────────────';

DECLARE @now DATETIME2 = SYSUTCDATETIME();

/* ────────────────────────────────────────────────────────────────────────────
   1. parking_slots — extend the 6 bootstrap slots up to 30 (15 per floor)
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM dbo.parking_slots WHERE slot_id = 'B1_01')
BEGIN
    INSERT INTO dbo.parking_slots (slot_id, slot_name, floor, is_available, is_violation_zone) VALUES
        ('B1_01', 'Slot B1 01', 'B1', 1, 0),
        ('B1_02', 'Slot B1 02', 'B1', 1, 0),
        ('B1_03', 'Slot B1 03', 'B1', 1, 0),
        ('B1_04', 'Slot B1 04', 'B1', 1, 0),
        ('B1_05', 'Slot B1 05', 'B1', 1, 0),
        ('B1_06', 'Slot B1 06', 'B1', 1, 0),
        ('B1_07', 'Slot B1 07', 'B1', 1, 0),
        ('B1_08', 'Slot B1 08', 'B1', 1, 0),
        ('B1_09', 'Slot B1 09', 'B1', 1, 0),
        ('B1_10', 'Slot B1 10', 'B1', 1, 0),
        ('B1_11', 'Slot B1 11', 'B1', 1, 1),  -- violation zone (handicap)
        ('B1_12', 'Slot B1 12', 'B1', 1, 0),
        ('B2_01', 'Slot B2 01', 'B2', 1, 0),
        ('B2_02', 'Slot B2 02', 'B2', 1, 0),
        ('B2_03', 'Slot B2 03', 'B2', 1, 0),
        ('B2_04', 'Slot B2 04', 'B2', 1, 0),
        ('B2_05', 'Slot B2 05', 'B2', 1, 0),
        ('B2_06', 'Slot B2 06', 'B2', 1, 0),
        ('B2_07', 'Slot B2 07', 'B2', 1, 0),
        ('B2_08', 'Slot B2 08', 'B2', 1, 0),
        ('B2_09', 'Slot B2 09', 'B2', 1, 0),
        ('B2_10', 'Slot B2 10', 'B2', 1, 0),
        ('B2_11', 'Slot B2 11', 'B2', 1, 0),
        ('B2_12', 'Slot B2 12', 'B2', 1, 1);  -- violation zone (handicap)
    PRINT '  Seeded 24 additional parking_slots (12 per floor)';
END;

/* Re-run the floor_id backfill so the new rows get their FK link. */
IF COL_LENGTH(N'dbo.parking_slots', N'floor_id') IS NOT NULL
    UPDATE ps SET floor_id = f.id
    FROM dbo.parking_slots ps INNER JOIN dbo.floors f ON f.name = ps.floor
    WHERE ps.floor_id IS NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   2. vehicles — 15 synthetic plates: employees, visitors, blacklisted
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @now DATETIME2 = SYSUTCDATETIME();

IF NOT EXISTS (SELECT 1 FROM dbo.vehicles WHERE plate_number = 'ABC-1001')
BEGIN
    INSERT INTO dbo.vehicles
        (plate_number, owner_name, vehicle_type, employee_id, is_registered, registered_at, notes, title, is_employee, phone, email)
    VALUES
        ('ABC-1001', 'Test User 01', 'sedan',     'EMP-001', 1, DATEADD(day, -120, @now), 'Sample employee vehicle', 'Mr',  1, '+966-5XX-XXX-001', 'user01@example.test'),
        ('ABC-1002', 'Test User 02', 'sedan',     'EMP-002', 1, DATEADD(day, -110, @now), NULL,                      'Ms',  1, '+966-5XX-XXX-002', 'user02@example.test'),
        ('ABC-1003', 'Test User 03', 'suv',       'EMP-003', 1, DATEADD(day, -100, @now), NULL,                      'Mr',  1, '+966-5XX-XXX-003', 'user03@example.test'),
        ('ABC-1004', 'Test User 04', 'sedan',     'EMP-004', 1, DATEADD(day,  -90, @now), NULL,                      'Mrs', 1, '+966-5XX-XXX-004', 'user04@example.test'),
        ('ABC-1005', 'Test User 05', 'truck',     'EMP-005', 1, DATEADD(day,  -80, @now), NULL,                      'Mr',  1, '+966-5XX-XXX-005', 'user05@example.test'),
        ('ABC-1006', 'Test User 06', 'sedan',     'EMP-006', 1, DATEADD(day,  -70, @now), NULL,                      'Ms',  1, '+966-5XX-XXX-006', 'user06@example.test'),
        ('ABC-1007', 'Test User 07', 'suv',       'EMP-007', 1, DATEADD(day,  -60, @now), NULL,                      'Mr',  1, '+966-5XX-XXX-007', 'user07@example.test'),
        ('VIS-2001', 'Visitor 01',   'sedan',     NULL,      1, DATEADD(day,  -30, @now), 'Visitor — daily pass',    '',    0, '+966-5XX-XXX-101', NULL),
        ('VIS-2002', 'Visitor 02',   'sedan',     NULL,      1, DATEADD(day,  -25, @now), NULL,                      '',    0, '+966-5XX-XXX-102', NULL),
        ('VIS-2003', 'Visitor 03',   'suv',       NULL,      1, DATEADD(day,  -20, @now), NULL,                      '',    0, '+966-5XX-XXX-103', NULL),
        ('VIS-2004', 'Visitor 04',   'sedan',     NULL,      1, DATEADD(day,  -15, @now), NULL,                      '',    0, '+966-5XX-XXX-104', NULL),
        ('VIS-2005', 'Visitor 05',   'truck',     NULL,      1, DATEADD(day,  -10, @now), NULL,                      '',    0, '+966-5XX-XXX-105', NULL),
        ('UNK-3001', 'Unknown 01',   'sedan',     NULL,      0, NULL,                     'Detected but not registered', '', 0, NULL, NULL),
        ('UNK-3002', 'Unknown 02',   'motorbike', NULL,      0, NULL,                     'Detected but not registered', '', 0, NULL, NULL),
        ('BLK-9001', 'Blacklisted',  'sedan',     NULL,      1, DATEADD(day, -200, @now), 'Blacklisted — do not allow entry', '', 0, NULL, NULL);
    PRINT '  Seeded 15 vehicles';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   3. slot_status — current state for ~20 slots (mix OCCUPIED / FREE)
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @now DATETIME2 = SYSUTCDATETIME();

IF NOT EXISTS (SELECT 1 FROM dbo.slot_status WHERE slot_id = 'B1_CRO' AND plate_number = 'ABC-1001')
BEGIN
    INSERT INTO dbo.slot_status (slot_id, plate_number, status, time) VALUES
        ('B1_CRO', 'ABC-1001', 'OCCUPIED', DATEADD(minute, -45, @now)),
        ('B1_CTO', 'ABC-1002', 'OCCUPIED', DATEADD(minute, -90, @now)),
        ('B1_CFO', NULL,       'FREE',     DATEADD(minute, -10, @now)),
        ('B1_01',  'ABC-1003', 'OCCUPIED', DATEADD(minute, -120, @now)),
        ('B1_02',  NULL,       'FREE',     DATEADD(minute, -5, @now)),
        ('B1_03',  'VIS-2001', 'OCCUPIED', DATEADD(minute, -200, @now)),
        ('B1_04',  NULL,       'FREE',     DATEADD(minute, -3, @now)),
        ('B1_05',  'ABC-1004', 'OCCUPIED', DATEADD(minute, -60, @now)),
        ('B1_06',  NULL,       'FREE',     DATEADD(minute, -7, @now)),
        ('B1_07',  'VIS-2002', 'OCCUPIED', DATEADD(minute, -300, @now)),
        ('B1_11',  'UNK-3001', 'OCCUPIED', DATEADD(minute, -25, @now)),  -- intrusion (violation zone)
        ('B2_14',  NULL,       'FREE',     DATEADD(minute, -2, @now)),
        ('B2_15',  'ABC-1005', 'OCCUPIED', DATEADD(minute, -150, @now)),
        ('B2_16',  NULL,       'FREE',     DATEADD(minute, -8, @now)),
        ('B2_01',  'ABC-1006', 'OCCUPIED', DATEADD(minute, -75, @now)),
        ('B2_02',  NULL,       'FREE',     DATEADD(minute, -1, @now)),
        ('B2_03',  'VIS-2003', 'OCCUPIED', DATEADD(minute, -240, @now)),
        ('B2_04',  NULL,       'FREE',     DATEADD(minute, -4, @now)),
        ('B2_05',  'ABC-1007', 'OCCUPIED', DATEADD(minute, -100, @now)),
        ('B2_12',  'UNK-3002', 'OCCUPIED', DATEADD(minute, -15, @now)); -- intrusion (violation zone)
    PRINT '  Seeded 20 slot_status rows';
END;

/* Backfill parking_slot_id (INT FK partner) for the new rows. */
IF COL_LENGTH(N'dbo.slot_status', N'parking_slot_id') IS NOT NULL
    UPDATE t SET parking_slot_id = ps.id
    FROM dbo.slot_status t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
    WHERE t.parking_slot_id IS NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   4. entry_exit_log — last 7 days of gate crossings (~40 rows)
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @now DATETIME2 = SYSUTCDATETIME();

IF NOT EXISTS (SELECT 1 FROM dbo.entry_exit_log WHERE snapshot_path = 'detection_images/seed_entry_001.jpg')
BEGIN
    INSERT INTO dbo.entry_exit_log
        (plate_number, vehicle_id, vehicle_type, gate, camera_id, event_time, parking_duration, snapshot_path, is_test, plate_confidence)
    SELECT s.plate_number, v.id, s.vehicle_type, s.gate, s.camera_id, s.event_time, s.parking_duration, s.snapshot_path, 0, s.plate_confidence
    FROM (VALUES
        -- Today
        ('ABC-1001', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -2,   @now), NULL,    'detection_images/seed_entry_001.jpg', 0.97),
        ('ABC-1002', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -3,   @now), NULL,    'detection_images/seed_entry_002.jpg', 0.95),
        ('ABC-1003', 'suv',       'entry', 'ANPR-Entry', DATEADD(hour, -4,   @now), NULL,    'detection_images/seed_entry_003.jpg', 0.92),
        ('VIS-2001', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -5,   @now), NULL,    'detection_images/seed_entry_004.jpg', 0.89),
        ('ABC-1004', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -6,   @now), NULL,    'detection_images/seed_entry_005.jpg', 0.94),
        ('ABC-1005', 'truck',     'entry', 'ANPR-Entry', DATEADD(hour, -7,   @now), NULL,    'detection_images/seed_entry_006.jpg', 0.91),
        ('ABC-1001', 'sedan',     'exit',  'ANPR-Exit',  DATEADD(hour, -1,   @now), 3600,    'detection_images/seed_exit_001.jpg',  0.96),
        ('VIS-2002', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -8,   @now), NULL,    'detection_images/seed_entry_007.jpg', 0.88),
        -- Yesterday
        ('ABC-1006', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -26,  @now), NULL,    'detection_images/seed_entry_010.jpg', 0.93),
        ('ABC-1006', 'sedan',     'exit',  'ANPR-Exit',  DATEADD(hour, -18,  @now), 28800,   'detection_images/seed_exit_010.jpg',  0.95),
        ('ABC-1007', 'suv',       'entry', 'ANPR-Entry', DATEADD(hour, -27,  @now), NULL,    'detection_images/seed_entry_011.jpg', 0.90),
        ('ABC-1007', 'suv',       'exit',  'ANPR-Exit',  DATEADD(hour, -19,  @now), 28800,   'detection_images/seed_exit_011.jpg',  0.92),
        ('VIS-2003', 'suv',       'entry', 'ANPR-Entry', DATEADD(hour, -30,  @now), NULL,    'detection_images/seed_entry_012.jpg', 0.87),
        ('VIS-2003', 'suv',       'exit',  'ANPR-Exit',  DATEADD(hour, -28,  @now), 7200,    'detection_images/seed_exit_012.jpg',  0.89),
        ('VIS-2004', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -32,  @now), NULL,    'detection_images/seed_entry_013.jpg', 0.91),
        ('VIS-2004', 'sedan',     'exit',  'ANPR-Exit',  DATEADD(hour, -29,  @now), 10800,   'detection_images/seed_exit_013.jpg',  0.94),
        ('BLK-9001', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -36,  @now), NULL,    'detection_images/seed_entry_014.jpg', 0.85),
        -- Earlier this week
        ('ABC-1001', 'sedan',     'entry', 'ANPR-Entry', DATEADD(day,  -2,   @now), NULL,    'detection_images/seed_entry_020.jpg', 0.96),
        ('ABC-1001', 'sedan',     'exit',  'ANPR-Exit',  DATEADD(day,  -2,   DATEADD(hour, 8, @now)), 28800, 'detection_images/seed_exit_020.jpg', 0.95),
        ('ABC-1002', 'sedan',     'entry', 'ANPR-Entry', DATEADD(day,  -3,   @now), NULL,    'detection_images/seed_entry_021.jpg', 0.94),
        ('ABC-1002', 'sedan',     'exit',  'ANPR-Exit',  DATEADD(day,  -3,   DATEADD(hour, 9, @now)), 32400, 'detection_images/seed_exit_021.jpg', 0.93),
        ('ABC-1003', 'suv',       'entry', 'ANPR-Entry', DATEADD(day,  -4,   @now), NULL,    'detection_images/seed_entry_022.jpg', 0.92),
        ('ABC-1003', 'suv',       'exit',  'ANPR-Exit',  DATEADD(day,  -4,   DATEADD(hour, 7, @now)), 25200, 'detection_images/seed_exit_022.jpg', 0.91),
        ('VIS-2005', 'truck',     'entry', 'ANPR-Entry', DATEADD(day,  -5,   @now), NULL,    'detection_images/seed_entry_023.jpg', 0.86),
        ('VIS-2005', 'truck',     'exit',  'ANPR-Exit',  DATEADD(day,  -5,   DATEADD(hour, 6, @now)), 21600, 'detection_images/seed_exit_023.jpg', 0.88),
        ('ABC-1004', 'sedan',     'entry', 'ANPR-Entry', DATEADD(day,  -6,   @now), NULL,    'detection_images/seed_entry_024.jpg', 0.95),
        ('ABC-1004', 'sedan',     'exit',  'ANPR-Exit',  DATEADD(day,  -6,   DATEADD(hour, 9, @now)), 32400, 'detection_images/seed_exit_024.jpg', 0.94),
        ('ABC-1005', 'truck',     'entry', 'ANPR-Entry', DATEADD(day,  -7,   @now), NULL,    'detection_images/seed_entry_025.jpg', 0.90),
        ('ABC-1005', 'truck',     'exit',  'ANPR-Exit',  DATEADD(day,  -7,   DATEADD(hour, 8, @now)), 28800, 'detection_images/seed_exit_025.jpg', 0.92),
        ('UNK-3001', 'sedan',     'entry', 'ANPR-Entry', DATEADD(hour, -1,   @now), NULL,    'detection_images/seed_entry_030.jpg', 0.62),
        ('UNK-3002', 'motorbike', 'entry', 'ANPR-Entry', DATEADD(minute, -40, @now), NULL,   'detection_images/seed_entry_031.jpg', 0.55)
    ) AS s (plate_number, vehicle_type, gate, camera_id, event_time, parking_duration, snapshot_path, plate_confidence)
    LEFT JOIN dbo.vehicles v ON v.plate_number = s.plate_number;
    PRINT '  Seeded entry_exit_log rows';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   5. parking_sessions — derived from entry_exit; ~5 still active
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @now DATETIME2 = SYSUTCDATETIME();

IF NOT EXISTS (SELECT 1 FROM dbo.parking_sessions WHERE entry_snapshot_path = 'detection_images/seed_entry_001.jpg')
BEGIN
    INSERT INTO dbo.parking_sessions
        (plate_number, vehicle_id, vehicle_type, is_employee, entry_time, exit_time, duration_seconds,
         entry_camera_id, exit_camera_id, entry_snapshot_path, exit_snapshot_path,
         floor, slot_id, slot_number, parked_at, slot_camera_id, slot_snapshot_path, status)
    SELECT s.plate_number, v.id, s.vehicle_type, s.is_employee, s.entry_time, s.exit_time, s.duration_seconds,
           s.entry_camera_id, s.exit_camera_id, s.entry_snapshot_path, s.exit_snapshot_path,
           s.floor, s.slot_id, s.slot_number, s.parked_at, s.slot_camera_id, s.slot_snapshot_path, s.status
    FROM (VALUES
        -- Active sessions (no exit yet) — these match slot_status OCCUPIED rows above
        ('ABC-1002', 'sedan',     1, DATEADD(hour, -3,   @now),                        NULL, NULL, 'ANPR-Entry', NULL,         'detection_images/seed_entry_002.jpg', NULL, 'B1', 'B1_CTO', 'B1 CTO', DATEADD(minute, -90,  @now), 'Cam_03', 'detection_images/seed_slot_002.jpg', 'parked'),
        ('ABC-1003', 'suv',       1, DATEADD(hour, -4,   @now),                        NULL, NULL, 'ANPR-Entry', NULL,         'detection_images/seed_entry_003.jpg', NULL, 'B1', 'B1_01',  'B1 01',  DATEADD(minute, -120, @now), 'Cam_04', 'detection_images/seed_slot_003.jpg', 'parked'),
        ('VIS-2001', 'sedan',     0, DATEADD(hour, -5,   @now),                        NULL, NULL, 'ANPR-Entry', NULL,         'detection_images/seed_entry_004.jpg', NULL, 'B1', 'B1_03',  'B1 03',  DATEADD(minute, -200, @now), 'Cam_05', 'detection_images/seed_slot_004.jpg', 'parked'),
        ('ABC-1004', 'sedan',     1, DATEADD(hour, -6,   @now),                        NULL, NULL, 'ANPR-Entry', NULL,         'detection_images/seed_entry_005.jpg', NULL, 'B1', 'B1_05',  'B1 05',  DATEADD(minute, -60,  @now), 'Cam_06', 'detection_images/seed_slot_005.jpg', 'parked'),
        ('ABC-1005', 'truck',     1, DATEADD(hour, -7,   @now),                        NULL, NULL, 'ANPR-Entry', NULL,         'detection_images/seed_entry_006.jpg', NULL, 'B2', 'B2_15',  'B2 15',  DATEADD(minute, -150, @now), 'Cam_09', 'detection_images/seed_slot_006.jpg', 'parked'),
        -- Closed sessions
        ('ABC-1001', 'sedan',     1, DATEADD(hour, -2,   @now), DATEADD(hour, -1,    @now), 3600,  'ANPR-Entry', 'ANPR-Exit',  'detection_images/seed_entry_001.jpg', 'detection_images/seed_exit_001.jpg', 'B1', 'B1_CRO', 'B1 CRO', DATEADD(hour, -2, @now), 'Cam_03', 'detection_images/seed_slot_001.jpg', 'closed'),
        ('ABC-1006', 'sedan',     1, DATEADD(hour, -26,  @now), DATEADD(hour, -18,   @now), 28800, 'ANPR-Entry', 'ANPR-Exit',  'detection_images/seed_entry_010.jpg', 'detection_images/seed_exit_010.jpg', 'B2', 'B2_01',  'B2 01',  DATEADD(hour, -25, @now), 'Cam_09', NULL, 'closed'),
        ('ABC-1007', 'suv',       1, DATEADD(hour, -27,  @now), DATEADD(hour, -19,   @now), 28800, 'ANPR-Entry', 'ANPR-Exit',  'detection_images/seed_entry_011.jpg', 'detection_images/seed_exit_011.jpg', 'B2', 'B2_05',  'B2 05',  DATEADD(hour, -26, @now), 'Cam_10', NULL, 'closed'),
        ('VIS-2003', 'suv',       0, DATEADD(hour, -30,  @now), DATEADD(hour, -28,   @now), 7200,  'ANPR-Entry', 'ANPR-Exit',  'detection_images/seed_entry_012.jpg', 'detection_images/seed_exit_012.jpg', 'B2', 'B2_03',  'B2 03',  DATEADD(hour, -29, @now), 'Cam_10', NULL, 'closed'),
        ('VIS-2004', 'sedan',     0, DATEADD(hour, -32,  @now), DATEADD(hour, -29,   @now), 10800, 'ANPR-Entry', 'ANPR-Exit',  'detection_images/seed_entry_013.jpg', 'detection_images/seed_exit_013.jpg', 'B1', 'B1_07',  'B1 07',  DATEADD(hour, -31, @now), 'Cam_05', NULL, 'closed'),
        ('VIS-2002', 'sedan',     0, DATEADD(hour, -8,   @now),                        NULL, NULL, 'ANPR-Entry', NULL,         'detection_images/seed_entry_007.jpg', NULL, 'B1', 'B1_07',  'B1 07',  DATEADD(minute, -300, @now), 'Cam_05', NULL, 'parked')
    ) AS s (plate_number, vehicle_type, is_employee, entry_time, exit_time, duration_seconds,
            entry_camera_id, exit_camera_id, entry_snapshot_path, exit_snapshot_path,
            floor, slot_id, slot_number, parked_at, slot_camera_id, slot_snapshot_path, status)
    LEFT JOIN dbo.vehicles v ON v.plate_number = s.plate_number;
    PRINT '  Seeded parking_sessions rows';
END;

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

/* ────────────────────────────────────────────────────────────────────────────
   6. alerts — last 14 days, mix of types/severities/resolved
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @now DATETIME2 = SYSUTCDATETIME();

IF NOT EXISTS (SELECT 1 FROM dbo.alerts WHERE snapshot_path = 'detection_images/seed_alert_001.jpg')
BEGIN
    INSERT INTO dbo.alerts
        (alert_type, camera_id, zone_id, zone_name, slot_id, slot_number, event_type,
         description, snapshot_path, is_test, is_resolved, triggered_at, resolved_at,
         plate_number, severity, location_display, vehicle_id)
    SELECT s.alert_type, s.camera_id, s.zone_id, s.zone_name, s.slot_id, s.slot_number, s.event_type,
           s.description, s.snapshot_path, 0, s.is_resolved, s.triggered_at, s.resolved_at,
           s.plate_number, s.severity, s.location_display, v.id
    FROM (VALUES
        -- Today
        ('intrusion',          'Cam_05',     'B1-PARKING', 'B1 Parking', 'B1_11', 'B1 11', 'slot_violation',     'Vehicle parked in handicap-only zone',           'detection_images/seed_alert_001.jpg', 0, DATEADD(minute, -25, @now), NULL,                              'UNK-3001', 'critical', 'B1 / Slot 11',     CAST(NULL AS NVARCHAR(50))),
        ('intrusion',          'Cam_11',     'B2-PARKING', 'B2 Parking', 'B2_12', 'B2 12', 'slot_violation',     'Unknown vehicle in violation zone',              'detection_images/seed_alert_002.jpg', 0, DATEADD(minute, -15, @now), NULL,                              'UNK-3002', 'critical', 'B2 / Slot 12',     NULL),
        ('unauthorized_entry', 'ANPR-Entry', NULL,         NULL,         NULL,    NULL,    'blacklist_match',    'Blacklisted plate attempted entry',              'detection_images/seed_alert_003.jpg', 0, DATEADD(minute, -40, @now), NULL,                              'BLK-9001', 'critical', 'Entry Gate',       NULL),
        ('unknown_plate',      'ANPR-Entry', NULL,         NULL,         NULL,    NULL,    'low_confidence',     'Low-confidence plate read',                      'detection_images/seed_alert_004.jpg', 0, DATEADD(hour,   -1, @now), NULL,                              'UNK-3001', 'warning',  'Entry Gate',       NULL),
        ('parking_violation',  'Cam_05',     'B1-PARKING', 'B1 Parking', 'B1_03', 'B1 03', 'duration_exceeded',  'Visitor exceeded 4-hour parking limit',          'detection_images/seed_alert_005.jpg', 0, DATEADD(hour,   -2, @now), NULL,                              'VIS-2001', 'warning',  'B1 / Slot 03',     NULL),
        -- Yesterday
        ('camera_offline',     'Cam_07',     NULL,         NULL,         NULL,    NULL,    'connectivity_lost',  'Camera Cam_07 stopped responding',               NULL,                                  0, DATEADD(hour,  -20, @now), DATEADD(hour, -18, @now),         NULL,       'warning',  'B1 / Camera Cam_07', NULL),
        ('parking_violation',  'Cam_09',     'B2-PARKING', 'B2 Parking', 'B2_03', 'B2 03', 'duration_exceeded',  'Visitor exceeded 4-hour parking limit',          'detection_images/seed_alert_006.jpg', 1, DATEADD(hour,  -22, @now), DATEADD(hour, -19, @now),         'VIS-2003', 'warning',  'B2 / Slot 03',     NULL),
        ('intrusion',          'Cam_06',     'B1-PARKING', 'B1 Parking', 'B1_06', 'B1 06', 'unregistered_park',  'Unregistered vehicle parked',                    'detection_images/seed_alert_007.jpg', 1, DATEADD(hour,  -28, @now), DATEADD(hour, -27, @now),         'UNK-3002', 'info',     'B1 / Slot 06',     NULL),
        -- Earlier this week
        ('unauthorized_entry', 'ANPR-Entry', NULL,         NULL,         NULL,    NULL,    'blacklist_match',    'Blacklisted plate attempted entry',              'detection_images/seed_alert_010.jpg', 1, DATEADD(day,   -3, @now), DATEADD(day,  -3, DATEADD(hour, 1, @now)), 'BLK-9001', 'critical', 'Entry Gate',       NULL),
        ('parking_violation',  'Cam_03',     'B1-PARKING', 'B1 Parking', 'B1_CRO','B1 CRO','duration_exceeded',  'Visitor exceeded parking limit',                 'detection_images/seed_alert_011.jpg', 1, DATEADD(day,   -4, @now), DATEADD(day,  -4, DATEADD(hour, 2, @now)), 'VIS-2002', 'warning',  'B1 / Slot CRO',    NULL),
        ('camera_offline',     'Cam_12',     NULL,         NULL,         NULL,    NULL,    'connectivity_lost',  'Camera Cam_12 stopped responding',               NULL,                                  1, DATEADD(day,   -5, @now), DATEADD(day,  -5, DATEADD(hour, 1, @now)), NULL,       'warning',  'B2 / Camera Cam_12', NULL),
        ('intrusion',          'Cam_09',     'B2-PARKING', 'B2 Parking', 'B2_03', 'B2 03', 'unregistered_park',  'Unregistered vehicle parked',                    'detection_images/seed_alert_012.jpg', 1, DATEADD(day,   -6, @now), DATEADD(day,  -6, DATEADD(hour, 3, @now)), 'UNK-3001', 'warning',  'B2 / Slot 03',     NULL),
        ('parking_violation',  'Cam_04',     'B1-PARKING', 'B1 Parking', 'B1_01', 'B1 01', 'duration_exceeded',  'Visitor exceeded parking limit',                 'detection_images/seed_alert_013.jpg', 1, DATEADD(day,   -7, @now), DATEADD(day,  -7, DATEADD(hour, 1, @now)), 'VIS-2004', 'info',     'B1 / Slot 01',     NULL),
        ('unknown_plate',      'ANPR-Entry', NULL,         NULL,         NULL,    NULL,    'low_confidence',     'Low-confidence plate read',                      'detection_images/seed_alert_014.jpg', 1, DATEADD(day,   -8, @now), DATEADD(day,  -8, DATEADD(hour, 1, @now)), 'UNK-3002', 'info',     'Entry Gate',       NULL),
        ('camera_offline',     'Cam_03',     NULL,         NULL,         NULL,    NULL,    'connectivity_lost',  'Camera Cam_03 stopped responding',               NULL,                                  1, DATEADD(day,  -10, @now), DATEADD(day, -10, DATEADD(hour, 2, @now)), NULL,       'warning',  'B1 / Camera Cam_03', NULL),
        ('intrusion',          'Cam_05',     'B1-PARKING', 'B1 Parking', 'B1_11', 'B1 11', 'slot_violation',     'Vehicle parked in handicap-only zone',           'detection_images/seed_alert_015.jpg', 1, DATEADD(day,  -11, @now), DATEADD(day, -11, DATEADD(hour, 1, @now)), 'UNK-3001', 'critical', 'B1 / Slot 11',     NULL),
        ('parking_violation',  'Cam_11',     'B2-PARKING', 'B2 Parking', 'B2_05', 'B2 05', 'duration_exceeded',  'Visitor exceeded parking limit',                 'detection_images/seed_alert_016.jpg', 1, DATEADD(day,  -12, @now), DATEADD(day, -12, DATEADD(hour, 1, @now)), 'VIS-2005', 'warning',  'B2 / Slot 05',     NULL),
        ('unauthorized_entry', 'ANPR-Entry', NULL,         NULL,         NULL,    NULL,    'blacklist_match',    'Blacklisted plate attempted entry',              'detection_images/seed_alert_017.jpg', 1, DATEADD(day,  -13, @now), DATEADD(day, -13, DATEADD(hour, 1, @now)), 'BLK-9001', 'critical', 'Entry Gate',       NULL)
    ) AS s (alert_type, camera_id, zone_id, zone_name, slot_id, slot_number, event_type,
            description, snapshot_path, is_resolved, triggered_at, resolved_at,
            plate_number, severity, location_display, _placeholder)
    LEFT JOIN dbo.vehicles v ON v.plate_number = s.plate_number;
    PRINT '  Seeded alerts rows';
END;

/* Backfill parking_slot_id integer FK partner for the new alerts. */
IF COL_LENGTH(N'dbo.alerts', N'parking_slot_id') IS NOT NULL
    UPDATE t SET parking_slot_id = ps.id
    FROM dbo.alerts t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
    WHERE t.parking_slot_id IS NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   7. zone_occupancy — bump current_count to plausible values for the dashboard
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @now DATETIME2 = SYSUTCDATETIME();

UPDATE dbo.zone_occupancy
   SET current_count = CASE zone_id
                           WHEN 'B1-PARKING'   THEN 7
                           WHEN 'B2-PARKING'   THEN 5
                           WHEN 'GARAGE-TOTAL' THEN 12
                           ELSE current_count
                       END,
       max_capacity  = CASE zone_id
                           WHEN 'B1-PARKING'   THEN 15
                           WHEN 'B2-PARKING'   THEN 15
                           WHEN 'GARAGE-TOTAL' THEN 30
                           ELSE max_capacity
                       END,
       last_updated  = @now
 WHERE zone_id IN ('B1-PARKING', 'B2-PARKING', 'GARAGE-TOTAL')
   AND (current_count = 0 OR current_count IS NULL);
GO

/* ────────────────────────────────────────────────────────────────────────────
   8. camera_feeds — recent dashboard-ticker entries
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @now DATETIME2 = SYSUTCDATETIME();

IF NOT EXISTS (SELECT 1 FROM dbo.camera_feeds WHERE snapshot_path = 'detection_images/seed_feed_001.jpg')
BEGIN
    INSERT INTO dbo.camera_feeds (camera_id, location_label, event_description, detection_source, plate_number, snapshot_path, timestamp) VALUES
        ('ANPR-Entry', 'Entry Gate',   'Vehicle entry detected',         'anpr',  'ABC-1001', 'detection_images/seed_feed_001.jpg', DATEADD(hour,   -2, @now)),
        ('ANPR-Entry', 'Entry Gate',   'Vehicle entry detected',         'anpr',  'ABC-1002', 'detection_images/seed_feed_002.jpg', DATEADD(hour,   -3, @now)),
        ('ANPR-Exit',  'Exit Gate',    'Vehicle exit detected',          'anpr',  'ABC-1001', 'detection_images/seed_feed_003.jpg', DATEADD(hour,   -1, @now)),
        ('Cam_03',     'B1 Parking',   'Slot occupancy change',          'cv',    'ABC-1001', 'detection_images/seed_feed_004.jpg', DATEADD(minute, -45, @now)),
        ('Cam_05',     'B1 Parking',   'Slot occupancy change',          'cv',    'UNK-3001', 'detection_images/seed_feed_005.jpg', DATEADD(minute, -25, @now)),
        ('Cam_11',     'B2 Parking',   'Slot occupancy change',          'cv',    'UNK-3002', 'detection_images/seed_feed_006.jpg', DATEADD(minute, -15, @now)),
        ('Cam_09',     'B2 Parking',   'Slot occupancy change',          'cv',    'ABC-1005', 'detection_images/seed_feed_007.jpg', DATEADD(minute, -150,@now));
    PRINT '  Seeded camera_feeds rows';
END;
GO

PRINT '──────────────────────────────────────────────';
PRINT '  seed.sql finished';
PRINT '──────────────────────────────────────────────';
GO
