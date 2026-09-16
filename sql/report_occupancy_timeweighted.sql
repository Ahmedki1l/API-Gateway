-- ============================================================================
-- Time-weighted occupancy — the Report-1 point-1 anchor query (Q1 / Q2 / Q6).
--
-- Validated against damanat_pms on 2026-08-23 over 2026-08-01..2026-08-04.
-- Query 1 and Query 2 reconcile exactly, per floor and overall:
--     Ground 23.13%   B1 18.42%   B2 23.60%   OVERALL 21.72%
--
-- SCOPE — must stay in step with app/routers/occupancy.py (_slot_type_excl
-- + is_violation_zone), or this report and /occupancy/kpis will disagree:
--     slot_type NOT IN ('special_zone','roi') AND is_violation_zone = 0
--   -> 35 slots: Ground 8, B1 12, B2 15.
--   parking_slots holds 62 rows; the other 27 are 22 roi + 2 special_zone
--   + 3 violation-zone. The 3 violation-zone slots carry 6,527 slot_status
--   rows and counting them overstates overall occupancy by ~1.6pp.
--   (SLOT_TEST_E2E, floor='1', was dropped from the DB on 2026-08-23.)
--
-- TWO LOAD-BEARING DETAILS, both of which read as harmless style choices:
--   1. LEAD() runs over ALL rows; the status='occupied' filter is applied
--      AFTER. Filtering first makes LEAD skip to the next *occupied* row and
--      swallow the vacant gap between the two.
--   2. The final join is LEFT. With INNER, a slot that is never occupied in
--      the window vanishes instead of reporting 0 — on a 2-hour night window
--      that returned 3 rows instead of 35.
--
-- KNOWN DATA CAVEATS (properties of slot_status, not of this SQL):
--   * A slot whose only state is carried in from before @START_TIME reads
--     100% for the whole window (e.g. B25 over Aug 1-4). Time-weighting
--     cannot distinguish a genuine long stay from a stuck state.
--   * Ingest gaps are attributed to the last known status, so a VA outage
--     is billed as occupancy. Largest gap in this window is 3.0h overnight.
--
-- PERFORMANCE: slot_status has no index leading on `time`, so the range
-- predicate always falls back to a full scan (161 pages, 2 scans, 320 reads).
-- The optimizer asks for this unprompted, twice:
--     CREATE NONCLUSTERED INDEX ix_slot_status_time
--         ON slot_status (time) INCLUDE (slot_id, status);
-- Worth adding before this runs over month-scale ranges. Note the join to
-- floor_slots inside the two scans does NOT reduce reads — floor_slots is a
-- CTE, re-expanded at each reference, which turns those scans into 70
-- nested-loop passes (39,237 reads). It is kept only for readability.
-- ============================================================================


-- ==================================================== QUERY 1 — per-slot totals
DECLARE @START_TIME DATETIME = '2026-08-01 00:00:00';
DECLARE @END_TIME   DATETIME = '2026-08-04 00:00:00';
DECLARE @floor VARCHAR(50) = NULL;
WITH floor_slots AS (
    SELECT slot_id, floor FROM parking_slots
      WHERE slot_type NOT IN ('special_zone', 'roi')
      AND is_violation_zone = 0
      AND (@floor IS NULL OR floor = @floor)
),
start_status AS (
    SELECT id, slot_id, status, @START_TIME AS time
    FROM (SELECT slot_status.id, slot_status.slot_id, slot_status.status, slot_status.time,
            ROW_NUMBER() OVER (PARTITION BY slot_status.slot_id ORDER BY slot_status.time DESC) AS RowNum
          FROM slot_status JOIN floor_slots ON slot_status.slot_id = floor_slots.slot_id
          WHERE slot_status.time < @START_TIME) AS subquery
    WHERE RowNum = 1
),
period_status AS (
    SELECT slot_status.id, slot_status.slot_id, slot_status.status, slot_status.time
    FROM slot_status JOIN floor_slots ON slot_status.slot_id = floor_slots.slot_id
    WHERE slot_status.time >= @START_TIME AND slot_status.time < @END_TIME
),
end_status AS (
    SELECT NULL AS id, slot_id, NULL AS status, @END_TIME AS time FROM floor_slots
)
SELECT floor_slots.floor, floor_slots.slot_id,
       COALESCE(SUM(occupied_time.TimeDifference), 0) AS TotalOccupiedSeconds
