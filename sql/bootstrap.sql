/* ============================================================================
   bootstrap.sql — single full schema for the Parking System database

   Idempotent — every CREATE / ALTER / INSERT is guarded so you can safely
   re-run the whole file on an existing database without errors.

   Run order:
     1. Connect as a user with CREATE TABLE permissions.
     2. Make sure the target database exists (CREATE DATABASE damanat_pms;
        outside of this script — on Windows Authentication this is `sqlcmd
        -E -S . -Q "CREATE DATABASE damanat_pms"`).
     3. Run this file:
        sqlcmd -E -S localhost -d damanat_pms -i bootstrap.sql
        (or `-U sa -P "YourStrong!Pass1"` for SQL auth)

   What it creates:
     - alembic_version          (migration tracking)
     - vehicles                 (registered vehicles)
     - alerts                   (UC5/UC6 alert events)
     - parking_slots            (per-slot polygons + flags)
     - slot_status              (latest CV-derived state per slot)
     - parking_sessions         (entry/exit pairs + slot binding)
     - entry_exit_log           (raw gate crossings)
     - zone_occupancy           (line-crossing counters per floor + GARAGE-TOTAL)
     - intrusions               (legacy intrusion events)
     - cameras                  (Gateway-owned camera registry)
     - camera_feeds             (camera-event feed for the dashboard)

   Indexes are plain CREATE INDEX statements only — nothing that requires
   SQL Server enterprise features or extensions to be installed first.

   Sample data inserted at the bottom:
     - 1 alembic_version row (current head: a6b7c8d9e0f1)
     - parking_slots for floor B1/B2 (3 example slots per floor)
     - zone_occupancy for B1-PARKING / B2-PARKING / GARAGE-TOTAL

   To add cameras with encrypted passwords, run a separate file generated
   by your environment (camera credentials are encrypted with the runtime
   CAMERAS_ENCRYPTION_KEY; never check that into source control).
   ============================================================================ */

SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

PRINT '──────────────────────────────────────────────';
PRINT '  Parking System — bootstrap.sql';
PRINT '──────────────────────────────────────────────';

/* ────────────────────────────────────────────────────────────────────────────
   1. alembic_version
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.alembic_version', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.alembic_version (
        version_num VARCHAR(32) NOT NULL,
        CONSTRAINT alembic_version_pkc PRIMARY KEY CLUSTERED (version_num)
    );
    PRINT '  Created table dbo.alembic_version';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   2. vehicles  (canonical fields are the post-Phase-3 ones)
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.vehicles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.vehicles (
        id              INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        plate_number    VARCHAR(50)  NOT NULL,
        owner_name      VARCHAR(200) NOT NULL,
        vehicle_type    VARCHAR(50)  NOT NULL,
        employee_id     VARCHAR(100) NULL,
        is_registered   BIT          NOT NULL CONSTRAINT DF_vehicles_is_registered DEFAULT (1),
        registered_at   DATETIME2    NULL,
        notes           VARCHAR(MAX) NULL,
        title           VARCHAR(50)  NOT NULL CONSTRAINT DF_vehicles_title DEFAULT (''),
        is_employee     BIT          NOT NULL CONSTRAINT DF_vehicles_is_employee DEFAULT (0),
        phone           VARCHAR(50)  NULL,
        email           VARCHAR(255) NULL
    );
    CREATE UNIQUE INDEX ux_vehicles_plate_number ON dbo.vehicles (plate_number);
    PRINT '  Created table dbo.vehicles';
END;
GO

/* Additive columns added after the original CREATE TABLE — gated by
   COL_LENGTH so re-running the bootstrap is idempotent. These give VA a
   place to record "where is this car right now" and let the Gateway
   answer it from the vehicles row alone (no parking_sessions JOIN). */
