import os
from datetime import datetime, timezone
from pathlib import Path

# Point the application at a temporary SQLite database before importing it.
TEST_DB = Path(__file__).resolve().parent / "test_device_monitor.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


Base.metadata.create_all(bind=engine)
client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def device_payload(**overrides):
    data = {
        "id": "dev-test",
        "name": "Test Temperature Sensor",
        "type": "temperature-sensor",
        "status": "active",
        "unit": "°C",
        "normal_min": 2,
        "normal_max": 8,
    }
    data.update(overrides)
    return data


def create_test_device(**overrides):
    response = client.post("/api/devices", json=device_payload(**overrides))
    assert response.status_code == 201
    return response.json()


def test_device_crud():
    created = create_test_device()
    assert created["id"] == "dev-test"

    listed = client.get("/api/devices")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        "/api/devices/dev-test",
        json={"name": "Updated Sensor"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Sensor"

    deleted = client.delete("/api/devices/dev-test")
    assert deleted.status_code == 204

    missing = client.get("/api/devices/dev-test")
    assert missing.status_code == 404


def test_normal_reading_does_not_create_alert():
    create_test_device()

    response = client.post(
        "/api/devices/dev-test/readings",
        json={"value": 5, "unit": "°C"},
    )
    assert response.status_code == 201

    alerts = client.get("/api/alerts?resolved=false")
    assert alerts.status_code == 200
    assert alerts.json() == []


def test_out_of_range_reading_creates_alert():
    create_test_device()

    response = client.post(
        "/api/devices/dev-test/readings",
        json={"value": 12, "unit": "°C"},
    )
    assert response.status_code == 201

    alerts = client.get("/api/alerts?resolved=false")
    data = alerts.json()
    assert len(data) == 1
    assert data[0]["device_id"] == "dev-test"
    assert "above maximum" in data[0]["message"]


def test_alert_can_be_resolved():
    create_test_device()

    client.post(
        "/api/devices/dev-test/readings",
        json={"value": 0.5, "unit": "°C"},
    )

    alerts = client.get("/api/alerts?resolved=false").json()
    alert_id = alerts[0]["id"]

    response = client.patch(f"/api/alerts/{alert_id}/resolve")
    assert response.status_code == 200
    assert response.json()["resolved"] is True

    remaining = client.get("/api/alerts?resolved=false").json()
    assert remaining == []


def test_inactive_device_rejects_readings():
    create_test_device(
        id="inactive-1",
        name="Inactive Sensor",
        status="inactive",
        normal_min=None,
        normal_max=None,
    )

    response = client.post(
        "/api/devices/inactive-1/readings",
        json={"value": 5, "unit": "°C"},
    )
    assert response.status_code == 409


def test_readings_can_be_filtered_by_time_range():
    create_test_device()

    timestamps = [
        "2026-08-10T08:00:00Z",
        "2026-08-10T08:15:00Z",
        "2026-08-10T08:30:00Z",
    ]

    for i, timestamp in enumerate(timestamps):
        response = client.post(
            "/api/devices/dev-test/readings",
            json={
                "value": 4 + i * 0.1,
                "unit": "°C",
                "timestamp": timestamp,
            },
        )
        assert response.status_code == 201

    response = client.get(
        "/api/devices/dev-test/readings",
        params={
            "start": "2026-08-10T08:10:00Z",
            "end": "2026-08-10T08:25:00Z",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["value"] == 4.1


def test_wrong_unit_is_rejected():
    create_test_device()

    response = client.post(
        "/api/devices/dev-test/readings",
        json={"value": 5, "unit": "bar"},
    )
    assert response.status_code == 422
