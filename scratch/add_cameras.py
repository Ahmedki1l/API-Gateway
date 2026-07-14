"""
Reconcile the dbo.cameras table from a single source of truth in this file.

What it does on each run (idempotent):
- Ensures every canonical cameras column exists (ALTER-ing in any missing one) —
  see ENSURE_COLUMNS. Brings an older table up to the full bootstrap.sql shape.
- Upserts every camera in CAMERAS (MERGE on ip_address — the stable physical
  identity): existing rows updated whatever their camera_id, new IPs inserted.
  No duplicates even across deployments that name cameras differently.
- Encrypts each password with app.services.crypto.cipher (the same
  CAMERAS_ENCRYPTION_KEY the gateway boots with). The plaintext never hits the DB.

PASSWORDS ARE SECRETS — they live in .env, NOT in this file. For each camera the
script reads  CAMERA_PW_<NORMALIZED_ID>  from .env (camera_id upper-cased, every
non-alphanumeric char → '_'), falling back to CAMERA_PW_DEFAULT. Examples:
    CAM-ENTRY -> CAMERA_PW_CAM_ENTRY
    CAM-03    -> CAMERA_PW_CAM_03
    CAM-15    -> CAMERA_PW_CAM_15
A camera with no matching env var (and no CAMERA_PW_DEFAULT) is reported and
skipped — nothing is half-written.

`area` is the constrained sub-zone. Allowed values:
      B1-A  B1-B  B1-C  RAMP-DOWN   B2-A  B2-B  B2-C  RAMP-UP   (or None)
  (see app/schemas_enums.py:CameraArea).

Run from the repo root with the gateway's venv active:
    python scratch/add_cameras.py
Pass --dry-run to print what would change (and which passwords resolve) without writing.
"""
import os
import re
import sys

# Repo root = the parent of this scratch/ dir. Put it on sys.path so `import app`
# works no matter where the repo is checked out or what the current working
# directory is (the old hardcoded absolute path broke on other machines).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import dotenv_values
from app.database import SessionLocal
from app.services.crypto import cipher
from sqlalchemy import text

# ── Secret source: .env at the repo root (gitignored). os.environ overrides it. ──
_ENV = {**dotenv_values(os.path.join(_REPO_ROOT, ".env")), **os.environ}


def _pw_key(camera_id: str) -> str:
    """camera_id -> CAMERA_PW_<NORMALIZED_ID> env-var name."""
    return "CAMERA_PW_" + re.sub(r"[^A-Z0-9]", "_", camera_id.upper())


def env_password(camera_id: str) -> str | None:
    """Resolve a camera's plaintext password from .env, or CAMERA_PW_DEFAULT."""
    return _ENV.get(_pw_key(camera_id)) or _ENV.get("CAMERA_PW_DEFAULT")

# ──────────────────────────────────────────────────────────────────────────────
# 1. LIST YOUR CAMERAS HERE
# ──────────────────────────────────────────────────────────────────────────────
# One dict per camera. `camera_id` is the business key used for matching.
# The PASSWORD IS NOT HERE — it's a secret in .env, looked up as
# CAMERA_PW_<NORMALIZED_ID> (see module docstring). Optional keys fall back to
# the defaults in DEFAULTS below.
#
# Allowed `area` values: B1-A, B1-B, B1-C, RAMP-DOWN, B2-A, B2-B, B2-C, RAMP-UP, or None
# (There is no `role` field — the gateway derives role from the camera_id pattern.)
#
# Template (copy this block for each camera; then add CAMERA_PW_<ID> to .env):
#     {
#         "camera_id": "CAM-15",
#         "name": "B2 Parking — Camera 15",
#         "area": "B2-A",
#         "floor": "B2",
#         "ip_address": "10.1.13.74",
#         "username": "kloudspot",
#         # optional overrides:
#         # "rtsp_port": 554,
#         # "rtsp_path": "/Streaming/Channels/101",
#         # "watches_floor": "B2",
#         # "enabled": True,
#         # "notes": "string",
#     },

