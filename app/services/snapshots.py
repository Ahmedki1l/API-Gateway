from urllib.parse import urlparse

from app.config import settings

_LOCAL_PREFIX = "detection_images/"


def resolve_snapshot_url(value: str | None) -> str | None:
    """Always return a full gateway URL of the form
    `{snapshots_public_base}/snapshots/<file>`.

    Accepts:
      - a full http(s):// URL (e.g. legacy DigitalOcean Spaces values) — the
        host is discarded and only the path is kept
      - a local-relative path like `detection_images/foo.jpg` — `detection_images/`
        is stripped, the rest is appended
      - a bare filename — passed through

    The gateway's `/snapshots` static mount (see `app/main.py`) serves the
    actual bytes from `snapshots_local_dir`, which in deployed setups is a
    shared volume from PMS-AI's `detection_images/`.
    """
    if not value:
        return None
    path = urlparse(value).path if value.startswith(("http://", "https://")) else value
    stripped = path.lstrip("/")
    rel = stripped[len(_LOCAL_PREFIX):] if stripped.startswith(_LOCAL_PREFIX) else stripped
    return f"{settings.snapshots_public_base.rstrip('/')}/snapshots/{rel}"
