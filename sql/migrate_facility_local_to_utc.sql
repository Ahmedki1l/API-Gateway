/* =============================================================================
   migrate_facility_local_to_utc.sql

   ONE-TIME backfill to convert legacy DATETIME columns from
   facility-local-pretending-to-be-UTC (the old PMS-AI parser stripped the
   camera's `+03:00` tzinfo without converting) to true UTC.

   Run this AFTER deploying the parser fix at:
     Damanat PMS AI/damanat-backend/app/services/entry_exit_service.py:41
     Damanat PMS AI/damanat-backend/app/services/entry_exit_service.py:135
     Damanat PMS AI/damanat-backend/app/services/parking_session_service.py:21

   ============================================================================
   ASSUMPTIONS
   ============================================================================
   - Cameras report timestamps with `+03:00` (Saudi Arabia / Riyadh; verified
     2026-05-03 via PMS-AI events.log: `<dateTime>2026-...+03:00</dateTime>`).
   - All historical event timestamps are 3 hours ahead of true UTC.
   - @cutover_time is the wallclock instant the parser fix was deployed.
     Rows AFTER this moment are already true UTC and must NOT be shifted.

   ============================================================================
   PRE-FLIGHT CHECKLIST
   ============================================================================
   1. Take a SQL Server backup (.bak or full DB snapshot).
   2. Confirm the parser fix is deployed and PMS-AI is restarted.
   3. Capture @cutover_time precisely — set it to the deploy moment below.
   4. Run inside a single transaction. If any UPDATE looks wrong, ROLLBACK.
   5. After commit, spot-check by comparing `event_time` of a recent gate
      crossing against the camera clock — they should differ by exactly the
      facility offset (3 hours), with the DB being EARLIER (true UTC).

   ============================================================================
   DRY-RUN: count rows that will be touched (run this first)
   ============================================================================ */
DECLARE @cutover_time DATETIME = '2026-05-03 12:00:00'; -- *** EDIT TO ACTUAL DEPLOY TIME ***
DECLARE @offset_hours INT       = -3;                   -- subtract 3h to convert facility-local→UTC

PRINT '--- Dry-run row counts ---';
SELECT 'entry_exit_log.event_time'    AS column_name, COUNT(*) AS rows_to_shift FROM entry_exit_log    WHERE created_at < @cutover_time AND event_time IS NOT NULL
UNION ALL SELECT 'parking_sessions.entry_time',     COUNT(*) FROM parking_sessions WHERE created_at < @cutover_time AND entry_time IS NOT NULL
UNION ALL SELECT 'parking_sessions.exit_time',      COUNT(*) FROM parking_sessions WHERE created_at < @cutover_time AND exit_time IS NOT NULL
UNION ALL SELECT 'parking_sessions.parked_at',      COUNT(*) FROM parking_sessions WHERE created_at < @cutover_time AND parked_at IS NOT NULL
UNION ALL SELECT 'parking_sessions.slot_left_at',   COUNT(*) FROM parking_sessions WHERE created_at < @cutover_time AND slot_left_at IS NOT NULL
UNION ALL SELECT 'alerts.triggered_at',             COUNT(*) FROM alerts           WHERE triggered_at < @cutover_time AND triggered_at IS NOT NULL
UNION ALL SELECT 'alerts.resolved_at',              COUNT(*) FROM alerts           WHERE triggered_at < @cutover_time AND resolved_at IS NOT NULL
UNION ALL SELECT 'zone_occupancy.last_updated',     COUNT(*) FROM zone_occupancy   WHERE last_updated < @cutover_time AND last_updated IS NOT NULL
UNION ALL SELECT 'slot_status.[time]',              COUNT(*) FROM slot_status      WHERE [time] < @cutover_time AND [time] IS NOT NULL
UNION ALL SELECT 'camera_feeds.timestamp',          COUNT(*) FROM camera_feeds     WHERE [timestamp] < @cutover_time AND [timestamp] IS NOT NULL;
GO

/* ============================================================================
   APPLY: shift every facility-local row -3 hours to land on true UTC.
   Uncomment the BEGIN TRAN / COMMIT block below ONLY when ready.
   ============================================================================ */

-- BEGIN TRAN;

-- DECLARE @cutover_time DATETIME = '2026-05-03 12:00:00'; -- *** EDIT TO ACTUAL DEPLOY TIME ***

-- UPDATE entry_exit_log
--   SET event_time = DATEADD(HOUR, -3, event_time)
--   WHERE created_at < @cutover_time AND event_time IS NOT NULL;

-- UPDATE parking_sessions
--   SET entry_time   = DATEADD(HOUR, -3, entry_time),
--       exit_time    = CASE WHEN exit_time    IS NOT NULL THEN DATEADD(HOUR, -3, exit_time)    ELSE NULL END,
--       parked_at    = CASE WHEN parked_at    IS NOT NULL THEN DATEADD(HOUR, -3, parked_at)    ELSE NULL END,
--       slot_left_at = CASE WHEN slot_left_at IS NOT NULL THEN DATEADD(HOUR, -3, slot_left_at) ELSE NULL END
--   WHERE created_at < @cutover_time;

-- UPDATE alerts
--   SET triggered_at = DATEADD(HOUR, -3, triggered_at),
--       resolved_at  = CASE WHEN resolved_at IS NOT NULL THEN DATEADD(HOUR, -3, resolved_at) ELSE NULL END
--   WHERE triggered_at < @cutover_time;

-- UPDATE zone_occupancy SET last_updated = DATEADD(HOUR, -3, last_updated)
--   WHERE last_updated < @cutover_time;

-- UPDATE slot_status SET [time] = DATEADD(HOUR, -3, [time])
--   WHERE [time] < @cutover_time;

-- UPDATE camera_feeds SET [timestamp] = DATEADD(HOUR, -3, [timestamp])
--   WHERE [timestamp] < @cutover_time;

-- -- Spot check before commit: pick one well-known historical event and verify
-- -- its time is now 3 hours earlier than what you remember.
-- SELECT TOP 5 plate_number, event_time, gate FROM entry_exit_log ORDER BY event_time DESC;

-- COMMIT;
-- -- (Use ROLLBACK; if anything looks wrong.)
GO

/* ============================================================================
   ROLLBACK (if you committed and need to undo)
   ============================================================================
   Apply the SAME SQL with +3 instead of -3. Confirm @cutover_time hasn't
   moved. Wrap in BEGIN TRAN / COMMIT.
   ============================================================================ */
