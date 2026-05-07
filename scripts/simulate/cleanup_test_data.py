#!/usr/bin/env python
"""Wipe TEST-* lifecycle rows out of `damanat_pms` so re-runs start clean.

Connects directly to SQL Server via `pyodbc` (already in requirements.txt)
and counts/deletes rows whose `plate_number` matches the prefix. Order of
deletes is FK-safe: alerts -> parking_sessions -> entry_exit_log ->
camera_feeds -> vehicles. The vehicles delete is gated by
`is_registered = 0` so seeded staff/visitor rows are never touched.

Idempotent — running twice in a row on a clean DB is a no-op.

Examples:
    python cleanup_test_data.py --plate-prefix TEST-
    python cleanup_test_data.py --plate-prefix TEST-LIFE --dry-run
    python cleanup_test_data.py --plate-prefix TEST- --trusted
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make the leading-underscore _common.py importable.
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from _common import cyan, green, red, yellow  # noqa: E402

try:
    import pyodbc  # type: ignore
except ImportError:
    red("pyodbc not installed — `pip install pyodbc` and retry")
    sys.exit(1)


# API-Gateway/.env holds the real DB credentials (the deployment uses
# DB_USER/DB_PASSWORD or DB_TRUSTED_CONNECTION). Without this loader the
# script falls back to the .env.example placeholder password and gets a 28000
# Login failed error every time. Tiny parser — no dotenv dependency.
GATEWAY_ROOT = HERE.parent.parent  # scripts/simulate/ -> scripts/ -> API-Gateway/
DEFAULT_ENV_FILE = GATEWAY_ROOT / ".env"


def _load_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE pairs from a .env file. Strips quotes; skips comments/blank."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        # Strip optional surrounding quotes.
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        out[key] = val
    return out


def _truthy(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


# Order matters: alerts/parking_sessions/entry_exit_log/camera_feeds reference
# vehicles via plate_number, so they get deleted first to avoid FK errors.
COUNT_QUERIES: list[tuple[str, str]] = [
    ("alerts", "SELECT COUNT(*) FROM dbo.alerts WHERE plate_number LIKE ?"),
    ("parking_sessions", "SELECT COUNT(*) FROM dbo.parking_sessions WHERE plate_number LIKE ?"),
    ("entry_exit_log", "SELECT COUNT(*) FROM dbo.entry_exit_log WHERE plate_number LIKE ?"),
    ("camera_feeds", "SELECT COUNT(*) FROM dbo.camera_feeds WHERE plate_number LIKE ?"),
    ("slot_status", "SELECT COUNT(*) FROM dbo.slot_status WHERE plate_number LIKE ?"),
    ("vehicles", "SELECT COUNT(*) FROM dbo.vehicles WHERE plate_number LIKE ? AND is_registered = 0"),
]

# Order: child rows first (FK-safe). slot_status sits next to camera_feeds
# because both reference plate_number directly. The parking_slots reset is a
# separate UPDATE — we don't delete slot rows, just unstick is_available
# flags the simulator may have toggled.
DELETE_QUERIES: list[tuple[str, str]] = [
    ("alerts", "DELETE FROM dbo.alerts WHERE plate_number LIKE ?"),
    ("parking_sessions", "DELETE FROM dbo.parking_sessions WHERE plate_number LIKE ?"),
    ("entry_exit_log", "DELETE FROM dbo.entry_exit_log WHERE plate_number LIKE ?"),
    ("camera_feeds", "DELETE FROM dbo.camera_feeds WHERE plate_number LIKE ?"),
    ("slot_status", "DELETE FROM dbo.slot_status WHERE plate_number LIKE ?"),
    ("vehicles", "DELETE FROM dbo.vehicles WHERE plate_number LIKE ? AND is_registered = 0"),
]

# After deleting slot_status TEST rows, any parking_slots row whose latest
# remaining slot_status is NULL or 'available' should be is_available=1 again.
# Also covers slots that had no slot_status history at all but were toggled
# via the simulator's direct UPDATE during a failed run.
RESET_PARKING_SLOTS_SQL = """
UPDATE parking_slots
SET is_available = 1
WHERE is_available = 0
  AND NOT EXISTS (
      SELECT 1
      FROM slot_status ss
      WHERE ss.slot_id = parking_slots.slot_id
        AND ss.status = 'occupied'
        AND ss.time = (
            SELECT MAX(time) FROM slot_status WHERE slot_id = ss.slot_id
        )
  )
