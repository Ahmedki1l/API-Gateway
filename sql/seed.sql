/* ============================================================================
   seed.sql — cloned from the live damanat_pms database

   Companion to bootstrap.sql, which is schema-only (DDL + additive ALTERs +
   FKs). Run this AFTER bootstrap.sql to populate the database.

   Tables seeded:
     1. parking_slots          (32 rows — B1 / B2 / Ground)
     2. cameras                (16-row canonical fleet, MERGE-style upsert,
                                Fernet-encrypted RTSP credentials)
     3. zone_occupancy         (3 rows: B1 / B2 / GARAGE-TOTAL)
     4. vehicles               (5 registered vehicles)
     5. slot_status            (32 rows — latest state per slot)
     6. entry_exit_log         (26 gate crossings from live ANPR)
     7. parking_sessions       (17 rows — real entry/exit/park sessions)
     8. alerts                 (24 simulated rows — 4 types across 14 days)
     9. camera_feeds           (0 rows — table empty in live DB)
    10. Floor alias normalization

   Idempotent — every block is guarded by IF NOT EXISTS or by MERGE so
   re-running the file does nothing on a populated DB.

   IMPORTANT — cameras section:
     The encrypted passwords below were created with a specific
     CAMERAS_ENCRYPTION_KEY. If your gateway runs with a different key,
     decryption will fail at runtime (InvalidToken); re-seed by POSTing
     to /cameras/ with plaintext passwords so the gateway encrypts with
     your key.

   Run:
     sqlcmd -E -S localhost -d damanat_pms -i sql/seed.sql
     (or `-U sa -P "..."` for SQL auth)

   Data cloned from live DB on 2026-04-26.
   ============================================================================ */

SET NOCOUNT ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

PRINT '──────────────────────────────────────────────';
PRINT '  Parking System — seed.sql (live DB clone)';
PRINT '──────────────────────────────────────────────';

/* ────────────────────────────────────────────────────────────────────────────
   1. parking_slots — 32 slots (B1 / B2 / Ground)
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM dbo.parking_slots WHERE slot_id = 'B1_CRO')
BEGIN
    INSERT INTO dbo.parking_slots (slot_id, slot_name, floor, is_available, is_violation_zone) VALUES
        (N'B1_CRO', N'Slot B1 CRO', N'B1', 1, 0),
        (N'B10_CTO', N'Slot B10 CTO', N'B1', 1, 0),
        (N'B11_CFO', N'Slot B11_CFO', N'B1', 0, 0),
        (N'B12', N'Slot B12', N'B1', 1, 0),
        (N'B13_COO', N'Slot B13 COO', N'B1', 1, 0),
        (N'B14', N'Slot B14', N'B2', 0, 0),
        (N'B15', N'Slot B15', N'B2', 0, 0),
        (N'B16', N'Slot B16', N'B2', 1, 0),
        (N'B17', N'Slot B17', N'B2', 0, 0),
        (N'B18', N'Slot B18', N'B2', 0, 0),
        (N'B19', N'Slot B19', N'B2', 1, 0),
        (N'B2', N'Slot B2', N'B1', 1, 0),
        (N'B20', N'Slot B20', N'B2', 0, 0),
        (N'B21', N'Slot B21', N'B2', 1, 0),
        (N'B22', N'Slot B22', N'B2', 1, 0),
        (N'B23', N'Slot B23', N'B2', 1, 0),
        (N'B24', N'Slot B24', N'B2', 0, 0),
        (N'B25', N'Slot B25', N'B2', 0, 0),
        (N'B27', N'Slot B27', N'B2', 0, 0),
        (N'B3_CEO', N'Slot B3 CEO', N'B1', 0, 0),
        (N'B6_Reserved', N'Slot B6 Reserved', N'B1', 1, 0),
        (N'B8', N'Slot B8', N'B1', 1, 0),
        (N'B9', N'Slot B9', N'B1', 0, 0),
        (N'G1', N'G1_SN', N'Ground', 0, 0),
        (N'G2', N'Slot G2', N'Ground', 0, 0),
        (N'G3', N'Slot G3', N'Ground', 1, 0),
        (N'G4', N'Slot G4', N'Ground', 1, 0),
        (N'G5', N'Slot G5', N'Ground', 0, 0),
        (N'G6', N'Slot G6', N'Ground', 1, 0),
        (N'GMIA', N'GMIA', N'B1', 0, 0),
        (N'V1_Violation_1', N'Slot V1 Violation 1', N'Ground', 1, 1),
        (N'V2_Violation_2', N'Slot V2 Violation 2', N'Ground', 1, 1);
    PRINT '  Seeded 32 parking_slots';
END;

/* Backfill floors lookup from the slots we just seeded. */
INSERT INTO dbo.floors (name)
SELECT DISTINCT ps.floor FROM dbo.parking_slots ps
WHERE ps.floor IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = ps.floor);

IF COL_LENGTH(N'dbo.parking_slots', N'floor_id') IS NOT NULL
    UPDATE ps SET floor_id = f.id
    FROM dbo.parking_slots ps INNER JOIN dbo.floors f ON f.name = ps.floor
    WHERE ps.floor_id IS NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   2. cameras — canonical 16-camera fleet (Fernet-encrypted credentials)
   ────────────────────────────────────────────────────────────────────────────
   MERGE so re-running updates fields without inserting duplicates.
   ──────────────────────────────────────────────────────────────────────────── */
