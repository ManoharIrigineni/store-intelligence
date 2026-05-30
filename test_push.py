import urllib.request
import json

# A sequential 4-event journey for the same visitor session
data = [
    {
        'event_id': 'f1111111-1111-4bad-9bdd-2b0d7b3dcb6d',
        'store_id': 'STORE_BLR_002',
        'camera_id': 'CAM_ENTRY_01',
        'visitor_id': 'VIS_c8a2f1',
        'event_type': 'ENTRY',
        'timestamp': '2026-03-03T14:10:00Z', # 1. Enters store
        'dwell_ms': 0,
        'is_staff': False,
        'confidence': 0.99,
        'metadata': {'session_seq': 1}
    },
    {
        'event_id': 'f2222222-2222-4bad-9bdd-2b0d7b3dcb6d',
        'store_id': 'STORE_BLR_002',
        'camera_id': 'CAM_FLOOR_01',
        'visitor_id': 'VIS_c8a2f1',
        'event_type': 'ZONE_ENTER',
        'timestamp': '2026-03-03T14:15:00Z', # 2. Browses product floor
        'zone_id': 'SKINCARE',
        'dwell_ms': 120000,
        'is_staff': False,
        'confidence': 0.95,
        'metadata': {'session_seq': 2}
    },
    {
        'event_id': 'f3333333-3333-4bad-9bdd-2b0d7b3dcb6d',
        'store_id': 'STORE_BLR_002',
        'camera_id': 'CAM_BILLING_01',
        'visitor_id': 'VIS_c8a2f1',
        'event_type': 'BILLING_QUEUE_JOIN',
        'timestamp': '2026-03-03T14:22:10Z', # 3. Joins billing queue (Within 5m of POS!)
        'zone_id': 'BILLING',
        'dwell_ms': 45000,
        'is_staff': False,
        'confidence': 0.98,
        'metadata': {'session_seq': 3}
    }
]

try:
    req = urllib.request.Request(
        'http://localhost:8000/events/ingest', 
        data=json.dumps(data).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    response = urllib.request.urlopen(req)
    print("Ingestion Status:", response.read().decode())
except Exception as e:
    print("Error:", e)