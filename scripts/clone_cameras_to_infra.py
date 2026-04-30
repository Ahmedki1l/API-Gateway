"""
Clone cameras + floors from this gateway's DB into another gateway's DB.

Reads source data from the local gateway's existing connection (DB_* vars
already in .env) and writes to a target DB whose connection details are
supplied via CLI args or a --target-env file.

Idempotent:
  - floors: matched by `name`. Existing rows are kept; missing ones inserted.
  - cameras: matched by `camera_id`. Existing rows are skipped (use
    --update-existing to overwrite metadata).

Password handling:
  - Default: `password_encrypted` is copied as an opaque blob. The target
    gateway must hold the same `CAMERAS_ENCRYPTION_KEY` to decrypt it.
    If the keys differ, the password ciphertexts will be valid Fernet
    tokens that simply fail to decrypt at runtime — the operator can
    reset them via PATCH /cameras/{id}/credentials or by re-running
    this script with --reset-passwords.
  - --reset-passwords inserts NULL into password_encrypted, which the
    operator must fill in afterwards (the gateway will refuse to build
    RTSP URLs for unset passwords).

Usage:
    # dry-run with target credentials on the CLI
    python scripts/clone_cameras_to_infra.py \\
        --target-host infra.example.com --target-db damanat_pms \\
        --target-user sa --target-password '...'

    # actually write
    python scripts/clone_cameras_to_infra.py --target-env infra.env --commit

    # blow away encrypted passwords and let the operator set them later
    python scripts/clone_cameras_to_infra.py --target-env infra.env \\
        --commit --reset-passwords

The --target-env file uses standard .env shape and is read for these
keys (any subset):
    DB_DRIVER, DB_SERVER, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
CLI args win over .env values.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Allow `from app...` when invoked from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyodbc  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402


# Columns we copy from source rows. `id`, `created_at`, `updated_at`,
# `last_*` and runtime liveness fields are deliberately excluded — the
# target picks fresh values.
CAMERA_COLUMNS = [
    "camera_id", "name", "floor", "role", "watches_floor", "watches_slots_json",
    "ip_address", "rtsp_port", "rtsp_path", "username", "password_encrypted",
    "enabled", "notes",
]


@dataclass
class TargetConfig:
    driver: str
    server: str
    port: int
    db_name: str
    user: str
    password: str

    def connection_string(self) -> str:
        return (
            f"DRIVER={{{self.driver}}};SERVER={self.server},{self.port};"
            f"DATABASE={self.db_name};UID={self.user};PWD={self.password};"
            "TrustServerCertificate=Yes"
        )


def parse_env_file(path: Path) -> dict[str, str]:
    """Tiny .env reader — KEY=value, # comments. No quoting tricks."""
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (
            v.startswith("'") and v.endswith("'")
        ):
            v = v[1:-1]
        out[k.strip()] = v
    return out


def build_target(args: argparse.Namespace) -> TargetConfig:
    env: dict[str, str] = {}
    if args.target_env:
        if not args.target_env.exists():
            sys.exit(f"error: --target-env file not found: {args.target_env}")
        env = parse_env_file(args.target_env)

    def pick(cli_val: Optional[str], env_key: str, default: Optional[str] = None) -> Optional[str]:
        if cli_val is not None:
            return cli_val
        if env_key in env:
            return env[env_key]
        return default

    driver = pick(args.target_driver, "DB_DRIVER", "ODBC Driver 17 for SQL Server")
    server = pick(args.target_host, "DB_SERVER")
    port_str = pick(args.target_port, "DB_PORT", "1433")
    db_name = pick(args.target_db, "DB_NAME")
    user = pick(args.target_user, "DB_USER")
    password = pick(args.target_password, "DB_PASSWORD")

    missing = [
        n for n, v in [
            ("server", server), ("db", db_name), ("user", user), ("password", password),
        ] if not v
    ]
    if missing:
        sys.exit(f"error: target DB connection missing: {', '.join(missing)}")

    return TargetConfig(
        driver=driver,
        server=server,
        port=int(port_str),
        db_name=db_name,
        user=user,
        password=password,
    )


def fetch_source_floors() -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.execute(text(
            "SELECT name, sort_order, is_active FROM floors ORDER BY sort_order, id"
        )).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


