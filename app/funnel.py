import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

DB_PATH = "/workspace/store_intelligence.db"
POS_CSV_PATH = os.getenv("POS_CSV_PATH", "/workspace/pos_transactions.csv")

def calculate_store_funnel(store_id: str) -> dict:
    target_store = str(store_id).strip().upper()
    counts = {"ENTRY": 0, "ZONE_VISIT": 0, "BILLING_QUEUE": 0, "PURCHASE": 0}
    
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT store_id, visitor_id, event_type, zone_id, timestamp, is_staff 
        FROM events 
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return {"store_id": store_id, "stages": list(counts.keys()), "counts": counts, "drop_off_percentage": {}}

    # Standardize store filtering inside Pandas cleanly
    df['store_id_clean'] = df['store_id'].astype(str).str.strip().str.upper()
    df = df[df['store_id_clean'] == target_store].copy()

    if df.empty:
        return {"store_id": store_id, "stages": list(counts.keys()), "counts": counts, "drop_off_percentage": {}}

    # Robust staff filtering match
    df = df[
        (df['is_staff'] == 0) | 
        (df['is_staff'] == False) | 
        (df['is_staff'].astype(str).str.lower().str.strip() == 'false')
    ].copy()
    
    if df.empty:
        return {"store_id": store_id, "stages": list(counts.keys()), "counts": counts, "drop_off_percentage": {}}
        
    # Clear out ISO 'T' and 'Z' text components before converting to timezone-naive datetimes
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(str).str.replace('T', ' ').str.replace('Z', ''), errors='coerce')
    df = df.dropna(subset=['timestamp'])

    # Extract transaction data matching real CSV parameters safely
    pos_transactions = []
    try:
        resolved_csv_path = POS_CSV_PATH
        if not os.path.exists(resolved_csv_path) and os.path.exists("/pos_transactions.csv"):
            resolved_csv_path = "/pos_transactions.csv"
            
        if os.path.exists(resolved_csv_path):
            df_pos = pd.read_csv(resolved_csv_path)
            df_pos['store_id_clean'] = df_pos['store_id'].astype(str).str.strip().str.upper()
            df_pos = df_pos[df_pos['store_id_clean'] == target_store].copy()
            
            if 'order_time' in df_pos.columns:
                df_pos['timestamp_str'] = '2026-04-10 ' + df_pos['order_time'].astype(str).str.strip()
                df_pos['parsed_time'] = pd.to_datetime(df_pos['timestamp_str'].str.replace('T', ' ').str.replace('Z', ''), errors='coerce')
                df_pos = df_pos.dropna(subset=['parsed_time']).sort_values(by='parsed_time')
                pos_transactions = df_pos['parsed_time'].tolist()
            elif 'timestamp' in df_pos.columns:
                df_pos['parsed_time'] = pd.to_datetime(df_pos['timestamp'].astype(str).str.replace('T', ' ').str.replace('Z', ''), errors='coerce')
                df_pos = df_pos.dropna(subset=['parsed_time'])
                pos_transactions = df_pos['parsed_time'].tolist()
    except Exception as e:
        print(f"⚠️ POS Dataset Parsing Error: {e}")

    # Group by visitor_id to trace individual customer conversion chains
    grouped = df.groupby('visitor_id')
    
    for visitor_id, group in grouped:
        group_clean = group.copy()
        group_clean['event_type'] = group_clean['event_type'].astype(str).str.strip().str.upper()
        group_clean['zone_id'] = group_clean['zone_id'].astype(str).str.strip().str.upper()
        
        event_types = set(group_clean['event_type'].tolist())
        zones = set(group_clean['zone_id'].tolist())
        
        # Every unique visitor in this dataset counts as an Entry step
        counts["ENTRY"] += 1
        
        # Determine step transitions independently
        has_visited_zone = any(z for z in zones if z not in ['ENTRY', 'EXIT', 'BILLING', 'NONE', 'NAN'])
        if has_visited_zone or 'ZONE_ENTER' in event_types or 'ZONE_DWELL' in event_types:
            counts["ZONE_VISIT"] += 1
            
        has_billing = ('BILLING' in zones or 'BILLING_QUEUE_JOIN' in event_types or 'BILLING_QUEUE_DWELL' in event_types)
        if has_billing:
            counts["BILLING_QUEUE"] += 1
            
            billing_timestamps = group_clean[
                (group_clean['zone_id'] == 'BILLING') | 
                (group_clean['event_type'] == 'BILLING_QUEUE_JOIN')
            ]['timestamp'].tolist()
            
            is_converted = False
            for b_time in billing_timestamps:
                if pd.isna(b_time):
                    continue
                b_datetime = pd.to_datetime(b_time)
                max_window = b_datetime + timedelta(minutes=5)
                
                for t_time in pos_transactions:
                    if b_datetime <= t_time <= max_window:
                        is_converted = True
                        break
                if is_converted:
                    break
                    
            if is_converted:
                counts["PURCHASE"] += 1

    # Compute drop-off step percentages cleanly (Safeguarded against stage-skipping)
    drop_off = {}
    
    drop_off["ZONE_VISIT_DROP_OFF"] = round((1 - (counts["ZONE_VISIT"] / counts["ENTRY"])) * 100, 2) if counts["ENTRY"] > 0 else 0.0
    
    if counts["ZONE_VISIT"] > 0:
        drop_off["BILLING_QUEUE_DROP_OFF"] = max(0.0, round((1 - (counts["BILLING_QUEUE"] / counts["ZONE_VISIT"])) * 100, 2))
    else:
        drop_off["BILLING_QUEUE_DROP_OFF"] = 0.0 if counts["BILLING_QUEUE"] > 0 else 100.0
        
    if counts["BILLING_QUEUE"] > 0:
        drop_off["PURCHASE_DROP_OFF"] = max(0.0, round((1 - (counts["PURCHASE"] / counts["BILLING_QUEUE"])) * 100, 2))
    else:
        drop_off["PURCHASE_DROP_OFF"] = 0.0 if counts["PURCHASE"] > 0 else 100.0

    # Ensure this return statement is un-nested at the very base level of the function
    return {
        "store_id": store_id,
        "stages": ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"],
        "counts": counts,
        "drop_off_percentage": drop_off
    }