IF OBJECT_ID(N'dbo.cameras', 'U') IS NOT NULL
BEGIN
    -- camera_id is the canonical dash-uppercase form (CAM-XX, CAM-ENTRY, CAM-EXIT)
    -- — matches what PMS-AI emits to event tables and what the dispatcher's
    -- hardcoded zone-occupancy list checks for. `name` is unique per camera;
    -- ops should refine the placeholder values to operational names
    -- (e.g. "B1 — North Aisle Pillar 3"). The encrypted passwords below were
    -- created with a specific CAMERAS_ENCRYPTION_KEY — see header note.
    MERGE INTO dbo.cameras AS Target
    USING (VALUES
        -- ENTRY camera username is `kloudspott` (DOUBLE T) — verified live against the
        -- ISAPI on 2026-05-04. `kloudspot` (single t) returns 401. The seeded ciphertext
        -- below was encrypted with the dev CAMERAS_ENCRYPTION_KEY shipped in .env.example;
        -- on a production deploy with a different key, re-encrypt by calling
        -- POST /cameras/{id} with the new credentials, or run a script that uses
        -- app.services.crypto.cipher.encrypt(<password>) before INSERT.
        (N'CAM-ENTRY', N'Ground Entry Gate (ANPR)', N'Ground', N'10.1.13.100', 554, N'/Streaming/Channels/101', N'kloudspott', N'gAAAAABp6fG_8xKy6gcai-WzQ6_kf80AvCqmnwOJ2oDFJ7Aq_kAIXcs_gaTYHWoECpzWfmoEuNM2fpn3pyDzSF5w5E7lcTHXRw==', 1, N'string'),
        (N'CAM-EXIT',  N'Ground Exit Gate (ANPR)',  N'Ground', N'10.1.13.101', 554, N'/Streaming/Channels/101', N'kloudspot1', N'gAAAAABp6fIGrXXkRo3nz-Yhm1IexonNM734GyEgDtrvDAY8p52FyETJt3BEwUWrfxd9ivggeG7J3-_lKInyVg95uvnLQCerFg==', 1, N'string'),
        (N'CAM-01',    N'Ground Floor — Camera 1', N'Ground', N'10.1.13.60', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6e6A6j_Qpr6-uimln8jM5osSSPctIy-0dob6PjUGWLAHTd6XIkWiSaUaKfmXNT_u4iy2W8Pr4VA45Kk4favDsOClHw==', 1, N'string'),
        (N'CAM-02',    N'Ground Floor — Camera 2', N'Ground', N'10.1.13.61', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6e7RABH1t0SZa7kgGjwLfoObuiSkpJpxRsYQ3VGD3xxB1DeeRZ0Dka2xXztPXi2S-afIEjlVT_xBG7sf5kmL3ZI1bA==', 1, N'string'),
        (N'CAM-03',    N'B1 Parking — Camera 03',     N'B1',     N'10.1.13.62', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6e-D18fZxcTrYrdfe7P8FiJVi-02hz7N9LMKSeWZpkYzNh14YFRljelTq-JBWYjuDT5n-TYAhw6bUQYY5XuK2yWdtw==', 1, N'string'),
        (N'CAM-04',    N'B1 Parking — Camera 04',     N'B1',     N'10.1.13.63', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6e-gp-OCNTt8AU8c3vIVIIZwbTHSSfTPoCqal9nNQCeSaoFjTc7eBGDJSBWfmGfJ5atZEkpBoVZ_T8NO790HCZpUaA==', 1, N'string'),
        (N'CAM-05',    N'B1 Parking — Camera 05',     N'B1',     N'10.1.13.64', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6e_uYUN6Qr46oV3elkRDLFd09qFaKwrgzv9I8PpWX9inFP2-RlFtmmJxVTHiqq9x6UdGJaFuTumPwyha9K60rjMdkA==', 1, N'string'),
        (N'CAM-06',    N'B1 Parking — Camera 06',     N'B1',     N'10.1.13.65', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6e_2bsqW8uCeal2wXSkAxbZyrKYUFkFxUiK7SaRKSnx4AAyppzvzwFTd5BRjhFt82a_laGZ1SVLPh2Et0IxifnL6ow==', 1, N'string'),
        (N'CAM-07',    N'B1 Parking — Camera 07',     N'B1',     N'10.1.13.66', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6e_9LgEh_4GCmDwEd_FHVAEMnWT0GFgMy3M-nhC4GKOOuHVN-CfAdyTHJPCtJAM1RViV-IwSObVKLzs-3GZowfFmIA==', 1, N'string'),
        (N'CAM-08',    N'B1 Parking — Camera 08',     N'B1',     N'10.1.13.67', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6fAY2-AEnVw7taPduRk__zPqqrTWEf1qWzkgxsmu17x6RDZMEkrmoO7mdInTY00dUywiJkMjlwWo1v_nNJrue-Ndhw==', 1, N'string'),
        (N'CAM-09',    N'B2 Parking — Camera 09',     N'B2',     N'10.1.13.68', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6fCPk_5bVzvA6f54c6asDneRNfFKlGRkxHYioYMBbq9J85mfiLvWgDCf01FjPe2oGsMhDYLd7U_apRZhboHxOqH1eg==', 1, N'string'),
        (N'CAM-10',    N'B2 Parking — Camera 10',     N'B2',     N'10.1.13.69', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6fDQw9C51CFlYc-Ls3lINRvWyUvrhtKkN9uCsczDkcc0E_hKhENbL18hCgCwlqQEM83m5eInc8q4Y6w9gWTOalKwzA==', 1, N'string'),
        (N'CAM-11',    N'B2 Parking — Camera 11',     N'B2',     N'10.1.13.70', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6fDYHfJQsQY3UdFxVeZCQ184_jcVlJvSE1f3w41my8Rnqeckrop5dRSWpD8HkDWTUc5JiaFYpQwJvF7QXrYOQlsL0g==', 1, N'string'),
        (N'CAM-12',    N'B2 Parking — Camera 12',     N'B2',     N'10.1.13.71', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6fDw1Qdj1Rs4SREgTw6QMXnLgNoub-jthp1_DdFbVoSM4LISfMhwi4_YfKA2llgsrszPFcOVup_e7DAIfkc-00VuhA==', 1, N'string'),
        (N'CAM-13',    N'B2 Parking — Camera 13',     N'B2',     N'10.1.13.72', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6fEA1_0Ts-N94Y_OItQemw_In7YtqAfC5sDtSKEUuB3OuySeimbMDhGznZGYHBsQ0rqCg7T4gZy2MwIE93kTHp8oVQ==', 1, N'string'),
        (N'CAM-14',    N'B2 Parking — Camera 14',     N'B2',     N'10.1.13.73', 554, N'/Streaming/Channels/101', N'kloudspot', N'gAAAAABp6fEI7ltsTbu8siRozaH_9zi1MVOrwBO8rumjDSVSJN_5SZlFNK3ChoaSB0VjtHH52ukLdm8hMgd535ap0fSDQho7Gg==', 1, N'string')
    ) AS Source (camera_id, name, floor, ip_address, rtsp_port, rtsp_path, username, password_encrypted, enabled, notes)
    ON Target.camera_id = Source.camera_id
    WHEN MATCHED THEN
        UPDATE SET
            name = Source.name,
            floor = Source.floor,
            ip_address = Source.ip_address,
            rtsp_port = Source.rtsp_port,
            rtsp_path = Source.rtsp_path,
            username = Source.username,
            password_encrypted = Source.password_encrypted,
            enabled = Source.enabled,
            notes = Source.notes,
            updated_at = GETUTCDATE()
    WHEN NOT MATCHED THEN
        INSERT (camera_id, name, floor, ip_address, rtsp_port, rtsp_path, username, password_encrypted, enabled, notes)
        VALUES (Source.camera_id, Source.name, Source.floor, Source.ip_address, Source.rtsp_port, Source.rtsp_path, Source.username, Source.password_encrypted, Source.enabled, Source.notes);
    PRINT '  Seeded 16 cameras (canonical fleet).';
END
GO

/* Ensure new camera floor names exist in floors lookup, then backfill
   cameras.floor_id and cameras.watches_floor_id for the inserted rows. */
INSERT INTO dbo.floors (name)
SELECT DISTINCT t.floor FROM dbo.cameras t
WHERE t.floor IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM dbo.floors f WHERE f.name = t.floor);

IF COL_LENGTH(N'dbo.cameras', N'floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.cameras', N'floor') IS NOT NULL
    UPDATE t SET floor_id = f.id
    FROM dbo.cameras t INNER JOIN dbo.floors f ON f.name = t.floor
    WHERE t.floor_id IS NULL;

IF COL_LENGTH(N'dbo.cameras', N'watches_floor_id') IS NOT NULL
   AND COL_LENGTH(N'dbo.cameras', N'watches_floor') IS NOT NULL
    UPDATE t SET watches_floor_id = f.id
    FROM dbo.cameras t INNER JOIN dbo.floors f ON f.name = t.watches_floor
    WHERE t.watches_floor_id IS NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   3. zone_occupancy — line-crossing counters (B1, B2, GARAGE-TOTAL)
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM dbo.zone_occupancy WHERE zone_id = 'B1-PARKING')
BEGIN
    INSERT INTO dbo.zone_occupancy (zone_id, camera_id, current_count, max_capacity, last_updated, zone_name, floor) VALUES
        (N'B1-PARKING', N'CAM-03', 2, 11, GETUTCDATE(), N'B1 Parking', N'B1'),
        (N'B2-PARKING', N'CAM-09', 13, 13, GETUTCDATE(), N'B2 Parking', N'B2'),
        (N'GARAGE-TOTAL', N'CAM-03', 15, 24, GETUTCDATE(), N'Garage Total', N'ALL');
    PRINT '  Seeded 3 zone_occupancy rows';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   4. vehicles — 5 registered vehicles from live DB
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM dbo.vehicles WHERE plate_number = N'ZXY-123')
BEGIN
    INSERT INTO dbo.vehicles
        (plate_number, owner_name, vehicle_type, employee_id, is_registered, registered_at, notes, title, is_employee, phone, email)
    VALUES
        (N'ZXY-123', N'Ahmed alaa', N'sedan', N'452', 1, '2026-04-13 01:21:54.437', N'good', N'eng.', 1, NULL, NULL),
        (N'cdf-123', N'Mohamed Henaish', N'cross', N'emp-2', 1, '2026-04-13 10:17:29.103', N'good', N'eng.', 1, NULL, NULL),
        (N'kgh-587', N'mohamed gamal', N'suv', N'875', 1, '2026-04-14 12:56:19.08', N'good', N'eng.', 1, NULL, NULL),
        (N'TEST-001', N'Ahmed Test', N'sedan', NULL, 1, '2026-04-22 20:51:12.707', NULL, N'Mr', 1, N'+201234567890', N'test@example.com'),
        (N'asdr1234', N'ahmed alaa 2', N'sedan', NULL, 1, '2026-04-25 12:59:22.78', NULL, N'test', 0, NULL, NULL);
    PRINT '  Seeded 5 vehicles';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   5. slot_status — latest state per slot (32 rows)
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM dbo.slot_status WHERE slot_id = N'B1_CRO')
BEGIN
    INSERT INTO dbo.slot_status (slot_id, plate_number, status, time) VALUES
        (N'B1_CRO', NULL, N'available', '2026-04-14 05:48:27.59'),
        (N'B10_CTO', NULL, N'available', '2026-04-14 10:13:25.26'),
        (N'B11_CFO', NULL, N'occupied', '2026-04-14 08:17:08.75'),
        (N'B12', NULL, N'available', '2026-04-14 10:20:20.407'),
        (N'B13_COO', NULL, N'available', '2026-04-14 10:24:37.607'),
        (N'B14', NULL, N'occupied', '2026-04-14 08:12:03.843'),
        (N'B15', NULL, N'occupied', '2026-04-14 10:22:35.65'),
        (N'B16', NULL, N'available', '2026-04-13 05:51:48.703'),
        (N'B17', NULL, N'occupied', '2026-04-14 10:22:35.49'),
        (N'B18', NULL, N'occupied', '2026-04-14 10:22:35.5'),
        (N'B19', NULL, N'available', '2026-04-11 12:08:58.663'),
        (N'B2', NULL, N'available', '2026-04-14 10:24:46.6'),
        (N'B20', NULL, N'occupied', '2026-04-14 10:22:35.507'),
        (N'B21', NULL, N'available', '2026-04-14 10:23:04.88'),
        (N'B22', NULL, N'available', '2026-04-14 10:13:25.79'),
        (N'B23', NULL, N'available', '2026-04-13 21:01:01.633'),
        (N'B24', NULL, N'occupied', '2026-04-14 08:11:19.173'),
        (N'B25', NULL, N'occupied', '2026-04-14 10:23:41.293'),
        (N'B27', NULL, N'occupied', '2026-04-14 10:22:35.653'),
        (N'B3_CEO', NULL, N'occupied', '2026-04-14 10:22:35.183'),
        (N'B6_Reserved', NULL, N'available', '2026-04-14 10:23:05.18'),
        (N'B8', NULL, N'available', '2026-04-14 10:13:42.14'),
        (N'B9', NULL, N'occupied', '2026-04-14 05:07:21.223'),
        (N'G1', NULL, N'occupied', '2026-04-14 08:20:36.567'),
        (N'G2', NULL, N'occupied', '2026-04-14 10:13:10.943'),
        (N'G3', NULL, N'available', '2026-04-14 10:13:50.293'),
        (N'G4', NULL, N'available', '2026-04-14 10:23:59.667'),
        (N'G5', NULL, N'occupied', '2026-04-14 05:47:13.703'),
        (N'G6', NULL, N'available', '2026-04-14 09:17:58.93'),
        (N'GMIA', NULL, N'occupied', '2026-04-14 09:17:45.46'),
        (N'V1_Violation_1', NULL, N'available', '2026-04-14 08:11:45.177'),
        (N'V2_Violation_2', NULL, N'available', '2026-04-14 05:12:50.89');
    PRINT '  Seeded 32 slot_status rows (latest per slot)';
END;

/* Backfill parking_slot_id (INT FK partner) for the new rows. */
IF COL_LENGTH(N'dbo.slot_status', N'parking_slot_id') IS NOT NULL
    UPDATE t SET parking_slot_id = ps.id
    FROM dbo.slot_status t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
    WHERE t.parking_slot_id IS NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   6. entry_exit_log — 26 gate crossings from live ANPR
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM dbo.entry_exit_log WHERE plate_number = N'EEB-80' AND event_time = '2026-04-01 09:24:05')
BEGIN
    INSERT INTO dbo.entry_exit_log
        (plate_number, vehicle_type, gate, camera_id, event_time, parking_duration, snapshot_path, is_test)
    VALUES
        (N'EEB-80', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-01 09:24:05', NULL, NULL, 0),
        (N'SHR-1198', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-01 09:34:42', NULL, NULL, 0),
        (N'BGD-7593', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-01 09:37:30', NULL, NULL, 0),
        (N'HDU-7', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-02 09:34:34', NULL, NULL, 0),
        (N'NJS-7894', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-02 10:13:51', NULL, NULL, 0),
        (N'TRS-9117', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-02 11:13:02', NULL, NULL, 0),
        (N'SHR-1198', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-02 11:15:55', NULL, NULL, 0),
        (N'HVA-77', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-02 11:23:35', NULL, NULL, 0),
        (N'ZRS-6511', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 08:44:32', NULL, NULL, 0),
        (N'AAD-2560', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 08:47:05', NULL, NULL, 0),
        (N'HGD-2926', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 08:50:09', NULL, NULL, 0),
        (N'UEU-777', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 08:50:17', NULL, NULL, 0),
        (N'TTB-8627', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 08:50:30', NULL, NULL, 0),
        (N'KKR-2994', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 08:52:27.43', NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055235_397226.jpg', 0),
        (N'SHR-1198', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 08:59:13.117', NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055923_066242.jpg', 0),
        (N'NDD-4141', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 09:06:02', NULL, NULL, 0),
        (N'HBR-4920', N'unknown', N'exit', N'CAM-EXIT', '2026-04-13 09:07:07.513', NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-EXIT_20260413_060709_927038.jpg', 0),
        (N'RTB-2016', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-13 09:10:38', NULL, NULL, 0),
        (N'RGR-6466', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-14 08:06:46', NULL, NULL, 0),
        (N'HGD-2926', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-14 08:11:21', NULL, NULL, 0),
        (N'SDD-6707', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-14 08:35:45', NULL, NULL, 0),
        (N'NXR-2727', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-14 08:37:16', NULL, NULL, 0),
        (N'AAD-2560', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-14 08:46:28', NULL, NULL, 0),
        (N'SHR-1198', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-14 08:47:53', NULL, NULL, 0),
        (N'EEB-80', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-14 08:51:30', NULL, NULL, 0),
        (N'RDJ-9640', N'unknown', N'entry', N'CAM-ENTRY', '2026-04-14 13:27:16', NULL, NULL, 0);
    PRINT '  Seeded 26 entry_exit_log rows';
END;
GO

/* ────────────────────────────────────────────────────────────────────────────
   7. parking_sessions — 17 real sessions from live DB
   ──────────────────────────────────────────────────────────────────────────── */
IF NOT EXISTS (SELECT 1 FROM dbo.parking_sessions WHERE plate_number = N'ZRS-6511' AND entry_time = '2026-04-13 08:44:32')
BEGIN
    INSERT INTO dbo.parking_sessions
        (plate_number, vehicle_type, is_employee, entry_time, exit_time, duration_seconds,
         entry_camera_id, exit_camera_id, entry_snapshot_path, exit_snapshot_path,
         floor, zone_id, zone_name, slot_id, slot_number, parked_at, slot_left_at,
         slot_camera_id, slot_snapshot_path, status, created_at, updated_at)
    VALUES
        (N'ZRS-6511', N'unknown', 0, '2026-04-13 08:44:32', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'AAD-2560', N'unknown', 0, '2026-04-13 08:47:05', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'HGD-2926', N'unknown', 0, '2026-04-13 08:50:09', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'UEU-777', N'unknown', 0, '2026-04-13 08:50:17', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'TTB-8627', N'unknown', 0, '2026-04-13 08:50:30', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'KKR-2994', N'unknown', 0, '2026-04-13 08:52:27.43', NULL, NULL, N'CAM-ENTRY', NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055235_397226.jpg', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'SHR-1198', N'unknown', 0, '2026-04-13 08:59:13.117', NULL, NULL, N'CAM-ENTRY', NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055923_066242.jpg', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'NDD-4141', N'unknown', 0, '2026-04-13 09:06:02', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'RTB-2016', N'unknown', 0, '2026-04-13 09:10:38', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'RGR-6466', N'unknown', 0, '2026-04-14 08:06:46', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'SDD-6707', N'unknown', 0, '2026-04-14 08:35:45', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'NXR-2727', N'unknown', 0, '2026-04-14 08:37:16', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'EEB-80', N'unknown', 0, '2026-04-14 08:51:30', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'RDJ-9640', N'unknown', 0, '2026-04-14 13:27:16', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE()),
        (N'TEST-001', N'sedan', 1, '2026-04-20 20:51:51.2', '2026-04-20 22:21:51.2', 5400, N'CAM-ENTRY', N'CAM-EXIT', NULL, NULL, N'B1', N'B1-S12', N'B1 East', NULL, N'S12', NULL, NULL, NULL, NULL, N'closed', GETUTCDATE(), GETUTCDATE()),
        (N'TEST-001', N'sedan', 1, '2026-04-21 20:51:51.203', '2026-04-21 21:36:51.203', 2700, N'CAM-ENTRY', N'CAM-EXIT', NULL, NULL, N'B2', N'B2-S07', N'B2 West', NULL, N'S07', NULL, NULL, NULL, NULL, N'closed', GETUTCDATE(), GETUTCDATE()),
        (N'TEST-001', N'sedan', 1, '2026-04-22 20:36:51.203', NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, N'B1', N'B1-S03', N'B1 North', NULL, N'S03', NULL, NULL, NULL, NULL, N'open', GETUTCDATE(), GETUTCDATE());
    PRINT '  Seeded 17 parking_sessions rows';
END;

/* Backfill floor_id / parking_slot_id integer FK partners. */
IF COL_LENGTH(N'dbo.parking_sessions', N'floor_id') IS NOT NULL
    UPDATE t SET floor_id = f.id
    FROM dbo.parking_sessions t INNER JOIN dbo.floors f ON f.name = t.floor
    WHERE t.floor_id IS NULL;

IF COL_LENGTH(N'dbo.parking_sessions', N'parking_slot_id') IS NOT NULL
    UPDATE t SET parking_slot_id = ps.id
    FROM dbo.parking_sessions t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
    WHERE t.parking_slot_id IS NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   8. alerts — 24 simulated alerts (4 types) spanning 14 days
   ────────────────────────────────────────────────────────────────────────────
   Types:
     vehicle_violation  — parking in a violation/no-park slot (V1, V2)
     vehicle_intrusion  — parking in a restricted/reserved slot (CEO, CTO, etc.)
     capacity_exceeded  — floor at or over max slot capacity
     unknown_vehicle    — unregistered plate detected at entry/exit gate
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @now DATETIME2 = SYSUTCDATETIME();

IF NOT EXISTS (SELECT 1 FROM dbo.alerts WHERE description = N'Simulated seed alert — do not delete')
BEGIN
    INSERT INTO dbo.alerts
        (alert_type, camera_id, zone_id, zone_name, slot_id, slot_number, event_type,
         description, snapshot_path, is_test, is_resolved, triggered_at, resolved_at,
         plate_number, severity, location_display)
    VALUES
        /* ── vehicle_violation — violation slot parking ────────────────────── */
        (N'vehicle_violation', N'Cam_01', N'GF-FRONT',   N'GF Front',            N'V1_Violation_1', N'Slot V1 Violation 1', N'vehicle_detected', N'Vehicle parked in violation slot V1',                    NULL, 0, 0, DATEADD(minute, -35, @now),  NULL,                                 N'SHR-1198', N'critical', N'Ground / V1 Violation 1'),
        (N'vehicle_violation', N'Cam_01', N'GF-FRONT',   N'GF Front',            N'V2_Violation_2', N'Slot V2 Violation 2', N'vehicle_detected', N'Vehicle parked in violation slot V2',                    NULL, 0, 0, DATEADD(minute, -20, @now),  NULL,                                 N'AAD-2560', N'critical', N'Ground / V2 Violation 2'),
        (N'vehicle_violation', N'Cam_01', N'GF-FRONT',   N'GF Front',            N'V1_Violation_1', N'Slot V1 Violation 1', N'vehicle_detected', N'Vehicle parked in violation slot V1',                    NULL, 0, 1, DATEADD(day,  -3, @now),     DATEADD(day,  -3, DATEADD(hour, 2, @now)), N'HGD-2926', N'critical', N'Ground / V1 Violation 1'),
        (N'vehicle_violation', N'Cam_01', N'GF-FRONT',   N'GF Front',            N'V2_Violation_2', N'Slot V2 Violation 2', N'vehicle_detected', N'Vehicle parked in violation slot V2',                    NULL, 0, 1, DATEADD(day,  -7, @now),     DATEADD(day,  -7, DATEADD(hour, 1, @now)), N'NXR-2727', N'critical', N'Ground / V2 Violation 2'),
        (N'vehicle_violation', N'Cam_01', N'GF-FRONT',   N'GF Front',            N'V1_Violation_1', N'Slot V1 Violation 1', N'vehicle_detected', N'Vehicle parked in violation slot V1',                    NULL, 0, 1, DATEADD(day, -12, @now),     DATEADD(day, -12, DATEADD(hour, 3, @now)), N'TTB-8627', N'warning',  N'Ground / V1 Violation 1'),

        /* ── vehicle_intrusion — restricted slot intrusion ────────────────── */
        (N'vehicle_intrusion', N'Cam_03', N'B1-PARKING', N'B1 Parking',           N'B3_CEO',         N'Slot B3 CEO',         N'vehicle_detected', N'Unauthorized vehicle in reserved CEO slot',              NULL, 0, 0, DATEADD(minute, -50, @now),  NULL,                                 N'KKR-2994', N'critical', N'B1 / Slot B3 CEO'),
        (N'vehicle_intrusion', N'Cam_03', N'B1-PARKING', N'B1 Parking',           N'B1_CRO',         N'Slot B1 CRO',         N'vehicle_detected', N'Unauthorized vehicle in reserved CRO slot',              NULL, 0, 0, DATEADD(hour,  -2, @now),    NULL,                                 N'RGR-6466', N'critical', N'B1 / Slot B1 CRO'),
        (N'vehicle_intrusion', N'Cam_04', N'B1-PARKING', N'B1 Parking',           N'B10_CTO',        N'Slot B10 CTO',        N'vehicle_detected', N'Unauthorized vehicle in reserved CTO slot',              NULL, 0, 1, DATEADD(day,  -1, @now),     DATEADD(day,  -1, DATEADD(hour, 1, @now)), N'RTB-2016', N'critical', N'B1 / Slot B10 CTO'),
        (N'vehicle_intrusion', N'Cam_05', N'B1-PARKING', N'B1 Parking',           N'B6_Reserved',    N'Slot B6 Reserved',    N'vehicle_detected', N'Unauthorized vehicle in reserved slot B6',               NULL, 0, 1, DATEADD(day,  -4, @now),     DATEADD(day,  -4, DATEADD(hour, 2, @now)), N'SDD-6707', N'warning',  N'B1 / Slot B6 Reserved'),
        (N'vehicle_intrusion', N'Cam_06', N'B1-PARKING', N'B1 Parking',           N'GMIA',           N'GMIA',                N'vehicle_detected', N'Unauthorized vehicle in restricted GMIA slot',           NULL, 0, 1, DATEADD(day,  -6, @now),     DATEADD(day,  -6, DATEADD(hour, 1, @now)), N'EEB-80',   N'warning',  N'B1 / GMIA'),
        (N'vehicle_intrusion', N'Cam_03', N'B1-PARKING', N'B1 Parking',           N'B13_COO',        N'Slot B13 COO',        N'vehicle_detected', N'Unauthorized vehicle in reserved COO slot',              NULL, 0, 1, DATEADD(day, -10, @now),     DATEADD(day, -10, DATEADD(hour, 4, @now)), N'NDD-4141', N'critical', N'B1 / Slot B13 COO'),

        /* ── capacity_exceeded — floor at/over max slot capacity ─────────── */
        (N'capacity_exceeded', N'Cam_09', N'B2-PARKING', N'B2 Parking',           NULL,              NULL,                   N'occupancy_update', N'Floor B2 is full: 100% (13/13 slots occupied)',                   NULL, 0, 0, DATEADD(hour,  -1, @now),    NULL,                                 NULL,        N'warning',  N'B2 Parking'),
        (N'capacity_exceeded', N'Cam_09', N'B2-PARKING', N'B2 Parking',           NULL,              NULL,                   N'occupancy_update', N'Floor B2 exceeded capacity: 108% (14/13 slots occupied)',        NULL, 0, 0, DATEADD(minute, -45, @now),  NULL,                                 NULL,        N'critical', N'B2 Parking'),
        (N'capacity_exceeded', N'Cam_03', N'B1-PARKING', N'B1 Parking',           NULL,              NULL,                   N'occupancy_update', N'Floor B1 nearly full: 91% (10/11 slots occupied)',            NULL, 0, 1, DATEADD(day,  -2, @now),     DATEADD(day,  -2, DATEADD(hour, 3, @now)), NULL,        N'warning',  N'B1 Parking'),
        (N'capacity_exceeded', N'Cam_09', N'B2-PARKING', N'B2 Parking',           NULL,              NULL,                   N'occupancy_update', N'Floor B2 exceeded capacity: 115% (15/13 slots occupied)',        NULL, 0, 1, DATEADD(day,  -5, @now),     DATEADD(day,  -5, DATEADD(hour, 2, @now)), NULL,        N'critical', N'B2 Parking'),
        (N'capacity_exceeded', N'Cam_03', N'B1-PARKING', N'B1 Parking',           NULL,              NULL,                   N'occupancy_update', N'Floor B1 is full: 100% (11/11 slots occupied)',                   NULL, 0, 1, DATEADD(day,  -8, @now),     DATEADD(day,  -8, DATEADD(hour, 1, @now)), NULL,        N'warning',  N'B1 Parking'),
        (N'capacity_exceeded', N'Cam_09', N'B2-PARKING', N'B2 Parking',           NULL,              NULL,                   N'occupancy_update', N'Floor B2 nearly full: 92% (12/13 slots occupied)',            NULL, 0, 1, DATEADD(day, -11, @now),     DATEADD(day, -11, DATEADD(hour, 2, @now)), NULL,        N'warning',  N'B2 Parking'),

        /* ── unknown_vehicle — unregistered plate at gate ─────────────────── */
        (N'unknown_vehicle',   N'ANPR-Entry', N'entry', N'Entry Gate',            NULL,              NULL,                   N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate SHR-1198',  NULL, 0, 0, DATEADD(minute, -15, @now),  NULL,                                 N'SHR-1198', N'critical', N'Entry Gate'),
        (N'unknown_vehicle',   N'ANPR-Entry', N'entry', N'Entry Gate',            NULL,              NULL,                   N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate AAD-2560',  NULL, 0, 0, DATEADD(hour,  -3, @now),    NULL,                                 N'AAD-2560', N'critical', N'Entry Gate'),
        (N'unknown_vehicle',   N'ANPR-Exit',  N'exit',  N'Exit Gate',             NULL,              NULL,                   N'AccessControllerEvent', N'Unregistered vehicle at exit gate: plate HBR-4920',   NULL, 0, 0, DATEADD(hour,  -5, @now),    NULL,                                 N'HBR-4920', N'critical', N'Exit Gate'),
        (N'unknown_vehicle',   N'ANPR-Entry', N'entry', N'Entry Gate',            NULL,              NULL,                   N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate BGD-7593',  NULL, 0, 1, DATEADD(day,  -1, @now),     DATEADD(day,  -1, DATEADD(hour, 2, @now)), N'BGD-7593', N'critical', N'Entry Gate'),
        (N'unknown_vehicle',   N'ANPR-Entry', N'entry', N'Entry Gate',            NULL,              NULL,                   N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate NJS-7894',  NULL, 0, 1, DATEADD(day,  -3, @now),     DATEADD(day,  -3, DATEADD(hour, 1, @now)), N'NJS-7894', N'warning',  N'Entry Gate'),
        (N'unknown_vehicle',   N'ANPR-Entry', N'entry', N'Entry Gate',            NULL,              NULL,                   N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate HVA-77',    NULL, 0, 1, DATEADD(day,  -6, @now),     DATEADD(day,  -6, DATEADD(hour, 3, @now)), N'HVA-77',   N'warning',  N'Entry Gate'),
        (N'unknown_vehicle',   N'ANPR-Entry', N'entry', N'Entry Gate',            NULL,              NULL,                   N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate RDJ-9640',  NULL, 0, 1, DATEADD(day,  -9, @now),     DATEADD(day,  -9, DATEADD(hour, 1, @now)), N'RDJ-9640', N'warning',  N'Entry Gate');

    /* Sentinel row so the IF NOT EXISTS guard works on re-run */
    INSERT INTO dbo.alerts
        (alert_type, camera_id, zone_id, zone_name, event_type,
         description, is_test, is_resolved, triggered_at, severity)
    VALUES
        (N'unknown_vehicle', N'ANPR-Entry', N'entry', N'Entry Gate', N'seed_marker',
         N'Simulated seed alert — do not delete', 0, 1, '2000-01-01', N'info');

    PRINT '  Seeded 24 simulated alerts (4 types)';
END;

/* Backfill parking_slot_id integer FK partner for the new alerts. */
IF COL_LENGTH(N'dbo.alerts', N'parking_slot_id') IS NOT NULL
    UPDATE t SET parking_slot_id = ps.id
    FROM dbo.alerts t INNER JOIN dbo.parking_slots ps ON ps.slot_id = t.slot_id
    WHERE t.parking_slot_id IS NULL;
GO

/* ────────────────────────────────────────────────────────────────────────────
   9. camera_feeds — empty in live DB, nothing to seed
   ──────────────────────────────────────────────────────────────────────────── */
/* No rows to seed — camera_feeds table is empty in the live database. */
GO

/* ────────────────────────────────────────────────────────────────────────────
   10. Floor-name alias normalization (idempotent; safe to re-run)
   ────────────────────────────────────────────────────────────────────────────
   Cameras seed introduces floor='Ground'; PMS-AI may at some point write
   floor='Ground Floor' for the same physical floor. Without normalization
   the dashboard splits them into separate buckets. This block:
     1. re-points integer FK columns from "Ground Floor" → "Ground";
     2. rewrites legacy `floor` string columns on every source table;
     3. deletes the now-empty "Ground Floor" row from `floors`.
   Append rows to @aliases to add more name → canonical mappings.
   ──────────────────────────────────────────────────────────────────────────── */
DECLARE @aliases TABLE (alias NVARCHAR(50), canonical NVARCHAR(50));
INSERT INTO @aliases (alias, canonical) VALUES
    ('Ground Floor', 'Ground');
    -- additional aliases here, e.g. ('GF', 'Ground'), ('Basement 1', 'B1')

DECLARE @alias NVARCHAR(50), @canonical NVARCHAR(50), @from_id INT, @to_id INT;
DECLARE alias_cur CURSOR LOCAL FAST_FORWARD FOR SELECT alias, canonical FROM @aliases;
OPEN alias_cur;
FETCH NEXT FROM alias_cur INTO @alias, @canonical;
WHILE @@FETCH_STATUS = 0
BEGIN
    SELECT @from_id = id FROM dbo.floors WHERE name = @alias;
    SELECT @to_id   = id FROM dbo.floors WHERE name = @canonical;

    IF @from_id IS NOT NULL AND @to_id IS NOT NULL AND @from_id <> @to_id
    BEGIN
        IF COL_LENGTH(N'dbo.parking_slots', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.parking_slots   SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF COL_LENGTH(N'dbo.parking_sessions', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.parking_sessions SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF COL_LENGTH(N'dbo.cameras', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.cameras SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF COL_LENGTH(N'dbo.cameras', N'watches_floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.cameras SET watches_floor_id = @t WHERE watches_floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF COL_LENGTH(N'dbo.alerts', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.alerts SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;
        IF OBJECT_ID(N'dbo.floor_occupancy', N'U') IS NOT NULL
           AND COL_LENGTH(N'dbo.floor_occupancy', N'floor_id') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.floor_occupancy SET floor_id = @t WHERE floor_id = @f',
                               N'@f INT, @t INT', @f = @from_id, @t = @to_id;

        IF COL_LENGTH(N'dbo.parking_slots', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.parking_slots   SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF COL_LENGTH(N'dbo.parking_sessions', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.parking_sessions SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF COL_LENGTH(N'dbo.cameras', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.cameras SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF COL_LENGTH(N'dbo.cameras', N'watches_floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.cameras SET watches_floor = @t WHERE watches_floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF COL_LENGTH(N'dbo.alerts', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.alerts SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;
        IF OBJECT_ID(N'dbo.floor_occupancy', N'U') IS NOT NULL
           AND COL_LENGTH(N'dbo.floor_occupancy', N'floor') IS NOT NULL
            EXEC sp_executesql N'UPDATE dbo.floor_occupancy SET floor = @t WHERE floor = @f',
                               N'@f NVARCHAR(50), @t NVARCHAR(50)', @f = @alias, @t = @canonical;

        DELETE FROM dbo.floors WHERE id = @from_id;
        PRINT '  Normalized floor alias: ' + @alias + ' -> ' + @canonical;
    END

    FETCH NEXT FROM alias_cur INTO @alias, @canonical;
END
CLOSE alias_cur;
DEALLOCATE alias_cur;
GO

/* Pin the canonical operator-facing floor order: Ground first, basements
   descending. (Was DENSE_RANK over name which sorted alphabetically and put
   Ground last; see migrate_floors_sort_order.sql for the historical fix.) */
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

PRINT '──────────────────────────────────────────────';
PRINT '  seed.sql finished';
PRINT '──────────────────────────────────────────────';
GO

