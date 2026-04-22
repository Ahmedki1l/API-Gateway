"""
Ingest an upstream service's camera config (env file) into the gateway's cameras
table. Encrypts passwords with the same cipher the gateway uses.

Usage:
    python scripts/migrate_cameras_from_env.py --source /path/to/upstream/.env
    python scripts/migrate_cameras_from_env.py --source ... --commit
    python scripts/migrate_cameras_from_env.py --source ... --commit --overwrite-passwords
    python scripts/migrate_cameras_from_env.py --source ... --prefix CAMERA

Defaults to dry-run for safety. Pass --commit to actually write.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

# Add parent directory so `from app...` works when invoked from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.services.crypto import cipher  # noqa: E402


DEFAULT_RTSP_PATH = "/Streaming/Channels/101"
DEFAULT_RTSP_PORT = 554

KNOWN_SUFFIXES = {
    "NAME", "FLOOR", "ZONE", "IP", "RTSP_PORT", "RTSP_PATH",
    "USER", "PASS", "ENABLED", "NOTES", "RTSP",
}


@dataclass
class CameraSpec:
    camera_id: str
    name: Optional[str] = None
    floor: Optional[str] = None
    zone_id: Optional[str] = None
    ip_address: Optional[str] = None
    rtsp_port: int = DEFAULT_RTSP_PORT
    rtsp_path: str = DEFAULT_RTSP_PATH
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = True
    notes: Optional[str] = None
    saw_full_rtsp_url: bool = False
    saw_decomposed_field: bool = False
    raw_keys: list[str] = field(default_factory=list)


def parse_env_file(path: Path) -> dict[str, str]:
    """Minimal .env parser — KEY=value lines, # comments, no quoting tricks."""
    pairs: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        pairs[key] = value
    return pairs


def coerce_bool(s: str) -> bool:
    return s.strip().lower() in {"1", "true", "yes", "on"}


def decompose_full_rtsp_url(url: str, spec: CameraSpec) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"rtsp", "rtsps"}:
        raise ValueError(f"unsupported scheme '{parsed.scheme}' in {url}")
    if not parsed.hostname:
        raise ValueError(f"no host in {url}")
    spec.ip_address = parsed.hostname
    spec.rtsp_port = parsed.port or DEFAULT_RTSP_PORT
    path = parsed.path or DEFAULT_RTSP_PATH
    if parsed.query:
        path = f"{path}?{parsed.query}"
    spec.rtsp_path = path
    if parsed.username:
        spec.username = unquote(parsed.username)
    if parsed.password:
        spec.password = unquote(parsed.password)


def group_by_camera(pairs: dict[str, str], prefix: str) -> dict[str, CameraSpec]:
    pattern = re.compile(rf"^{re.escape(prefix)}(?P<id>[A-Za-z0-9]+)_(?P<suffix>[A-Z_]+)$")
    cameras: dict[str, CameraSpec] = {}
    ignored: list[str] = []

    for key, value in pairs.items():
        m = pattern.match(key)
        if not m:
            continue
        cam_id = f"{prefix}{m.group('id')}"
        suffix = m.group("suffix")
        if suffix not in KNOWN_SUFFIXES:
            ignored.append(key)
            continue

        spec = cameras.setdefault(cam_id, CameraSpec(camera_id=cam_id))
        spec.raw_keys.append(key)

        if suffix == "RTSP":
            spec.saw_full_rtsp_url = True
            decompose_full_rtsp_url(value, spec)
        else:
            spec.saw_decomposed_field = True
            if suffix == "NAME":
                spec.name = value
            elif suffix == "FLOOR":
                spec.floor = value
            elif suffix == "ZONE":
                spec.zone_id = value
            elif suffix == "IP":
                spec.ip_address = value
            elif suffix == "RTSP_PORT":
                spec.rtsp_port = int(value)
            elif suffix == "RTSP_PATH":
                spec.rtsp_path = value if value.startswith("/") else f"/{value}"
            elif suffix == "USER":
                spec.username = value
            elif suffix == "PASS":
                spec.password = value if value != "" else None
            elif suffix == "ENABLED":
                spec.enabled = coerce_bool(value)
            elif suffix == "NOTES":
                spec.notes = value

    if ignored:
        print(f"[migrate] ignored {len(ignored)} unmapped key(s): {', '.join(ignored[:10])}"
              + (" ..." if len(ignored) > 10 else ""))

    return cameras


def validate_spec(spec: CameraSpec) -> Optional[str]:
    if spec.saw_full_rtsp_url and spec.saw_decomposed_field:
        decomposed = [k for k in spec.raw_keys if not k.endswith("_RTSP")]
        return (
            f"camera_id={spec.camera_id!r} has both _RTSP=<full url> and decomposed fields "
            f"({', '.join(decomposed)}). Pick one — refusing to guess which wins."
        )
    if not spec.ip_address:
        return f"camera_id={spec.camera_id!r} missing IP / RTSP URL"
    return None


def cameras_table_exists() -> bool:
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'cameras'")
        )
        return (result.scalar() or 0) > 0
    finally:
        db.close()


def fetch_existing(camera_id: str) -> Optional[dict]:
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                "SELECT camera_id, ip_address, rtsp_port, rtsp_path, username, "
                "password_encrypted, enabled, name, floor, zone_id, notes "
                "FROM cameras WHERE camera_id = :camera_id"
            ),
            {"camera_id": camera_id},
        )
        cols = result.keys()
        row = result.fetchone()
        return dict(zip(cols, row)) if row else None
    finally:
        db.close()


