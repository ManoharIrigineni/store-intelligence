from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import datetime

app = FastAPI(title="Apex Retail Store Intelligence API")
MOCK_EVENTS_DB = {}

class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: int

class StoreEvent(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: datetime.datetime
    zone_id: Optional[str] = None
    dwell_ms: int
    is_staff: bool
    confidence: float
    metadata: EventMetadata

@app.post("/events/ingest", status_code=status.HTTP_200_OK)
async def ingest_events(events: List[StoreEvent]):
    if len(events) > 500:
        raise HTTPException(status_code=400, detail="Batch size exceeds 500.")
    for event in events:
        MOCK_EVENTS_DB[event.event_id] = event
    return {"status": "success", "processed": len(events)}

@app.get("/stores/{id}/metrics")
async def get_store_metrics(id: str):
    return {
        "store_id": id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "metrics": {"unique_visitors": 0, "conversion_rate": 0.0, "avg_dwell_per_zone": {}, "queue_depth": 0, "abandonment_rate": 0.0},
        "data_confidence": False
    }

@app.get("/stores/{id}/funnel")
async def get_store_funnel(id: str):
    return {"store_id": id, "funnel": ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"], "counts": {}, "drop_off_percentage": {}}

@app.get("/stores/{id}/heatmap")
async def get_store_heatmap(id: str):
    return {"store_id": id, "heatmap": []}

@app.get("/stores/{id}/anomalies")
async def get_store_anomalies(id: str):
    return {"store_id": id, "anomalies": []}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "last_event_timestamp": None, "feed_status": "OK"}
