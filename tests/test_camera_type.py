"""cameras.camera_type (migrator 0014): create / edit / get / list filter,
and GET /cameras/types — the Camera Type Distribution donut.

Runs against the database in .env. Creates cameras with marker ids through the
API and deletes them afterwards.

    pytest tests/test_camera_type.py -v -p no:cacheprovider
"""
import os
import sys

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal  # noqa: E402
from app.routers._helpers import _floor_schema  # noqa: E402

MARK = "ZZ-CAMTYPE-"
TYPES = ["fixed", "dome", "ptz", "anpr", "other"]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def url():
    from app.routers.cameras import prefix
    return prefix


@pytest.fixture(scope="module", autouse=True)
def needs_column_and_cleanup():
    _floor_schema.cache_clear()
    if not _floor_schema()["cameras_camera_type"]:
        pytest.skip("cameras.camera_type missing: run migrator 0014")
    yield
    db = SessionLocal()
    db.execute(text("DELETE FROM cameras WHERE camera_id LIKE :m"), {"m": MARK + "%"})
    db.commit()
    db.close()


def _create(client, url, suffix, **extra):
    body = {"camera_id": MARK + suffix, "name": "pytest", "ip_address": "10.255.255.1", **extra}
    r = client.post(url + "/", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _types(client, url):
    r = client.get(url + "/types")
    assert r.status_code == 200, r.text
    return r.json()


class TestCrud:
    def test_create_defaults_to_fixed(self, client, url):
        assert _create(client, url, "1")["camera_type"] == "fixed"

    def test_create_with_type_and_get(self, client, url):
        _create(client, url, "2", camera_type="dome")
        r = client.get(f"{url}/{MARK}2")
        assert r.json()["camera_type"] == "dome"

    def test_edit_type(self, client, url):
        _create(client, url, "3", camera_type="dome")
        r = client.put(f"{url}/{MARK}3", json={"camera_type": "ptz"})
        assert r.status_code == 200 and r.json()["camera_type"] == "ptz"

    def test_edit_other_field_keeps_type(self, client, url):
        _create(client, url, "4", camera_type="anpr")
        r = client.put(f"{url}/{MARK}4", json={"name": "renamed"})
        assert r.json()["camera_type"] == "anpr"

    def test_unknown_type_is_422(self, client, url):
        r = client.post(url + "/", json={"camera_id": MARK + "5", "ip_address": "10.255.255.1",
                                         "camera_type": "bullet"})
        assert r.status_code == 422
        _create(client, url, "6")
        assert client.put(f"{url}/{MARK}6", json={"camera_type": "bullet"}).status_code == 422

    def test_null_type_on_edit_is_400(self, client, url):
        _create(client, url, "7")
        assert client.put(f"{url}/{MARK}7", json={"camera_type": None}).status_code == 400

    def test_list_filter(self, client, url):
        _create(client, url, "8", camera_type="ptz")
        r = client.get(url + "/", params={"camera_type": "ptz", "search": MARK, "page_size": 100})
        ids = {c["camera_id"] for c in r.json()["items"]}
        assert MARK + "8" in ids
        assert all(c["camera_type"] == "ptz" for c in r.json()["items"])


class TestDistribution:
    def test_shape_all_five_in_order(self, client, url):
        body = _types(client, url)
        assert [i["camera_type"] for i in body["items"]] == TYPES
        assert body["total"] == sum(i["count"] for i in body["items"])

    def test_total_is_every_camera(self, client, url):
        db = SessionLocal()
        n = db.execute(text("SELECT COUNT(*) FROM cameras")).scalar()
        db.close()
        assert _types(client, url)["total"] == n

    def test_new_camera_moves_its_slice(self, client, url):
        before = {i["camera_type"]: i["count"] for i in _types(client, url)["items"]}
        _create(client, url, "9", camera_type="dome")
        after = {i["camera_type"]: i["count"] for i in _types(client, url)["items"]}
        assert after["dome"] == before["dome"] + 1
        assert {t: after[t] for t in TYPES if t != "dome"} == {t: before[t] for t in TYPES if t != "dome"}

    def test_pct(self, client, url):
        body = _types(client, url)
        for i in body["items"]:
            assert i["pct"] == round(i["count"] / body["total"] * 100, 1)

    def test_value_outside_the_five_counts_as_other(self, client, url):
        _create(client, url, "10")
        before = {i["camera_type"]: i["count"] for i in _types(client, url)["items"]}
        db = SessionLocal()
        db.execute(text("UPDATE cameras SET camera_type = 'bullet' WHERE camera_id = :c"),
                   {"c": MARK + "10"})
        db.commit()
        db.close()
        after = {i["camera_type"]: i["count"] for i in _types(client, url)["items"]}
        assert after["other"] == before["other"] + 1
        assert after["fixed"] == before["fixed"] - 1

    def test_without_the_column_everything_is_fixed(self, client, url, monkeypatch):
        from app.routers import cameras
        real = _floor_schema()
        monkeypatch.setattr(cameras, "_floor_schema", lambda: {**real, "cameras_camera_type": False})
        body = _types(client, url)
        counts = {i["camera_type"]: i["count"] for i in body["items"]}
        assert counts["fixed"] == body["total"] and body["total"] > 0
        r = client.get(url + "/", params={"page_size": 1})
        assert r.status_code == 200 and r.json()["items"][0]["camera_type"] == "fixed"