def upsert_camera(spec: CameraSpec, *, overwrite_passwords: bool) -> str:
    """Returns one of: 'inserted', 'updated', 'skipped'."""
    existing = fetch_existing(spec.camera_id)
    now = datetime.now(timezone.utc)

    if existing is None:
        encrypted = cipher.encrypt(spec.password) if spec.password else None
        db = SessionLocal()
        try:
            db.execute(
                text(
                    "INSERT INTO cameras "
                    "(camera_id, name, floor, zone_id, ip_address, rtsp_port, rtsp_path, "
                    " username, password_encrypted, enabled, notes, created_at, updated_at) "
                    "VALUES (:camera_id, :name, :floor, :zone_id, :ip_address, :rtsp_port, "
                    " :rtsp_path, :username, :password_encrypted, :enabled, :notes, :now, :now)"
                ),
                {
                    "camera_id": spec.camera_id,
                    "name": spec.name,
                    "floor": spec.floor,
                    "zone_id": spec.zone_id,
                    "ip_address": spec.ip_address,
                    "rtsp_port": spec.rtsp_port,
                    "rtsp_path": spec.rtsp_path,
                    "username": spec.username,
                    "password_encrypted": encrypted,
                    "enabled": 1 if spec.enabled else 0,
                    "notes": spec.notes,
                    "now": now,
                },
            )
            db.commit()
        finally:
            db.close()
        return "inserted"

    # update path
    set_password = bool(spec.password) and (
        overwrite_passwords or not existing["password_encrypted"]
    )
    encrypted = cipher.encrypt(spec.password) if (set_password and spec.password) else None

    sets = [
        "name = :name", "floor = :floor", "zone_id = :zone_id", "ip_address = :ip_address",
        "rtsp_port = :rtsp_port", "rtsp_path = :rtsp_path", "username = :username",
        "enabled = :enabled", "notes = :notes", "updated_at = :now",
    ]
    params: dict = {
        "camera_id": spec.camera_id,
        "name": spec.name,
        "floor": spec.floor,
        "zone_id": spec.zone_id,
        "ip_address": spec.ip_address,
        "rtsp_port": spec.rtsp_port,
        "rtsp_path": spec.rtsp_path,
        "username": spec.username,
        "enabled": 1 if spec.enabled else 0,
        "notes": spec.notes,
        "now": now,
    }
    if set_password:
        sets.append("password_encrypted = :password_encrypted")
        params["password_encrypted"] = encrypted

    db = SessionLocal()
    try:
        db.execute(
            text(f"UPDATE cameras SET {', '.join(sets)} WHERE camera_id = :camera_id"),
            params,
        )
        db.commit()
    finally:
        db.close()
    return "updated"


def mask_password(p: Optional[str]) -> str:
    if not p:
        return "(none)"
    return f"***{len(p)} chars***"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest upstream camera config (env file) into the cameras table.",
    )
    parser.add_argument("--source", required=True, type=Path, help="Path to upstream .env file")
    parser.add_argument(
        "--prefix", default="CAM",
        help="Key prefix that identifies camera entries (default: CAM)",
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="Actually write to the DB. Without this flag, only a dry-run report is printed.",
    )
    parser.add_argument(
        "--overwrite-passwords", action="store_true",
        help="Overwrite existing encrypted passwords. By default, existing passwords are kept.",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"error: source file not found: {args.source}", file=sys.stderr)
        return 2

    if not cameras_table_exists():
        print(
            "error: 'cameras' table does not exist. "
            "Run migrations/add_cameras_table.sql first.",
            file=sys.stderr,
        )
        return 2

    pairs = parse_env_file(args.source)
    print(f"[migrate] parsed {len(pairs)} key=value lines from {args.source}")

    cameras = group_by_camera(pairs, prefix=args.prefix)
    if not cameras:
        print(f"[migrate] no entries matched prefix '{args.prefix}' — nothing to do")
        return 0

    errors: list[str] = []
    valid: list[CameraSpec] = []
    for spec in cameras.values():
        err = validate_spec(spec)
        if err:
            errors.append(err)
        else:
            valid.append(spec)

    print(f"[migrate] {len(valid)} valid camera(s), {len(errors)} error(s)\n")
    for err in errors:
        print(f"  ! {err}")
    if errors and not valid:
        return 1

    print(f"{'camera_id':<14} {'action':<10} {'ip':<18} {'port':<5} {'user':<12} password")
    print("-" * 78)

    summary = {"inserted": 0, "updated": 0, "skipped": 0}

    for spec in sorted(valid, key=lambda s: s.camera_id):
        existing = fetch_existing(spec.camera_id)
        if args.commit:
            action = upsert_camera(spec, overwrite_passwords=args.overwrite_passwords)
        else:
            if existing is None:
                action = "would-insert"
            elif spec.password and (args.overwrite_passwords or not existing["password_encrypted"]):
                action = "would-update*"
            else:
                action = "would-update"
        if action in summary:
            summary[action] += 1
        print(
            f"{spec.camera_id:<14} {action:<10} {spec.ip_address or '':<18} "
            f"{spec.rtsp_port:<5} {(spec.username or ''):<12} {mask_password(spec.password)}"
        )

    print()
    if args.commit:
        print(
            f"[migrate] done — {summary['inserted']} inserted, "
            f"{summary['updated']} updated, {summary['skipped']} skipped, "
            f"{len(errors)} errors"
        )
    else:
        print(f"[migrate] dry-run only — pass --commit to apply. ({len(valid)} would be processed)")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
