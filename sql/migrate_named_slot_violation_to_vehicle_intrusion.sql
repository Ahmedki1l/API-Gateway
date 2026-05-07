/* =============================================================================
   migrate_named_slot_violation_to_vehicle_intrusion.sql

   ONE-TIME rename: replaces `alert_type='named_slot_violation'` (the legacy
   internal name VA used for reserved-slot intrusions) with the canonical
   `vehicle_intrusion`. Operator-facing terminology: the Alerts page filter
   vocabulary aligns on `vehicle_intrusion`. Severity also escalates from
   `warning` (the legacy bucket) to `critical` (where vehicle_intrusion lives).

   Run AFTER deploying:
     - VA src/services/alert_service.py:15            (returns "vehicle_intrusion")
     - VA src/services/slot_status_service.py:24-28   (description map)
     - VA src/core/engine/engine_runtime.py:597,603   (drops legacy name)
     - Gateway routers/alerts.py:103-105 + 154-159    (severity map updated)

   Then restart VA and Gateway.

   ============================================================================
   PRE-FLIGHT
   ============================================================================
   1. Take a SQL Server backup.
   2. Confirm no in-flight writers still emit the legacy name:
        - grep -rn '"named_slot_violation"' Damanat-PMS-VideoAnalytics/src/
        - grep -rn 'named_slot_violation' "Damanat PMS AI/damanat-backend/app/"
      Expected: matches only in tests / docs / severity-map back-compat entry.

   ============================================================================
   DRY-RUN
   ============================================================================ */
PRINT '--- Rows that will be renamed ---';
SELECT alert_type, COUNT(*) AS row_count
  FROM alerts
  WHERE alert_type = 'named_slot_violation'
  GROUP BY alert_type;
GO

/* ============================================================================
   APPLY
   ============================================================================ */

BEGIN TRAN;

UPDATE alerts
  SET alert_type = 'vehicle_intrusion'
  WHERE alert_type = 'named_slot_violation';

PRINT '--- Rows still named_slot_violation post-update (should be 0) ---';
SELECT COUNT(*) AS remaining_legacy
  FROM alerts
  WHERE alert_type = 'named_slot_violation';

COMMIT;
GO

/* ============================================================================
   ROLLBACK (if needed before commit, just ROLLBACK;
              after commit, run the reverse UPDATE within a fresh BEGIN TRAN)
   ============================================================================ */
