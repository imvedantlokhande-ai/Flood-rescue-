# Automated Flood Evacuation Route Planner & NGO Rescue Dispatcher
### Real-Time Municipal Telemetry • Pure Python DSA Engine • Live Google Maps Emergency Operations

A real-time municipal emergency evacuation pathfinding and autonomous NGO rescue dispatch system built with pure Python DSA (3.10+), FastAPI backend, Server-Sent Events (SSE), Open-Meteo real-time environmental telemetry, and a full-screen Google Maps JavaScript API dashboard.

> **STRICT DSA MANDATE COMPLIANCE**:
> All graph routing, reachability, pathfinding, and triage prioritization are implemented **100% from scratch** without `networkx`, `heapq`, `queue.PriorityQueue`, `collections.deque`, or any Google Directions/Routes/Distance Matrix API.
> The Google Maps JavaScript API is used **strictly for client-side rendering** (markers, polylines, circle overlays, info windows, traffic layer).

---

## 1. System Architecture & 10-Step Automated Pipeline

The system operates autonomously in the background without requiring manual user button clicks:

```text
[1. Open-Meteo & GloFAS Feed] ──> [2. Flood Risk Score] ──> [3. Threat Gate Check]
                                                                    │
[6. BFS / DFS Reachability]   <── [5. Mark Road Inundation] <── [4. Road Graph Assembly]
         │
         ├──> [7. MinHeap Dijkstra Route] ──> [8. Google Maps Render (Flowing Chevrons)]
         │
         └──> [9. MinHeap NGO Dispatch]   ──> [10. SSE Telemetry Push & Auto Alerts]
```

### Automated 10-Step Pipeline Execution:

| Step # | Pipeline Phase | Description | Custom DSA / Mathematical Concept | Execution Speed |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **Auto Ingest** | Periodic Open-Meteo live precipitation & GloFAS river discharge feed. | `services/data_feed.py` (Asyncio polling) | ~12 ms |
| **2** | **Risk Assessment** | Hydrologic threat calculation: `LOW`, `MODERATE`, `HIGH`, `SEVERE`. | `algorithms/flood_risk/risk_calculator.py` | ~1.2 ms |
| **3** | **Threat Gate Check** | If dangerous $\to$ proceed; if safe $\to$ state "Normal conditions, no evacuation required". | Conditional gate check | ~0.4 ms |
| **4** | **Graph Assembly** | 100 intersections as nodes with elevations, 247 road edges with weights in km. | `data_structures/graph.py` (Adjacency List) + `Haversine` | ~3.8 ms |
| **5** | **Road Inundation** | Roads $\ge 0.5\text{m}$ submerged/blocked; $0.2 - 0.49\text{m}$ penalized ($2.5\times$). | `modules/flood_marker.py` (Dynamic Weight Multiplier) | ~2.1 ms |
| **6** | **BFS & DFS Scan** | Explores reachable nodes; partitions disconnected clusters and isolates stranded zones. | `CustomQueue` BFS + `CustomStack` DFS Components | ~4.6 ms |
| **7** | **Dijkstra Safe Route**| Single-Source Shortest Path to nearest reachable designated safe shelter. | `MinHeap` Dijkstra Priority Queue | ~5.2 ms |
| **8** | **Display Evacuation Route**| Live map rendering with animated flowing chevrons, walk/drive ETAs. | Google Maps JS API (`SymbolPath.FORWARD_CLOSED_ARROW`) | ~16 ms (render) |
| **9** | **Auto NGO Dispatch** | Pushes stranded zones to `MinHeap` with priority $= -(R \times P)$; assigns nearest base. | `services/rescue_dispatcher.py` (`MinHeap` + `Dijkstra`) | ~6.8 ms |
| **10** | **Auto Alerts & Stream** | Sends alerts (Demo, Email, Telegram); pushes live state via SSE `GET /api/stream`. | `services/notifier.py` + SSE Push | Real-time |

---

## 2. Telemetry Data Sources (Real vs. Estimated)

| Telemetry Dimension | Source Type | Provider / Formula | Update Cadence |
| :--- | :---: | :--- | :---: |
| **Current Precipitation** | **Real** | Open-Meteo Forecast API (`precipitation`, `rain` in mm/hr) | Every 2 min |
| **24h & 6h Forecast** | **Real** | Open-Meteo Hourly API (past 24h history + next 6h trend) | Every 2 min |
| **River Discharge** | **Real** | Open-Meteo Flood API (Pavana / Mula River GloFAS in m³/s) | Every 2 min |
| **Terrain Elevation** | **Real** | Open-Meteo STRM 90m Elevation API (cached per node in JSON) | One-time / Cached |
| **Municipal Road Network** | **Real** | OpenStreetMap Overpass API (highway extract for PCMC Pune) | One-time (`fetch_roads.py`) |
| **Road Water Inundation** | **Estimated** | Hydraulic equation: $D = (R \times 0.012) + (Q_{\text{river}} \times 0.015) + \max(0, 565 - \text{Elev}_{\min}) \times 0.04$ | Computed per cycle |
| **Road Impassability** | **Estimated** | Impassable if $D \ge 0.5\text{m}$; caution penalty if $0.2\text{m} \le D < 0.5\text{m}$ | Computed per cycle |
| **Evacuation ETA** | **Estimated** | Walking speed $4.5\text{ km/h}$; emergency vehicle speed $35\text{ km/h}$ under storm conditions | Computed per cycle |

