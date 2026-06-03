# Apex Retail Store Intelligence System

An end-to-end computer vision telemetry ingestion and real-time retail analytics backend platform. [cite_start]The system processes spatial behavioral tracking data from in-store camera streams, persists localized event timelines using SQLite, and correlates visitor behavioral traces against Point of Sale (POS) transactional records to calculate real-time store metrics and sequential funnel drop-off analytics[cite: 16, 48, 94].

---

## 🧱 System Architecture & Data Flow

1. [cite_start]**Video Processing Ingestion Layer (`/pipeline`):** Frame-by-frame streaming engine using OpenCV to simulate spatial cross-zone visitor tracking centroids, packaging tracking steps into structured JSON telemetry strings[cite: 16, 27, 54].
2. [cite_start]**REST API Gateway Engine (`/app`):** An asynchronous FastAPI microservice validating batch arrays against Pydantic schema rule configurations, enforcing a strict challenge constraint limit of 500 events per chunk[cite: 27, 95].
3. [cite_start]**Analytical Data Core:** A high-performance vectorized Pandas execution pipeline that unifies string timestamp formatting across systems and evaluates user transactions using an un-nested, stage-skipping tolerant 5-minute conversion engine logic horizon[cite: 49, 50, 95].

---

## 🚀 Getting Started & Local Setup

### 1. Build and Run the Docker Infrastructure
Deploy the containerized environment and spin up the unified application stack using Docker Compose:
```bash
docker-compose up --build -d
```

### 2. Mock and Process Video Telemetry Assets
Simulate real-time retail computer vision tracking:

```bash
# Generate the simulated tracking .mp4 clip inside the container container
docker exec -it store_intelligence_api python3 generate_mock_video.py

# Execute the stream detection pipeline to send events to the server
docker exec -it store_intelligence_api python3 pipeline/process_videos.py
```
### 3. Run the Automated Testing Matrix
Validate code reliability, constraint boundaries, and confidence filters seamlessly via PyTest inside the environment container:

```bash
docker exec -it store_intelligence_api env PYTHONPATH=. pytest tests/ -v
```

## Core API Specification
### 1. Real-time Analytical Metrics Dashboard
Returns real-time core metrics: unique visitors, conversion rate, average zone dwell metrics, queue depth tracking, and baseline confidence validations.

#### Endpoint: GET /stores/{id}/metrics
#### Sample Request:
```bash
curl -s http://localhost:8000/stores/ST1008/metrics
```
#### Success Response Payload (200 OK):
```bash
{
  "unique_visitors": 1,
  "conversion_rate": 1.0,
  "avg_dwell_per_zone": {
    "SKINCARE": 120000.0
  },
  "queue_depth": 1,
  "abandonment_rate": 0.0,
  "data_confidence": true
}
```

### 2. Customer Journey Conversion Funnel

Tracks multi-stage customer retail lifecycle conversions cleanly, utilizing defensive code logic to calculate drop-offs accurately even when intermediary store stages are skipped.
#### Endpoint: GET /stores/{id}/funnel
#### Sample Request:
```bash
curl -s http://localhost:8000/stores/ST1008/funnel
```
#### Success Response Payload (200 OK):
```bash
{
  "store_id": "ST1008",
  "stages": ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"],
  "counts": {
    "ENTRY": 1,
    "ZONE_VISIT": 1,
    "BILLING_QUEUE": 1,
    "PURCHASE": 1
  },
  "drop_off_percentage": {
    "ZONE_VISIT_DROP_OFF": 0.0,
    "BILLING_QUEUE_DROP_OFF": 0.0,
    "PURCHASE_DROP_OFF": 0.0
  }
}
```

### 3. Spatial Heatmap Distribution Density
Aggregates and returns foot-traffic shopper density counters grouped across distinct physical store zones.
#### Endpoint: GET /stores/{id}/heatmap
#### Sample Request:
```bash
curl -s http://localhost:8000/stores/ST1008/heatmap
```

#### Success Response Payload (200 OK):
```bash
{
  "store_id": "ST1008",
  "heatmap": [
    {
      "zone": "SKINCARE",
      "density": 1
    }
  ]
}
```
### 4. Operational In-Store System Anomalies
Identifies system noise, camera drops, or edge cases like low computer vision detection confidence maps.
#### Endpoint: GET /stores/{id}/anomalies
#### Sample Request:
```bash
curl -s http://localhost:8000/stores/ST1008/anomalies
```
#### Success Response Payload (200 OK):
```bash
{
  "store_id": "ST1008",
  "anomalies": []
}
```
## Defensive Engineering Implementations
### Architecture Safeguards: 
The platform integrates defensive coding practices directly at the ingestion boundary to handle real-world telemetry noise gracefully.

1.**Strict Schema Verification:** Incorporates a robust two-tier Pydantic schema architecture (StoreEvent wrapping an explicit EventMetadata sub-object) protecting input streams.

2.**Low-Confidence Anti-Noise Guard:** Automatically isolates and filters out telemetry logs with an extraction confidence score below 0.50 at the ingestion route boundary.

3.**Skipped-Stage Funnel Floor:** Leverages localized conditional logic arrays and a max(0.0, ...) constraint to prevent mathematical negative drop-off percentages or zero-division runtime exceptions.



