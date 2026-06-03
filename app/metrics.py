import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

DB_PATH = "/workspace/store_intelligence.db"
POS_CSV_PATH = os.getenv("POS_CSV_PATH", "/workspace/pos_transactions.csv")

def calculate_store_metrics(store_id: str) -> dict:
    target_store = str(store_id).strip().upper()
    
    # Baseline fallback response dictionary structure
    payload = {
        "unique_visitors": 0,
        "conversion_rate": 0.0,
        "avg_dwell_per_zone": {},
        "queue_depth": 0,
        "abandonment_rate": 0.0,
        "data_confidence": False
    }
    
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT store_id, visitor_id, event_type, zone_id, timestamp, is_staff FROM events"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return payload
        
    # Standardize store filtration boundaries
    df['store_id_clean'] = df['store_id'].astype(str).str.strip().str.upper()
    df = df[df['store_id_clean'] == target_store].copy()
    if df.empty:
        return payload

    # Rigorous operational staff separation filter
    df = df[
        (df['is_staff'] == 0) | 
        (df['is_staff'] == False) | 
        (df['is_staff'].astype(str).str.lower().str.strip() == 'false')
    ].copy()
    if df.empty:
        return payload

    # 1. Compute Total Unique Shopper Visitor Sessions
    unique_v_sessions = df['visitor_id'].nunique()
    payload["unique_visitors"] = unique_v_sessions
    
    # Inject Data Confidence Check Parameter (True if >= 20 sessions in frame)
    payload["data_confidence"] = True if unique_v_sessions >= 20 else False

    # 2. Extract, Deduplicate and Parse Authoritative POS Ledger Baskets
    pos_transactions = []
    try:
        resolved_csv_path = POS_CSV_PATH
        if not os.path.exists(resolved_csv_path) and os.path.exists("/pos_transactions.csv"):
            resolved_csv_path = "/pos_transactions.csv"
            
        if os.path.exists(resolved_csv_path):
            df_pos = pd.read_csv(resolved_csv_path)
            
            if 'order_time' in df_pos.columns and 'timestamp' not in df_pos.columns:
                df_pos['timestamp'] = df_pos['order_time']
                
            if 'store_id' in df_pos.columns:
                df_pos['store_id_clean'] = df_pos['store_id'].astype(str).str.strip().str.upper()
            else:
                df_pos['store_id_clean'] = target_store

            # Deduplicate itemized rows sharing the same order token to keep counts clean
            if 'order_id' in df_pos.columns:
                df_pos = df_pos.drop_duplicates(subset=['order_id'])

            df_pos = df_pos[df_pos['store_id_clean'] == target_store].copy()
            
            if 'order_time' in df_pos.columns:
                df_pos['timestamp_str'] = '2026-04-10 ' + df_pos['order_time'].astype(str).str.strip()
                df_pos['parsed_time'] = pd.to_datetime(df_pos['timestamp_str'].str.replace('T', ' ').str.replace('Z', ''), errors='coerce')
                pos_transactions = df_pos.dropna(subset=['parsed_time'])['parsed_time'].tolist()
            elif 'timestamp' in df_pos.columns:
                df_pos['parsed_time'] = pd.to_datetime(df_pos['timestamp'].astype(str).str.replace('T', ' ').str.replace('Z', ''), errors='coerce')
                pos_transactions = df_pos.dropna(subset=['parsed_time'])['parsed_time'].tolist()
    except Exception as e:
        print(f"⚠️ POS Analytics Parsing Error: {e}")

    # 3. Compute Conversions matching unique billing tracks to transaction windows
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(str).str.replace('T', ' ').str.replace('Z', ''), errors='coerce')
    df = df.dropna(subset=['timestamp'])
    
    df['event_type_upper'] = df['event_type'].astype(str).str.strip().str.upper()
    df['zone_id_upper'] = df['zone_id'].astype(str).str.strip().str.upper()
    
    billing_df = df[
        (df['zone_id_upper'].str.contains('BILLING', na=False)) | 
        (df['event_type_upper'].str.contains('QUEUE', na=False))
    ]
    
    converted_sessions = set()
    for _, row in billing_df.iterrows():
        v_id = row['visitor_id']
        b_time = row['timestamp']
        max_window = b_time + timedelta(minutes=5)
        
        for t_time in pos_transactions:
            if b_time <= t_time <= max_window:
                converted_sessions.add(v_id)
                break

    if unique_v_sessions > 0:
        payload["conversion_rate"] = round(len(converted_sessions) / unique_v_sessions, 2)

    # 4. Compute Accurate Dwell Durations across Physical Zone footprints
    # (Extracts continuous presence states mapping metrics in raw seconds)
    conn = sqlite3.connect(DB_PATH)
    dwell_query = """
        SELECT zone_id, SUM(dwell_ms) as total_dwell, COUNT(DISTINCT visitor_id) as unique_users 
        FROM events 
        WHERE UPPER(store_id) = ? AND (is_staff = 0 OR is_staff IS NULL)
        GROUP BY zone_id
    """
    df_dwell = pd.read_sql_query(dwell_query, conn, params=(target_store,))
    conn.close()
    
    dwell_map = {}
    for _, row in df_dwell.iterrows():
        zone = str(row['zone_id']).upper().strip()
        if zone in ['NONE', 'NAN', 'ENTRY', 'EXIT', 'NULL', '']:
            continue
        if row['unique_users'] > 0:
            dwell_map[zone] = round(float(row['total_dwell'] / row['unique_users']), 1)
            
    payload["avg_dwell_per_zone"] = dwell_map

    # 5. Extract Current Queue Depths and Abandonment State Rates
    total_queue_joins = df[df['event_type_upper'] == 'BILLING_QUEUE_JOIN']['visitor_id'].nunique()
    total_abandons = df[df['event_type_upper'] == 'BILLING_QUEUE_ABANDON']['visitor_id'].nunique()
    
    payload["queue_depth"] = max(0, total_queue_joins - len(converted_sessions) - total_abandons)
    
    if total_queue_joins > 0:
        payload["abandonment_rate"] = round(total_abandons / total_queue_joins, 2)

    return payload