CAMERAS = [
    # ── Existing fleet (16) — captured from the live cameras table. camera_id,
    #    username and password are preserved exactly so the upsert matches the
    #    current rows (no duplicates) and credentials round-trip. `area` is the
    #    physical sub-zone — left None until you assign each camera's section.
    {"camera_id": "ANPR-Entry", "name": "ENTRY-GATE", "area": None, "floor": "Ground",          "ip_address": "10.1.13.100", "username": "kloudspot", "notes": "string"},
    {"camera_id": "ANPR-Exit",  "name": "EXIT-GATE",  "area": None, "floor": "Ground",           "ip_address": "10.1.13.101", "username": "kloudspot1", "notes": "string"},
    {"camera_id": "CAM-01", "name": "GF-FRONT",    "area": None, "floor": "Ground", "ip_address": "10.1.13.60", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-02", "name": "GF-FRONT",    "area": None, "floor": "Ground", "ip_address": "10.1.13.61", "username": "kloudspot",     "notes": "string"},
    #--------------------------B1----------------------
    {"camera_id": "CAM-03", "name": "B1-PARKING",  "area": "B1-A", "floor": "B1", "ip_address": "10.1.13.62", "username": "kloudspot", "notes": "string"},
    {"camera_id": "CAM-04", "name": "B1-PARKING",  "area": "B1-C", "floor": "B1", "ip_address": "10.1.13.63", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-05", "name": "B1-PARKING",  "area": "RAMP-UP", "floor": "B1", "ip_address": "10.1.13.64", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-06", "name": "B1-PARKING",  "area": "B1-C", "floor": "B1", "ip_address": "10.1.13.65", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-07", "name": "B1-PARKING",  "area": "B1-A", "floor": "B1", "ip_address": "10.1.13.66", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-08", "name": "B1-PARKING",  "area": "B1-C", "floor": "B1", "ip_address": "10.1.13.67", "username": "kloudspot", "notes": "string"},
    #--------------------------B2----------------------
    {"camera_id": "CAM-09", "name": "B2-PARKING",  "area": "B2-A", "floor": "B2", "ip_address": "10.1.13.68", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-10", "name": "B2-PARKING",  "area": "B2-C", "floor": "B2", "ip_address": "10.1.13.69", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-11", "name": "B2-PARKING",  "area": "B2-C", "floor": "B2", "ip_address": "10.1.13.70", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-12", "name": "B2-PARKING",  "area": "B2-A", "floor": "B2", "ip_address": "10.1.13.71", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-13", "name": "B2-PARKING",  "area": "B2-A", "floor": "B2", "ip_address": "10.1.13.72", "username": "kloudspot",     "notes": "string"},
    {"camera_id": "CAM-14", "name": "B2-PARKING",  "area": "B2-C", "floor": "B2", "ip_address": "10.1.13.73", "username": "kloudspot",     "notes": "string"},

    # ── New cameras (9) on 10.1.13.x — user kloudspot. Set `area`/`floor`/`name`
    #    per camera when you know the mount location.
    #--------------------------B2----------------------
    {"camera_id": "CAM-15", "name": "B2-PARKING", "area": "B2-C", "floor": "B2", "ip_address": "10.1.13.84", "username": "kloudspot"},
    {"camera_id": "CAM-16", "name": "B2-PARKING", "area": "B2-A", "floor": "B2", "ip_address": "10.1.13.85", "username": "kloudspot"},
    {"camera_id": "CAM-17", "name": "B2-PARKING", "area":"B2-B", "floor": "B2", "ip_address": "10.1.13.86", "username": "kloudspot"},
    {"camera_id": "CAM-18", "name": "B2-PARKING", "area": "B2-B", "floor": "B2", "ip_address": "10.1.13.87", "username": "kloudspot"},
    {"camera_id": "CAM-19", "name": "B2-PARKING", "area": "B2-A", "floor": "B2", "ip_address": "10.1.13.88", "username": "kloudspot"},
    #----------------------B1----------------------
    {"camera_id": "CAM-20", "name": "B1-Entrance Gate", "area": "B1-A", "floor": "B1", "ip_address": "10.1.13.89", "username": "kloudspot"},
    {"camera_id": "CAM-21", "name": "B1-Parking", "area": "B1-B", "floor": "B1", "ip_address": "10.1.13.90", "username": "kloudspot"},
    {"camera_id": "CAM-22", "name": "B1-Parking", "area": "B1-B", "floor": "B1", "ip_address": "10.1.13.91", "username": "kloudspot"},
    {"camera_id": "CAM-23", "name": "B1-Entry Ramp", "area": None, "floor": "B1", "ip_address": "10.1.13.94", "username": "kloudspot"},
]

# ──────────────────────────────────────────────────────────────────────────────
# 2. Defaults applied to any key a camera dict omits
# ──────────────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "name": None,
    "area": None,
    "floor": None,
    # floor_id / watches_floor_id are NOT set by hand — they're resolved from the
    # `floors` lookup table by name in resolve_floor_ids() (mirrors how the
    # gateway dual-writes them). Left None here so every param carries the key.
    "floor_id": None,
    "watches_floor": None,
    "watches_floor_id": None,
    "ip_address": None,
    "rtsp_port": 554,
    "rtsp_path": "/Streaming/Channels/101",
    "username": None,
    "enabled": True,
    "notes": None,
}