IF COL_LENGTH(N'dbo.vehicles', N'current_slot_id') IS NULL
    ALTER TABLE dbo.vehicles ADD current_slot_id VARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.vehicles', N'floor') IS NULL
    ALTER TABLE dbo.vehicles ADD floor NVARCHAR(50) NULL;
IF COL_LENGTH(N'dbo.vehicles', N'floor_id') IS NULL
    ALTER TABLE dbo.vehicles ADD floor_id INT NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   3. parking_slots
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.parking_slots', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.parking_slots (
        slot_id            VARCHAR(50)  NOT NULL PRIMARY KEY,
        slot_name          VARCHAR(100) NULL,
        floor              VARCHAR(50)  NULL,
        polygon            NVARCHAR(MAX) NULL,
        is_available       BIT          NULL CONSTRAINT DF_parking_slots_is_available DEFAULT (1),
        is_violation_zone  BIT          NULL CONSTRAINT DF_parking_slots_is_violation DEFAULT (0)
    );
    CREATE INDEX ix_parking_slots_floor ON dbo.parking_slots (floor);
    PRINT '  Created table dbo.parking_slots';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   4. slot_status  (latest VA computer-vision state per slot)
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.slot_status', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.slot_status (
        id           INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        slot_id      VARCHAR(50)  NOT NULL,
        plate_number VARCHAR(20)  NULL,
        status       VARCHAR(20)  NULL,
        time         DATETIME2    NULL CONSTRAINT DF_slot_status_time DEFAULT (GETUTCDATE())
    );
    CREATE INDEX ix_slot_status_slot_id ON dbo.slot_status (slot_id);
    CREATE INDEX ix_slot_status_time    ON dbo.slot_status (time);
    PRINT '  Created table dbo.slot_status';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   5. alerts
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.alerts', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.alerts (
        id                          INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        alert_type                  VARCHAR(50)  NOT NULL,
        camera_id                   VARCHAR(50)  NOT NULL,
        zone_id                     VARCHAR(100) NULL,
        zone_name                   VARCHAR(100) NULL,
        slot_id                     VARCHAR(50)  NULL,
        slot_number                 VARCHAR(100) NULL,
        region_id                   INT          NULL,
        event_type                  VARCHAR(100) NULL,
        description                 VARCHAR(MAX) NULL,
        snapshot_path               VARCHAR(MAX) NULL,
        is_test                     BIT          NOT NULL CONSTRAINT DF_alerts_is_test DEFAULT (0),
        is_resolved                 BIT          NOT NULL CONSTRAINT DF_alerts_is_resolved DEFAULT (0),
        triggered_at                DATETIME2    NOT NULL CONSTRAINT DF_alerts_triggered_at DEFAULT (GETUTCDATE()),
        resolved_at                 DATETIME2    NULL,
        plate_number                VARCHAR(50)  NULL,
        severity                    VARCHAR(20)  NOT NULL CONSTRAINT DF_alerts_severity DEFAULT ('warning'),
        location_display            VARCHAR(255) NULL,
        vehicle_id                  INT          NULL,
        vehicle_event_id            INT          NULL,
        triggering_camera_event_id  INT          NULL,
        resolved_by                 VARCHAR(100) NULL,
        resolution_notes            VARCHAR(MAX) NULL
    );
    CREATE INDEX ix_alerts_alert_type    ON dbo.alerts (alert_type);
    CREATE INDEX ix_alerts_is_resolved   ON dbo.alerts (is_resolved);
    CREATE INDEX ix_alerts_triggered_at  ON dbo.alerts (triggered_at);
    CREATE INDEX ix_alerts_plate_number  ON dbo.alerts (plate_number);
    CREATE INDEX ix_alerts_slot_id       ON dbo.alerts (slot_id);
    PRINT '  Created table dbo.alerts';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   6. entry_exit_log
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.entry_exit_log', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.entry_exit_log (
        id                 INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        plate_number       VARCHAR(50)  NOT NULL,
        vehicle_id         INT          NULL,
        vehicle_type       VARCHAR(50)  NULL,
        gate               VARCHAR(20)  NOT NULL,
        camera_id          VARCHAR(50)  NOT NULL,
        event_time         DATETIME2    NOT NULL,
        parking_duration   INT          NULL,
        snapshot_path      VARCHAR(MAX) NULL,
        matched_entry_id   INT          NULL,
        is_test            BIT          NOT NULL CONSTRAINT DF_entry_exit_is_test DEFAULT (0),
        created_at         DATETIME2    NULL CONSTRAINT DF_entry_exit_created DEFAULT (GETUTCDATE()),
        vehicle_event_id   INT          NULL,
        camera_event_id    INT          NULL,
        plate_confidence   FLOAT        NULL
    );
    CREATE INDEX ix_entry_exit_plate_number ON dbo.entry_exit_log (plate_number);
    CREATE INDEX ix_entry_exit_event_time   ON dbo.entry_exit_log (event_time);
    CREATE INDEX ix_entry_exit_vehicle_id   ON dbo.entry_exit_log (vehicle_id);
    PRINT '  Created table dbo.entry_exit_log';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   7. parking_sessions  (the canonical "VehicleEvent" data)
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.parking_sessions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.parking_sessions (
        id                    INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        plate_number          VARCHAR(50)  NOT NULL,
        vehicle_id            INT          NULL,
        vehicle_type          VARCHAR(50)  NULL,
        is_employee           BIT          NOT NULL CONSTRAINT DF_parking_sessions_is_employee DEFAULT (0),
        entry_time            DATETIME2    NOT NULL,
        exit_time             DATETIME2    NULL,
        duration_seconds      INT          NULL,
        entry_camera_id       VARCHAR(50)  NOT NULL,
        exit_camera_id        VARCHAR(50)  NULL,
        entry_snapshot_path   VARCHAR(MAX) NULL,
        exit_snapshot_path    VARCHAR(MAX) NULL,
        floor                 VARCHAR(50)  NULL,
        zone_id               VARCHAR(100) NULL,
        zone_name             VARCHAR(100) NULL,
        slot_id               VARCHAR(50)  NULL,
        slot_number           VARCHAR(100) NULL,
        parked_at             DATETIME2    NULL,
        slot_left_at          DATETIME2    NULL,
        slot_camera_id        VARCHAR(50)  NULL,
        slot_snapshot_path    VARCHAR(MAX) NULL,
        status                VARCHAR(20)  NOT NULL CONSTRAINT DF_parking_sessions_status DEFAULT ('open'),
        created_at            DATETIME2    NOT NULL CONSTRAINT DF_parking_sessions_created_at DEFAULT (GETUTCDATE()),
        updated_at            DATETIME2    NOT NULL CONSTRAINT DF_parking_sessions_updated_at DEFAULT (GETUTCDATE())
    );
    CREATE INDEX ix_parking_sessions_plate_number ON dbo.parking_sessions (plate_number);
    CREATE INDEX ix_parking_sessions_entry_time   ON dbo.parking_sessions (entry_time);
    CREATE INDEX ix_parking_sessions_exit_time    ON dbo.parking_sessions (exit_time);
    CREATE INDEX ix_parking_sessions_status       ON dbo.parking_sessions (status);
    CREATE INDEX ix_parking_sessions_vehicle_id   ON dbo.parking_sessions (vehicle_id);
    CREATE INDEX ix_parking_sessions_slot_id      ON dbo.parking_sessions (slot_id);
    PRINT '  Created table dbo.parking_sessions';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   8. zone_occupancy  (line-crossing counters; GARAGE-TOTAL is synthetic)
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.zone_occupancy', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.zone_occupancy (
        id            INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        zone_id       VARCHAR(100) NOT NULL,
        camera_id     VARCHAR(50)  NOT NULL,
        current_count INT          NOT NULL CONSTRAINT DF_zone_occupancy_current_count DEFAULT (0),
        max_capacity  INT          NOT NULL CONSTRAINT DF_zone_occupancy_max_capacity DEFAULT (10),
        last_updated  DATETIME2    NULL,
        zone_name     VARCHAR(100) NULL,
        floor         VARCHAR(50)  NULL
    );
    CREATE UNIQUE INDEX ux_zone_occupancy_zone_id ON dbo.zone_occupancy (zone_id);
    PRINT '  Created table dbo.zone_occupancy';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   9. intrusions  (legacy table; kept for back-compat)
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.intrusions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.intrusions (
        id           INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        slot_id      VARCHAR(50) NOT NULL,
        plate_number VARCHAR(20) NULL,
        status       VARCHAR(20) NULL,
        detected_at  DATETIME2   NULL,
        resolved_at  DATETIME2   NULL,
        camera_id    VARCHAR(50) NULL
    );
    PRINT '  Created table dbo.intrusions';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   10. cameras  (Gateway-owned camera registry)
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.cameras', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.cameras (
        id                  INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        camera_id           VARCHAR(50)   NOT NULL,
        name                VARCHAR(100)  NULL,
        floor               VARCHAR(50)   NULL,
        role                VARCHAR(30)   NOT NULL CONSTRAINT DF_cameras_role DEFAULT ('other'),
        watches_floor       VARCHAR(50)   NULL,
        watches_slots_json  NVARCHAR(MAX) NULL,
        ip_address          VARCHAR(64)   NOT NULL,
        rtsp_port           INT           NOT NULL CONSTRAINT DF_cameras_rtsp_port DEFAULT (554),
        rtsp_path           VARCHAR(255)  NOT NULL CONSTRAINT DF_cameras_rtsp_path DEFAULT ('/Streaming/Channels/101'),
        username            VARCHAR(100)  NULL,
        password_encrypted  NVARCHAR(MAX) NULL,
        enabled             BIT           NOT NULL CONSTRAINT DF_cameras_enabled DEFAULT (1),
        notes               NVARCHAR(MAX) NULL,
        last_check_at       DATETIME2     NULL,
        last_seen_at        DATETIME2     NULL,
        last_status         VARCHAR(50)   NULL,
        created_at          DATETIME2     NOT NULL CONSTRAINT DF_cameras_created_at DEFAULT (GETUTCDATE()),
        updated_at          DATETIME2     NOT NULL CONSTRAINT DF_cameras_updated_at DEFAULT (GETUTCDATE())
    );
    CREATE UNIQUE INDEX ux_cameras_camera_id ON dbo.cameras (camera_id);
    CREATE INDEX ix_cameras_floor   ON dbo.cameras (floor);
    CREATE INDEX ix_cameras_enabled ON dbo.cameras (enabled);
    CREATE INDEX ix_cameras_role    ON dbo.cameras (role);
    PRINT '  Created table dbo.cameras';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   11. camera_feeds  (camera-event feed for the dashboard)
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.camera_feeds', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.camera_feeds (
        id                INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        camera_id         VARCHAR(50)  NULL,
        location_label    VARCHAR(100) NULL,
        event_description VARCHAR(MAX) NULL,
        detection_source  VARCHAR(50)  NULL,
        plate_number      VARCHAR(50)  NULL,
        snapshot_path     VARCHAR(MAX) NULL,
        timestamp         DATETIME2    NOT NULL CONSTRAINT DF_camera_feeds_timestamp DEFAULT (GETUTCDATE())
    );
    CREATE INDEX ix_camera_feeds_timestamp        ON dbo.camera_feeds (timestamp);
    CREATE INDEX ix_camera_feeds_camera_id        ON dbo.camera_feeds (camera_id);
    CREATE INDEX ix_camera_feeds_plate_number     ON dbo.camera_feeds (plate_number);
    CREATE INDEX ix_camera_feeds_detection_source ON dbo.camera_feeds (detection_source);
    PRINT '  Created table dbo.camera_feeds';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   Foreign keys (added after all tables exist)
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_entry_exit_log_vehicle_id')
   AND OBJECT_ID(N'dbo.entry_exit_log') IS NOT NULL
   AND OBJECT_ID(N'dbo.vehicles') IS NOT NULL