def fetch_source_cameras() -> list[dict[str, Any]]:
    """Source cameras + the floor name they reference (so we can resolve
    floor_id on the target without depending on numeric IDs lining up)."""
    db = SessionLocal()
    try:
        # LEFT JOIN floors so we can carry the resolved floor name even when
        # cameras.floor_id was set but cameras.floor was stale.
        sql = (
            "SELECT c.{cols},"
            " fl_main.name AS _floor_name,"
            " fl_watch.name AS _watches_floor_name"
            " FROM cameras c"
            " LEFT JOIN floors fl_main ON fl_main.id = c.floor_id"
            " LEFT JOIN floors fl_watch ON fl_watch.id = c.watches_floor_id"
            " ORDER BY c.id"
        ).format(cols=", c.".join(CAMERA_COLUMNS))
        rows = db.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


def cameras_table_exists(cur: pyodbc.Cursor) -> bool:
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'cameras'"
    )
    return cur.fetchone()[0] > 0


def floors_table_exists(cur: pyodbc.Cursor) -> bool:
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'floors'"
    )
    return cur.fetchone()[0] > 0


def get_or_insert_floor(
    cur: pyodbc.Cursor, *, name: str, sort_order: int, is_active: bool, commit: bool, now: datetime
) -> tuple[Optional[int], str]:
    """Returns (floor_id, action). action ∈ {'existing', 'inserted', 'would-insert'}."""
    cur.execute("SELECT id FROM floors WHERE name = ?", name)
    row = cur.fetchone()
    if row:
        return int(row[0]), "existing"

    if not commit:
        return None, "would-insert"

    cur.execute(
        "INSERT INTO floors (name, sort_order, is_active, created_at, updated_at) "
        "OUTPUT inserted.id "
        "VALUES (?, ?, ?, ?, ?)",
        name, sort_order, 1 if is_active else 0, now, now,
    )
    new_id = int(cur.fetchone()[0])
    return new_id, "inserted"


def get_camera_existing(cur: pyodbc.Cursor, camera_id: str) -> bool:
    cur.execute("SELECT 1 FROM cameras WHERE camera_id = ?", camera_id)
    return cur.fetchone() is not None


def insert_camera(
    cur: pyodbc.Cursor,
    *,
    spec: dict[str, Any],
    floor_id: Optional[int],
    watches_floor_id: Optional[int],
    reset_passwords: bool,
    now: datetime,
) -> None:
    pwd = None if reset_passwords else spec.get("password_encrypted")
    cur.execute(
        "INSERT INTO cameras "
        "(camera_id, name, floor, role, watches_floor, watches_slots_json, "
        " ip_address, rtsp_port, rtsp_path, username, password_encrypted, "
        " enabled, notes, floor_id, watches_floor_id, "
        " created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        spec["camera_id"], spec.get("name"), spec.get("floor"), spec["role"],
        spec.get("watches_floor"), spec.get("watches_slots_json"),
        spec["ip_address"], spec["rtsp_port"], spec["rtsp_path"],
        spec.get("username"), pwd,
        1 if spec.get("enabled") else 0, spec.get("notes"),
        floor_id, watches_floor_id,
        now, now,
    )


def update_camera_metadata(
    cur: pyodbc.Cursor,
    *,
    spec: dict[str, Any],
    floor_id: Optional[int],
    watches_floor_id: Optional[int],
    reset_passwords: bool,
    now: datetime,
) -> None:
    """Overwrite metadata; only touches password_encrypted if reset_passwords."""
    sets = [
        "name = ?", "floor = ?", "role = ?",
        "watches_floor = ?", "watches_slots_json = ?",
        "ip_address = ?", "rtsp_port = ?", "rtsp_path = ?",
        "username = ?",
        "enabled = ?", "notes = ?",
        "floor_id = ?", "watches_floor_id = ?",
        "updated_at = ?",
    ]
    params: list[Any] = [
        spec.get("name"), spec.get("floor"), spec["role"],
        spec.get("watches_floor"), spec.get("watches_slots_json"),
        spec["ip_address"], spec["rtsp_port"], spec["rtsp_path"],
        spec.get("username"),
        1 if spec.get("enabled") else 0, spec.get("notes"),
        floor_id, watches_floor_id,
        now,
    ]
    if reset_passwords:
        sets.append("password_encrypted = NULL")

    params.append(spec["camera_id"])
    cur.execute(
        f"UPDATE cameras SET {', '.join(sets)} WHERE camera_id = ?",
        *params,
    )


