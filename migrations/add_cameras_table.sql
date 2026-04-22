SET NOCOUNT ON;

PRINT 'Running cameras configurator migration...';

IF OBJECT_ID(N'dbo.cameras', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.cameras (
        id                  INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
        camera_id           NVARCHAR(50)  NOT NULL,
        name                NVARCHAR(100) NULL,
        floor               NVARCHAR(50)  NULL,
        zone_id             NVARCHAR(100) NULL,
        ip_address          NVARCHAR(64)  NOT NULL,
        rtsp_port           INT           NOT NULL CONSTRAINT DF_cameras_rtsp_port DEFAULT (554),
        rtsp_path           NVARCHAR(255) NOT NULL CONSTRAINT DF_cameras_rtsp_path DEFAULT ('/Streaming/Channels/101'),
        username            NVARCHAR(100) NULL,
        password_encrypted  NVARCHAR(MAX) NULL,
        enabled             BIT           NOT NULL CONSTRAINT DF_cameras_enabled DEFAULT (1),
        notes               NVARCHAR(MAX) NULL,
        last_check_at       DATETIME2     NULL,
        last_seen_at        DATETIME2     NULL,
        last_status         NVARCHAR(50)  NULL,
        created_at          DATETIME2     NOT NULL CONSTRAINT DF_cameras_created_at DEFAULT (GETUTCDATE()),
        updated_at          DATETIME2     NOT NULL CONSTRAINT DF_cameras_updated_at DEFAULT (GETUTCDATE())
    );
    PRINT '  Created table dbo.cameras';
END;

IF OBJECT_ID(N'dbo.cameras', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ux_cameras_camera_id'
          AND object_id = OBJECT_ID(N'dbo.cameras')
    )
        CREATE UNIQUE INDEX ux_cameras_camera_id ON dbo.cameras (camera_id);

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_cameras_floor'
          AND object_id = OBJECT_ID(N'dbo.cameras')
    )
        CREATE INDEX ix_cameras_floor ON dbo.cameras (floor);

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'ix_cameras_enabled'
          AND object_id = OBJECT_ID(N'dbo.cameras')
    )
        CREATE INDEX ix_cameras_enabled ON dbo.cameras (enabled);
END;

PRINT 'Cameras configurator migration finished.';
