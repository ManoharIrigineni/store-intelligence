# Architectural Design Specification - Store Intelligence System

This document outlines the structural design, data pipelines, and component boundaries of the Apex Store Intelligence System.

## 🧱 Component Topology

The platform is split into three main decoupled layers:
1. [cite_start]**Ingestion Edge Pipeline (`/pipeline`):** Frame-by-frame streaming engine using OpenCV to simulate spatial cross-zone visitor tracking centroids, packaging state transitions into JSON telemetry payloads[cite: 103, 150].
2. [cite_start]**REST Gateway Interface (`/app/main.py`):** Asynchronous FastAPI gateway handling serialization validation, execution rate guards, adaptive inbound remapping, and server health states[cite: 95, 156].
3. [cite_start]**Analytical Compute Engine (`/app/metrics.py`, `/app/funnel.py`):** Vectorized Pandas layer conducting cross-source calculations against SQLite event histories and itemized flat POS datasets.

## 🔄 System Ingestion Dataflow

[Camera Streams] ──> (pipeline/process_videos.py) ──(HTTP POST Batch)──> [FastAPI REST Gateway]
                                                                                │
                                                                   (Inbound Field Remapper)
                                                                                │
                                                                                ▼
                                                                      (Pydantic Validation)
                                                                                │
                                                                                ▼
[Pandas Core Engine] <──(SQL Read Engine)── [SQLite Database] <─── (Batch DB Transaction)
        │
        ├───> Correlations matching with pos_transactions.csv (Deduplicated 5-Minute Window Matrix)
        │
        └───> Dashboard Endpoints (/metrics, /funnel, /heatmap, /anomalies)

## 🗄️ Relational Database Schema (`events` Table)

[cite_start]Data is written to a flat, indexed SQLite schema to provide decoupled storage efficiency, keeping our underlying production tables highly structured despite incoming variation[cite: 95, 201]:

* [cite_start]`event_id` (TEXT, PRIMARY KEY): Globally unique identifier ensuring absolute transaction ingestion idempotency[cite: 95, 100].
* [cite_start]`store_id` (TEXT): High-level physical retail store branch routing key[cite: 67].
* [cite_start]`camera_id` (TEXT): Streaming tracking hardware device label identifier[cite: 68].
* [cite_start]`visitor_id` (TEXT): Persistent computer vision tracking trace hash mapping unique visitor sessions[cite: 69].
* [cite_start]`event_type` (TEXT): Target lifecycle transition state tracker (`ENTRY`, `ZONE_ENTER`, `ZONE_EXIT`, `BILLING_QUEUE_JOIN`)[cite: 70, 89].
* [cite_start]`timestamp` (TEXT): Normalized string representations formatted systematically into standard ISO-8601 `YYYY-MM-DDTHH:MM:SSZ` formats[cite: 72].
* [cite_start]`zone_id` (TEXT): Target store spatial boundary classification (`SKINCARE`, `COSMETICS`, `BILLING`)[cite: 73, 89].
* [cite_start]`dwell_ms` (INTEGER): Active chronometric temporal duration mapping client presence inside coordinates[cite: 74].
* [cite_start]`is_staff` (INTEGER): Binary mapping flag isolating staff identifiers from public retail consumer metrics[cite: 75, 91].
* [cite_start]`confidence` (REAL): Float value mapping object prediction certainty scores[cite: 79, 91].
* [cite_start]`metadata` (TEXT): Compressed JSON layout strings storing nested parameters (such as `queue_depth`)[cite: 81, 82].

## ⚡ Analytics & Temporal Correlation Engine Logic

### 1. Multi-Stage Funnel State Conversion Mechanics
[cite_start]The conversion engine parses four linear milestone states: `ENTRY` ➔ `ZONE_VISIT` ➔ `BILLING_QUEUE` ➔ `PURCHASE`[cite: 95]. [cite_start]To account for real-world behavior where edge cases step past intermediary stages entirely [cite: 40][cite_start], milestones are computed independently using flexible, vectorized logical presence indicators (`any()` masks, sub-string matching, and token tracking arrays).

### 2. Multi-Item POS Basket Aggregation Strategy
[cite_start]The production transactional data (`POS - sample transactions.csv`) utilizes a product-itemized ledger topology[cite: 203]. [cite_start]If a consumer purchases multiple cosmetics inside a single shopping visit, they generate multiple consecutive rows sharing an identical `order_id` and checkout timestamp[cite: 203]. 

To prevent artificial inflation of the conversion metrics, our Pandas core applies a fast-vectorized deduplication layer:
```python
if 'order_id' in df_pos.columns:
    df_pos = df_pos.drop_duplicates(subset=['order_id'])