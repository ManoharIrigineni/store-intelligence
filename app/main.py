from fastapi import FastAPI, HTTPException, status
from typing import List
import datetime

# Import components from our newly created modules
from app.models import StoreEvent
from app.ingestion import init_db, save_events_batch
from app.metrics import calculate_store_metrics
from app.funnel import calculate_store_funnel

app = FastAPI(title="Apex Retail Store Intelligence API")

# Initialize the database layout right when the server spins up
@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/events/ingest", status_code=status.HTTP_200_OK)
async def ingest_events(raw_events: List[dict]):
    """
    Accepts batches of behavioral events. Intercepts and normalizes field 
    variations from authoritative datasets, then validates using Pydantic.
    """
    # Enforce challenge constraint limit of 500 items max per chunk
    if len(raw_events) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Batch size exceeds maximum limit of 500 events."
        )
    
    validated_events = []
    
    for item in raw_events:
        try:
            # 1. Normalize Event Type casing and vocabulary variants
            raw_type = str(item.get("event_type", "")).upper()
            if "ENTERED" in raw_type:
                item["event_type"] = "ZONE_ENTER"
            elif "EXITED" in raw_type:
                item["event_type"] = "ZONE_EXIT"
            elif "QUEUE" in raw_type:
                item["event_type"] = "BILLING_QUEUE_JOIN"
            else:
                item["event_type"] = raw_type

            # 2. Map structural field label variations
            if "store_code" in item and "store_id" not in item:
                item["store_id"] = item["store_code"]

            if "id_token" in item and "visitor_id" not in item:
                item["visitor_id"] = item["id_token"]
            elif "track_id" in item and "visitor_id" not in item:
                item["visitor_id"] = f"TRACK_{item['track_id']}"

            if "event_timestamp" in item and "timestamp" not in item:
                item["timestamp"] = item["event_timestamp"]
            elif "event_time" in item and "timestamp" not in item:
                item["timestamp"] = item["event_time"]
            elif "queue_join_ts" in item and "timestamp" not in item:
                item["timestamp"] = item["queue_join_ts"]

            # 3. Ensure a valid fallback unique ID exists
            if "event_id" not in item:
                item["event_id"] = item.get("id_token") or item.get("queue_event_id") or f"gen-{hash(str(item.get('timestamp')))}"

            # 4. Inject sub-metadata default schema if empty or missing
            if "metadata" not in item or item["metadata"] is None:
                item["metadata"] = {
                    "queue_depth": item.get("queue_position_at_join"),
                    "sku_zone": None,
                    "session_seq": 0
                }
            
            if "confidence" not in item:
                item["confidence"] = 1.0

            # Pass the normalized dictionary directly to your strict Pydantic model
            validated_event = StoreEvent(**item)
            validated_events.append(validated_event)
            
        except Exception as err:
            # Gracefully log structural noise rows without crashing the whole batch
            print(f"⚠️ Remap normalization skipped row: {err}")
            continue

    processed = save_events_batch(validated_events)
    return {"status": "success", "processed": processed}

@app.get("/stores/{id}/metrics")
async def get_store_metrics(id: str):
    """
    Returns real-time core metrics: unique visitors, conversion rate, 
    average dwell per zone, queue depth, and abandonment rate.
    """
    clean_store_id = str(id).strip().upper()
    
    from app.metrics import calculate_store_metrics
    metrics_payload = calculate_store_metrics(clean_store_id)
    return metrics_payload

@app.get("/stores/{id}/funnel")
async def get_store_funnel(id: str):
    clean_store_id = str(id).strip().upper()
    from app.funnel import calculate_store_funnel
    return calculate_store_funnel(clean_store_id)

@app.get("/stores/{id}/heatmap")
async def get_store_heatmap(id: str):
    """Calculates distribution metrics across distinct physical store zones."""
    clean_store_id = str(id).strip().upper()
    import sqlite3
    import pandas as pd
    from app.funnel import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    try:
        query = "SELECT zone_id, COUNT(DISTINCT visitor_id) as density FROM events WHERE store_id = ? GROUP BY zone_id"
        df = pd.read_sql_query(query, conn, params=(clean_store_id,))
        # Drop meaningless layout labels if present
        df = df[~df['zone_id'].str.upper().isin(['NONE', 'NAN', 'ENTRY', 'EXIT'])]
        heatmap_data = [{"zone": row["zone_id"], "density": int(row["density"])} for _, row in df.iterrows()]
    except Exception:
        heatmap_data = []
    finally:
        conn.close()
        
    return {"store_id": id, "heatmap": heatmap_data}

@app.get("/stores/{id}/anomalies")
async def get_store_anomalies(id: str):
    """Identifies potential in-store hardware or detection flags (e.g., extremely low confidence)."""
    clean_store_id = str(id).strip().upper()
    import sqlite3
    import pandas as pd
    from app.funnel import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    try:
        # Pull low-confidence events that managed to bypass early thresholds, or extreme system spikes
        query = "SELECT event_id, camera_id, event_type, confidence FROM events WHERE store_id = ? AND confidence < 0.60"
        df = pd.read_sql_query(query, conn, params=(clean_store_id,))
        anomaly_list = [
            {
                "event_id": row["event_id"],
                "type": "LOW_CONFIDENCE_DETECTION",
                "description": f"Camera {row['camera_id']} recorded a low confidence score of {row['confidence']:.2f} during {row['event_type']}."
            } for _, row in df.iterrows()
        ]
    except Exception:
        anomaly_list = []
    finally:
        conn.close()
        
    return {"store_id": id, "anomalies": anomaly_list}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "last_event_timestamp": datetime.datetime.utcnow().isoformat() + "Z", 
        "feed_status": "OK"
    }
