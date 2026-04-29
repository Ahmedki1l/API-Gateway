from app.config import settings

_LOCAL_PREFIX = "detection_images/"


def resolve_snapshot_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    stripped = value.lstrip("/")
    rel = stripped[len(_LOCAL_PREFIX):] if stripped.startswith(_LOCAL_PREFIX) else stripped
    return f"{settings.snapshots_public_base}/snapshots/{rel}"
