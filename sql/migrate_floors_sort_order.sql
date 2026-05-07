-- =============================================================================
-- migrate_floors_sort_order.sql
--
-- One-shot migration to put `floors.sort_order` in the order operators expect:
--   Ground (top of building, surface)  → sort_order = 0
--   B1     (first basement)            → sort_order = 1
--   B2     (second basement)           → sort_order = 2
--   any other levels                   → kept in alphabetic order after these
--
-- Why a CASE: bootstrap.sql / seed.sql backfill sort_order via
-- `DENSE_RANK() OVER (ORDER BY name)` which sorts alphabetically and puts
-- Ground LAST (B1=0, B2=1, Ground=2). The `/occupancy/floors` endpoint
-- ORDER BY sort_order then surfaces the wrong physical order. Discovered
-- 2026-05-06 — frontend showed B1 / B2 / Ground when it should show
-- Ground / B1 / B2.
--
-- Idempotent: re-running just re-asserts the same values.
-- Safe to run while the Gateway is up — UPDATE only, no schema change.
-- =============================================================================

UPDATE dbo.floors
   SET sort_order = CASE name
       WHEN N'Ground' THEN 0
       WHEN N'B1'     THEN 1
       WHEN N'B2'     THEN 2
       WHEN N'B3'     THEN 3
       WHEN N'B4'     THEN 4
       WHEN N'B5'     THEN 5
       ELSE 1000 + sort_order   -- park unknown floor names after the canonical set
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

-- Normalize stray "Ground Floor" string literals across every referencing
-- table so the JOIN `floors.name = parking_slots.floor` (and friends) actually
-- matches. Defensive `COL_LENGTH` guards keep this safe on older schemas
-- where some of these floor columns may not exist yet (e.g. alerts.floor was
-- added in a later phase and may not be present in every deployment).
IF COL_LENGTH(N'dbo.parking_slots',   N'floor') IS NOT NULL
    EXEC ('UPDATE dbo.parking_slots   SET floor = N''Ground'' WHERE floor = N''Ground Floor''');
IF COL_LENGTH(N'dbo.parking_sessions', N'floor') IS NOT NULL
    EXEC ('UPDATE dbo.parking_sessions SET floor = N''Ground'' WHERE floor = N''Ground Floor''');
IF COL_LENGTH(N'dbo.cameras',          N'floor') IS NOT NULL
    EXEC ('UPDATE dbo.cameras          SET floor = N''Ground'' WHERE floor = N''Ground Floor''');
IF COL_LENGTH(N'dbo.cameras',          N'watches_floor') IS NOT NULL
    EXEC ('UPDATE dbo.cameras          SET watches_floor = N''Ground'' WHERE watches_floor = N''Ground Floor''');
IF COL_LENGTH(N'dbo.alerts',           N'floor') IS NOT NULL
    EXEC ('UPDATE dbo.alerts           SET floor = N''Ground'' WHERE floor = N''Ground Floor''');
GO

-- ── Verify ──────────────────────────────────────────────────────────────────
-- Run after applying:
--   SELECT id, name, sort_order FROM dbo.floors ORDER BY sort_order;
-- Expected order: Ground (0), B1 (1), B2 (2), …
