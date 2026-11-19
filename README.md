# Emergency Ambulance Route Optimization System for Bengaluru

**Graph-Theoretic Routing, Resilience Analysis, and Fleet Planning for Emergency Healthcare**  
*Experiential Learning Project · Discrete Mathematics · Module 4: Graph Theory*  
*Submitted by: Sebastian and team · November 2026*  

---

## 1. Executive Summary

When a medical emergency occurs, the latency between call dispatch and tertiary hospital admission directly dictates patient survival rates. In dense metropolitan cities like **Bengaluru**, commercial civilian navigation systems (Google Maps, Apple Maps) answer only one narrow question: *what is the shortest route right now?* They fail to account for single points of failure, topological chokepoints, hospital clinical capacity, fleet-wide coordination, and route resilience under sudden infrastructure blockages.

This system models the road network of Bengaluru as a weighted, directed street graph ($|V| = 24,242$, $|E_{\text{dir}}| = 62,501$) and implements rigorous discrete mathematics algorithms to solve four fundamental operational challenges:
1. **Deterministic Shortest-Path Dispatch:** Priority-queue Dijkstra and admissible $A^*$ search with dynamic traffic weighting.
2. **Structural Fragility & Resilience Analysis:** Tarjan's low-link algorithm for cut edges (strict bridges) and cut vertices (articulation points), soft-bridge detour ratios ($\rho \ge 1.5$), Menger edge connectivity, and composite Resilience Scoring ($R$).
3. **Contingency Planning & Blockage Simulation:** Yen's $K$-shortest paths ($K=3$), edge-disjoint routing, and interactive edge-deletion simulation with live recalculation.
4. **Fleet Optimization & Strategic Placement:** Hungarian matching for multi-accident fleet assignment, bottleneck assignment, facility multi-criteria scoring, and graph eccentricity/$k$-center/$p$-median station coverage.

---

## 2. System Architecture

The project follows a decoupled, production-grade architecture combining a high-performance Python/NetworkX graph computing engine with a modern React + Leaflet interactive frontend.

```mermaid
flowchart TD
    subgraph Data_Layer ["1. Data & Spatial Ingestion"]
        OSM["OpenStreetMap via OSMnx<br>Central Bengaluru Bounding Box"] --> GraphML["data/bengaluru.graphml<br>24,242 nodes | 62,501 edges"]
        HOSP["data/hospitals.json<br>Victoria, NIMHANS, Bowring, etc."] --> Facilities
        STN["data/stations.json<br>Majestic, Koramangala, etc."] --> Facilities
        TRF["data/traffic.json<br>Time-of-day multipliers"] --> TrafficModel
    end

    subgraph Graph_Engine ["2. Core Graph Representation"]
        GraphML --> Digraph["Directed MultiDiGraph (G)<br>Travel Time Weights w(e) = length / speed"]
        GraphML --> Undir["Undirected Simple Graph (G_undir)<br>Handshake Lemma Verified: Σ deg(v) = 2|E|"]
    end

    subgraph Algorithms ["3. Self-Implemented Discrete Math Algorithms"]
        Digraph --> Dijkstra["backend/algorithms/dijkstra.py<br>Min-Heap SSSP O((V+E) log V)"]
        Digraph --> AStar["backend/algorithms/astar.py<br>Admissible Heuristic h(u) = d_hav / v_max"]
        Undir --> Tarjan["backend/algorithms/critical.py<br>Tarjan's Low-Link Bridges & Articulations O(V+E)"]
        Digraph --> Resilience["Composite Resilience Score<br>R = 100 * (0.4L + 0.4D + 0.2C)"]
        Digraph --> Backup["backend/algorithms/backup.py<br>Yen's K-Shortest & Menger Edge-Disjoint"]
        Digraph --> Assign["backend/algorithms/assignment.py<br>Hungarian (Kuhn-Munkres) & Bottleneck"]
        Digraph --> Place["backend/algorithms/placement.py<br>Eccentricity, K-Center & P-Median Coverage"]
        Facilities & TrafficModel --> Score["backend/algorithms/scoring.py<br>Score = Travel Time + P_trauma + P_load"]
    end

    subgraph API_Layer ["4. REST API (FastAPI)"]
        Dijkstra & AStar & Tarjan & Backup & Assign & Place & Score --> Endpoints["FastAPI Endpoints (backend/api.py)<br>POST /route | POST /critical | POST /backup<br>POST /block | POST /assign | POST /hospitals/score<br>POST /race | GET /coverage"]
    end

    subgraph Frontend_App ["5. Interactive Web Interface (React + Vite + Leaflet)"]
        Endpoints --> UI_Router["React Router (frontend/src/App.jsx)"]
        UI_Router --> LandingPage["Landing Page ('/')<br>Hero, Problem, Flow, Features, Math Table"]
        UI_Router --> MapSim["Map Simulator ('/app')<br>Leaflet Map, HUD, Legend, Layer Toggles, Sidebars"]
        MapSim --> RaceModal["Dijkstra vs A* Algorithm Race<br>Dual Synchronized Animation Panels"]
    end
```

