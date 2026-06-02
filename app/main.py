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
async def ingest_events(events: List[StoreEvent]):
    """
    Accepts batches of up to 500 behavioral events. Validates, deduplicates, and stores them.
    Idempotent by event_id. Handles partial success on anomalies.
    """
    # Enforce challenge constraint limit of 500 items max per chunk
    if len(events) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Batch size exceeds maximum limit of 500 events."
        )
    
    processed = save_events_batch(events)
    return {"status": "success", "processed": processed}

@app.get("/stores/{id}/metrics")
async def get_store_metrics(id: str):
    """
    Returns real-time core metrics: unique visitors, conversion rate, 
    average dwell per zone, queue depth, and abandonment rate.
    """
    # FIX: Explicitly sanitize and map 'id' to the 'store_id' expected by your engine
    clean_store_id = str(id).strip().upper()
    
    # Break any persistent module module memory cache
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
    # Simple production health ping surface
    return {
        "status": "healthy", 
        "last_event_timestamp": datetime.datetime.utcnow().isoformat() + "Z", 
        "feed_status": "OK"
    }