FROM floor_slots
LEFT JOIN (
    SELECT *, DATEDIFF(SECOND, time, NextTime) AS TimeDifference
    FROM (SELECT *, LEAD(time) OVER (PARTITION BY slot_id ORDER BY time ASC) AS NextTime
          FROM (SELECT * FROM start_status UNION ALL SELECT * FROM period_status UNION ALL SELECT * FROM end_status) AS combined_status
         ) AS with_next_time
    WHERE status = 'occupied'
) AS occupied_time ON floor_slots.slot_id = occupied_time.slot_id
GROUP BY floor_slots.floor, floor_slots.slot_id
ORDER BY floor_slots.floor, floor_slots.slot_id;

GO

-- ================================= QUERY 2 — day x hour x floor grid (Stage 1)
-- The shape the endpoint actually needs: one scan feeding all three groupings
-- (hourly buckets by day, day-of-week averages, floor breakdown). Serves
-- points 1, 2, 6, 7, 8, 9, 10, 11, 14, 15, 40, 42, 47, 53.
-- 216 rows / ~0.12s for a 3-day range; ~0.10s for the full 31-day history.
--
-- Note the IS NULL guard in `grid`: on a LEFT JOIN miss, `NULL > h_start` is
-- UNKNOWN, so the CASE falls to ELSE and silently credits a full 3600s. That
-- bug reads as 99% occupancy and is invisible without a cross-check.
DECLARE @START_TIME DATETIME = '2026-08-01 00:00:00';
DECLARE @END_TIME   DATETIME = '2026-08-04 00:00:00';
DECLARE @floor VARCHAR(50) = NULL;

WITH floor_slots AS (
    SELECT slot_id, floor FROM parking_slots
    WHERE slot_type NOT IN ('special_zone','roi')
      AND is_violation_zone = 0
      AND (@floor IS NULL OR floor = @floor)
),
events AS (
    SELECT slot_id, status, time FROM (
        SELECT ss.slot_id, ss.status, @START_TIME AS time,
               ROW_NUMBER() OVER (PARTITION BY ss.slot_id ORDER BY ss.time DESC, ss.id DESC) rn
        FROM slot_status ss JOIN floor_slots f ON f.slot_id = ss.slot_id
        WHERE ss.time < @START_TIME
    ) carry WHERE rn = 1
    UNION ALL
    SELECT ss.slot_id, ss.status, ss.time
    FROM slot_status ss JOIN floor_slots f ON f.slot_id = ss.slot_id
    WHERE ss.time >= @START_TIME AND ss.time < @END_TIME
),
intervals AS (
    -- LEAD over ALL events, THEN filter to occupied. Filtering first would make
    -- LEAD skip to the next *occupied* row and swallow the vacant gap between.
    SELECT slot_id, seg_start, seg_end FROM (
        SELECT slot_id, status, time AS seg_start,
               ISNULL(LEAD(time) OVER (PARTITION BY slot_id ORDER BY time), @END_TIME) AS seg_end
        FROM events
    ) e WHERE status = 'occupied'
),
hours AS (
    SELECT DATEADD(HOUR, n, @START_TIME) AS h_start, DATEADD(HOUR, n+1, @START_TIME) AS h_end
    FROM (SELECT TOP (DATEDIFF(HOUR, @START_TIME, @END_TIME))
                 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
          FROM sys.all_objects a CROSS JOIN sys.all_objects b) t
),
grid AS (
    SELECT h.h_start, f.floor, f.slot_id,
           -- The IS NULL guard is load-bearing: on a LEFT JOIN miss, `NULL > h_start`
           -- is UNKNOWN, so the CASE would fall to ELSE and credit a full 3600s.
           ISNULL(SUM(CASE WHEN i.seg_start IS NULL THEN 0 ELSE DATEDIFF(SECOND,
               CASE WHEN i.seg_start > h.h_start THEN i.seg_start ELSE h.h_start END,
               CASE WHEN i.seg_end   < h.h_end   THEN i.seg_end   ELSE h.h_end   END) END), 0) AS occ_sec
    FROM hours h
    CROSS JOIN floor_slots f
    LEFT JOIN intervals i ON i.slot_id = f.slot_id AND i.seg_start < h.h_end AND i.seg_end > h.h_start
    GROUP BY h.h_start, f.floor, f.slot_id
)
SELECT CAST(h_start AS DATE) AS d, DATEPART(HOUR, h_start) AS hr, floor,
       SUM(occ_sec) AS occ_sec, COUNT(*) AS slots,
       CAST(100.0*SUM(occ_sec)/(COUNT(*)*3600.0) AS DECIMAL(5,2)) AS pct
FROM grid GROUP BY CAST(h_start AS DATE), DATEPART(HOUR, h_start), floor
ORDER BY d, hr, floor;
GO
