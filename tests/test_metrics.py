import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_metrics_endpoint_structure():
    """Verifies the metrics endpoint returns the expected JSON schema structure."""
    response = client.get("/stores/ST1008/metrics")
    assert response.status_code == 200
    data = response.json()
    # Verified against your live root-level flat JSON output keys:
    assert "unique_visitors" in data
    assert "queue_depth" in data
    assert "conversion_rate" in data

def test_invalid_store_fallback():
    """Ensures an unknown store ID handles fallback gracefully instead of crashing."""
    response = client.get("/stores/UNKNOWN_STORE/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["unique_visitors"] == 0