"""


def build_conn_str(args: argparse.Namespace) -> str:
    """Mirror app/config.py:db_connection_string but for raw pyodbc DSN."""
    base = (
        f"DRIVER={{{args.db_driver}}};"
        f"SERVER={args.db_server},{args.db_port};"
        f"DATABASE={args.db_name};"
        "TrustServerCertificate=Yes;"
    )
    if args.trusted:
        return base + "Trusted_Connection=Yes;"
    return base + f"UID={args.db_user};PWD={args.db_password};"


def parse_args() -> argparse.Namespace:
    """CLI flags fall back to env-file values, which fall back to hardcoded
    defaults. Precedence (highest first): explicit CLI flag → environment var
    set in the shell → API-Gateway/.env → hardcoded default."""
    # 1. Load the env file (Gateway's .env by default).
    env_file_arg = None
    for i, a in enumerate(sys.argv):
        if a == "--env-file" and i + 1 < len(sys.argv):
            env_file_arg = Path(sys.argv[i + 1])
            break
    env_path = env_file_arg if env_file_arg else DEFAULT_ENV_FILE
    file_env = _load_env_file(env_path)

    # 2. Resolve effective values (env file → process env → hardcoded default).
    def envv(key: str, default: str) -> str:
        return os.environ.get(key) or file_env.get(key) or default

    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--plate-prefix", default="TEST-")
    p.add_argument("--env-file", default=str(env_path),
                   help="Path to .env file (default: API-Gateway/.env)")
    p.add_argument("--db-driver",   default=envv("DB_DRIVER",   "ODBC Driver 18 for SQL Server"))
    p.add_argument("--db-server",   default=envv("DB_SERVER",   "localhost"))
    p.add_argument("--db-port",     type=int, default=int(envv("DB_PORT", "1433")))
    p.add_argument("--db-name",     default=envv("DB_NAME",     "damanat_pms"))
    p.add_argument("--db-user",     default=envv("DB_USER",     "sa"))
    p.add_argument("--db-password", default=envv("DB_PASSWORD", "YourStrong!Pass1"))
    p.add_argument("--trusted",     action="store_true", default=_truthy(envv("DB_TRUSTED_CONNECTION", "")),
                   help="Use Windows Authentication (ignores --db-user/--db-password).")
    p.add_argument("--dry-run",     action="store_true",
                   help="Print row counts but skip the DELETEs.")
    # Accepted-but-unused so run_full_lifecycle.py can pass these uniformly.
    p.add_argument("--pms-ai",  default=None, help=argparse.SUPPRESS)
    p.add_argument("--gateway", default=None, help=argparse.SUPPRESS)
    args = p.parse_args()
    if file_env:
        cyan(f"loaded env defaults from {env_path}")
    elif env_path.exists() is False:
        yellow(f"env file not found at {env_path} — using hardcoded defaults")
    return args


def main() -> int:
    args = parse_args()
    pfx = (args.plate_prefix or "") + "%"
    conn_str = build_conn_str(args)
    cyan(f"connecting: SERVER={args.db_server},{args.db_port}  DB={args.db_name}  "
         f"AUTH={'WindowsAuth' if args.trusted else 'SqlAuth'}")
    cyan(f"prefix LIKE pattern: {pfx!r}    dry_run={args.dry_run}")

    try:
        conn = pyodbc.connect(conn_str, autocommit=False)
    except Exception as exc:
        red(f"connection failed: {exc!r}")
        return 1

    total_rows = 0
    try:
        cur = conn.cursor()

        # 1. Counts (read-only, always safe).
        cyan("\nrow counts:")
        counts: dict[str, int] = {}
        for tbl, sql in COUNT_QUERIES:
            cur.execute(sql, pfx)
            n = cur.fetchone()[0] or 0
            counts[tbl] = int(n)
            total_rows += int(n)
            print(f"  {tbl:<20} {n:>6}")
        print(f"  {'TOTAL':<20} {total_rows:>6}")

        if args.dry_run:
            green("\ndry-run complete (no DELETEs issued)")
            return 0

        if total_rows == 0:
            green("\nnothing to delete (already clean)")
            return 0

        # 2. Deletes (FK-safe order). Single transaction so any failure rolls back.
        cyan("\ndeleting:")
        for tbl, sql in DELETE_QUERIES:
            cur.execute(sql, pfx)
            print(f"  {tbl:<20} -> {cur.rowcount:>6} rows deleted")
        # 3. Reset is_available on slots whose latest remaining slot_status
        #    is no longer 'occupied'. Without this, a TEST run that toggled
        #    a slot to is_available=0 leaves it stuck after cleanup.
        cur.execute(RESET_PARKING_SLOTS_SQL)
        if cur.rowcount > 0:
            print(f"  parking_slots       -> {cur.rowcount:>6} rows reset to is_available=1")
        conn.commit()
        green(f"\ndeleted {total_rows} TEST rows across {len(DELETE_QUERIES)} tables")
        return 0
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        red(f"cleanup failed (rolled back): {exc!r}")
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
