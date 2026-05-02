from app.config import settings

_LOCAL_PREFIX = "detection_images/"


def resolve_snapshot_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value

    # Standardize slashes and strip leading slash
    val = value.replace("\\", "/").lstrip("/")

    # Get bases and strip trailing slashes for safety
    base1 = (settings.snapshots_public_base or "").rstrip("/")
    base2 = (settings.system2_snapshots_public_base or "").rstrip("/")

    # ── SYSTEM 1 (PMS-AI) ──
    if val.startswith("detection_images/"):
        rel = val[len("detection_images/"):]
        return f"{base1}/snapshots/{rel}"

    # ── SYSTEM 2 (VideoAnalytics) ──
    if val.startswith("vehicle_images/"):
        rel = val[len("vehicle_images/"):]
        return f"{base2}/snapshots/{rel}"

    # Fallback (preserves legacy behavior)
    rel = val[len(_LOCAL_PREFIX):] if val.startswith(_LOCAL_PREFIX) else val
    return f"{base1}/snapshots/{rel}"