BEGIN
    -- Only add if no orphan rows would block the constraint
    IF NOT EXISTS (
        SELECT 1 FROM dbo.entry_exit_log eel
        LEFT JOIN dbo.vehicles v ON v.id = eel.vehicle_id
        WHERE eel.vehicle_id IS NOT NULL AND v.id IS NULL
    )
    BEGIN
        ALTER TABLE dbo.entry_exit_log WITH CHECK
        ADD CONSTRAINT fk_entry_exit_log_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES dbo.vehicles (id) ON DELETE NO ACTION;
        PRINT '  Added FK fk_entry_exit_log_vehicle_id';
    END
    ELSE
        PRINT '  Skipped fk_entry_exit_log_vehicle_id — orphan rows exist';
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_parking_sessions_vehicle_id')
   AND OBJECT_ID(N'dbo.parking_sessions') IS NOT NULL
   AND OBJECT_ID(N'dbo.vehicles') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM dbo.parking_sessions ps
        LEFT JOIN dbo.vehicles v ON v.id = ps.vehicle_id
        WHERE ps.vehicle_id IS NOT NULL AND v.id IS NULL
    )
    BEGIN
        ALTER TABLE dbo.parking_sessions WITH CHECK
        ADD CONSTRAINT fk_parking_sessions_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES dbo.vehicles (id) ON DELETE NO ACTION;
        PRINT '  Added FK fk_parking_sessions_vehicle_id';
    END
    ELSE
        PRINT '  Skipped fk_parking_sessions_vehicle_id — orphan rows exist';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   Schema-version marker
   ────────────────────────────────────────────────────────────────────────────
   alembic_version is the only row this script writes — it pins the migration
   head so PMS-AI's alembic doesn't try to re-apply migrations the consolidated
   bootstrap already represents. All other content lives in sql/seed.sql.
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM dbo.alembic_version WHERE version_num = 'a6b7c8d9e0f1')
BEGIN
    DELETE FROM dbo.alembic_version;
    INSERT INTO dbo.alembic_version (version_num) VALUES ('a6b7c8d9e0f1');
    PRINT '  Pinned alembic_version = a6b7c8d9e0f1';
