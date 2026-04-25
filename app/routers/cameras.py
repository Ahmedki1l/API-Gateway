"""
Cameras configurator — CRUD for camera devices, with encrypted credentials and
liveness monitoring. Acts as the central registry consumed by the upstream
VideoAnalytics service via /cameras/internal/all.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, rows, scalar
from app.schemas import (
    CameraCheckResult,
    CameraCreate,
    CameraCredentials,
    CameraInternalListResponse,
    CameraItem,
    CameraKPIs,
    CameraUpdate,
    CameraWithCredentials,
    EntityActionResponse,
    PagedResponse,
)
from app.config import settings
from app.routers._helpers import _floor_schema, resolve_floor_id
from app.services.camera_monitor import check_one, derive_is_online
from app.services.crypto import build_rtsp_url, cipher, mask_rtsp_url
from app.shared import build_paged, stream_csv


from app.services.auth import require_internal_token

router = APIRouter(prefix="/cameras", tags=["Cameras"])


# ── Camera role derivation (WS-8.E) ───────────────────────────────────────────
# Roles still derive from camera_id naming convention (no role column in DB),
# but `watches_floor` is now read directly from `cameras.watches_floor_id` /
# `cameras.watches_floor` rather than the hardcoded `'CAM-03' → 'B1'` switch.
def _derive_role(
    camera_id: str,
    floor: Optional[str],
    floor_id: Optional[int] = None,
    watches_floor_id: Optional[int] = None,
    watches_floor: Optional[str] = None,
) -> tuple[str, Optional[str], Optional[int], None]:
    """Returns (role, watches_floor, watches_floor_id, watches_slots).

    Role derivation rules (camera_id pattern):
      - CAM-ENTRY / CAM-ENTRANCE / CAM-GATE-IN → entry (gate cameras don't
        watch a floor)
      - CAM-EXIT / CAM-GATE-OUT                → exit
      - any camera with watches_floor[_id] set → floor_counting
      - everything else                        → slot_detection

    `watches_floor` / `watches_floor_id` come straight from the DB row when
    set; we no longer hardcode `CAM-03 → B1` / `CAM-09 → B2`. When neither is
    set the camera is treated as covering its own `floor` (back-compat for
    pre-WS-8 rows where watches_floor wasn't populated)."""
    cid = (camera_id or "").upper()
    if cid in ("CAM-ENTRY", "CAM-ENTRANCE", "CAM-GATE-IN"):
        return ("entry", None, None, None)
    if cid in ("CAM-EXIT", "CAM-GATE-OUT"):
        return ("exit", None, None, None)
    # If the row has an explicit watches_floor[_id], it's a floor-counting cam.
    if watches_floor_id is not None or watches_floor is not None:
        return ("floor_counting", watches_floor, watches_floor_id, None)
    # Default: slot-detection cameras watching slots on their own floor.
    return ("slot_detection", floor, floor_id, None)


# T-SQL expression for the role filter in WHERE clauses. The watches_floor
# filter no longer needs a CASE — it reads `watches_floor` / `watches_floor_id`
# directly from the row. Role still derives via CASE (no `role` column in DB).
#
# The threshold for is_online comes from settings.camera_monitor_interval_seconds
# (same value the camera_monitor service uses to decide if a camera "looks
# offline"). We multiply by a small buffer so a single missed probe doesn't
# flip is_online → False.
#
# WS-8 schema-compat shim: when `cameras.watches_floor_id` doesn't exist yet
# (pre-migration DB), drop the `OR watches_floor_id IS NOT NULL` half so we
# don't reference a missing column.
def _role_case_sql() -> str:
    schema = _floor_schema()
    cond = "watches_floor IS NOT NULL"
    if schema["cameras_watches_floor_id"]:
        cond += " OR watches_floor_id IS NOT NULL"
    return (
        "CASE "
        "WHEN UPPER(camera_id) IN ('CAM-ENTRY','CAM-ENTRANCE','CAM-GATE-IN') THEN 'entry' "
        "WHEN UPPER(camera_id) IN ('CAM-EXIT','CAM-GATE-OUT') THEN 'exit' "
        f"WHEN {cond} THEN 'floor_counting' "
        "ELSE 'slot_detection' END"
    )


def _is_online_case_sql() -> str:
    """SQL expression returning 1 when last_seen_at is recent enough."""
    threshold_seconds = int(settings.camera_monitor_interval_seconds * 2)
    return (
        "CASE WHEN last_seen_at IS NOT NULL "
        f"AND last_seen_at >= DATEADD(SECOND, -{threshold_seconds}, GETUTCDATE()) "
        "THEN 1 ELSE 0 END"
    )


# ── Row → response mapping ────────────────────────────────────────────────────
def _row_to_item(row: dict) -> dict:
    has_password = bool(row.get("password_encrypted"))
    masked = mask_rtsp_url(
        ip=row["ip_address"],
        port=int(row["rtsp_port"]),
        path=row["rtsp_path"],
        user=row.get("username"),
        has_password=has_password,
    )
    # WS-8.E: watches_floor[_id] read straight from the row (was hardcoded CASE).
    role, watches_floor, watches_floor_id, watches_slots = _derive_role(
        row["camera_id"],
        row.get("floor"),
        row.get("floor_id"),
        row.get("watches_floor_id"),
        row.get("watches_floor"),
    )
    return {
        "id": row["id"],
        "camera_id": row["camera_id"],
        "name": row.get("name"),
        "floor": row.get("floor"),
        "floor_id": row.get("floor_id"),
        "role": role,
        "watches_floor": watches_floor,
        "watches_floor_id": watches_floor_id,
        "watches_slots": watches_slots,
        "ip_address": row["ip_address"],
        "rtsp_port": int(row["rtsp_port"]),
        "rtsp_path": row["rtsp_path"],
        "username": row.get("username"),
        "has_password": has_password,
        "rtsp_url_masked": masked,
        "enabled": bool(row["enabled"]),
        "notes": row.get("notes"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_check_at": row.get("last_check_at"),
        "last_seen_at": row.get("last_seen_at"),
        "last_status": row.get("last_status"),
        "is_online": derive_is_online(row.get("last_seen_at")),
    }


# WS-8.E: floor_id, watches_floor, watches_floor_id added so _row_to_item can
# populate the new schema fields and so the role-case SQL has its inputs.
#
# Schema-compat shim: when `cameras.floor_id` / `cameras.watches_floor_id`
# don't exist yet (pre-migration DB), emit `NULL AS <col>` so the SELECT
# stays valid and `_row_to_item` still gets None for those keys via
# `row.get(...)`. `watches_floor` (the legacy string column) has been in the
# schema since Phase 4A so no fallback is needed for it.
def _select_cols() -> str:
    schema = _floor_schema()
    def col(name: str, present: bool) -> str:
        return name if present else f"NULL AS {name}"
    cols = [
        "id", "camera_id", "name",
        col("floor",            schema["cameras_floor"]),
        col("floor_id",         schema["cameras_floor_id"]),
        col("watches_floor",    schema["cameras_watches_floor"]),
        col("watches_floor_id", schema["cameras_watches_floor_id"]),
        "ip_address", "rtsp_port", "rtsp_path",
        "username", "password_encrypted", "enabled",
        col("notes",         schema["cameras_notes"]),
        col("last_check_at", schema["cameras_last_check_at"]),
        col("last_seen_at",  schema["cameras_last_seen_at"]),
        col("last_status",   schema["cameras_last_status"]),
        "created_at", "updated_at",
    ]
    return ", ".join(cols)


# ── KPIs ──────────────────────────────────────────────────────────────────────
@router.get("/kpis", response_model=CameraKPIs)
async def cameras_kpis(db: Session = Depends(get_db)):
    """Camera-fleet headline tile + per-floor breakdown.

    `online` matches the per-row `is_online` field on /cameras/ — a camera
    counts as online iff `last_seen_at` falls within the camera_monitor's
    threshold window (a single missed probe doesn't flip state). Disabled
    cameras are excluded from the online/offline numbers because they're
    intentionally off."""
    schema = _floor_schema()
    total = scalar(db, "SELECT COUNT(*) FROM cameras") or 0
    enabled = scalar(db, "SELECT COUNT(*) FROM cameras WHERE enabled = 1") or 0

    # WS-8 schema-compat: skip the by_floor aggregate when the column is missing.
    if schema["cameras_floor"]:
        by_floor_rows = rows(
            db,
            "SELECT COALESCE(floor, '(unspecified)') AS floor, COUNT(*) AS n "
            "FROM cameras GROUP BY floor",
        )
    else:
        by_floor_rows = []

    # Threshold-based "currently online" — same definition as the per-row
    # `is_online` so headline and list view always agree.
    threshold = int(settings.camera_monitor_interval_seconds * 2)
    if schema["cameras_last_seen_at"]:
        online = scalar(
            db,
            f"""
            SELECT COUNT(*) FROM cameras
            WHERE enabled = 1
              AND last_seen_at IS NOT NULL
              AND last_seen_at >= DATEADD(SECOND, -{threshold}, GETUTCDATE())
            """,
        ) or 0
    else:
        online = 0
    offline = max(enabled - online, 0)

    return CameraKPIs(
        total=total,
        enabled=enabled,
        disabled=total - enabled,
        online=online,
        offline=offline,
        by_floor={r["floor"]: r["n"] for r in by_floor_rows},
    )


# ── Paged list ────────────────────────────────────────────────────────────────
@router.get("/", response_model=PagedResponse[CameraItem])
async def list_cameras(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="matches camera_id, name, ip_address, notes"),
    floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?floor=` when both are sent.
    floor_id: Optional[int] = Query(None),
    enabled: Optional[bool] = Query(None),
    is_online: Optional[bool] = Query(None),
    last_status: Optional[str] = Query(None),
    role: Optional[str] = Query(None, description="entry|exit|floor_counting|slot_detection|other"),
    watches_floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?watches_floor=` when both are sent.
    watches_floor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    # Cache the schema probe once per request — drives every conditional below.
    schema = _floor_schema()
    clauses = ["1=1"]
    params: dict = {}

    if search:
        clauses.append(
            "(camera_id LIKE :search OR name LIKE :search "
            "OR ip_address LIKE :search OR notes LIKE :search)"
        )
        params["search"] = f"%{search}%"
    # WS-8.E: prefer `floor_id` (resolved from either side) for the new column;
    # the legacy string `floor =` filter is preserved when only `?floor=` is sent
    # so callers running against pre-WS-8 rows (where `floor_id` is NULL) still
    # match. Schema-compat: when the floor_id column doesn't exist yet, fall
    # back to the legacy string filter.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=None)
    if resolved_floor_id is not None and schema["cameras_floor_id"]:
        clauses.append("floor_id = :floor_id")
        params["floor_id"] = resolved_floor_id
    elif floor and schema["cameras_floor"]:
        clauses.append("floor = :floor")
        params["floor"] = floor
    if enabled is not None:
        clauses.append("enabled = :enabled")
        params["enabled"] = 1 if enabled else 0
    if last_status and schema["cameras_last_status"]:
        clauses.append("last_status = :last_status")
        params["last_status"] = last_status
    # G-5 fix: push role / watches_floor / is_online into SQL so total_count
    # matches the items returned. WS-8 compat: only emit role-derivation CASE
    # when the underlying watches_floor[_id] columns exist.
    if role is not None and (schema["cameras_watches_floor"] or schema["cameras_watches_floor_id"]):
        clauses.append(f"({_role_case_sql()}) = :role")
        params["role"] = role
    # WS-8.E: same dual-key pattern for watches_floor. Schema-compat: when
    # watches_floor_id column is missing, fall through to the string filter.
    resolved_watches_floor_id = resolve_floor_id(db, floor_id=watches_floor_id, floor_name=None)
    if resolved_watches_floor_id is not None and schema["cameras_watches_floor_id"]:
        clauses.append("watches_floor_id = :watches_floor_id")
        params["watches_floor_id"] = resolved_watches_floor_id
    elif watches_floor is not None and schema["cameras_watches_floor"]:
        clauses.append("watches_floor = :watches_floor")
        params["watches_floor"] = watches_floor
    if is_online is not None:
        clauses.append(f"({_is_online_case_sql()}) = :is_online")
        params["is_online"] = 1 if is_online else 0

    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM cameras WHERE {where}", params) or 0

    params["offset"] = (page - 1) * page_size
    params["page_size"] = page_size

    raw = rows(
        db,
        f"SELECT {_select_cols()} FROM cameras WHERE {where} "
        f"ORDER BY camera_id OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY",
        params,
    )
    items = [_row_to_item(r) for r in raw]

    return build_paged(items, total, page, page_size)


# ── Single show ───────────────────────────────────────────────────────────────
def _fetch_one_or_404(db: Session, camera_id: str) -> dict:
    raw = rows(
        db,
        f"SELECT {_select_cols()} FROM cameras WHERE camera_id = :camera_id",
        {"camera_id": camera_id},
    )
    if not raw:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return raw[0]


@router.get("/{camera_id}", response_model=CameraItem)
async def get_camera(camera_id: str, db: Session = Depends(get_db)):
    return _row_to_item(_fetch_one_or_404(db, camera_id))


# ── Create ────────────────────────────────────────────────────────────────────
@router.post("/", response_model=CameraItem, status_code=201)
async def create_camera(body: CameraCreate, db: Session = Depends(get_db)):
    existing = scalar(
        db, "SELECT COUNT(*) FROM cameras WHERE camera_id = :camera_id",
        {"camera_id": body.camera_id},
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"camera_id '{body.camera_id}' already exists")

    encrypted = cipher.encrypt(body.password) if body.password else None

    # WS-8.E: dual-write floor_id / watches_floor_id alongside the legacy name
    # columns. resolve_floor_id picks whichever side the caller provided.
    # Schema-compat: silently drop the integer columns from INSERT when they
    # don't exist yet — the gateway must accept the request body either way.
    schema = _floor_schema()
    resolved_floor_id = resolve_floor_id(db, floor_id=body.floor_id, floor_name=body.floor)
    resolved_watches_floor_id = resolve_floor_id(
        db, floor_id=body.watches_floor_id, floor_name=body.watches_floor,
    )

    cols = ["camera_id", "name"]
    vals = [":camera_id", ":name"]
    params: dict = {
        "camera_id": body.camera_id,
        "name": body.name,
        "ip_address": body.ip_address,
        "rtsp_port": body.rtsp_port,
        "rtsp_path": body.rtsp_path,
        "username": body.username,
        "password_encrypted": encrypted,
        "enabled": 1 if body.enabled else 0,
        "now": datetime.now(timezone.utc),
    }
    # WS-8 schema-compat: only INSERT into columns that actually exist in this
    # DB. Older deployments are missing some of: floor, floor_id,
    # watches_floor, watches_floor_id, notes.
    if schema["cameras_floor"]:
        cols.append("floor")
        vals.append(":floor")
        params["floor"] = body.floor
    if schema["cameras_floor_id"]:
        cols.append("floor_id")
        vals.append(":floor_id")
        params["floor_id"] = resolved_floor_id
    if schema["cameras_watches_floor"]:
        cols.append("watches_floor")
        vals.append(":watches_floor")
        params["watches_floor"] = body.watches_floor
    if schema["cameras_watches_floor_id"]:
        cols.append("watches_floor_id")
        vals.append(":watches_floor_id")
        params["watches_floor_id"] = resolved_watches_floor_id
    cols.extend(["ip_address", "rtsp_port", "rtsp_path",
                 "username", "password_encrypted", "enabled"])
    vals.extend([":ip_address", ":rtsp_port", ":rtsp_path",
                 ":username", ":password_encrypted", ":enabled"])
    if schema["cameras_notes"]:
        cols.append("notes")
        vals.append(":notes")
        params["notes"] = body.notes
    cols.extend(["created_at", "updated_at"])
    vals.extend([":now", ":now"])

    sql = f"INSERT INTO cameras ({', '.join(cols)}) VALUES ({', '.join(vals)})"
    db.execute(text(sql), params)
    db.commit()
    return _row_to_item(_fetch_one_or_404(db, body.camera_id))


# ── Update ────────────────────────────────────────────────────────────────────
# WS-8.E: floor_id / watches_floor / watches_floor_id added to dual-write the
# new schema fields when the caller updates the legacy or new floor keys.
_UPDATABLE_COLUMNS = {
    "name", "floor", "floor_id", "watches_floor", "watches_floor_id",
    "ip_address", "rtsp_port", "rtsp_path",
    "username", "enabled", "notes",
}


@router.put("/{camera_id}", response_model=CameraItem)
async def update_camera(camera_id: str, body: CameraUpdate, db: Session = Depends(get_db)):
    _fetch_one_or_404(db, camera_id)

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    sets: list[str] = []
    params: dict = {"camera_id": camera_id, "now": datetime.now(timezone.utc)}

    # WS-8.E: when the caller sends either side of a floor pair, dual-write the
    # other side too so the row stays consistent. Only resolve when the caller
    # actually included one of the floor fields (exclude_unset above kept them
    # out of `updates` if not provided).
    schema = _floor_schema()
    if ("floor" in updates) or ("floor_id" in updates):
        resolved = resolve_floor_id(
            db,
            floor_id=updates.get("floor_id"),
            floor_name=updates.get("floor"),
        )
        updates["floor_id"] = resolved
    if ("watches_floor" in updates) or ("watches_floor_id" in updates):
        resolved_w = resolve_floor_id(
            db,
            floor_id=updates.get("watches_floor_id"),
            floor_name=updates.get("watches_floor"),
        )
        updates["watches_floor_id"] = resolved_w

    # Schema-compat: silently drop columns from the UPDATE that don't exist
    # in the DB yet. Older deployments may be missing any of these.
    if not schema["cameras_floor"]:
        updates.pop("floor", None)
    if not schema["cameras_floor_id"]:
        updates.pop("floor_id", None)
    if not schema["cameras_watches_floor"]:
        updates.pop("watches_floor", None)
    if not schema["cameras_watches_floor_id"]:
        updates.pop("watches_floor_id", None)
    if not schema["cameras_notes"]:
        updates.pop("notes", None)

    for k, v in updates.items():
        if k == "password":
            continue
        if k not in _UPDATABLE_COLUMNS:
            continue
        if k == "enabled":
            params[k] = 1 if v else 0
        else:
            params[k] = v
        sets.append(f"{k} = :{k}")

    if "password" in updates:
        new_pw = updates["password"]
        if new_pw == "":
            raise HTTPException(status_code=400, detail="Password cannot be empty string")
        params["password_encrypted"] = cipher.encrypt(new_pw) if new_pw is not None else None
        sets.append("password_encrypted = :password_encrypted")

    if not sets:
        raise HTTPException(status_code=400, detail="No applicable fields to update")

    sets.append("updated_at = :now")
    sql = f"UPDATE cameras SET {', '.join(sets)} WHERE camera_id = :camera_id"
    db.execute(text(sql), params)
    db.commit()
    return _row_to_item(_fetch_one_or_404(db, camera_id))


# ── Delete ────────────────────────────────────────────────────────────────────
@router.delete("/{camera_id}", response_model=EntityActionResponse)
async def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM cameras WHERE camera_id = :camera_id"),
        {"camera_id": camera_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return EntityActionResponse(id=camera_id)


# ── Live check-now ────────────────────────────────────────────────────────────
@router.post("/{camera_id}/check-now", response_model=CameraCheckResult)
async def check_camera_now(
    camera_id: str,
    force: bool = Query(
        False,
        description=(
            "When false (default), reuse the cached camera_monitor result if it's "
            "newer than camera_monitor_interval_seconds — avoids hammering the "
            "camera and the gateway under 'refresh-all' UX. Pass true to bypass "
            "the cache and run a fresh TCP probe right now."
        ),
    ),
    db: Session = Depends(get_db),
):
    schema = _floor_schema()
    if not force and schema["cameras_last_check_at"] and schema["cameras_last_seen_at"]:
        # Return the cached values if last_check_at is recent enough. Skipped
        # entirely when the liveness columns don't exist in this DB yet
        # (pre-Phase-4A) — falls through to the fresh-probe path below.
        threshold_seconds = settings.camera_monitor_interval_seconds
        last_status_col = "last_status" if schema["cameras_last_status"] else "NULL AS last_status"
        cached = rows(db, f"""
            SELECT camera_id, last_check_at, last_seen_at, {last_status_col},
                   CASE WHEN last_seen_at IS NOT NULL
                        AND last_seen_at >= DATEADD(SECOND, -:threshold, GETUTCDATE())
                        THEN 1 ELSE 0 END AS is_online
            FROM cameras
            WHERE camera_id = :cid
              AND last_check_at IS NOT NULL
              AND last_check_at >= DATEADD(SECOND, -:threshold, GETUTCDATE())
        """, {"cid": camera_id, "threshold": int(threshold_seconds)})
        if cached:
            row = cached[0]
            return CameraCheckResult(
                camera_id=row["camera_id"],
                is_online=bool(row["is_online"]),
                last_status=row.get("last_status"),
                last_check_at=row.get("last_check_at"),
                last_seen_at=row.get("last_seen_at"),
            )

    # No cache hit (or force=true) — run a fresh probe.
    result = await check_one(camera_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return CameraCheckResult(**result)


# ── Single-camera plaintext credentials ───────────────────────────────────────
@router.get(
    "/{camera_id}/credentials",
    response_model=CameraCredentials,
    dependencies=[Depends(require_internal_token)],
)
async def get_camera_credentials(camera_id: str, request: Request, db: Session = Depends(get_db)):
    row = _fetch_one_or_404(db, camera_id)
    password: Optional[str] = None
    if row["password_encrypted"]:
        try:
            password = cipher.decrypt(row["password_encrypted"])
        except InvalidToken:
            raise HTTPException(
                status_code=409,
                detail="Credentials encrypted under a different key — re-enter the password to recover.",
            )
    rtsp_url = build_rtsp_url(
        ip=row["ip_address"],
        port=int(row["rtsp_port"]),
        path=row["rtsp_path"],
        user=row.get("username"),
        password=password,
    )
    caller = request.client.host if request.client else "unknown"
    print(f"[cameras] credentials read camera_id={camera_id} caller={caller}")
    return CameraCredentials(username=row.get("username"), password=password, rtsp_url=rtsp_url)


# ── Bulk decrypted list for upstream consumers (VideoAnalytics) ───────────────
@router.get(
    "/internal/all",
    response_model=CameraInternalListResponse,
    dependencies=[Depends(require_internal_token)],
)
async def list_all_with_credentials(
    request: Request,
    enabled: Optional[bool] = Query(True, description="filter by enabled flag; True only enabled, False only disabled"),
    include_disabled: bool = Query(False, description="if true, return both enabled and disabled cameras (overrides 'enabled')"),
    db: Session = Depends(get_db),
):
    """Unpaginated by design — upstream consumers need the full list in one shot."""
    if include_disabled:
        where, params = "1=1", {}
    elif enabled:
        where, params = "enabled = 1", {}
    else:
        where, params = "enabled = 0", {}

    raw = rows(db, f"SELECT {_select_cols()} FROM cameras WHERE {where} ORDER BY camera_id", params)

    cameras: list[dict] = []
    decryption_errors: list[dict] = []

    for row in raw:
        item = _row_to_item(row)
        password: Optional[str] = None
        if row["password_encrypted"]:
            try:
                password = cipher.decrypt(row["password_encrypted"])
            except InvalidToken:
                decryption_errors.append(
                    {"camera_id": row["camera_id"], "error": "decryption_failed"}
                )
                continue
        rtsp_url = build_rtsp_url(
            ip=row["ip_address"],
            port=int(row["rtsp_port"]),
            path=row["rtsp_path"],
            user=row.get("username"),
            password=password,
        )
        item["password"] = password
        item["rtsp_url"] = rtsp_url
        cameras.append(item)

    caller = request.client.host if request.client else "unknown"
    print(
        f"[cameras] internal/all fetched count={len(cameras)} "
        f"errors={len(decryption_errors)} caller={caller}"
    )

    return CameraInternalListResponse(
        total=len(cameras),
        fetched_at=datetime.now(timezone.utc),
        cameras=[CameraWithCredentials(**c) for c in cameras],
        decryption_errors=decryption_errors,
    )


# ── CSV export (no credentials) ───────────────────────────────────────────────
@router.get("/export/csv")
async def export_cameras_csv(
    search: Optional[str] = Query(None),
    floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?floor=` when both are sent.
    floor_id: Optional[int] = Query(None),
    enabled: Optional[bool] = Query(None),
    is_online: Optional[bool] = Query(None),
    last_status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    watches_floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?watches_floor=` when both are sent.
    watches_floor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """CSV export. Filter set matches `GET /cameras/` so the download mirrors
    the on-screen filtered view."""
    schema = _floor_schema()
    clauses = ["1=1"]
    params: dict = {}
    if search:
        clauses.append(
            "(camera_id LIKE :search OR name LIKE :search "
            "OR ip_address LIKE :search OR notes LIKE :search)"
        )
        params["search"] = f"%{search}%"
    # WS-8.E: prefer floor_id (already-resolved id) when provided. Schema-compat:
    # fall back to the legacy string filter when the column is missing.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=None)
    if resolved_floor_id is not None and schema["cameras_floor_id"]:
        clauses.append("floor_id = :floor_id")
        params["floor_id"] = resolved_floor_id
    elif floor:
        clauses.append("floor = :floor")
        params["floor"] = floor
    if enabled is not None:
        clauses.append("enabled = :enabled")
        params["enabled"] = 1 if enabled else 0
    if last_status and schema["cameras_last_status"]:
        clauses.append("last_status = :last_status")
        params["last_status"] = last_status
    if role is not None and (schema["cameras_watches_floor"] or schema["cameras_watches_floor_id"]):
        clauses.append(f"({_role_case_sql()}) = :role")
        params["role"] = role
    # WS-8.E: dual-key watches_floor filter, same pattern. Schema-compat: when
    # the integer column is missing, fall back to the legacy string filter.
    resolved_watches_floor_id = resolve_floor_id(db, floor_id=watches_floor_id, floor_name=None)
    if resolved_watches_floor_id is not None and schema["cameras_watches_floor_id"]:
        clauses.append("watches_floor_id = :watches_floor_id")
        params["watches_floor_id"] = resolved_watches_floor_id
    elif watches_floor is not None and schema["cameras_watches_floor"]:
        clauses.append("watches_floor = :watches_floor")
        params["watches_floor"] = watches_floor
    if is_online is not None and schema["cameras_last_seen_at"]:
        clauses.append(f"({_is_online_case_sql()}) = :is_online")
        params["is_online"] = 1 if is_online else 0

    where = " AND ".join(clauses)

    # Schema-compat: every conditional column emits `NULL AS <col>` when the
    # underlying column doesn't exist yet (pre-migration DB).
    def col_or_null(name: str, present: bool) -> str:
        return name if present else f"NULL AS {name}"
    cols_csv = ", ".join([
        "id", "camera_id", "name",
        col_or_null("floor",            schema["cameras_floor"]),
        col_or_null("floor_id",         schema["cameras_floor_id"]),
        col_or_null("watches_floor",    schema["cameras_watches_floor"]),
        col_or_null("watches_floor_id", schema["cameras_watches_floor_id"]),
        "ip_address", "rtsp_port", "rtsp_path",
        "username", "enabled",
        col_or_null("last_seen_at", schema["cameras_last_seen_at"]),
        col_or_null("last_status",  schema["cameras_last_status"]),
        "created_at", "updated_at",
    ])
    raw = rows(
        db,
        f"SELECT {cols_csv} FROM cameras WHERE {where} ORDER BY camera_id",
        params,
    )

    csv_rows = []
    for r in raw:
        # WS-8.E: pass DB-row values straight through; no more `'CAM-03' → 'B1'` magic.
        role, wf_name, wf_id, _ = _derive_role(
            r["camera_id"], r.get("floor"),
            r.get("floor_id"), r.get("watches_floor_id"), r.get("watches_floor"),
        )
        csv_rows.append({
            "id": r["id"],
            "camera_id": r["camera_id"],
            "name": r.get("name"),
            "floor": r.get("floor"),
            "floor_id": r.get("floor_id"),
            "role": role,
            "watches_floor": wf_name,
            "watches_floor_id": wf_id,
            "ip_address": r["ip_address"],
            "rtsp_port": r["rtsp_port"],
            "rtsp_path": r["rtsp_path"],
            "username": r.get("username"),
            "enabled": bool(r["enabled"]),
            "is_online": derive_is_online(r.get("last_seen_at")),
            "last_seen_at": r.get("last_seen_at"),
            "last_status": r.get("last_status"),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })

    headers = [
        "id", "camera_id", "name", "floor", "floor_id", "role",
        "watches_floor", "watches_floor_id",
        "ip_address", "rtsp_port",
        "rtsp_path", "username", "enabled", "is_online", "last_seen_at", "last_status",
        "created_at", "updated_at",
    ]
    return stream_csv(csv_rows, headers, filename="cameras.csv")
