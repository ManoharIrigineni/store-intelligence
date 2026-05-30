import pytest
import os
import sqlite3

@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Sets up a localized playground to isolate testing writes from production."""
    # Ensure tables exist inside the runtime test path
    db_path = "/workspace/store_intelligence.db"
    conn = sqlite3.connect(db_path)
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
    yield