---

## 3. Feature to Graph Theory Concept Mapping

Every system feature maps directly to formal discrete mathematics principles:

| System Feature | Mathematical Concept | Formal Definition / Theorem | Algorithmic Implementation | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **Topological Validation** | **Euler's Handshake Lemma** | $\sum_{v \in V} \deg(v) = 2|E|$ | Verified on undirected graph ($91,112 = 2 \times 45,556$). Classifies junctions: dead-ends ($\deg=1$), bends ($\deg=2$), intersections ($\deg \ge 3$). | $O(V)$ |
| **Emergency Routing** | **Shortest Path on Directed Weighted Graph** | $\min_{P} \sum_{e \in P} w(e)$ where $w(e) = \frac{\text{length}(e)}{\text{speed}(e)}$ | Min-heap priority-queue Dijkstra from scratch (`backend/algorithms/dijkstra.py`). Respects one-ways and turn restrictions. | $O((V+E)\log V)$ |
| **Station Dispatch** | **Multi-Source SSSP** | $\min_{s \in S, t \in T} d(s, t)$ | Super-source Dijkstra initialized with all ambulance stations to find the minimum-latency ambulance. | $O((V+E)\log V)$ |
| **Critical Road Detection** | **Cut Edges & Cut Vertices (Bridges)** | Edge $e$ is a bridge if $G \setminus \{e\}$ has more connected components than $G$. Vertex $v$ is an articulation point if $G \setminus \{v\}$ increases components. | Tarjan's low-link algorithm with discovery order $dfn[u]$ and back-edge tracking $low[u]$ via iterative DFS (`backend/algorithms/critical.py`). | $O(V+E)$ |
| **Soft Bridges** | **Detour Ratio Impact** | $\rho(e) = \frac{\text{cost}(G \setminus \{e\})}{\text{cost}(G)}$; flagged if $\rho(e) \ge 1.5$ | Single-edge deletion re-routing on all route segments to identify high-penalty detours. | $O(|P_{\text{route}}| \cdot (V+E)\log V)$ |
| **Edge Connectivity** | **Menger's Theorem** | Maximum number of edge-disjoint paths between $s$ and $t$ equals the minimum capacity edge cut $\lambda(s, t)$. | Max-flow min-cut computation on unit-capacity transformation of route graph. | Polynomial |
| **Resilience Score** | **Composite Robustness Metric** | $R = 100 \times (0.4L + 0.4D + 0.2C)$ with normalized path redundancy $L$, detour factor $D$, and bridge penalty $C$. | Synthesizes topological vulnerability into an auditable 0–100 score (`Resilient`, `Moderate`, `Fragile`). | $O(1)$ |
| **Backup Routes** | **Yen's $K$-Shortest Simple Paths** | Enumerates $K$ loopless paths $P_1, P_2, \dots, P_K$ in strictly increasing order of cost. | Yen's algorithm ($K=3$) with deviation node branch testing (`backend/algorithms/backup.py`). | $O(K \cdot V(E + V \log V))$ |
| **Route Redundancy** | **Edge-Disjoint Paths** | Paths $P_A, P_B$ such that $E(P_A) \cap E(P_B) = \emptyset$. | Residual graph saturation removing utilized forward and backward edges. | $O(k \cdot (V+E)\log V)$ |
| **Blockage Simulation** | **Dynamic Edge Deletion & Recovery** | $G' = G \setminus \{e_{\text{blocked}}\}$; recompute $d_{G'}(s, t)$. | Interactive road-click deletion on working copy of graph with live detour delta reporting. | $O((V+E)\log V)$ |
| **Station Placement** | **Graph Eccentricity, Center & Radius** | $\text{ecc}(v) = \max_{u \in D} d(v, u)$; $\text{rad}(G) = \min_{v} \text{ecc}(v)$; $\text{center}(G) = \{v \mid \text{ecc}(v) = \text{rad}(G)\}$. | Grid-sampled demand vertices ($N=300\text{--}500$) evaluated over candidate junctions (`backend/algorithms/placement.py`). | $O(|C| \cdot (V+E)\log V)$ |
| **Multi-Station Fleet** | **$k$-Center & $p$-Median** | $k$-Center: $\min_{S \subseteq C, |S|=k} \max_{u \in D} d(u, S)$<br>$p$-Median: $\min_{S \subseteq C, |S|=p} \sum_{u \in D} d(u, S)$ | Greedy furthest-point heuristic for $k$-center; 1-swap local neighborhood search for $p$-median. | Heuristic Polynomial |
| **Coverage Heatmap** | **Isochrone Contour Bands** | Level sets $L_t = \{v \in V \mid \min_{s \in S} d(s, v) \le t\}$ for $t \in \{8, 15, 30\}\text{ min}$. | Single multi-source Dijkstra from all active stations, partitioned into emergency response bands. | $O((V+E)\log V)$ |
| **Multi-Accident Matching** | **Weighted Bipartite Matching (Assignment)** | $\min_{\pi} \sum_{i=1}^n c_{i, \pi(i)}$ on complete bipartite graph $K_{n, m}$. | Hungarian (Kuhn-Munkres) algorithm via SciPy `linear_sum_assignment` (`backend/algorithms/assignment.py`). | $O(n^3)$ |
| **Equity Dispatch** | **Bottleneck Assignment** | $\min_{\pi} \max_{i=1}^n c_{i, \pi(i)}$. | Binary search over edge costs paired with Hopcroft-Karp maximal bipartite matching. | $O(n^{2.5} \log C)$ |
| **Smart Hospital Choice** | **Multi-Criteria Vertex Evaluation** | $\text{Score} = \text{travel\_time} + P_{\text{trauma}} + P_{\text{load}}$. | Evaluates tertiary facilities based on real-time bed capacity and specialty requirements. | $O(|H|)$ |
| **Dynamic Congestion** | **Time-Varying Edge Weights** | $w(e, t) = w(e) \times \alpha(t, \text{class}, \text{corridor})$. | Temporal multipliers for off-peak ($1.0$), morning peak ($1.6$), evening peak ($1.8$), and night ($0.8$). | $O(1)$ per edge |
| **Heuristic Search Race** | **Admissible & Consistent $A^*$ Search** | $f(u) = g(u) + h(u)$ where $h(u) = \frac{d_{\text{haversine}}(u, t)}{v_{\max}} \le t^*(u, t)$. | Custom $A^*$ benchmarked against Dijkstra; proves zero cost delta while cutting search space by $>80\%$. | $O((V+E)\log V)$ |

