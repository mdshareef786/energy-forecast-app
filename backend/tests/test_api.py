import os
import sys
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///./test_energy.db"

from app.main import app  # noqa: E402
from app.db.database import Base, get_db, engine, SessionLocal  # noqa: E402
from app import models as _models  # noqa: E402,F401

TestingSessionLocal = SessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    engine.dispose()
    if os.path.exists("./test_energy.db"):
        os.remove("./test_energy.db")
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    if os.path.exists("./test_energy.db"):
        os.remove("./test_energy.db")


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_token(client):
    client.post("/api/auth/register", json={
        "full_name": "Admin", "email": "admin@test.com", "password": "pass1234", "role": "admin"
    })
    resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "pass1234"})
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def building_and_device(client, auth_headers):
    b = client.post("/api/buildings", json={"name": "Test Building", "location": "Test City"}, headers=auth_headers)
    building_id = b.json()["id"]
    d = client.post("/api/devices", json={
        "name": "Test Device", "device_type": "HVAC", "building_id": building_id, "rated_capacity_kw": 20
    }, headers=auth_headers)
    device_id = d.json()["id"]
    return building_id, device_id


@pytest.fixture(scope="session")
def seeded_readings(building_and_device):
    _, device_id = building_and_device
    session = TestingSessionLocal()
    from app.models.reading import EnergyReading
    import random, math
    start = datetime.utcnow() - timedelta(days=10)
    for h in range(10 * 24):
        ts = start + timedelta(hours=h)
        val = max(0, 20 + 10 * math.sin(h / 24 * 2 * math.pi) + random.gauss(0, 1))
        if h == 100:
            val += 100  # inject one clear anomaly
        session.add(EnergyReading(device_id=device_id, timestamp=ts, energy_kwh=val, temperature_c=25.0))
    session.commit()
    session.close()
    return device_id


class TestAuth:
    def test_register_and_login(self, client):
        resp = client.post("/api/auth/register", json={
            "full_name": "Analyst", "email": "analyst@test.com", "password": "pass1234", "role": "analyst"
        })
        assert resp.status_code == 201

        resp = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass1234"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password_fails(self, client):
        resp = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_duplicate_registration_fails(self, client):
        resp = client.post("/api/auth/register", json={
            "full_name": "Dup", "email": "analyst@test.com", "password": "pass1234", "role": "analyst"
        })
        assert resp.status_code == 400

    def test_unauthenticated_request_rejected(self, client):
        resp = client.get("/api/buildings")
        assert resp.status_code == 401


