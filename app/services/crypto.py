"""
Symmetric encryption + RTSP URL builder for camera credentials.

The cipher is instantiated at import time from settings.cameras_encryption_key.
A missing or malformed key fails the gateway's boot — that's intentional.
"""
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class CredentialCipher:
    def __init__(self, key: str):
        # Fernet validates the key shape on construction; bad key → ValueError at import.
        self._fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()


cipher = CredentialCipher(settings.cameras_encryption_key)


def build_rtsp_url(*, ip: str, port: int, path: str, user: str | None, password: str | None) -> str:
    """Assemble an RTSP URL with percent-encoded credentials.

    Reserved characters (`@`, `:`, `/`, `#`, `?`) in user/password are escaped so they
    don't corrupt the URL parser on the receiving end.
    """
    auth = ""
    if user:
        u = quote(user, safe="")
        if password:
            p = quote(password, safe="")
            auth = f"{u}:{p}@"
        else:
            auth = f"{u}@"
    safe_path = path if path.startswith("/") else f"/{path}"
    return f"rtsp://{auth}{ip}:{port}{safe_path}"


def mask_rtsp_url(*, ip: str, port: int, path: str, user: str | None, has_password: bool) -> str:
    """Same shape as build_rtsp_url but with the password replaced by ***.

    Used by list/show endpoints so the JSON shows the URL shape without leaking secrets.
    """
    auth = ""
    if user:
        u = quote(user, safe="")
        auth = f"{u}:***@" if has_password else f"{u}@"
    safe_path = path if path.startswith("/") else f"/{path}"
    return f"rtsp://{auth}{ip}:{port}{safe_path}"


__all__ = ["cipher", "CredentialCipher", "InvalidToken", "build_rtsp_url", "mask_rtsp_url"]
