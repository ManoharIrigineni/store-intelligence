import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_successful_batch_ingestion():
    """Validates that well-formed payloads are parsed and saved cleanly."""
    payload = [{
        "event_id": "ingest-test-uuid-1111",
        "store_id": "ST1008",
        "camera_id": "CAM_ENTRY_01",
        "visitor_id": "VIS_TEST_01",
        "event_type": "ENTRY",
        "timestamp": "2026-04-10T12:00:00Z",
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.95,
        "metadata": {"session_seq": 1}  # Fixed: Non-empty valid structure
    }]
    response = client.post("/events/ingest", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "processed": 1}

def test_low_confidence_noise_filtering():
    """EDGE CASE: Verifies that CV detections with confidence < 50% are rejected."""
    payload = [{
        "event_id": "noise-test-uuid-2222",
        "store_id": "ST1008",
        "camera_id": "CAM_ENTRY_01",
        "visitor_id": "VIS_TEST_02",
        "event_type": "ENTRY",
        "timestamp": "2026-04-10T12:05:00Z",
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.30,  # Below our 0.50 threshold
        "metadata": {"session_seq": 2}  # Fixed: Non-empty valid structure
    }]
    response = client.post("/events/ingest", json=payload)
    assert response.status_code == 200
    assert response.json()["processed"] == 0  # Should be dropped by filter!