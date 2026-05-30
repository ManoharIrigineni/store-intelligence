import sqlite3
import json
from app.models import StoreEvent

DB_PATH = "/workspace/store_intelligence.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create events table
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    processed_count = 0
    
    # Wrap the batch in an explicit transaction for rapid ingestion performance
    cursor.execute("BEGIN TRANSACTION")
    
    for event in events:
        try:
            # Capture total changes BEFORE executing this statement
            changes_before = conn.total_changes
            
            # INSERT OR IGNORE enforces strict idempotency by event_id
            cursor.execute("""
                INSERT OR IGNORE INTO events 
                (event_id, store_id, camera_id, visitor_id, event_type, timestamp, zone_id, dwell_ms, is_staff, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.store_id,
                event.camera_id,
                event.visitor_id,
                event.event_type,
                event.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
                event.zone_id,
                event.dwell_ms,
                1 if event.is_staff else 0,
                event.confidence,
                json.dumps(event.metadata.model_dump())
            ))
            
            # Only increment if THIS specific statement inserted a row
            if conn.total_changes > changes_before:
                processed_count += 1
        except Exception:
            continue # Partial success: skip malformed entries smoothly
            
    conn.commit()
    conn.close()
    return processed_count
