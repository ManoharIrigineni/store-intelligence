# Apex Retail Store Intelligence System

An end-to-end computer vision telemetry ingestion and real-time retail analytics backend platform. The system processes spatial behavioral tracking data from in-store camera streams, persists localized event timelines using SQLite, and correlates visitor behavioral traces against Point of Sale (POS) transactional records to calculate real-time store metrics and sequential funnel drop-off analytics.

##  System Architecture & Data Flow

1. **Video Processing Ingestion Layer (`/pipeline`):** Uses OpenCV spatial coordinates matching to track visual targets across distinct camera layouts (`CAM_FLOOR_01`, `CAM_BILLING_01`), formatting tracking steps into structured JSON telemetry strings.
2. **REST API Gateway Engine (`/app`):** An asynchronous FastAPI microservice validating batch arrays against Pydantic schema rule configurations, processing up to 500 events per chunk.
3. **Analytical Data Core:** A high-performance vectorized Pandas execution pipeline that unifies string timestamp formatting across systems and evaluates user transactions using an un-nested, stage-skipping tolerant 5-minute conversion engine logic horizon.

##  Getting Started & Local Setup

### 1. Build and Run the Docker Infrastructure
Deploy the asynchronous microservice app wrapper cluster using Docker Compose:
```bash
docker-compose up --build -d
