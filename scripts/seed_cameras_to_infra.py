"""
One-shot seed of the 16 cameras and 3 floors into whatever DB the
gateway's `SessionLocal` currently points at — i.e. the DB configured
in the same `.env` the gateway reads at startup.

Designed for the case where the data lives on a developer's laptop
and we need to ship it into a sealed prod pod that has no network
path back to the laptop. The data is baked in below; no DB-to-DB
copy, no JSON file transfer.

Usage (inside the pod, repo already cloned):
    python scripts/seed_cameras_to_infra.py             # dry-run
    python scripts/seed_cameras_to_infra.py --commit    # actually write

Idempotent:
  - floors: matched by `name`. Existing rows kept; missing ones inserted.
  - cameras: matched by `camera_id`. Existing rows skipped by default;
    pass --update-existing to overwrite metadata.

Password handling:
  - 14 of the 16 cameras have ciphertexts encrypted with the current
    `CAMERAS_ENCRYPTION_KEY`; those decrypt cleanly on any gateway
    sharing that key (i.e. the prod pod).
  - `ANPR-Entry` and `ANPR-Exit` were encrypted with an older key
    that nobody has anymore, so their `password_encrypted` is set to
    NULL in this seed. After running this script, set their real
    passwords with:

        PATCH /cameras/{id}/credentials   {"password": "..."}

  - --reset-passwords inserts NULL into ALL password_encrypted columns
    (use this if the target's key has been rotated to something else).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Allow `from app...` when invoked from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Baked-in source data (exported from the laptop dev DB).
# ─────────────────────────────────────────────────────────────────────

FLOORS: list[dict[str, Any]] = [
    {'name': 'B1', 'sort_order': 0, 'is_active': True},
    {'name': 'B2', 'sort_order': 1, 'is_active': True},
    {'name': 'Ground', 'sort_order': 2, 'is_active': True},
]

CAMERAS: list[dict[str, Any]] = [
    {
        'camera_id': 'ANPR-Entry',
        'name': 'ENTRY-GATE',
        '_floor_name': 'Ground',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.100',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        # Encrypted with an older key. Set the real password after seeding via
        # PATCH /cameras/{id}/credentials (id = the new row's int PK).
        'password_encrypted': None,
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'ANPR-Exit',
        'name': 'EXIT-GATE',
        '_floor_name': 'Ground',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.101',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot1',
        # Encrypted with an older key. Set the real password after seeding via
        # PATCH /cameras/{id}/credentials (id = the new row's int PK).
        'password_encrypted': None,
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_01',
        'name': 'GF-FRONT',
        '_floor_name': 'Ground',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.60',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-72BC8a7Ccl62zB9sIIbUFWF1jtvQY2qYheGnm1aflrMCB90-jy7or_s8f5puv3Jy0WKq7DXZVZMStrEuBrUjf6w==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_02',
        'name': 'GF-FRONT',
        '_floor_name': 'Ground',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.61',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-8spo9JrjLYozJZYRUjXaXpOMebAEC6aWsNzdW0KKoUu4PjeHche4lQ5yE-uuA5mwhOUW0WLD3J7uMSv-MoPusYQ==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_03',
        'name': 'B1-PARKING',
        '_floor_name': 'B1',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.62',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-sWV-wudjIHxDGk52NYKTMbZTzK-WptpTYgrOQWFXASVbSPWkf4LBor0gl3fdYCpB6r-PcFH_pZ78ZMGYHhWrIIA==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_04',
        'name': 'B1-PARKING',
        '_floor_name': 'B1',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.63',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-8haEwE_CLzZAnPg8kAQ20AsWpeWdRcEXQgWIbXB3UAks1gM1BrhlsZy7sZOihqeCXssOJ4k2mdmaeOGym4RPuvw==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_05',
        'name': 'B1-PARKING',
        '_floor_name': 'B1',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.64',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-8EZKTh4UIbaQuYIbQUrGR4JAlGvBnWGnGtZYm8gnod9SBtpV6YATduqeB3XGoe3v2osVStk0Th9ag7vmnmP_m8A==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_06',
        'name': 'B1-PARKING',
        '_floor_name': 'B1',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.65',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-8uh5rGwRb2MHOOR7lwMBaJhpB0RNXtxVxx13J4l3QJqy-LtiZPsXPQQ4du8Lof-F1auPd0ZML1G0rWRCfGCNNAQ==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_07',
        'name': 'B1-PARKING',
        '_floor_name': 'B1',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.66',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-9j6KTrQqiZvhb8xH_46H7mzyIfb0KsRsip7LfLHrmiOxXXStphYug3_ln1DhrvNTtxvbg889GCmU69RMv5QSMDQ==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_08',
        'name': 'B1-PARKING',
        '_floor_name': 'B1',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.67',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N--ugsfgRl_7vHxbKY_apsQjRJifjqgS6AtwXKcHPzNmwM4Scb4gyVTWObGy1r3p_KnaymGRbfSVGNVHwLg-M8YMg==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_09',
        'name': 'B2-PARKING',
        '_floor_name': 'B2',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.68',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-93m_hz8mLAYbdmlWsu1lI1e1D10jNjwtNuXLrxdqysFJf0L4u3llmb3B_D-jUiRDA8Pczesy2G5uf86BGeeRYjw==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_10',
        'name': 'B2-PARKING',
        '_floor_name': 'B2',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.69',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-9sDjz_2nRoX82KghGDdgRCJYUPk-nOwDj4NgZm82Bu-PSnc6K1bIX7sLhtjifEBavr6IHV0RcX99R-q-0ymFcOw==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_11',
        'name': 'B2-PARKING',
        '_floor_name': 'B2',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.70',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N-9C9iKq5vHetIv3cwvH9RWJDoR0DM_J5-qPC105KMnlAIHNrOs_8JqAzYSrhXR1YVM-C_tl3ZnwtEdWrrqFt-tUg==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_12',
        'name': 'B2-PARKING',
        '_floor_name': 'B2',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.71',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N--lAt8ibg4VuRfR7E-_HMbj0gYAOtXEexz9PmFmnmxqVBrUjLoTw888aiystdFf765qb_mS8PHkmfWwqN8jNQ4Cw==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_13',
        'name': 'B2-PARKING',
        '_floor_name': 'B2',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.72',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N---Xc999iqCfyBD75jA4Nt7-xraQQM-PTgPRqgmlWPUW9AEOKrCsUl9tbUnadatl-wK5hfgLJS0_GmMrKdwGbGiQ==',
        'enabled': True,
        'notes': 'string',
    },
    {
        'camera_id': 'Cam_14',
        'name': 'B2-PARKING',
        '_floor_name': 'B2',
        '_watches_floor_name': None,
        'role': 'other',
        'watches_floor': None,
        'watches_slots_json': None,
        'ip_address': '10.1.13.73',
        'rtsp_port': 554,
        'rtsp_path': '/Streaming/Channels/101',
        'username': 'kloudspot',
        'password_encrypted': 'gAAAAABp8N--zM-fzmggW2GrYv9Yodo7DrZbLmfxpxrIOvr9RfaKf-6qEFQj99e-cuVmS53g4q43dewGdPz3TkWy098onDcOEA==',
        'enabled': True,
        'notes': 'string',
    },
]


# ─────────────────────────────────────────────────────────────────────
# Seeding logic
# ─────────────────────────────────────────────────────────────────────


def _floor_id_by_name(db, name: str) -> Optional[int]:
    row = db.execute(
        text("SELECT id FROM floors WHERE name = :name"), {"name": name}
    ).first()
    return int(row[0]) if row else None


def _camera_exists(db, camera_id: str) -> bool:
    return db.execute(
        text("SELECT 1 FROM cameras WHERE camera_id = :cid"), {"cid": camera_id}
    ).first() is not None


def _ensure_tables(db) -> None:
    for tname in ("floors", "cameras"):
        present = db.execute(
            text(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_NAME = :t"
            ),
            {"t": tname},
        ).scalar()
        if not present:
            sys.exit(
                f"error: target DB has no `{tname}` table — "
                "run sql/bootstrap.sql there first"
            )


def main() -> int:
    p = argparse.ArgumentParser(
        description="Seed cameras + floors into the gateway's configured DB.",
    )
    p.add_argument(
        "--commit", action="store_true",
        help="Actually write to the DB. Without this flag, prints what it would do.",
    )
    p.add_argument(
        "--update-existing", action="store_true",
        help="Overwrite metadata of cameras that already exist (matched by camera_id). "
             "Default is to skip them.",
    )
    p.add_argument(
        "--reset-passwords", action="store_true",
        help="Insert NULL for password_encrypted instead of the baked-in ciphertext. "
             "Use this if the target DB uses a different CAMERAS_ENCRYPTION_KEY.",
    )
    args = p.parse_args()

    print(f"[seed] {len(FLOORS)} floor(s), {len(CAMERAS)} camera(s) baked into this script")

    db = SessionLocal()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        _ensure_tables(db)

        # ── floors ────────────────────────────────────────────────
        floor_summary = {"existing": 0, "inserted": 0, "would-insert": 0}
        floor_id_by_name: dict[str, int] = {}

        print()
        print(f"{'floor':<14} {'action':<14} {'target_id'}")
        print("-" * 38)
        for fl in FLOORS:
            existing_id = _floor_id_by_name(db, fl["name"])
            if existing_id is not None:
                floor_id_by_name[fl["name"]] = existing_id
                action = "existing"
            elif args.commit:
                row = db.execute(
                    text(
                        "INSERT INTO floors (name, sort_order, is_active, created_at, updated_at) "
                        "OUTPUT inserted.id "
                        "VALUES (:name, :so, :ia, :now, :now)"
                    ),
                    {"name": fl["name"], "so": fl["sort_order"],
                     "ia": 1 if fl["is_active"] else 0, "now": now},
                ).first()
                new_id = int(row[0])
                floor_id_by_name[fl["name"]] = new_id
                existing_id = new_id
                action = "inserted"
            else:
                action = "would-insert"
            floor_summary[action] = floor_summary.get(action, 0) + 1
            print(f"{fl['name']:<14} {action:<14} {existing_id if existing_id is not None else '-'}")

        # ── cameras ──────────────────────────────────────────────
        cam_summary = {"inserted": 0, "updated": 0, "skipped": 0,
                       "would-insert": 0, "would-update": 0, "would-skip": 0}

        print()
        print(f"{'camera_id':<14} {'action':<14} {'floor':<8} {'ip':<16} {'role':<14} pwd")
        print("-" * 78)
        for cam in CAMERAS:
            existed = _camera_exists(db, cam["camera_id"])
            floor_name = cam.get("_floor_name") or cam.get("floor")
            watches_name = cam.get("_watches_floor_name") or cam.get("watches_floor")
            target_floor_id = floor_id_by_name.get(floor_name) if floor_name else None
            target_watches_id = floor_id_by_name.get(watches_name) if watches_name else None

            if existed and not args.update_existing:
                action = "skipped" if args.commit else "would-skip"
            elif existed and args.update_existing:
                if args.commit:
                    sets = [
                        "name = :name", "floor = :floor", "role = :role",
                        "watches_floor = :wf", "watches_slots_json = :wsj",
                        "ip_address = :ip", "rtsp_port = :port", "rtsp_path = :path",
                        "username = :user",
                        "enabled = :en", "notes = :notes",
                        "floor_id = :fid", "watches_floor_id = :wfid",
                        "updated_at = :now",
                    ]
                    params: dict[str, Any] = {
                        "cid": cam["camera_id"], "name": cam.get("name"),
                        "floor": cam.get("_floor_name") or cam.get("floor"),
                        "role": cam["role"],
                        "wf": cam.get("watches_floor"),
                        "wsj": cam.get("watches_slots_json"),
                        "ip": cam["ip_address"], "port": cam["rtsp_port"],
                        "path": cam["rtsp_path"], "user": cam.get("username"),
                        "en": 1 if cam.get("enabled") else 0,
                        "notes": cam.get("notes"),
                        "fid": target_floor_id, "wfid": target_watches_id,
                        "now": now,
                    }
                    if args.reset_passwords:
                        sets.append("password_encrypted = NULL")
                    db.execute(
                        text(f"UPDATE cameras SET {', '.join(sets)} WHERE camera_id = :cid"),
                        params,
                    )
                    action = "updated"
                else:
                    action = "would-update"
            else:
                if args.commit:
                    pwd = None if args.reset_passwords else cam.get("password_encrypted")
                    db.execute(
                        text(
                            "INSERT INTO cameras "
                            "(camera_id, name, floor, role, watches_floor, watches_slots_json, "
                            " ip_address, rtsp_port, rtsp_path, username, password_encrypted, "
                            " enabled, notes, floor_id, watches_floor_id, "
                            " created_at, updated_at) "
                            "VALUES (:cid, :name, :floor, :role, :wf, :wsj, "
                            " :ip, :port, :path, :user, :pwd, "
                            " :en, :notes, :fid, :wfid, "
                            " :now, :now)"
                        ),
                        {
                            "cid": cam["camera_id"], "name": cam.get("name"),
                            "floor": cam.get("_floor_name") or cam.get("floor"),
                            "role": cam["role"],
                            "wf": cam.get("watches_floor"),
                            "wsj": cam.get("watches_slots_json"),
                            "ip": cam["ip_address"], "port": cam["rtsp_port"],
                            "path": cam["rtsp_path"], "user": cam.get("username"),
                            "pwd": pwd,
                            "en": 1 if cam.get("enabled") else 0,
                            "notes": cam.get("notes"),
                            "fid": target_floor_id, "wfid": target_watches_id,
                            "now": now,
                        },
                    )
                    action = "inserted"
                else:
                    action = "would-insert"

            cam_summary[action] = cam_summary.get(action, 0) + 1
            if args.reset_passwords:
                pwd_marker = "RESET"
            elif cam.get("password_encrypted"):
                pwd_marker = "(same)"
            else:
                pwd_marker = "NULL (set via API)"
            print(
                f"{cam['camera_id']:<14} {action:<14} {(floor_name or '-'):<8} "
                f"{(cam.get('ip_address') or ''):<16} {cam['role']:<14} {pwd_marker}"
            )

        if args.commit:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()

    print()
    print(f"[seed] floors:  {floor_summary}")
    print(f"[seed] cameras: {cam_summary}")
    if not args.commit:
        print("[seed] dry-run only — pass --commit to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
