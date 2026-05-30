import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "/workspace/store_intelligence.db"
POS_CSV_PATH = "/workspace/pos_transactions.csv"

def calculate_store_funnel(store_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Fetch all raw events for this store excluding staff members
    query = """
        SELECT visitor_id, event_type, zone_id, timestamp 
        FROM events 
        WHERE store_id = ? AND is_staff = 0
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(store_id,))
    
    # Initialize counts for our funnel stages
    counts = {"ENTRY": 0, "ZONE_VISIT": 0, "BILLING_QUEUE": 0, "PURCHASE": 0}
    
    if df.empty:
        conn.close()
        return {"store_id": store_id, "stages": list(counts.keys()), "counts": counts, "drop_off_percentage": {}}
        
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
    
    # 2. Extract transaction data for verification
    pos_transactions = []
    try:
        df_pos = pd.read_csv(POS_CSV_PATH)
        df_pos = df_pos[df_pos['store_id'] == store_id].copy()
        df_pos['timestamp'] = pd.to_datetime(df_pos['timestamp']).dt.tz_localize(None)
        pos_transactions = df_pos['timestamp'].tolist()
    except Exception:
        pass

    # 3. Group by visitor_id to trace individual customer conversion chains
    grouped = df.groupby('visitor_id')
    
    for visitor_id, group in grouped:
        event_types = set(group['event_type'].tolist())
        zones = set(group['zone_id'].dropna().tolist())
        
        # Every tracked session begins at the entry gate step
        counts["ENTRY"] += 1
        
        # Did they explore product zones?
        has_visited_zone = any(z for z in zones if z not in ['ENTRY', 'EXIT', 'BILLING'])
        if has_visited_zone or 'ZONE_ENTER' in event_types:
            counts["ZONE_VISIT"] += 1
            
            # Did they proceed to checkout lines?
            if 'BILLING' in zones or 'BILLING_QUEUE_JOIN' in event_types:
                counts["BILLING_QUEUE"] += 1
                
                # Did they successfully verify against a POS ticket?
                billing_timestamps = group[
                    (group['zone_id'] == 'BILLING') | 
                    (group['event_type'] == 'BILLING_QUEUE_JOIN')
                ]['timestamp'].tolist()
                
                is_converted = False
                for b_time in billing_timestamps:
                    for t_time in pos_transactions:
                        # Matched if purchase occurs within 5 mins AFTER being in the billing area
                        if b_time <= t_time <= (b_time + timedelta(minutes=5)):
                            is_converted = True
                            break
                    if is_converted:
                        break
                        
                if is_converted:
                    counts["PURCHASE"] += 1

    conn.close()
    
    # 4. Compute drop-off step percentages
    drop_off = {}
    drop_off["ZONE_VISIT_DROP_OFF"] = round((1 - (counts["ZONE_VISIT"] / counts["ENTRY"])) * 100, 2) if counts["ENTRY"] > 0 else 0.0
    drop_off["BILLING_QUEUE_DROP_OFF"] = round((1 - (counts["BILLING_QUEUE"] / counts["ZONE_VISIT"])) * 100, 2) if counts["ZONE_VISIT"] > 0 else 0.0
    drop_off["PURCHASE_DROP_OFF"] = round((1 - (counts["PURCHASE"] / counts["BILLING_QUEUE"])) * 100, 2) if counts["BILLING_QUEUE"] > 0 else 0.0

    return {
        "store_id": store_id,
        "funnel": ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"],
        "counts": counts,
        "drop_off_percentage": drop_off
    }