# Columns we may write, in preferred order. The script keeps only the ones that
# actually exist in dbo.cameras (probed at runtime) — this DB may pre-date some
# bootstrap.sql ALTERs (e.g. `watches_floor`), so we never reference a missing
# column. `role` is intentionally absent: the gateway derives it, never stores it.
# `password_encrypted` is set from the encrypted plaintext; `floor_id` /
# `watches_floor_id` are resolved from `floors` by name (see resolve_floor_ids).
WRITABLE_COLUMNS = [
    "name", "area", "floor", "floor_id", "watches_floor", "watches_floor_id",
    "ip_address", "rtsp_port", "rtsp_path", "username", "password_encrypted",
    "enabled", "notes",
]


def existing_columns(db) -> set:
    res = db.execute(text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'cameras'"
    ))
    return {r[0] for r in res.fetchall()}


# The full canonical dbo.cameras schema (mirrors sql/bootstrap.sql). The script
# ensures every one of these columns exists, ALTER-ing in any that's missing, so
# a single run brings any older cameras table up to the complete shape. `id`,
# `camera_id`, and `ip_address` are intentionally absent: `id` is IDENTITY,
# `camera_id` is the match key, and `ip_address` is NOT NULL with no default
# (can't be added to a populated table) — all three are guaranteed present.
# NOT NULL columns carry a DEFAULT so SQL Server can backfill existing rows.
ENSURE_COLUMNS = {
    "name":               "VARCHAR(100)  NULL",
    "area":               "VARCHAR(50)   NULL",
    "floor":              "VARCHAR(50)   NULL",
    "floor_id":           "INT           NULL",
    "zone_id":            "VARCHAR(100)  NULL",
    # NOTE: no `role` column. The gateway DERIVES role from the camera_id naming
    # pattern (see routers/cameras.py:_derive_role) and never stores it.
    "watches_floor":      "VARCHAR(50)   NULL",
    "watches_floor_id":   "INT           NULL",
    "watches_slots_json": "NVARCHAR(MAX) NULL",
    "rtsp_port":          "INT           NOT NULL DEFAULT (554)",
    "rtsp_path":          "VARCHAR(255)  NOT NULL DEFAULT ('/Streaming/Channels/101')",
    "username":           "VARCHAR(100)  NULL",
    "password_encrypted": "NVARCHAR(MAX) NULL",
    "enabled":            "BIT           NOT NULL DEFAULT (1)",
    "notes":              "NVARCHAR(MAX) NULL",
    "last_check_at":      "DATETIME2     NULL",
    "last_seen_at":       "DATETIME2     NULL",
    "last_status":        "VARCHAR(50)   NULL",
    "created_at":         "DATETIME2     NOT NULL DEFAULT (GETUTCDATE())",
    "updated_at":         "DATETIME2     NOT NULL DEFAULT (GETUTCDATE())",
}


def ensure_columns(db, *, dry_run: bool) -> None:
    """ALTER TABLE dbo.cameras ADD <col> for any ENSURE_COLUMNS not yet present."""
    have = existing_columns(db)
    for col, ddl in ENSURE_COLUMNS.items():
        if col in have:
            continue
        print(f"  {'[dry-run] ' if dry_run else ''}adding missing column dbo.cameras.{col} ({ddl})")
        if not dry_run:
            # COL_LENGTH guard keeps it idempotent even under concurrent runs.
            db.execute(text(
                f"IF COL_LENGTH(N'dbo.cameras', N'{col}') IS NULL "
                f"ALTER TABLE dbo.cameras ADD {col} {ddl}"
            ))
            db.commit()


def resolve_floor_ids(db, params: list[dict], *, dry_run: bool) -> None:
    """Fill each param's floor_id / watches_floor_id from the `floors` lookup,
    keyed by the floor NAME — same mapping the gateway uses. Missing floor names
    are inserted (name-only; floors' other columns have defaults), mirroring
    sql/bootstrap.sql. No-op when there's no floors table (floor_id stays None
    and COALESCE leaves any existing value untouched)."""
    have_floors = bool(db.execute(text(
        "SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'floors'"
    )).fetchone())
    if not have_floors:
        print("  (no floors table — leaving floor_id / watches_floor_id unset)")
        return

    needed = {p[k] for p in params for k in ("floor", "watches_floor") if p.get(k)}
    for name in sorted(needed):
        exists = db.execute(text("SELECT id FROM floors WHERE name = :n"), {"n": name}).fetchone()
        if exists:
            continue
        print(f"  {'[dry-run] ' if dry_run else ''}adding floor '{name}' to floors lookup")
        if not dry_run:
            db.execute(text("INSERT INTO floors (name) VALUES (:n)"), {"n": name})
    if not dry_run:
        db.commit()

    fmap = {r[1]: r[0] for r in db.execute(text("SELECT id, name FROM floors")).fetchall()}
    for p in params:
        if p.get("floor"):
            p["floor_id"] = fmap.get(p["floor"])
        if p.get("watches_floor"):
            p["watches_floor_id"] = fmap.get(p["watches_floor"])


