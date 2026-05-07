/* =============================================================================
   migrate_camera_ids_to_dash_form.sql

   ONE-TIME migration: convert legacy `cameras.camera_id` values to the
   canonical dash-uppercase form ("CAM-01" .. "CAM-14", "CAM-ENTRY", "CAM-EXIT")
   that PMS-AI emits and the event tables already use.

   Confirmed via PMS-AI events.log on 2026-05-03:
     [dispatch] type='ANPR' camera=CAM-ENTRY plate='9444HUD'
     [dispatch] type='ANPR' camera=CAM-EXIT  plate='BGD-7593'
     ... type=linedetection | camera=CAM-02 | ...

   Run AFTER deploying:
     - Damanat-PMS-VideoAnalytics/config.yaml (id: "CAM-XX")
     - Damanat-PMS-VideoAnalytics/src/vehicle_registry/vehicle_registry_identity.py:82
     - API-Gateway/sql/seed.sql (rewritten cameras MERGE block)

   ============================================================================
   PRE-FLIGHT CHECKLIST
   ============================================================================
   1. SQL Server backup taken.
   2. Confirm event tables already use dash-form (they do — verified via logs):
        SELECT DISTINCT camera_id FROM entry_exit_log;
        SELECT DISTINCT entry_camera_id FROM parking_sessions;
   3. If event tables have any non-dash IDs, fix them manually before running
      this script (the cameras table is what we're moving; events should already
      be canonical).

   ============================================================================
   DRY-RUN: see what will change
   ============================================================================ */
PRINT '--- Current cameras.camera_id values (BEFORE) ---';
SELECT camera_id, name, ip_address FROM cameras ORDER BY camera_id;

PRINT '--- Rows that will be migrated ---';
SELECT camera_id AS legacy_id,
       CASE
         WHEN camera_id LIKE 'Cam[_]0%' OR camera_id LIKE 'Cam[_]1%' OR camera_id LIKE 'CAM[_]0%' OR camera_id LIKE 'CAM[_]1%'
              THEN REPLACE(REPLACE(camera_id, 'Cam_', 'CAM-'), 'CAM_', 'CAM-')
         WHEN camera_id = 'ANPR-Entry' THEN 'CAM-ENTRY'
         WHEN camera_id = 'ANPR-Exit'  THEN 'CAM-EXIT'
         ELSE camera_id
       END AS new_id
  FROM cameras
  WHERE camera_id LIKE 'Cam[_]%'
     OR camera_id LIKE 'CAM[_]%'
     OR camera_id IN ('ANPR-Entry', 'ANPR-Exit');

PRINT '--- Join health (BEFORE) — should equal the count of distinct cam ids in event tables ---';
SELECT
  (SELECT COUNT(*) FROM parking_sessions ps LEFT JOIN cameras c ON c.camera_id = ps.entry_camera_id WHERE ps.entry_camera_id IS NOT NULL AND c.id IS NULL) AS parking_sessions_unmatched_entry,
  (SELECT COUNT(*) FROM parking_sessions ps LEFT JOIN cameras c ON c.camera_id = ps.exit_camera_id  WHERE ps.exit_camera_id  IS NOT NULL AND c.id IS NULL) AS parking_sessions_unmatched_exit,
  (SELECT COUNT(*) FROM parking_sessions ps LEFT JOIN cameras c ON c.camera_id = ps.slot_camera_id  WHERE ps.slot_camera_id  IS NOT NULL AND c.id IS NULL) AS parking_sessions_unmatched_slot,
  (SELECT COUNT(*) FROM entry_exit_log    e LEFT JOIN cameras c ON c.camera_id = e.camera_id        WHERE e.camera_id        IS NOT NULL AND c.id IS NULL) AS entry_exit_log_unmatched;
GO

/* ============================================================================
   APPLY: rewrite the cameras.camera_id values.
   Uncomment the BEGIN TRAN / COMMIT block when ready.
   ============================================================================ */

-- BEGIN TRAN;

-- -- Phase 1 cameras: 'Cam_03' / 'CAM_03' → 'CAM-03'
-- UPDATE cameras
--   SET camera_id = REPLACE(camera_id, 'Cam_', 'CAM-')
--   WHERE camera_id LIKE 'Cam[_]%';

-- UPDATE cameras
--   SET camera_id = REPLACE(camera_id, 'CAM_', 'CAM-')
--   WHERE camera_id LIKE 'CAM[_]%';

