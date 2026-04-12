SET NOCOUNT ON;

PRINT 'Running gateway compatibility + relationship fix script...';

IF OBJECT_ID(N'dbo.alerts', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.alerts', 'zone_name') IS NULL
        ALTER TABLE dbo.alerts ADD zone_name NVARCHAR(100) NULL;

    IF COL_LENGTH('dbo.alerts', 'region_id') IS NULL
        ALTER TABLE dbo.alerts ADD region_id INT NULL;

    IF COL_LENGTH('dbo.alerts', 'slot_number') IS NULL
        ALTER TABLE dbo.alerts ADD slot_number NVARCHAR(100) NULL;

    IF COL_LENGTH('dbo.alerts', 'snapshot_path') IS NULL
        ALTER TABLE dbo.alerts ADD snapshot_path NVARCHAR(MAX) NULL;

    IF COL_LENGTH('dbo.alerts', 'plate_number') IS NULL
        ALTER TABLE dbo.alerts ADD plate_number NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.alerts', 'severity') IS NULL
        ALTER TABLE dbo.alerts ADD severity NVARCHAR(20) NOT NULL
            CONSTRAINT DF_alerts_severity DEFAULT ('warning');

    IF COL_LENGTH('dbo.alerts', 'location_display') IS NULL
        ALTER TABLE dbo.alerts ADD location_display NVARCHAR(255) NULL;

    IF COL_LENGTH('dbo.alerts', 'is_test') IS NULL
        ALTER TABLE dbo.alerts ADD is_test BIT NOT NULL
            CONSTRAINT DF_alerts_is_test DEFAULT (0);
END;

IF OBJECT_ID(N'dbo.zone_occupancy', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.zone_occupancy', 'zone_name') IS NULL
        ALTER TABLE dbo.zone_occupancy ADD zone_name NVARCHAR(100) NULL;

    IF COL_LENGTH('dbo.zone_occupancy', 'floor') IS NULL
        ALTER TABLE dbo.zone_occupancy ADD floor NVARCHAR(50) NULL;
END;

IF OBJECT_ID(N'dbo.vehicles', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.vehicles', 'title') IS NULL
        ALTER TABLE dbo.vehicles ADD title NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.vehicles', 'is_employee') IS NULL
        ALTER TABLE dbo.vehicles ADD is_employee BIT NOT NULL
            CONSTRAINT DF_vehicles_is_employee DEFAULT (0);

    IF COL_LENGTH('dbo.vehicles', 'phone') IS NULL
        ALTER TABLE dbo.vehicles ADD phone NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.vehicles', 'email') IS NULL
        ALTER TABLE dbo.vehicles ADD email NVARCHAR(255) NULL;
END;

IF OBJECT_ID(N'dbo.entry_exit_log', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.entry_exit_log', 'snapshot_path') IS NULL
        ALTER TABLE dbo.entry_exit_log ADD snapshot_path NVARCHAR(MAX) NULL;

    IF COL_LENGTH('dbo.entry_exit_log', 'is_test') IS NULL
        ALTER TABLE dbo.entry_exit_log ADD is_test BIT NOT NULL
            CONSTRAINT DF_entry_exit_log_is_test DEFAULT (0);
END;

IF OBJECT_ID(N'dbo.parking_sessions', N'U') IS NULL
AND OBJECT_ID(N'dbo.vehicles', N'U') IS NOT NULL
BEGIN
    CREATE TABLE dbo.parking_sessions (
        id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
        plate_number NVARCHAR(50) NOT NULL,
        vehicle_id INT NULL,
        vehicle_type NVARCHAR(50) NULL,
        is_employee BIT NOT NULL CONSTRAINT DF_parking_sessions_is_employee DEFAULT (0),
        entry_time DATETIME2 NOT NULL,
        exit_time DATETIME2 NULL,
        duration_seconds INT NULL,
        entry_camera_id NVARCHAR(50) NOT NULL,
        exit_camera_id NVARCHAR(50) NULL,
        entry_snapshot_path NVARCHAR(MAX) NULL,
        exit_snapshot_path NVARCHAR(MAX) NULL,
        floor NVARCHAR(50) NULL,
        zone_id NVARCHAR(100) NULL,
        zone_name NVARCHAR(100) NULL,
        slot_number NVARCHAR(100) NULL,
        parked_at DATETIME2 NULL,
        slot_left_at DATETIME2 NULL,
        slot_camera_id NVARCHAR(50) NULL,
        slot_snapshot_path NVARCHAR(MAX) NULL,
        status NVARCHAR(20) NOT NULL CONSTRAINT DF_parking_sessions_status DEFAULT ('open'),
        created_at DATETIME2 NOT NULL CONSTRAINT DF_parking_sessions_created_at DEFAULT (GETDATE()),
        updated_at DATETIME2 NOT NULL CONSTRAINT DF_parking_sessions_updated_at DEFAULT (GETDATE())
    );
END;

IF OBJECT_ID(N'dbo.parking_sessions', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_parking_sessions_plate_number'
          AND object_id = OBJECT_ID(N'dbo.parking_sessions')
    )
        CREATE INDEX ix_parking_sessions_plate_number ON dbo.parking_sessions (plate_number);

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_parking_sessions_entry_time'
          AND object_id = OBJECT_ID(N'dbo.parking_sessions')
    )
        CREATE INDEX ix_parking_sessions_entry_time ON dbo.parking_sessions (entry_time);

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_parking_sessions_exit_time'
          AND object_id = OBJECT_ID(N'dbo.parking_sessions')
    )
        CREATE INDEX ix_parking_sessions_exit_time ON dbo.parking_sessions (exit_time);

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_parking_sessions_zone_id'
          AND object_id = OBJECT_ID(N'dbo.parking_sessions')
    )
        CREATE INDEX ix_parking_sessions_zone_id ON dbo.parking_sessions (zone_id);

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_parking_sessions_status'
          AND object_id = OBJECT_ID(N'dbo.parking_sessions')
    )
        CREATE INDEX ix_parking_sessions_status ON dbo.parking_sessions (status);