---

## 4. Visual Walkthrough & System Screenshots

All screenshots below were captured directly from the live running application using the automated browser testing suite and are stored in [docs/images/](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/).

### 4.1 Landing Page & Navigation
- **Hero & Problem Statement:** Highlights urban transit bottlenecks, hospital corridors, and introduces the graph theory solution.
  - View image: [docs/images/landing_page_hero.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/landing_page_hero.png)
  - Full desktop presentation: [docs/images/landing_page_desktop.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/landing_page_desktop.png)
- **Mobile Responsive Layout (360px):** Verified clean scaling across mobile devices.
  - View image: [docs/images/landing_page_mobile.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/landing_page_mobile.png)

![Landing Page Hero](docs/images/landing_page_hero.png)

### 4.2 Simulator App, Route HUD & Resilience Analysis
- **Interactive Map Simulator (`/app`):** Complete workspace with floating loading HUD, collapsible Layers & Legend panel, and live route metrics.
  - View image: [docs/images/simulator_app.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/simulator_app.png)
- **Resilience Score & Bridge Detection:** Displays strict bridges in red, soft bridges in orange, articulation points, and the composite Resilience Score badge.
  - View image: [docs/images/resilience_score_badge.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/resilience_score_badge.png)

![Simulator App](docs/images/simulator_app.png)

### 4.3 Road Blockage & Dynamic Detour Simulation
- **Edge Deletion & Rerouting:** Clicking a road segment deletes the edge in the graph, recalculates the shortest path, displays the added minutes banner, and highlights the closure with a red cross.
  - View image: [docs/images/road_blocked_detour.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/road_blocked_detour.png)

![Road Blockage Detour](docs/images/road_blocked_detour.png)

