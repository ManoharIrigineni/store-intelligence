import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "/workspace/store_intelligence.db"
POS_CSV_PATH = "/workspace/pos_transactions.csv" 

def calculate_store_metrics(store_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Gather all unique customer sessions (Staff excluded!)
    query_visitors = "SELECT DISTINCT visitor_id FROM events WHERE store_id = ? AND is_staff = 0"
    df_visitors = pd.read_sql_query(query_visitors, conn, params=(store_id,))
    total_unique_visitors = len(df_visitors)
    
    if total_unique_visitors == 0:
        conn.close()
        return {
            "unique_visitors": 0,
            "conversion_rate": 0.0,
            "avg_dwell_per_zone": {},
            "queue_depth": 0,
            "abandonment_rate": 0.0,
            "data_confidence": False
        }
    
    # 2. Extract billing interactions for conversion analysis
    query_billing = """
        SELECT visitor_id, timestamp 
        FROM events 
        WHERE store_id = ? AND is_staff = 0 AND (zone_id = 'BILLING' OR event_type = 'BILLING_QUEUE_JOIN')
    """
    df_billing = pd.read_sql_query(query_billing, conn, params=(store_id,))
    
    # Force UTC timezone normalization to strip any string format differences (+00:00 vs Z)
    df_billing['timestamp'] = pd.to_datetime(df_billing['timestamp']).dt.tz_localize(None)
    
    # 3. Load POS transactions dynamically
    converted_visitors = set()
    try:
        df_pos = pd.read_csv(POS_CSV_PATH)
        df_pos = df_pos[df_pos['store_id'] == store_id].copy()
        df_pos['timestamp'] = pd.to_datetime(df_pos['timestamp']).dt.tz_localize(None)
        
        # Correlate via time windows
        for _, txn in df_pos.iterrows():
            txn_time = txn['timestamp']
            window_start = txn_time - timedelta(minutes=5)
            
            # Find active sessions in the billing zone during this window
            active_in_window = df_billing[
                (df_billing['timestamp'] >= window_start) & 
                (df_billing['timestamp'] <= txn_time)
            ]['visitor_id'].unique()
            
            converted_visitors.update(active_in_window)
    except Exception as e:
        print("POS Processing Error:", e)
        
    num_converted = len(converted_visitors)
    conversion_rate = num_converted / total_unique_visitors if total_unique_visitors > 0 else 0.0
    
    # 4. Compute Avg Dwell times per location zone
    query_dwell = """
        SELECT zone_id, AVG(dwell_ms) as avg_dwell 
        FROM events 
        WHERE store_id = ? AND is_staff = 0 AND zone_id IS NOT NULL 
        GROUP BY zone_id
    """
    df_dwell = pd.read_sql_query(query_dwell, conn, params=(store_id,))
    dwell_dict = dict(zip(df_dwell['zone_id'], df_dwell['avg_dwell']))
    
    # 5. Extract current queue metrics & abandonment estimates
    # 5. Extract current queue metrics & abandonment estimates
    query_queue_joins = """
        SELECT COUNT(DISTINCT visitor_id) 
        FROM events 
        WHERE store_id = ? AND (event_type = 'BILLING_QUEUE_JOIN' OR zone_id = 'BILLING') AND is_staff = 0
    """
    
    query_queue_exits = """
        SELECT COUNT(DISTINCT visitor_id) 
        FROM events 
        WHERE store_id = ? AND event_type IN ('BILLING_QUEUE_LEAVE', 'BILLING_QUEUE_ABANDON') AND is_staff = 0
    """
    
    query_joins_raw = "SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN'"
    query_abandon_raw = "SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'BILLING_QUEUE_ABANDON'"
    
    try:
        total_queued_shoppers = conn.execute(query_queue_joins, (store_id,)).fetchone()[0] or 0
        total_exited_shoppers = conn.execute(query_queue_exits, (store_id,)).fetchone()[0] or 0
        
        # Calculate active queue depth dynamically based on live state delta
        dynamic_queue_depth = max(0, total_queued_shoppers - total_exited_shoppers)
        
        queue_joins = conn.execute(query_joins_raw, (store_id,)).fetchone()[0] or 0
        queue_abandons = conn.execute(query_abandon_raw, (store_id,)).fetchone()[0] or 0
        abandonment_rate = queue_abandons / queue_joins if queue_joins > 0 else 0.0
    except Exception:
        dynamic_queue_depth = 0
        abandonment_rate = 0.0

    conn.close()
    
    confidence_flag = True if total_unique_visitors >= 20 else False
    
    return {
        "unique_visitors": total_unique_visitors,
        "conversion_rate": round(conversion_rate, 4),
        "avg_dwell_per_zone": {k: round(v, 2) for k, v in dwell_dict.items()},
        "queue_depth": dynamic_queue_depth, # Now completely live!
        "abandonment_rate": round(abandonment_rate, 4),
        "data_confidence": confidence_flag
    }