---

## 3. Pure DSA Concept Summary Table

| Data Structure / Algorithm | File Location | Purpose & Flood-Specific Reason | Time Complexity | Space Complexity |
| :--- | :--- | :--- | :---: | :---: |
| **Graph (Adjacency List)** | `data_structures/graph.py` | Models road networks, intersections, safe shelters, elevations, and dynamic flood blocks. | $O(V + E)$ | $O(V + E)$ |
| **CustomQueue** | `data_structures/queue.py` | Singly linked-list FIFO queue powering BFS for reachability and turn minimization. | $O(1)$ push/pop | $O(V)$ |
| **CustomStack** | `data_structures/stack.py` | Singly linked-list LIFO stack powering iterative DFS for cluster discovery and isolated component analysis. | $O(1)$ push/pop | $O(V)$ |
| **MinHeap** | `data_structures/min_heap.py` | Binary min-heap powering Dijkstra shortest path and triage priority extraction $(-\text{Risk} \times \text{Pop})$. | $O(\log N)$ push/pop | $O(N)$ |
| **Haversine Formula** | `algorithms/haversine/haversine.py` | Pure spherical trigonometric distance formula for edge weights and GPS user snapping. | $O(1)$ distance, $O(V)$ snap | $O(1)$ |
| **BFS Traversal** | `algorithms/bfs/bfs.py` | Level-by-level exploration checking shelter reachability and fewest road turns. | $O(V + E)$ | $O(V)$ |
| **DFS Decomposition** | `algorithms/connected_components/` | Partitions flood-damaged network into connected subgraphs to isolate cut-off zones. | $O(V + E)$ | $O(V)$ |
| **Dijkstra's Algorithm** | `algorithms/dijkstra/dijkstra.py` | Finds shortest safe evacuation path avoiding submerged roads with risk penalties. | $O((V + E) \log V)$ | $O(V)$ |
| **Rescue Dispatcher** | `services/rescue_dispatcher.py` | Priority triage using `MinHeap` and nearest NGO base assignment via `Dijkstra`. | $O(K \log K + B (V + E) \log V)$ | $O(K + V)$ |

---

## 4. UI / UX Emergency Operations Design System

- **Typography**: Inter (UI interfaces) + JetBrains Mono (numerical readings & coordinates). 8px spatial grid.
- **Glassmorphism**: Backdrop blur (`blur(16px)`), subtle 1px border, layered soft shadows, 16px corner radius.
- **Strict Color Mapping**: Green (`#10b981`, safe), Amber (`#f59e0b`, caution), Orange (`#f97316`, risky), Red (`#ef4444`, danger/stranded), Blue (`#3b82f6`, information).
- **Icons**: Inline Lucide SVGs (no emojis).
- **Cards (Exact Layout Order)**:
  1. **Hero status card**: Huge risk badge (`LOW`, `MODERATE`, `HIGH`, `SEVERE`), rainfall mm/hr with 24h & 6h sparkline, background tint, pulsing alarm ring at `SEVERE`.
  2. **8-step pipeline tracker**: Vertical stepper with spinner-to-checkmark animation and millisecond timing.
  3. **Evacuation route card**: Safe shelter name, distance, walk/drive ETA tabs, waypoint list with hover highlight, "Start navigation" turn-by-turn guidance.
  4. **Reachability card**: SVG donut chart showing navigable vs. stranded node percentages.
  5. **Rescue requests card**: Priority-sorted list (`#1`, `#2`, ...), assigned NGO, and click-to-draw blue response route.
  6. **Simulation card**: Timeline slider (T+0h to T+5h) with play/pause/step controls.
  7. **Explain Mode**: Collapsible DSA inspection panel (Dijkstra heap, Dispatch MinHeap, BFS queue, DFS stack).
- **Full-Width Emergency Banner**: Appears on severe threats or when cut off, with tap-to-call NDRF (`tel:112`).
- **Responsive Mobile Bottom Sheet**: Touch drag handle with peek (110px), half (50vh), and full (90vh) snap points.