def build_upsert(present: list[str]) -> "text":
    # Match on ip_address — the stable PHYSICAL identity of a camera. Different
    # deployments name the same camera differently (CAM-ENTRY vs ANPR-Entry vs
    # Cam_01), so matching on camera_id created duplicate rows. Matching on IP
    # updates the existing row whatever its camera_id is — no duplicates — and
    # the existing camera_id is PRESERVED (camera_id is never in the UPDATE SET).
    #
    # On UPDATE, COALESCE(:col, Target.col) keeps the existing DB value when the
    # script passes NULL — so re-running never wipes a column that's already set.
    # INSERT (a genuinely new IP) takes the values as-is, NULL included.
    set_cols = [c for c in present if c != "ip_address"]  # ip is the match key
    set_clause = ",\n        ".join(f"{c} = COALESCE(:{c}, Target.{c})" for c in set_cols)
    insert_cols = ", ".join(["camera_id", *present])
    insert_vals = ", ".join(f":{c}" for c in ["camera_id", *present])
    return text(f"""
    MERGE INTO dbo.cameras AS Target
    USING (SELECT :ip_address AS ip_address) AS Source
        ON Target.ip_address = Source.ip_address
    WHEN MATCHED THEN UPDATE SET
        {set_clause},
        updated_at = GETUTCDATE()
    WHEN NOT MATCHED THEN INSERT
        ({insert_cols})
        VALUES
        ({insert_vals});
""")


ALLOWED_AREAS = {"B1-A", "B1-B", "B1-C", "RAMP-UP", "B2-A", "B2-B", "B2-C", "RAMP-DOWN", None}


def build_params(cam: dict) -> dict:
    p = {**DEFAULTS, **cam}
    if not p.get("camera_id"):
        raise ValueError(f"camera missing 'camera_id': {cam!r}")
    if not p.get("ip_address"):
        raise ValueError(f"{p['camera_id']}: missing 'ip_address'")
    if p["area"] not in ALLOWED_AREAS:
        raise ValueError(f"{p['camera_id']}: invalid area {p['area']!r} (allowed: {sorted(a for a in ALLOWED_AREAS if a)})")
    # Password is a secret sourced from .env (an inline "password" key, if present,
    # wins as a one-off override). Missing entirely → hard error so we never
    # silently wipe a camera's stored credential.
    plaintext = cam.get("password") or env_password(p["camera_id"])
    if not plaintext:
        raise ValueError(
            f"{p['camera_id']}: no password — set {_pw_key(p['camera_id'])} "
            f"(or CAMERA_PW_DEFAULT) in .env"
        )
    p.pop("password", None)
    p["password_encrypted"] = cipher.encrypt(plaintext)
    return p


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    if not CAMERAS:
        print("No cameras listed. Add entries to CAMERAS at the top of this file.")
        return

    params = [build_params(c) for c in CAMERAS]  # validate + encrypt all first

    db = SessionLocal()
    try:
        ensure_columns(db, dry_run=dry_run)  # self-provision `area` etc. if missing
        resolve_floor_ids(db, params, dry_run=dry_run)  # floor name -> floor_id
        present = [c for c in WRITABLE_COLUMNS if c in existing_columns(db)]
        skipped = [c for c in WRITABLE_COLUMNS if c not in present]
        if skipped:
            print(f"  (columns not on this DB, skipped: {', '.join(skipped)})")
        upsert = build_upsert(present)
        for p in params:
            row = {"camera_id": p["camera_id"], **{c: p.get(c) for c in present}}
            print(f"  {'[dry-run] ' if dry_run else ''}upsert {p['camera_id']:<10} "
                  f"area={p.get('area') or '-':<8} floor_id={p.get('floor_id') or '-':<4} ip={p['ip_address']}")
            if not dry_run:
                db.execute(upsert, row)
        if dry_run:
            print(f"\nDry run: {len(params)} camera(s) validated and encrypted, nothing written.")
        else:
            db.commit()
            print(f"\nDone: {len(params)} camera(s) upserted.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