### 4.4 Strategic Station Placement & Coverage Isochrones
- **Coverage Heatmap:** Multi-source isochrone bands: $<8\text{ min}$ (green), $8\text{--}15\text{ min}$ (amber), $15\text{--}30\text{ min}$ (red), and $>30\text{ min}$ (dark grey).
  - View image: [docs/images/coverage_heatmap.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/coverage_heatmap.png)

![Coverage Heatmap](docs/images/coverage_heatmap.png)

### 4.5 Multi-Accident Assignment (Hungarian vs. Bottleneck)
- **Simultaneous Emergency Dispatch:** Solves bipartite matching across multiple accidents and ambulance hubs, rendering color-coded dispatch routes.
  - View image: [docs/images/multi_accident_assignment.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/multi_accident_assignment.png)

![Multi-Accident Assignment](docs/images/multi_accident_assignment.png)

### 4.6 Hospital Scoring & Dynamic Traffic Weighting
- **Triage Decision Table:** Explains why an ambulance may bypass the nearest hospital due to trauma level requirements or ICU bed saturation.
  - View image: [docs/images/hospital_scoring_traffic.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/hospital_scoring_traffic.png)

![Hospital Scoring](docs/images/hospital_scoring_traffic.png)

### 4.7 Algorithm Race: Dijkstra vs. Admissible $A^*$
- **Dual Synchronized Map Panels:** Visualizes the radial expansion wave of Dijkstra ($4,521$ nodes) versus the goal-directed beam of $A^*$ ($820$ nodes) with identical optimal cost verification.
  - View image: [docs/images/algorithm_race_dual_maps.png](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/images/algorithm_race_dual_maps.png)

![Algorithm Race Dual Maps](docs/images/algorithm_race_dual_maps.png)

---

## 5. Getting Started & Installation

### Prerequisites
- **Python:** 3.11 or 3.12
- **Node.js:** 20+ and npm 10+
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/aayush-discrete-math/emergency-ambulance-routing.git
cd "Emergency Ambulance Route Optimization System"
```

### 2. Backend Installation & Server Launch
```bash
# Install Python dependencies
python -m pip install -r requirements.txt

