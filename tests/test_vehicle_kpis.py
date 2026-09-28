"""GET /vehicles/kpis — currently_parked and floors_count.

Runs against the database in .env and only reads it. Both numbers must match
/dashboard/kpis, which shows the same figures on another screen.

    pytest tests/test_vehicle_kpis.py -v -p no:cacheprovider
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_new_fields_match_the_dashboard(client):
    v = client.get("/vehicles/kpis")
    d = client.get("/dashboard/kpis")
    assert v.status_code == 200, v.text
    assert d.status_code == 200, d.text
    v, d = v.json(), d.json()
    assert v["currently_parked"] == d["parked_vehicles"]
    assert v["floors_count"] == d["floors_count"]


def test_existing_fields_unchanged(client):
    k = client.get("/vehicles/kpis").json()
    assert k["total_vehicles"] == k["registered"] + k["unregistered"] + k["employee"]
