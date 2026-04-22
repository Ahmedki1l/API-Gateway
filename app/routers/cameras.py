"""
Cameras configurator — CRUD for camera devices, with encrypted credentials and
liveness monitoring. Acts as the central registry consumed by the upstream
VideoAnalytics service via /cameras/internal/all.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
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
)
from app.services.camera_monitor import check_one, derive_is_online
from app.services.crypto import build_rtsp_url, cipher, mask_rtsp_url
from app.shared import build_paged, stream_csv


router = APIRouter(prefix="/cameras", tags=["Cameras"])


# ── Internal-token guard for credential-bearing endpoints ─────────────────────
def require_internal_token(
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
) -> None:
    if not settings.cameras_internal_token:
        raise HTTPException(status_code=503, detail="Internal token not configured")
    if x_internal_token != settings.cameras_internal_token:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Internal-Token")


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
    return {
        "id": row["id"],
        "camera_id": row["camera_id"],
        "name": row.get("name"),
        "floor": row.get("floor"),
        "zone_id": row.get("zone_id"),
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


_SELECT_COLS = (
    "id, camera_id, name, floor, zone_id, ip_address, rtsp_port, rtsp_path, "
    "username, password_encrypted, enabled, notes, last_check_at, last_seen_at, "
    "last_status, created_at, updated_at"
)


# ── KPIs ──────────────────────────────────────────────────────────────────────
@router.get("/kpis", response_model=CameraKPIs)
async def cameras_kpis(db: Session = Depends(get_db)):
    total = scalar(db, "SELECT COUNT(*) FROM cameras") or 0
    enabled = scalar(db, "SELECT COUNT(*) FROM cameras WHERE enabled = 1") or 0

    by_floor_rows = rows(
        db,
        "SELECT COALESCE(floor, '(unspecified)') AS floor, COUNT(*) AS n "
        "FROM cameras GROUP BY floor",
    )
    by_status_rows = rows(
        db,
        "SELECT COALESCE(last_status, 'unknown') AS status, COUNT(*) AS n "
        "FROM cameras GROUP BY last_status",
    )

    seen_rows = rows(db, "SELECT camera_id, last_seen_at FROM cameras WHERE enabled = 1")
    online = sum(1 for r in seen_rows if derive_is_online(r["last_seen_at"]))
    offline = max(enabled - online, 0)

    return CameraKPIs(
        total=total,
        enabled=enabled,
        disabled=total - enabled,
        online=online,
        offline=offline,
        by_floor={r["floor"]: r["n"] for r in by_floor_rows},
        by_status={r["status"]: r["n"] for r in by_status_rows},
    )


# ── Paged list ────────────────────────────────────────────────────────────────
@router.get("/")
async def list_cameras(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="matches camera_id, name, ip_address, notes"),
    floor: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    is_online: Optional[bool] = Query(None),
    last_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    clauses = ["1=1"]
    params: dict = {}

    if search:
        clauses.append(
            "(camera_id LIKE :search OR name LIKE :search "
            "OR ip_address LIKE :search OR notes LIKE :search)"
        )
        params["search"] = f"%{search}%"
    if floor:
        clauses.append("floor = :floor")
        params["floor"] = floor
    if enabled is not None:
        clauses.append("enabled = :enabled")
        params["enabled"] = 1 if enabled else 0
    if last_status:
        clauses.append("last_status = :last_status")
        params["last_status"] = last_status

    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM cameras WHERE {where}", params) or 0

    params["offset"] = (page - 1) * page_size
    params["page_size"] = page_size

    raw = rows(
        db,
        f"SELECT {_SELECT_COLS} FROM cameras WHERE {where} "
        f"ORDER BY camera_id OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY",
        params,
    )
    items = [_row_to_item(r) for r in raw]

    if is_online is not None:
        items = [it for it in items if it["is_online"] == is_online]

    return build_paged(items, total, page, page_size)


# ── Single show ───────────────────────────────────────────────────────────────
def _fetch_one_or_404(db: Session, camera_id: str) -> dict:
    raw = rows(
        db,
        f"SELECT {_SELECT_COLS} FROM cameras WHERE camera_id = :camera_id",
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

    db.execute(
        text(
            "INSERT INTO cameras "
            "(camera_id, name, floor, zone_id, ip_address, rtsp_port, rtsp_path, "
            " username, password_encrypted, enabled, notes, created_at, updated_at) "
            "VALUES (:camera_id, :name, :floor, :zone_id, :ip_address, :rtsp_port, "
            " :rtsp_path, :username, :password_encrypted, :enabled, :notes, "
            " :now, :now)"
        ),
        {
            "camera_id": body.camera_id,
            "name": body.name,
            "floor": body.floor,
            "zone_id": body.zone_id,
            "ip_address": body.ip_address,
            "rtsp_port": body.rtsp_port,
            "rtsp_path": body.rtsp_path,
            "username": body.username,
            "password_encrypted": encrypted,
            "enabled": 1 if body.enabled else 0,
            "notes": body.notes,
            "now": datetime.now(timezone.utc),
        },
    )
    db.commit()
    return _row_to_item(_fetch_one_or_404(db, body.camera_id))


# ── Update ────────────────────────────────────────────────────────────────────
_UPDATABLE_COLUMNS = {
    "name", "floor", "zone_id", "ip_address", "rtsp_port", "rtsp_path",
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
@router.delete("/{camera_id}")
async def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM cameras WHERE camera_id = :camera_id"),
        {"camera_id": camera_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    return {"success": True, "camera_id": camera_id}


# ── Live check-now ────────────────────────────────────────────────────────────
@router.post("/{camera_id}/check-now", response_model=CameraCheckResult)
async def check_camera_now(camera_id: str):
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

    raw = rows(db, f"SELECT {_SELECT_COLS} FROM cameras WHERE {where} ORDER BY camera_id", params)

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
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    clauses = ["1=1"]
    params: dict = {}
    if search:
        clauses.append(
            "(camera_id LIKE :search OR name LIKE :search "
            "OR ip_address LIKE :search OR notes LIKE :search)"
        )
        params["search"] = f"%{search}%"
    if floor:
        clauses.append("floor = :floor")
        params["floor"] = floor
    if enabled is not None:
        clauses.append("enabled = :enabled")
        params["enabled"] = 1 if enabled else 0

    where = " AND ".join(clauses)

    raw = rows(
        db,
        f"SELECT id, camera_id, name, floor, zone_id, ip_address, rtsp_port, rtsp_path, "
        f"username, enabled, last_seen_at, last_status, created_at, updated_at "
        f"FROM cameras WHERE {where} ORDER BY camera_id",
        params,
    )

    csv_rows = []
    for r in raw:
        csv_rows.append({
            "id": r["id"],
            "camera_id": r["camera_id"],
            "name": r.get("name"),
            "floor": r.get("floor"),
            "zone_id": r.get("zone_id"),
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
        "id", "camera_id", "name", "floor", "zone_id", "ip_address", "rtsp_port",
        "rtsp_path", "username", "enabled", "is_online", "last_seen_at", "last_status",
        "created_at", "updated_at",
    ]
    return stream_csv(csv_rows, headers, filename="cameras.csv")
