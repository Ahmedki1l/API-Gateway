-- =============================================================================
-- migrate_entry_camera_username.sql
--
-- Fix: the ENTRY ANPR camera's `cameras.username` value was seeded as
-- `kloudspot` (single t). The actual camera ISAPI rejects that with 401 —
-- the correct username is `kloudspott` (DOUBLE T). Verified live on
-- 2026-05-04 by hitting the camera's /ISAPI/Security/userCheck endpoint.
--
-- The EXIT camera keeps username `kloudspot1` (with digit one). The 14
-- floor cameras (CAM-01..CAM-14) keep `kloudspot` (single t) — only the
-- entry gate has the double-t outlier.
--
-- The match key is `ip_address = '10.1.13.100'` rather than `camera_id`
-- because the row may be `ANPR-Entry` (pre-T17 legacy) or `CAM-ENTRY`
-- (post-T17 dash form) depending on whether the camera-id migration
-- has run yet. The IP never moves.
--
-- Idempotent: re-running on a DB that already has `kloudspott` is a no-op.
-- Does NOT touch the password_encrypted column — your existing Fernet
-- ciphertext stays intact, so decrypt/build_rtsp_url still works.
-- =============================================================================

UPDATE dbo.cameras
   SET username = N'kloudspott'
 WHERE ip_address = '10.1.13.100'
   AND username = N'kloudspot';
GO

-- ── Verify ──────────────────────────────────────────────────────────────────
-- Run after applying:
--   SELECT camera_id, ip_address, username FROM dbo.cameras WHERE ip_address = '10.1.13.100';
-- Expected: username = 'kloudspott'.