def main() -> int:
    p = argparse.ArgumentParser(
        description="Clone cameras + floors from this gateway's DB to another's.",
    )
    p.add_argument("--target-env", type=Path, help="Path to a target .env file")
    p.add_argument("--target-driver", help="ODBC driver name (default ODBC Driver 17 for SQL Server)")
    p.add_argument("--target-host", help="Target DB_SERVER")
    p.add_argument("--target-port", help="Target DB_PORT (default 1433)")
    p.add_argument("--target-db", help="Target DB_NAME")
    p.add_argument("--target-user", help="Target DB_USER")
    p.add_argument("--target-password", help="Target DB_PASSWORD")

    p.add_argument(
        "--commit", action="store_true",
        help="Actually write to the target. Without this flag, the script reports what it would do.",
    )
    p.add_argument(
        "--update-existing", action="store_true",
        help="If a camera_id already exists on the target, overwrite its metadata. "
             "By default existing rows are skipped.",
    )
    p.add_argument(
        "--reset-passwords", action="store_true",
        help="Insert NULL for password_encrypted instead of copying the source ciphertext. "
             "Use this when the target uses a different CAMERAS_ENCRYPTION_KEY than the source.",
    )
    args = p.parse_args()

    target = build_target(args)

    src_floors = fetch_source_floors()
    src_cameras = fetch_source_cameras()
    print(f"[clone] source: {len(src_floors)} floor(s), {len(src_cameras)} camera(s)")

    conn = pyodbc.connect(target.connection_string(), autocommit=False)
    cur = conn.cursor()

    if not floors_table_exists(cur):
        print("error: target DB has no `floors` table — run sql/bootstrap.sql there first", file=sys.stderr)
        return 2
    if not cameras_table_exists(cur):
        print("error: target DB has no `cameras` table — run sql/bootstrap.sql there first", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # ── floors ────────────────────────────────────────────────────────
    floor_name_to_id: dict[str, int] = {}
    floor_summary = {"existing": 0, "inserted": 0, "would-insert": 0}
    print()
    print(f"{'floor':<14} {'action':<14} {'target_id'}")
    print("-" * 38)
    for fl in src_floors:
        new_id, action = get_or_insert_floor(
            cur, name=fl["name"],
            sort_order=int(fl.get("sort_order") or 0),
            is_active=bool(fl.get("is_active")),
            commit=args.commit, now=now,
        )
        floor_summary[action] = floor_summary.get(action, 0) + 1
        if new_id is not None:
            floor_name_to_id[fl["name"]] = new_id
        print(f"{fl['name']:<14} {action:<14} {new_id if new_id is not None else '-'}")

    # ── cameras ───────────────────────────────────────────────────────
    cam_summary = {"inserted": 0, "updated": 0, "skipped": 0,
                   "would-insert": 0, "would-update": 0, "would-skip": 0}
    print()
    print(f"{'camera_id':<14} {'action':<14} {'floor':<8} {'ip':<16} {'role':<14} pwd")
    print("-" * 78)
    for cam in src_cameras:
        existed = get_camera_existing(cur, cam["camera_id"])

        # Resolve floor_id / watches_floor_id by NAME on the target so
        # numeric ids don't have to line up across DBs.
        floor_name = cam.get("_floor_name") or cam.get("floor")
        watches_name = cam.get("_watches_floor_name") or cam.get("watches_floor")
        target_floor_id = floor_name_to_id.get(floor_name) if floor_name else None
        target_watches_id = floor_name_to_id.get(watches_name) if watches_name else None

        # If the floor doesn't exist yet (dry-run insert), pre-populate
        # known floors from the target side too (might be a subset of source).
        if floor_name and target_floor_id is None and not args.commit:
            target_floor_id = None  # surfaced as "-" in the table

        if existed and not args.update_existing:
            action = "skipped" if args.commit else "would-skip"
            cam_summary[action] += 1
        elif existed and args.update_existing:
            if args.commit:
                update_camera_metadata(
                    cur, spec=cam,
                    floor_id=target_floor_id, watches_floor_id=target_watches_id,
                    reset_passwords=args.reset_passwords, now=now,
                )
                action = "updated"
            else:
                action = "would-update"
            cam_summary[action] += 1
        else:
            if args.commit:
                insert_camera(
                    cur, spec=cam,
                    floor_id=target_floor_id, watches_floor_id=target_watches_id,
                    reset_passwords=args.reset_passwords, now=now,
                )
                action = "inserted"
            else:
                action = "would-insert"
            cam_summary[action] += 1

        pwd_marker = (
            "RESET" if args.reset_passwords else
            "(same)" if cam.get("password_encrypted") else "(none)"
        )
        print(
            f"{cam['camera_id']:<14} {action:<14} {(floor_name or '-'):<8} "
            f"{(cam.get('ip_address') or ''):<16} {cam['role']:<14} {pwd_marker}"
        )

    if args.commit:
        conn.commit()
    else:
        conn.rollback()

    conn.close()

    print()
    print(f"[clone] floors:  {floor_summary}")
    print(f"[clone] cameras: {cam_summary}")
    if not args.commit:
        print("[clone] dry-run only — pass --commit to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