```text
+-------------------------------------------------------------------------------------------------------+
|  [Logo] Flood Evacuation Ops  |  (● LIVE) Updated 2s ago  |  [Data Sources]  |  [🔔]  |  [🌙]           |
+-------------------------------------------------------------------------------------------------------+
|  [================ 🚨 CRITICAL FLOOD SURGE - GROUND ROUTE COMPROMISED ================ [Call 112] ]   |
|                                                                                                       |
|  +------------------------------+   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~   |
|  | 1. HERO STATUS CARD          |   ~                                                             ~   |
|  |   SEVERE RISK (84/100)       |   ~              FULL-SCREEN GOOGLE MAP                         ~   |
|  |   48.5 mm/hr | River: 42 m³/s|   ~                                                             ~   |
|  |   [~~~ 24h Sparkline ~~~]    |   ~   - Normal Roads (Gray)                                     ~   |
|  +------------------------------+   ~   - Risky Roads (Orange)                                    ~   |
|  | 2. 8-STEP PIPELINE TRACKER   |   ~   - Flooded Roads (Red Dashed)                              ~   |
|  |   ✓ Telemetry (12ms)         |   ~   - Evacuation Route (Flowing Green Chevrons)               ~   |
|  |   ✓ Dijkstra Route (5.2ms)   |   ~   - NGO Rescue Path (Blue)                                  ~   |
|  +------------------------------+   ~   - Safe Shelters (Green Pins)                              ~   |
|  | 3. EVACUATION ROUTE CARD     |   ~   - Stranded Areas (Red Pulsing Hazard Pins)                ~   |
|  |   DY Patil Hospital (2.29 km)|   ~   - Live User Location (Blue Radar Dot)                     ~   |
|  |   Drive: 5.4m | Walk: 30.5m  |   ~                                                             ~   |
|  |   [Start Navigation]         |   ~                                                             ~   |
|  +------------------------------+   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~   |
|  | 4. REACHABILITY DONUT (94%)  |                                                                     |
|  +------------------------------+   +-------------------------------------------------------------+   |
|  | 5. STRANDED RESCUE MISSIONS  |   | MAP LEGEND: Roads | Toggles: [Traffic] [BFS] [All Nodes]   |   |
|  |   #1 Old Sangvi (Airlift)    |   | DIJKSTRA REPLAY: [Animate Dijkstra] [Speed: 180ms]          |   |
|  +------------------------------+   +-------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------------+
```

---

## 5. Environment Variables (`.env`)

Configure operational settings in `.env` (copy from `.env.example`):

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `GOOGLE_MAPS_API_KEY` | `""` | Google Maps JavaScript API key (optional; setup modal and canvas fallback provided if omitted). |
| `CITY` | `"Pimpri-Chinchwad (PCMC), Pune"` | Municipal region name. |
| `POLL_INTERVAL` | `30` | Telemetry refresh interval in seconds ($30\text{s}$ for demo, $120\text{s}$ for live). |
| `DEMO_MODE` | `true` | If `true`, cycles through rainfall surge scenarios automatically. |
| `NOTIFY_CHANNEL` | `DEMO` | Notification channel: `DEMO` (in-memory log), `EMAIL` (SMTP), or `TELEGRAM`. |
| `NOTIFICATION_EMAIL` | `emergency-ops@pcmcindia.gov.in` | Recipient email address when `NOTIFY_CHANNEL=EMAIL`. |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP mail server hostname. |
| `SMTP_PORT` | `587` | SMTP port (TLS). |
| `SMTP_USER` | `""` | SMTP sender email username. |
| `SMTP_PASS` | `""` | SMTP sender application password. |
| `TELEGRAM_BOT_TOKEN` | `""` | Telegram Bot API token. |
| `TELEGRAM_CHAT_ID` | `""` | Target Telegram group or channel chat ID. |
| `APP_URL` | `http://localhost:8000` | Base host URL for generating navigation and acknowledgment links. |

---

## 6. How to Install and Run

### Step 1: Install Python Requirements
```bash
cd flood_evacuation_planner
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env and enter your GOOGLE_MAPS_API_KEY (optional; interactive setup screen available)
```

### Step 3: Run the One-Time Road Network Ingest (OpenStreetMap Overpass & Open-Meteo)
```bash
# Query OpenStreetMap Overpass and Open-Meteo Elevation API to build 100-node PCMC network
python3 scripts/fetch_roads.py
```

### Step 4: Run Unit Tests
```bash
# Run all 33 unit tests
python3 -m unittest discover tests

# Or run specific test suites
python3 -m unittest tests/test_algorithms.py
python3 -m unittest tests/test_rescue_dispatcher.py
python3 -m unittest tests/test_api_and_haversine.py
```

### Step 5: Start the Real-Time Server
```bash
python3 api.py
# Or with uvicorn directly:
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` in your browser. The application will:
1. Connect to the Server-Sent Events stream (`GET /api/stream`).
2. Fetch live Open-Meteo precipitation and GloFAS river discharge.
3. Automatically track your location with `navigator.geolocation.watchPosition` and snap to the nearest road intersection.
4. Render roads with smooth color transitions and animated flowing evacuation arrows.
5. Priority-triage cut-off neighborhoods using our custom `MinHeap` and dispatch nearest NGO response teams.
