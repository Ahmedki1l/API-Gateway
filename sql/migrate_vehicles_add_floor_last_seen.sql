-- =============================================================================
-- migrate_vehicles_add_floor.sql  (filename kept for history; only floor cols)
--
-- Adds two columns to `vehicles` so the row alone can answer "where is this
-- car right now?" without JOINing parking_sessions:
--   floor      NVARCHAR(50)   — last known floor (Ground / B1 / B2 / …)
--   floor_id   INT            — same value as integer FK to floors.id
--
-- VA (engine_runtime → update_vehicle_presence) writes both on every track
-- confirmation. PMS-AI (parking_session_service bind_slot / close_session)
-- keeps them in sync on park / exit. The Gateway then exposes them via
-- VehicleListItem.floor / floor_id — the schema fields already existed,
-- this just gives them a real source.
--
-- Idempotent: each ALTER is gated by COL_LENGTH so re-running is a no-op.
-- Safe to run while services are up — additive, no downtime.
-- =============================================================================

IF COL_LENGTH(N'dbo.vehicles', N'floor') IS NULL
    ALTER TABLE dbo.vehicles ADD floor NVARCHAR(50) NULL;
GO

IF COL_LENGTH(N'dbo.vehicles', N'floor_id') IS NULL
    ALTER TABLE dbo.vehicles ADD floor_id INT NULL;
GO

-- ── Verify ──────────────────────────────────────────────────────────────────
-- Run after applying:
--   SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
--     FROM INFORMATION_SCHEMA.COLUMNS
--     WHERE TABLE_NAME = 'vehicles' AND COLUMN_NAME IN ('floor','floor_id')
--     ORDER BY COLUMN_NAME;
-- Expected: 2 rows.
