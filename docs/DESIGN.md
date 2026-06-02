# Architectural Design Specification - Store Intelligence System

This document outlines the structural design, data pipelines, and component boundaries of the Apex Store Intelligence System.

## 🧱 Component Topology

The platform is split into three main decoupled layers:
1. **Ingestion Edge Pipeline (`/pipeline`):** Frame-by-frame streaming engine using OpenCV to simulate spatial cross-zone visitor tracking centroids, packaging state transitions into JSON telemetry payloads.
2. **REST Gateway Interface (`/app/main.py`):** Asynchronous FastAPI gateway handling serialization validation, execution rate guards, and server health states.
3. **Analytical Compute Engine (`/app/metrics.py`, `/app/funnel.py`):** Vectorized Pandas layer conducting cross-source calculations against SQLite event histories and flat POS datasets.

## 🔄 System Ingestion Dataflow

[Camera Streams] ──> (pipeline/process_videos.py) ──(HTTP POST Batch)──> [FastAPI REST Gateway]
│
(Pydantic Validation)
│
▼
[Pandas Core Engine] <──(SQL Read Engine)── [SQLite Database] <─── (Batch DB Transaction)
│
├───> Correlations matching with pos_transactions.csv (5-Minute Window Matrix)
│
└───> Dashboard Endpoints (/metrics, /funnel, /heatmap, /anomalies)

## 🗄️ Relational Database Schema (`events` Table)

Data is written to a flat, indexed SQLite schema to provide decoupled storage efficiency:

* `event_id` (TEXT, PRIMARY KEY): Globally unique UUIDv4 identifier ensuring absolute transaction ingestion idempotency.
* `store_id` (TEXT): High-level physical retail store branch routing key.
* `camera_id` (TEXT): Streaming tracking hardware device label identifier.
* `visitor_id` (TEXT): Persistent computer vision tracking trace hash mapping unique visitor sessions.
* `event_type` (TEXT): Target lifecycle transition state tracker (`ENTRY`, `ZONE_ENTER`, `ZONE_DWELL`, `BILLING_QUEUE_JOIN`, `BILLING_QUEUE_DWELL`).
* `timestamp` (TEXT): Normalized string representations formatted systematically into standard ISO-8601 `YYYY-MM-DDTHH:MM:SSZ` formats.
* `zone_id` (TEXT): Target store spatial boundary classification (`SKINCARE`, `PHARMACY`, `BILLING`).
* `dwell_ms` (INTEGER): Active chronometric temporal duration mapping client presence inside coordinates.
* `is_staff` (INTEGER): Binary mapping flag isolating staff identifiers from public retail consumer metrics.
* `confidence` (REAL): Float value ranging from 0.0 to 1.0 mapping object prediction certainty scores.
* `metadata` (TEXT): Compressed JSON layout dictionary strings storing nested system parameters.

## ⚡ Analytics & Temporal Correlation Engine Logic

### 1. Multi-Stage Funnel State Conversion Mechanics
The conversion engine parses four linear milestone states: `ENTRY` ➔ `ZONE_VISIT` ➔ `BILLING_QUEUE` ➔ `PURCHASE`. To account for real-world behavior where edge cases step past intermediary stages entirely (e.g., bypassing physical product aisles and walking directly up to point-of-sale areas), milestones are computed independently using logical presence indicators (`any()` arrays and multi-string matching parameters).

### 2. Timezone-Naive Matrix Correlator
To resolve string layout tracking discrepancies across live transactional text timestamps and SQLite strings, the Pandas core runs a systematic temporal normalizer:
* Strips trailing ISO character markers (`T` and `Z`) across records to produce consistent naive datetimes.
* Implements vector-buffered conditional range evaluations mapping whether a visitor's `BILLING_QUEUE_JOIN` timeline matches an un-nested POS window horizon where:
  $$T_{billing} \le T_{transaction} \le T_{billing} + 5\text{ minutes}$$