END;

IF OBJECT_ID(N'dbo.alerts', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_alerts_plate_number'
          AND object_id = OBJECT_ID(N'dbo.alerts')
    )
        CREATE INDEX ix_alerts_plate_number ON dbo.alerts (plate_number);
END;

IF OBJECT_ID(N'dbo.entry_exit_log', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_entry_exit_log_vehicle_id'
          AND object_id = OBJECT_ID(N'dbo.entry_exit_log')
    )
        CREATE INDEX ix_entry_exit_log_vehicle_id ON dbo.entry_exit_log (vehicle_id);
END;

IF OBJECT_ID(N'dbo.parking_sessions', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_parking_sessions_vehicle_id'
          AND object_id = OBJECT_ID(N'dbo.parking_sessions')
    )
        CREATE INDEX ix_parking_sessions_vehicle_id ON dbo.parking_sessions (vehicle_id);
END;

IF OBJECT_ID(N'dbo.entry_exit_log', N'U') IS NOT NULL
AND OBJECT_ID(N'dbo.vehicles', N'U') IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_entry_exit_log_vehicle_id'
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM dbo.entry_exit_log eel
        LEFT JOIN dbo.vehicles v ON v.id = eel.vehicle_id
        WHERE eel.vehicle_id IS NOT NULL
          AND v.id IS NULL
    )
        ALTER TABLE dbo.entry_exit_log WITH CHECK
        ADD CONSTRAINT fk_entry_exit_log_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES dbo.vehicles (id) ON DELETE NO ACTION;
    ELSE
        PRINT 'Skipped fk_entry_exit_log_vehicle_id because orphan vehicle_id rows exist.';
END;

IF OBJECT_ID(N'dbo.entry_exit_log', N'U') IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_entry_exit_log_matched_entry_id'
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM dbo.entry_exit_log child_row
        LEFT JOIN dbo.entry_exit_log parent_row ON parent_row.id = child_row.matched_entry_id
        WHERE child_row.matched_entry_id IS NOT NULL
          AND parent_row.id IS NULL
    )
        ALTER TABLE dbo.entry_exit_log WITH CHECK
        ADD CONSTRAINT fk_entry_exit_log_matched_entry_id
        FOREIGN KEY (matched_entry_id) REFERENCES dbo.entry_exit_log (id) ON DELETE NO ACTION;
    ELSE
        PRINT 'Skipped fk_entry_exit_log_matched_entry_id because orphan matched_entry_id rows exist.';
END;

IF OBJECT_ID(N'dbo.parking_sessions', N'U') IS NOT NULL
AND OBJECT_ID(N'dbo.vehicles', N'U') IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_parking_sessions_vehicle_id'
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM dbo.parking_sessions ps
        LEFT JOIN dbo.vehicles v ON v.id = ps.vehicle_id
        WHERE ps.vehicle_id IS NOT NULL
          AND v.id IS NULL
    )
        ALTER TABLE dbo.parking_sessions WITH CHECK
        ADD CONSTRAINT fk_parking_sessions_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES dbo.vehicles (id) ON DELETE NO ACTION;
    ELSE
        PRINT 'Skipped fk_parking_sessions_vehicle_id because orphan vehicle_id rows exist.';
END;

PRINT 'Gateway compatibility + relationship fix script finished.';
