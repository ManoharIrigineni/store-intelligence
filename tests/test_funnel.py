import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_funnel_endpoint_progression():
    """Verifies that the funnel returns the mandatory structural stages sequentially."""
    response = client.get("/stores/ST1008/funnel")
    assert response.status_code == 200
    data = response.json()
    assert data["store_id"] == "ST1008"
    assert "stages" in data  # Aligned with live return schema
    assert data["stages"] == ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"]
    assert "counts" in data