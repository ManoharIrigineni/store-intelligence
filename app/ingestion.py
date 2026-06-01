import sqlite3
import json
from datetime import datetime
from app.models import StoreEvent

DB_PATH = "/workspace/store_intelligence.db"

def init_db():
    """Initializes the SQLite database schema cleanly."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            store_id TEXT,
            camera_id TEXT,
            visitor_id TEXT,
            event_type TEXT,
            timestamp TEXT,
            zone_id TEXT,
            dwell_ms INTEGER,
            is_staff INTEGER,
            confidence REAL,
            metadata TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_events_batch(events: list[StoreEvent]) -> int:
    """Safely handles incoming batches from Pydantic and inserts them into SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    processed_count = 0
    
    cursor.execute("BEGIN TRANSACTION")
    
    for event in events:
        if event.confidence < 0.50:
            continue
        try:
            changes_before = conn.total_changes
            
            # Safe Timestamp Extraction: String or DateTime objects
            if hasattr(event.timestamp, 'strftime'):
                formatted_timestamp = event.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                try:
                    dt_obj = datetime.strptime(str(event.timestamp).strip(), '%Y-%m-%d %H:%M:%S')
                    formatted_timestamp = dt_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    formatted_timestamp = str(event.timestamp).strip()
            
            # Safe Metadata Extraction
            if hasattr(event.metadata, 'model_dump'):
                metadata_str = json.dumps(event.metadata.model_dump())
            elif hasattr(event.metadata, 'dict'):
                metadata_str = json.dumps(event.metadata.dict())
            else:
                metadata_str = json.dumps(event.metadata if event.metadata else {})

            cursor.execute("""
                INSERT OR IGNORE INTO events 
                (event_id, store_id, camera_id, visitor_id, event_type, timestamp, zone_id, dwell_ms, is_staff, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(event.event_id),
                str(event.store_id),
                str(event.camera_id),
                str(event.visitor_id),
                str(event.event_type),
                formatted_timestamp,
                str(event.zone_id) if event.zone_id else "None",
                int(event.dwell_ms) if event.dwell_ms else 0,
                1 if event.is_staff else 0,
                float(event.confidence),
                metadata_str
            ))
            
            if conn.total_changes > changes_before:
                processed_count += 1
        except Exception as e:
            print(f"⚠️ Row Ingestion Error: {e}")
            continue
            
    conn.commit()
    conn.close()
    return processed_count