END;
GO

/* ============================================================================
   -- Phase-1 of WS-8: floor + slot-PK additive schema
   ============================================================================
   Additive-only migration for the floor + slot-PK refactor. Everything below
   is idempotent and back-compat: new tables/columns/FKs land alongside the
   existing string-keyed schema. The destructive cutover (drop legacy `floor`
   string columns, swap parking_slots PK to `id`, add FK constraints on
   dependent tables) lands in a follow-up phase.
   ============================================================================ */

/* 1. floors — new lookup table that replaces the denormalized `floor` string. */
IF OBJECT_ID(N'dbo.floors', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.floors (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        name NVARCHAR(50) NOT NULL UNIQUE,
        sort_order INT NOT NULL DEFAULT 0,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

/* 2. Backfill floors from existing distinct parking_slots.floor values so the
      lookup is populated before any FK column points at it. The CASE pins
      the canonical operator-facing order (Ground=0, B1=1, B2=2, …) instead
      of alphabetic, which would put Ground after the basements. */
INSERT INTO dbo.floors (name, sort_order)
SELECT DISTINCT ps.floor,
       CASE ps.floor
           WHEN N'Ground' THEN 0
           WHEN N'B1'     THEN 1
           WHEN N'B2'     THEN 2
           WHEN N'B3'     THEN 3
           WHEN N'B4'     THEN 4
           WHEN N'B5'     THEN 5
           ELSE 1000
       END
FROM dbo.parking_slots ps
WHERE ps.floor IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = ps.floor);
GO

/* 3. parking_slots.id — surrogate INT (UNIQUE for now, future PK after cutover)
      so dependent tables can carry an INT FK instead of the VARCHAR slot_id. */
IF COL_LENGTH(N'dbo.parking_slots', N'id') IS NULL
BEGIN
    ALTER TABLE dbo.parking_slots ADD id INT IDENTITY(1,1) NOT NULL;
    ALTER TABLE dbo.parking_slots ADD CONSTRAINT uq_parking_slots_id UNIQUE (id);
END
GO

/* 4. parking_slots.floor_id — FK to floors. Nullable until backfill completes;
      this is the only dependent table that gets its FK constraint now (safe). */
IF COL_LENGTH(N'dbo.parking_slots', N'floor_id') IS NULL
    ALTER TABLE dbo.parking_slots ADD floor_id INT NULL;
GO
UPDATE ps SET floor_id = f.id
FROM dbo.parking_slots ps INNER JOIN dbo.floors f ON f.name = ps.floor
WHERE ps.floor_id IS NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'fk_parking_slots_floor')
    ALTER TABLE dbo.parking_slots
      ADD CONSTRAINT fk_parking_slots_floor FOREIGN KEY (floor_id) REFERENCES dbo.floors(id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_parking_slots_floor_id')
    CREATE INDEX ix_parking_slots_floor_id ON dbo.parking_slots(floor_id);
GO

/* 5. Dependent tables — add nullable parking_slot_id INT alongside the legacy
      VARCHAR slot_id. FK constraints are deferred to the destructive phase. */

-- 5a. slot_status.parking_slot_id
IF COL_LENGTH(N'dbo.slot_status', N'parking_slot_id') IS NULL
    ALTER TABLE dbo.slot_status ADD parking_slot_id INT NULL;
GO
UPDATE t SET parking_slot_id = ps.id
FROM dbo.slot_status t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
WHERE t.parking_slot_id IS NULL;
GO

-- 5b. alerts.parking_slot_id
IF COL_LENGTH(N'dbo.alerts', N'parking_slot_id') IS NULL
    ALTER TABLE dbo.alerts ADD parking_slot_id INT NULL;
GO
UPDATE t SET parking_slot_id = ps.id
FROM dbo.alerts t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
WHERE t.parking_slot_id IS NULL;
GO

-- 5c. parking_sessions.parking_slot_id
IF COL_LENGTH(N'dbo.parking_sessions', N'parking_slot_id') IS NULL
    ALTER TABLE dbo.parking_sessions ADD parking_slot_id INT NULL;
GO
UPDATE t SET parking_slot_id = ps.id
FROM dbo.parking_sessions t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
WHERE t.parking_slot_id IS NULL;
GO

-- 5d. intrusions.parking_slot_id
IF COL_LENGTH(N'dbo.intrusions', N'parking_slot_id') IS NULL
    ALTER TABLE dbo.intrusions ADD parking_slot_id INT NULL;
GO
UPDATE t SET parking_slot_id = ps.id
FROM dbo.intrusions t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
WHERE t.parking_slot_id IS NULL;
GO

/* 6. floor_id on parking_sessions + cameras (floor + watches_floor) — the same
      VARCHAR floor strings now have integer FK partners ready for cutover. */

-- 6a. parking_sessions.floor_id
IF COL_LENGTH(N'dbo.parking_sessions', N'floor_id') IS NULL
    ALTER TABLE dbo.parking_sessions ADD floor_id INT NULL;
GO
UPDATE t SET floor_id = f.id FROM dbo.parking_sessions t INNER JOIN dbo.floors f ON f.name = t.floor WHERE t.floor_id IS NULL;
GO

-- 6b. cameras.floor_id (mirrors cameras.floor)
IF COL_LENGTH(N'dbo.cameras', N'floor_id') IS NULL
    ALTER TABLE dbo.cameras ADD floor_id INT NULL;
GO
UPDATE t SET floor_id = f.id FROM dbo.cameras t INNER JOIN dbo.floors f ON f.name = t.floor WHERE t.floor_id IS NULL;
GO

-- 6c. cameras.watches_floor_id (mirrors cameras.watches_floor)
IF COL_LENGTH(N'dbo.cameras', N'watches_floor_id') IS NULL
    ALTER TABLE dbo.cameras ADD watches_floor_id INT NULL;
GO
UPDATE t SET watches_floor_id = f.id FROM dbo.cameras t INNER JOIN dbo.floors f ON f.name = t.watches_floor WHERE t.watches_floor_id IS NULL;
GO

/* 7. alerts.floor_id — alerts has a denormalized `floor` column from the
      GA-1 / G-6 work in some deployments; pair it with an integer FK for
      cutover. The backfill is dynamic-SQL so a missing `alerts.floor`
      column (older DBs) doesn't break the static parse. */
IF COL_LENGTH(N'dbo.alerts', N'floor_id') IS NULL
    ALTER TABLE dbo.alerts ADD floor_id INT NULL;
GO
IF COL_LENGTH(N'dbo.alerts', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET floor_id = f.id
        FROM dbo.alerts t INNER JOIN dbo.floors f ON f.name = t.floor
        WHERE t.floor_id IS NULL;';
GO

/* 8. floor_occupancy.floor_id — Phase-4A table; only present on DBs that
      ran System 1''s migration. Add the FK column back to floors when the
      table exists; skip cleanly when it doesn''t. */
IF OBJECT_ID(N'dbo.floor_occupancy', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.floor_occupancy', N'floor_id') IS NULL
    ALTER TABLE dbo.floor_occupancy ADD floor_id INT NULL;
GO
IF OBJECT_ID(N'dbo.floor_occupancy', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.floor_occupancy', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET floor_id = f.id
        FROM dbo.floor_occupancy t INNER JOIN dbo.floors f ON f.name = t.floor
        WHERE t.floor_id IS NULL;';
GO


/* ============================================================================
   -- Comprehensive floor seeding + backfill (replaces sql/fix_floor_ids.sql)
   ============================================================================
   The Phase-1 of WS-8 section above seeded `floors` only from
   `parking_slots.floor`. In a real deployment, floor names may exist on
   other tables too (cameras.floor, parking_sessions.floor, alerts.floor,
   etc.). This block pulls every distinct floor name from every source
   table that has a `floor` / `watches_floor` column, then re-runs the
   per-table floor_id backfills. Idempotent — safe to re-run any time
   new rows arrive with a floor name not yet in the lookup.

   Each source block is wrapped in `EXEC sp_executesql` so missing
   columns (older or partial schemas) no-op cleanly without breaking the
   static parse.
   ============================================================================ */

IF COL_LENGTH(N'dbo.parking_sessions', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        INSERT INTO dbo.floors (name)
        SELECT DISTINCT t.floor FROM dbo.parking_sessions t
        WHERE t.floor IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = t.floor);';

IF COL_LENGTH(N'dbo.cameras', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        INSERT INTO dbo.floors (name)
        SELECT DISTINCT t.floor FROM dbo.cameras t
        WHERE t.floor IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = t.floor);';

IF COL_LENGTH(N'dbo.cameras', N'watches_floor') IS NOT NULL
    EXEC sp_executesql N'
        INSERT INTO dbo.floors (name)
        SELECT DISTINCT t.watches_floor FROM dbo.cameras t
        WHERE t.watches_floor IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = t.watches_floor);';

IF COL_LENGTH(N'dbo.alerts', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        INSERT INTO dbo.floors (name)
        SELECT DISTINCT t.floor FROM dbo.alerts t
        WHERE t.floor IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = t.floor);';

IF COL_LENGTH(N'dbo.floor_occupancy', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        INSERT INTO dbo.floors (name)
        SELECT DISTINCT t.floor FROM dbo.floor_occupancy t
        WHERE t.floor IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = t.floor);';
GO

/* Re-apply the canonical operator-facing sort_order: Ground first (top of
   building), then descending basements. Unknown floor names land after the
   canonical set so they don't collide with B1/B2/etc. */
UPDATE dbo.floors
   SET sort_order = CASE name
       WHEN N'Ground' THEN 0
       WHEN N'B1'     THEN 1
       WHEN N'B2'     THEN 2
       WHEN N'B3'     THEN 3
       WHEN N'B4'     THEN 4
       WHEN N'B5'     THEN 5
       ELSE 1000 + sort_order
     END
 WHERE sort_order != CASE name
       WHEN N'Ground' THEN 0
       WHEN N'B1'     THEN 1
       WHEN N'B2'     THEN 2
       WHEN N'B3'     THEN 3
       WHEN N'B4'     THEN 4
       WHEN N'B5'     THEN 5
       ELSE 1000 + sort_order
     END;
GO

/* Re-run the per-table floor_id / parking_slot_id backfills now that
   `floors` is fully seeded. Each is dynamic-SQL so missing columns
   silently no-op. */

IF COL_LENGTH(N'dbo.parking_slots', N'floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.parking_slots', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE ps SET floor_id = f.id
        FROM dbo.parking_slots ps INNER JOIN dbo.floors f ON f.name = ps.floor
        WHERE ps.floor_id IS NULL;';

IF COL_LENGTH(N'dbo.parking_sessions', N'floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.parking_sessions', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET floor_id = f.id
        FROM dbo.parking_sessions t INNER JOIN dbo.floors f ON f.name = t.floor
        WHERE t.floor_id IS NULL;';

IF COL_LENGTH(N'dbo.parking_sessions', N'parking_slot_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.parking_slots', N'id') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET parking_slot_id = ps.id
        FROM dbo.parking_sessions t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
        WHERE t.parking_slot_id IS NULL;';

IF COL_LENGTH(N'dbo.cameras', N'floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.cameras', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET floor_id = f.id
        FROM dbo.cameras t INNER JOIN dbo.floors f ON f.name = t.floor
        WHERE t.floor_id IS NULL;';

IF COL_LENGTH(N'dbo.cameras', N'watches_floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.cameras', N'watches_floor') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET watches_floor_id = f.id
        FROM dbo.cameras t INNER JOIN dbo.floors f ON f.name = t.watches_floor
        WHERE t.watches_floor_id IS NULL;';

IF COL_LENGTH(N'dbo.alerts', N'floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.alerts', N'floor') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET floor_id = f.id
        FROM dbo.alerts t INNER JOIN dbo.floors f ON f.name = t.floor
        WHERE t.floor_id IS NULL;';

IF COL_LENGTH(N'dbo.alerts', N'parking_slot_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.parking_slots', N'id') IS NOT NULL
   AND COL_LENGTH(N'dbo.alerts', N'slot_id') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET parking_slot_id = ps.id
        FROM dbo.alerts t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
        WHERE t.parking_slot_id IS NULL;';

IF COL_LENGTH(N'dbo.slot_status', N'parking_slot_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.parking_slots', N'id') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET parking_slot_id = ps.id
        FROM dbo.slot_status t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
        WHERE t.parking_slot_id IS NULL;';

IF COL_LENGTH(N'dbo.intrusions', N'parking_slot_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.parking_slots', N'id') IS NOT NULL
    EXEC sp_executesql N'
        UPDATE t SET parking_slot_id = ps.id
        FROM dbo.intrusions t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
        WHERE t.parking_slot_id IS NULL;';
GO


PRINT '──────────────────────────────────────────────';
PRINT '  bootstrap.sql finished — schema ready (no data inserted).';
PRINT '  Run sql/seed.sql next to populate cameras + sample data.';
PRINT '──────────────────────────────────────────────';
GO
