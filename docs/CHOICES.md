# Architectural Tradeoffs & Engineering Choices

This document explains the technical rationale behind the software selections, algorithmic rules, and structural trade-offs implemented in this system.

## 📊 Technical Stack Rationale

### 1. Persistence Layer: SQLite vs. PostgreSQL/MongoDB
* **Choice Selected:** **SQLite**
* **Justification:** Given the localized nature of edge deployments inside physical brick-and-mortar retail locations, a single-file relational engine like SQLite eliminates network overhead and configuration complexities. It easily sustains the transaction loads of a high-volume retail store branch while providing atomic properties and cross-process stability via safe SQL transactional blocks (`BEGIN TRANSACTION` / `COMMIT`).

### 2. Data Analysis Engine: Vectorized Pandas vs. Native Python Iterators
* **Choice Selected:** **Pandas DataFrames**
* **Justification:** Running structural timeline window lookups using standard python nested loops features an $O(N \times M)$ time complexity algorithm that degrades severely when streaming large datasets like raw POS transaction histories. Pandas processes matching arrays via optimized vectorized execution maps, dropping runtime execution margins down to millisecond processing horizons.

### 3. Machine Vision Interface: Headless vs. Standard OpenCV Packaging
* **Choice Selected:** Standard `opencv-python` with custom system library injections in the Docker layer, rather than `opencv-python-headless`.
* **Justification:** While headless compilation variants minimize base container sizing bounds, standard OpenCV installations combined with targeted Linux library injections (`libgl1`, `ffmpeg`) allow the edge deployment wrapper script to scale up seamlessly. This ensures compatibility with display hardware drivers and hardware acceleration modules when moving from a mock simulation layer to live production CCTV streams.

---

## ⚙️ Algorithmic Trade-Offs & Safeguards

### 1. Ingestion Noise Floor Isolation Threshold
The gateway applies an early data-cleaning guard that automatically rejects events with a detection confidence score below **50%** (`confidence < 0.50`). 
* **Trade-off:** While this might drop genuine, fleeting frames captured in poor lighting or high-density shopper crowds, it cleanly safeguards downstream metrics from data pollution and artificial tracking splits.

### 2. Temporal Window Granularity Matching
A strict **5-minute time horizon window** is configured to match billing queue entries to confirmed sales.
* **Trade-off:** If a checkout queue experiences extreme delay (greater than 5 minutes), a customer's conversion will register as an abandonment anomaly rather than a conversion checkout path. This choice represents a deliberate operational compromise to minimize false-positive matches between different shoppers checking out around the same time.

### 3. Video Processing Capture Down-Sampling Rate
The processing framework optimizes the incoming raw footage capture cycle to sample precisely **1 frame per second**, actively discarding the intervening frames.
* **Trade-off:** This optimization downscales incoming video frame volumes by roughly **96%**, drastically freeing up processing threads and GPU memory bounds. The compromise is that exceptionally fast cross-zone client transits (shorter than 1 second) could escape tracking loops entirely, a minor edge case accepted to secure production system stability.

---

## 🔧 Event Schema Design & Ingestion Rationale (Part D Compliance)

### 1. Core Architectural Choice: POS Transaction Aggregation Strategy
* **Options Considered:**
  1. *Raw Row Line-Item Mapping:* Treating every single row in the POS transaction CSV as a distinct customer conversion.
  2. *Relational Database Joint Schema:* Splitting data into two separate tables (`orders` and `line_items`) linked relationally.
  3. *Vectorized Group-By Deduplication (Selected):* Applying a fast Pandas `.drop_duplicates(subset=['order_id'])` vector pass on dataset ingestion.

* **What the AI Suggested:** The AI initially recommended altering the relational database structure to introduce a foreign-key tracking table mapping every itemized product bought during a shopping trip.
* **What I Chose and Why (Engineering Override):** I explicitly rejected the relational database expansion. The final authoritative file (`POS - sample transactions.csv`) features a product-itemized ledger topology, where a customer buying multiple items generates multiple consecutive rows sharing an identical `order_id` and checkout timestamp. 

Creating multi-table joints would introduce unnecessary runtime overhead to our real-time analytics endpoints. Instead, I chose a vectorized deduplication approach directly inside our core analytics engines (`app/funnel.py` and `app/metrics.py`). By grouping data rows by `order_id` and isolating the primary basket event, we compress multiple product records into a single checkout session. This ensures our **Offline Store Conversion Rate** stays mathematically perfect and fully immune to itemized row inflation.

### 2. Adaptive Inbound Remapping Schema Architecture
* **Options Considered:**
  1. *Loose, Completely Optional Pydantic Models:* Making all attributes optional inside `StoreEvent` to accept any raw incoming field variation natively.
  2. *Inline Dictionary Vocabulary Translation Middleware (Selected):* Intercepting raw inputs inside `POST /events/ingest`, translating mismatched