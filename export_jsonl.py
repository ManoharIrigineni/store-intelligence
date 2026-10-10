import sqlite3
import json
import os

DB_PATH = "/workspace/store_intelligence.db"
OUTPUT_PATH = "/workspace/events.jsonl"

def export_to_jsonl():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file not found at {DB_PATH}")
        return

    print("🔄 Connecting to database and extracting processed telemetry...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Select all core fields matching your strict schema
    cursor.execute("""
        SELECT event_id, store_id, camera_id, visitor_id, event_type, 
               timestamp, zone_id, dwell_ms, is_staff, confidence, metadata 
        FROM events
    """)
    rows = cursor.fetchall()
    conn.close()

    print(f"📦 Found {len(rows)} events. Writing to valid JSONL schema...")
    with open(OUTPUT_PATH, 'w') as f:
        for row in rows:
            # Safely unpack and parse the nested metadata dictionary string
            try:
                meta = json.loads(row[10]) if row[10] else {"session_seq": 0}
            except Exception:
                meta = {"session_seq": 0}

            item = {
                "event_id": row[0],
                "store_id": row[1],
                "camera_id": row[2],
                "visitor_id": row[3],
                "event_type": row[4],
                "timestamp": row[5],
                "zone_id": row[6] if row[6] and row[6] != 'None' else None,
                "dwell_ms": int(row[7]) if row[7] is not None else 0,
                "is_staff": bool(row[8]),
                "confidence": float(row[9]) if row[9] is not None else 1.0,
                "metadata": meta
            }
            f.write(json.dumps(item) + '\n')
            
    print("✅ Generated events.jsonl inside the container successfully!")

if __name__ == "__main__":
    export_to_jsonl()