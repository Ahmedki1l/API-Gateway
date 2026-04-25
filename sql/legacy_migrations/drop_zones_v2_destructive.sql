-- drop_zones_v2_destructive.sql — Phase 4C (Gateway side)
--
-- Runs in parallel with Damanat-PMS-AI alembic migration
-- `b7c8d9e0f1a2_drop_zones_v2_destructive.py`. Use ONLY after Phase 4B soak.
--
-- Pre-flight checks:
--   1. grep the codebase for `zone_occupancy`, `zone_id`, `zone_name` in
--      Gateway + PMS-AI + VA response paths — should be empty.
--   2. Confirm /occupancy/zones deprecated endpoint traffic is zero in logs.
--   3. Take a DB backup before running.

SET XACT_ABORT ON;
BEGIN TRANSACTION;

-- ── 1. Drop zone_occupancy table ────────────────────────────────────────────
IF OBJECT_ID('dbo.zone_occupancy', 'U') IS NOT NULL
BEGIN
    DROP TABLE dbo.zone_occupancy;
END

-- ── 2. parking_slots: drop zone columns, rename is_violation_zone ──────────
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_NAME='parking_slots' AND COLUMN_NAME='zone_id')
BEGIN
    ALTER TABLE parking_slots DROP COLUMN zone_id;
END

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_NAME='parking_slots' AND COLUMN_NAME='zone_name')
BEGIN
    ALTER TABLE parking_slots DROP COLUMN zone_name;
END

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_NAME='parking_slots' AND COLUMN_NAME='is_violation_zone')
   AND NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_NAME='parking_slots' AND COLUMN_NAME='is_violation_slot')
BEGIN
    EXEC sp_rename 'dbo.parking_slots.is_violation_zone', 'is_violation_slot', 'COLUMN';
END

-- ── 3. parking_sessions: drop zone columns ─────────────────────────────────
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_NAME='parking_sessions' AND COLUMN_NAME='zone_id')
BEGIN
    ALTER TABLE parking_sessions DROP COLUMN zone_id;
END

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_NAME='parking_sessions' AND COLUMN_NAME='zone_name')
BEGIN
    ALTER TABLE parking_sessions DROP COLUMN zone_name;
END

-- ── 4. alerts: drop zone columns ───────────────────────────────────────────
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_NAME='alerts' AND COLUMN_NAME='zone_id')
BEGIN
    ALTER TABLE alerts DROP COLUMN zone_id;
END

IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_NAME='alerts' AND COLUMN_NAME='zone_name')
BEGIN
    ALTER TABLE alerts DROP COLUMN zone_name;
END

COMMIT TRANSACTION;
GO