-- -- Phase 2 gate cameras: 'ANPR-Entry'/'ANPR-Exit' → 'CAM-ENTRY'/'CAM-EXIT'
-- UPDATE cameras SET camera_id = 'CAM-ENTRY' WHERE camera_id = 'ANPR-Entry';
-- UPDATE cameras SET camera_id = 'CAM-EXIT'  WHERE camera_id = 'ANPR-Exit';

-- -- Verify joins now return zero unmatched
-- SELECT
--   (SELECT COUNT(*) FROM parking_sessions ps LEFT JOIN cameras c ON c.camera_id = ps.entry_camera_id WHERE ps.entry_camera_id IS NOT NULL AND c.id IS NULL) AS parking_sessions_unmatched_entry,
--   (SELECT COUNT(*) FROM parking_sessions ps LEFT JOIN cameras c ON c.camera_id = ps.exit_camera_id  WHERE ps.exit_camera_id  IS NOT NULL AND c.id IS NULL) AS parking_sessions_unmatched_exit,
--   (SELECT COUNT(*) FROM parking_sessions ps LEFT JOIN cameras c ON c.camera_id = ps.slot_camera_id  WHERE ps.slot_camera_id  IS NOT NULL AND c.id IS NULL) AS parking_sessions_unmatched_slot,
--   (SELECT COUNT(*) FROM entry_exit_log    e LEFT JOIN cameras c ON c.camera_id = e.camera_id        WHERE e.camera_id        IS NOT NULL AND c.id IS NULL) AS entry_exit_log_unmatched;

-- -- All four counts above should be 0. If not, ROLLBACK and investigate.

-- COMMIT;
-- -- (Use ROLLBACK; if anything looks wrong.)
GO

/* ============================================================================
   ALSO: refresh the cameras.name values per the new seed.

   Only needed if the cameras table was seeded BEFORE seed.sql was rewritten
   in this fix pass (i.e. names are still the old "B1-PARKING" / "GF-FRONT"
   duplicates). Either re-run seed.sql (idempotent MERGE), OR run the per-row
   updates below.
   ============================================================================ */

-- BEGIN TRAN;
-- UPDATE cameras SET name = 'Ground Floor — Camera 1'   WHERE camera_id = 'CAM-01';
-- UPDATE cameras SET name = 'Ground Floor — Camera 2'   WHERE camera_id = 'CAM-02';
-- UPDATE cameras SET name = 'B1 Parking — Camera 03'    WHERE camera_id = 'CAM-03';
-- UPDATE cameras SET name = 'B1 Parking — Camera 04'    WHERE camera_id = 'CAM-04';
-- UPDATE cameras SET name = 'B1 Parking — Camera 05'    WHERE camera_id = 'CAM-05';
-- UPDATE cameras SET name = 'B1 Parking — Camera 06'    WHERE camera_id = 'CAM-06';
-- UPDATE cameras SET name = 'B1 Parking — Camera 07'    WHERE camera_id = 'CAM-07';
-- UPDATE cameras SET name = 'B1 Parking — Camera 08'    WHERE camera_id = 'CAM-08';
-- UPDATE cameras SET name = 'B2 Parking — Camera 09'    WHERE camera_id = 'CAM-09';
-- UPDATE cameras SET name = 'B2 Parking — Camera 10'    WHERE camera_id = 'CAM-10';
-- UPDATE cameras SET name = 'B2 Parking — Camera 11'    WHERE camera_id = 'CAM-11';
-- UPDATE cameras SET name = 'B2 Parking — Camera 12'    WHERE camera_id = 'CAM-12';
-- UPDATE cameras SET name = 'B2 Parking — Camera 13'    WHERE camera_id = 'CAM-13';
-- UPDATE cameras SET name = 'B2 Parking — Camera 14'    WHERE camera_id = 'CAM-14';
-- UPDATE cameras SET name = 'Ground Entry Gate (ANPR)' WHERE camera_id = 'CAM-ENTRY';
-- UPDATE cameras SET name = 'Ground Exit Gate (ANPR)'  WHERE camera_id = 'CAM-EXIT';

-- -- Verify uniqueness
-- SELECT name, COUNT(*) AS dup_count FROM cameras GROUP BY name HAVING COUNT(*) > 1;
-- -- Should return zero rows.

-- COMMIT;
GO