class TestRBAC:
    def test_viewer_cannot_create_building(self, client):
        client.post("/api/auth/register", json={
            "full_name": "Viewer", "email": "viewer@test.com", "password": "pass1234", "role": "viewer"
        })
        login = client.post("/api/auth/login", json={"email": "viewer@test.com", "password": "pass1234"})
        token = login.json()["access_token"]
        resp = client.post("/api/buildings", json={"name": "Nope"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_admin_can_create_building(self, client, auth_headers):
        resp = client.post("/api/buildings", json={"name": "Admin Building"}, headers=auth_headers)
        assert resp.status_code == 200


class TestAssets:
    def test_create_device_requires_valid_building(self, client, auth_headers):
        resp = client.post("/api/devices", json={
            "name": "Ghost Device", "building_id": 999999
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_building_and_device_fixture_created(self, building_and_device):
        building_id, device_id = building_and_device
        assert building_id > 0
        assert device_id > 0


class TestDatasetUpload:
    def test_missing_columns_rejected(self, client, auth_headers):
        csv_content = b"timestamp,foo\n2024-01-01T00:00:00,1\n"
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("bad.csv", csv_content, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "Missing required columns" in resp.json()["detail"]

    def test_non_csv_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("bad.txt", b"not a csv", "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_valid_csv_with_unknown_device_reports_skip(self, client, auth_headers):
        csv_content = b"timestamp,device_id,energy_kwh\n2024-01-01T00:00:00,999999,5.0\n"
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("ok.csv", csv_content, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "unknown device_id" in resp.json()["notes"]

    def test_non_numeric_device_id_does_not_crash(self, client, auth_headers):
        """Regression test: a device_id like 'HVAC_1' used to raise an unhandled
        ValueError (int() on a non-numeric string) and return 500."""
        csv_content = b"timestamp,device_id,energy_kwh\n2024-01-01T00:00:00,NOT_A_REAL_DEVICE,5.0\n"
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("names.csv", csv_content, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["rows_inserted"] == 0
        assert "unknown device_id" in resp.json()["notes"]

    def test_device_id_matches_by_name(self, client, auth_headers, building_and_device):
        building_id, device_id = building_and_device
        device_resp = client.get(f"/api/devices?building_id={building_id}", headers=auth_headers)
        device_name = next(d["name"] for d in device_resp.json() if d["id"] == device_id)

        csv_content = f"timestamp,device_id,energy_kwh\n2024-01-01T00:00:00,{device_name},7.5\n".encode()
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("byname.csv", csv_content, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["rows_inserted"] == 1

    def test_negative_energy_rows_dropped(self, client, auth_headers, building_and_device):
        _, device_id = building_and_device
        csv_content = f"timestamp,device_id,energy_kwh\n2024-01-01T00:00:00,{device_id},-5.0\n2024-01-01T01:00:00,{device_id},5.0\n".encode()
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("neg.csv", csv_content, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["rows_inserted"] == 1


class TestForecasting:
    def test_forecast_requires_readings(self, client, auth_headers, building_and_device):
        building_id, device_id = building_and_device
        d = client.post("/api/devices", json={
            "name": "Empty Device", "building_id": building_id
        }, headers=auth_headers)
        empty_device_id = d.json()["id"]
        resp = client.post("/api/forecasts/generate", json={
            "device_id": empty_device_id, "horizon": "24h", "model_type": "regression"
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_forecast_generation_and_retrieval(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        resp = client.post("/api/forecasts/generate", json={
            "device_id": device_id, "horizon": "24h", "model_type": "regression"
        }, headers=auth_headers)
        assert resp.status_code == 202

        resp = client.get(f"/api/forecasts/latest/{device_id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["predictions"]) == 24
        assert all(p["predicted"] >= 0 for p in body["predictions"])

    def test_arima_forecast_generation(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        resp = client.post("/api/forecasts/generate", json={
            "device_id": device_id, "horizon": "24h", "model_type": "arima"
        }, headers=auth_headers)
        assert resp.status_code == 202

        resp = client.get(f"/api/forecasts/latest/{device_id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["model_type"] == "arima"
        assert len(body["predictions"]) == 24

    def test_retrain_all_requires_admin(self, client, auth_headers):
        # analyst can't trigger retraining (admin-only)
        client.post("/api/auth/register", json={
            "full_name": "Analyst2", "email": "analyst2@test.com", "password": "pass1234", "role": "analyst"
        })
        login = client.post("/api/auth/login", json={"email": "analyst2@test.com", "password": "pass1234"})
        token = login.json()["access_token"]
        resp = client.post("/api/forecasts/retrain-all", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_retrain_all_triggers_for_admin(self, client, auth_headers, seeded_readings):
        resp = client.post("/api/forecasts/retrain-all", headers=auth_headers)
        assert resp.status_code == 202


class TestAlerts:
    def test_high_severity_anomaly_creates_alert(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        client.post(f"/api/anomalies/detect/{device_id}?method=z_score", headers=auth_headers)
        resp = client.get("/api/alerts", headers=auth_headers)
        assert resp.status_code == 200
        # at least one alert should reference this device (injected spike is severity=high)
        assert any(a["device_id"] == device_id for a in resp.json())

    def test_unread_count_and_mark_read(self, client, auth_headers):
        resp = client.get("/api/alerts/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        count_before = resp.json()["count"]
        assert count_before >= 0

        resp = client.post("/api/alerts/read-all", headers=auth_headers)
        assert resp.status_code == 200

        resp = client.get("/api/alerts/unread-count", headers=auth_headers)
        assert resp.json()["count"] == 0


class TestReports:
    def test_csv_export_requires_readings(self, client, auth_headers, building_and_device):
        building_id, _ = building_and_device
        d = client.post("/api/devices", json={"name": "No Data Device", "building_id": building_id}, headers=auth_headers)
        empty_device_id = d.json()["id"]
        resp = client.get(f"/api/reports/device/{empty_device_id}/csv", headers=auth_headers)
        assert resp.status_code == 400

    def test_csv_export_success(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        resp = client.get(f"/api/reports/device/{device_id}/csv", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert b"timestamp,energy_kwh,temperature_c" in resp.content

    def test_pdf_export_success(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        resp = client.get(f"/api/reports/device/{device_id}/pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"


class TestAnomalyAndOptimization:
    def test_zscore_anomaly_detection_finds_injected_spike(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        resp = client.post(f"/api/anomalies/detect/{device_id}?method=z_score", headers=auth_headers)
        assert resp.status_code == 200
        anomalies = resp.json()
        assert len(anomalies) >= 1
        assert any(a["energy_kwh"] > 90 for a in anomalies)

    def test_peak_analysis_returns_threshold(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        resp = client.get(f"/api/anomalies/peaks/{device_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["threshold_kwh"] is not None

    def test_recommendations_generated(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        resp = client.post(f"/api/recommendations/generate/{device_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestSimulation:
    def test_simulation_requires_readings(self, client, auth_headers):
        b = client.post("/api/buildings", json={"name": "Empty Building"}, headers=auth_headers)
        building_id = b.json()["id"]
        resp = client.post("/api/simulations/run", json={
            "building_id": building_id, "name": "test", "scenario_type": "peak_reduction",
            "parameters": {"peak_reduction_percent": 10}
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_shutdown_scenario_reduces_consumption(self, client, auth_headers, building_and_device, seeded_readings):
        building_id, _ = building_and_device
        resp = client.post("/api/simulations/run", json={
            "building_id": building_id, "name": "Shutdown test", "scenario_type": "shutdown",
            "parameters": {"hours_shutdown_per_day": 6, "device_share_of_load": 0.3}
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["projected_kwh"] < body["baseline_kwh"]
        assert body["savings_kwh"] > 0

    def test_unknown_scenario_type_rejected(self, client, auth_headers, building_and_device):
        building_id, _ = building_and_device
        resp = client.post("/api/simulations/run", json={
            "building_id": building_id, "name": "Bad", "scenario_type": "not_a_real_scenario",
            "parameters": {}
        }, headers=auth_headers)
        assert resp.status_code == 400


class TestAnalytics:
    def test_building_summary(self, client, auth_headers, building_and_device):
        building_id, _ = building_and_device
        resp = client.get(f"/api/analytics/building/{building_id}/summary", headers=auth_headers)
        assert resp.status_code == 200
        assert "total_energy_kwh" in resp.json()

    def test_device_history(self, client, auth_headers, seeded_readings):
        device_id = seeded_readings
        resp = client.get(f"/api/analytics/device/{device_id}/history?days=30", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["readings"]) > 0