# Start FastAPI backend server (runs on port 8000)
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
```

The API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 3. Frontend Installation & Server Launch
```bash
# In a new terminal window:
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open your browser at [http://127.0.0.1:5173/](http://127.0.0.1:5173/) to access the application.

---

## 6. Single-Service Production Deployment & Docker

The system is configured to build and deploy as a single, self-contained container service where FastAPI serves the compiled React Single Page Application at `/` and all REST API routes under `/api`.

### 6.1 Multi-Stage Dockerfile Architecture

The build process uses a two-stage [Dockerfile](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/Dockerfile):
1. **Stage 1 (`node:20-alpine`):** Installs npm packages and builds the production React + Leaflet bundle into `frontend/dist`.
2. **Stage 2 (`python:3.11-slim`):** Installs Python backend dependencies, copies the pre-cached spatial road networks (`data/srinagar.graphml` and `data/bengaluru.graphml`), copies the compiled frontend assets from Stage 1 into `frontend/dist`, and launches Uvicorn on `$PORT`.

### 6.2 Building & Running the Docker Image

```bash
# Build the unified production container
docker build -t ambulance-router .

# Run container locally on port 8000
docker run -p 8000:8000 -e PORT=8000 ambulance-router
```

Once running, access the application directly at [http://localhost:8000/](http://localhost:8000/).

### 6.3 Offline Startup & Zero-Download Guarantee

The spatial GraphML files (`data/srinagar.graphml` and `data/bengaluru.graphml`) are committed directly into the container image. During container boot:
- The graph builder loads the offline graph directly from disk without initiating network requests to OpenStreetMap.
- The startup time is deterministic, reliable, and immune to external API rate limits.

### 6.4 Startup Memory Optimization & Attribute Pruning

To ensure suitability for constrained cloud containers (e.g. 512MB–1GB RAM limits on Cloud Run, Railway, Render):
- **Singleton In-Memory Caching:** The graph is parsed and loaded once at startup and reused across requests.
- **Attribute Pruning:** Unused attributes (Shapely LineString geometries, OSMIDs, street count tags) are purged on load, retaining only numerical edge travel times, lengths, road classes, and coordinates. This lowers runtime memory from >440MB to ~63MB.

### 6.5 Health Check Endpoint

Container orchestrators (Kubernetes, Docker Swarm, Cloud Run) monitor service readiness via:

```bash
curl -f http://localhost:8000/api/health
```

**Sample Response (`200 OK`):**
```json
{
  "status": "operational",
  "system": "Emergency Ambulance Route Optimization System",
  "city": "Bengaluru",
  "version": "1.0.0",
  "graph_loaded": true,
  "vertices": 24242,
  "directed_edges": 62501
}
```

---

## 7. Automated Verification & Test Suite

All algorithms and endpoints are backed by an automated test suite featuring **72 comprehensive unit and integration tests** cross-checking custom algorithms against NetworkX ground truth:

```bash
# Run all backend tests
pytest backend/tests/ -v
```

### Test Coverage Highlights:
- **`test_graph_builder.py`:** Validates graph loading, strongly connected components, edge weights, and Euler's Handshake Lemma.
- **`test_dijkstra.py`:** Tests custom min-heap Dijkstra against `nx.shortest_path_length` across 100 random source-target pairs.
- **`test_critical.py`:** Validates Tarjan's low-link bridges and articulation points against `nx.bridges` and `nx.articulation_points` on random Erdős–Rényi graphs and handcrafted bridge topologies.
- **`test_backup.py`:** Tests Yen's $K$-shortest paths for cost monotonicity and cycle freedom; verifies edge-disjoint path validity.
- **`test_placement.py`:** Verifies graph eccentricity, center, radius, greedy $k$-center, and $p$-median optimization.
- **`test_assignment.py`:** Compares Hungarian and Bottleneck assignments against exhaustive brute-force search on matrices up to $6 \times 6$.
- **`test_scoring.py`:** Validates hospital penalty scoring, trauma routing logic, and time-of-day traffic multipliers.
- **`test_astar.py`:** Verifies exact cost equality between Dijkstra and $A^*$ across 100 random vertex pairs, proving heuristic admissibility.
- **`test_api.py`:** End-to-end integration tests for all REST API endpoints.

**Test Execution Status:** `72 passed in 74.14s (100% PASS)`

---

## 8. Real-World Validation Against Public Map Services

Our routing model was rigorously validated against live public navigation services (Google Maps / OSRM) across 5 critical emergency transit corridors in Bengaluru.

| Corridor | Description | Model Dist. | Public Dist. | Error (%) | Model Peak Time | Public Peak Time | Time Concordance |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Corridor 1** | Majestic Station $\to$ Victoria Hospital (BMCRI) | 3.99 km | 4.10 km | $-2.7\%$ | 13.3 min | 14.0 min | **95.0%** |
| **Corridor 2** | Koramangala Hub $\to$ Manipal Hospital (HAL Rd) | 5.14 km | 5.30 km | $-3.0\%$ | 14.1 min | 15.0 min | **94.0%** |
| **Corridor 3** | Indiranagar Post $\to$ Bowring Hospital | 5.51 km | 5.40 km | $+2.0\%$ | 17.9 min | 18.0 min | **99.4%** |
| **Corridor 4** | Malleshwaram Station $\to$ KC General Hospital | 0.53 km | 0.55 km | $-3.6\%$ | 1.6 min | 2.0 min | **80.0%** |
| **Corridor 5** | Richmond Circle $\to$ St. John's Medical College | 6.49 km | 6.60 km | $-1.7\%$ | 16.5 min | 17.0 min | **97.1%** |

*Detailed methodology, variance analysis, and statistical proofs are documented in [docs/validation.md](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/docs/validation.md).*

---

## 9. Live Demonstration Guide

A minute-by-minute live presentation guide designed for professors, evaluators, and viva defense is available at [scripts/demo.md](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/scripts/demo.md):
- **Minute 1:** Introduction, Landing Page, and Euler's Handshake Lemma.
- **Minute 2:** Single Incident Placement, Multi-Source Station Dispatch, and Tarjan's Low-Link Resilience Analysis.
- **Minute 3:** Backup Routes (Yen's $K$-Shortest) and Interactive Road Blockage Simulation.
- **Minute 4:** Hungarian Multi-Incident Matching and Clinical Hospital Triage.
- **Minute 5:** Head-to-Head Algorithm Race (Dijkstra vs. Admissible $A^*$) and Viva Defense.

---

## 10. Project Metadata & Configuration

All team members, GitHub links, and academic project affiliations are configured centrally in [frontend/src/config.js](file:///c:/Users/Aayush/Desktop/Emergency%20Ambulance%20Route%20Optimization%20System/frontend/src/config.js):
- **Course:** Discrete Mathematics, Module 4: Graph Theory
- **Project Type:** Experiential Learning Project
- **City & Network:** Bengaluru, Karnataka, India
- **Academic Year:** 2026
