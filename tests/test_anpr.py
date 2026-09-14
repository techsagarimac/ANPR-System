"""Unit and API tests that do not require GPU models or a camera."""

from __future__ import annotations

import os

os.environ["ANPR_DISABLE_ENGINE"] = "true"

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.tracker import DuplicateSuppressor, VehicleTracker
from backend.services.validator import normalize_ocr_text, validate_plate
from backend.utils.geometry import BBox


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_normalize_and_standard_plate():
    result = validate_plate("mh 12 ab 1234")
    assert result.normalized == "MH12AB1234"
    assert result.is_valid_format is True


def test_bharat_series_plate():
    result = validate_plate("22BH1234AA")
    assert result.is_valid_format is True
    assert result.normalized == "22BH1234AA"


def test_positional_ocr_fix():
    result = validate_plate("MH12AB12B4")
    assert result.normalized == "MH12AB1284"
    assert result.is_valid_format is True


def test_reject_malformed():
    result = validate_plate("###")
    assert result.is_valid_format is False
    assert result.quality_score < 0.5


def test_normalize_strips_invalid_chars():
    assert normalize_ocr_text(" mh-12 ab 1234 ") == "MH12AB1234"


def test_tracker_assigns_stable_ids():
    class Det:
        def __init__(self, bbox, vehicle_type="car", confidence=0.9):
            self.bbox = bbox
            self.vehicle_type = vehicle_type
            self.confidence = confidence

    tracker = VehicleTracker()
    first = tracker.update([Det(BBox(10, 10, 110, 80))])
    second = tracker.update([Det(BBox(12, 12, 112, 82))])
    assert first[0].track.track_id == second[0].track.track_id


def test_duplicate_cooldown():
    suppressor = DuplicateSuppressor(cooldown_seconds=10)
    assert suppressor.should_save("MH12AB1234", 1) is True
    assert suppressor.should_save("MH12AB1234", 1) is False


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["engine"] == "stopped"


def test_stats_endpoint(client):
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert "total_detections" in body
    assert "today_detections" in body
    assert "unique_plates" in body


def test_create_list_search_and_export(client):
    payload = {
        "plate_number": "MH12AB1234",
        "vehicle_type": "car",
        "vehicle_confidence": 0.91,
        "plate_confidence": 0.88,
        "ocr_confidence": 0.93,
        "camera_id": "cam-01",
        "direction": "unknown",
        "is_valid_format": True,
    }
    created = client.post("/api/detection", json=payload)
    assert created.status_code == 201
    detection_id = created.json()["id"]

    listed = client.get("/api/vehicles")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    detail = client.get(f"/api/vehicles/{detection_id}")
    assert detail.status_code == 200
    assert detail.json()["plate_number"] == "MH12AB1234"

    search = client.get("/api/search", params={"plate_number": "MH12"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1

    missing = client.get("/api/vehicles/999999")
    assert missing.status_code == 404

    export = client.get("/api/export/csv")
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert b"MH12AB1234" in export.content


def test_invalid_date_filter(client):
    response = client.get("/api/search", params={"date": "not-a-date"})
    assert response.status_code == 400
