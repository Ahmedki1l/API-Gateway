"""PATCH /alerts/{id}/resolve — the error tells "not found" and "already
resolved" apart.

Runs against the database in .env. Inserts one marker alert and deletes it
afterwards.

    pytest tests/test_alert_resolve.py -v -p no:cacheprovider
"""
import os
import sys

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, scalar  # noqa: E402

PLATE = "ZZRS-0001"     # marker; no real plate starts with ZZRS


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture
def alert_id():
    db = SessionLocal()
    db.execute(text("""
        INSERT INTO alerts (alert_type, severity, description, is_resolved, triggered_at,
                            plate_number, camera_id, is_test)
        VALUES ('overstay', 'critical', 'pytest resolve marker', 0, '2026-08-04T12:00:00',
                :p, 'pytest', 0)
    """), {"p": PLATE})
    db.commit()
    aid = scalar(db, "SELECT MAX(id) FROM alerts WHERE plate_number = :p", {"p": PLATE})
    yield aid
    db.execute(text("DELETE FROM alerts WHERE plate_number = :p"), {"p": PLATE})
    db.commit()
    db.close()


def test_resolve_open_alert(client, alert_id):
    r = client.patch(f"/alerts/{alert_id}/resolve")
    assert r.status_code == 200, r.text
    assert client.get(f"/alerts/{alert_id}").json()["is_resolved"] is True


def test_resolving_twice_is_409_not_404(client, alert_id):
    assert client.patch(f"/alerts/{alert_id}/resolve").status_code == 200
    r = client.patch(f"/alerts/{alert_id}/resolve")
    assert r.status_code == 409
    assert r.json()["detail"].startswith("Alert was already resolved")


def test_unknown_alert_is_404(client):
    r = client.patch("/alerts/999999999/resolve")
    assert r.status_code == 404
    assert r.json()["detail"] == "Alert not found"
