# 5-Minute Live Demonstration Script: Emergency Ambulance Route Optimization

**Project:** Emergency Ambulance Route Optimization System for Bengaluru  
**Academic Module:** Discrete Mathematics · Module 4: Graph Theory  
**Target Audience:** Evaluators, Professors, and Viva Examination Committee  
**Total Duration:** Exactly 5 Minutes (300 Seconds)  

---

## Pre-Demo Checklist (0 Minutes / Setup)

1. **Verify Backend is Running:**
   ```bash
   python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
   ```
2. **Verify Frontend is Running:**
   ```bash
   npm run dev --prefix frontend
   ```
3. **Open Browser:**
   - Tab 1: `http://localhost:5173/` (Landing Page)
   - Tab 2: `http://localhost:5173/app` (Simulator Workspace)
4. **Ensure Network is Initialized:**
   - Graph cache `data/bengaluru.graphml` loaded ($24,242$ vertices, $62,501$ directed edges).

---

## Minute-by-Minute Live Presentation Flow

```text
0:00 ─── Minute 1: Motivation & Graph Foundation (Euler's Handshake Lemma)
1:00 ─── Minute 2: Single-Source Shortest Path & Structural Resilience (Tarjan)
2:00 ─── Minute 3: Dynamic Road Blockage & Multi-Route Planning (Yen & Menger)
3:00 ─── Minute 4: Fleet Assignment (Hungarian) & Strategic Hospital Triage
4:00 ─── Minute 5: Algorithm Race: Dijkstra vs. Admissible A* (Wavefronts)
5:00 ─── Conclusion & Viva Q&A Defense
```

---

### Minute 1 (0:00 – 1:00): Motivation & Mathematical Foundations

* **Screen Action:** Show the **Landing Page** (`http://localhost:5173/`). Scroll through the Hero section with the stylized street topology SVG, highlight the problem statement cards, and point out the 9 Discrete Math feature tags.
* **Speaker Script:**
  > *"Good morning, respected professors. In emergency medical services, minutes mean life. Standard civilian navigation apps only answer one question: 'what is the shortest route right now?' But they ignore single points of failure, topological chokepoints, and hospital capacity.*
  >
  > *For our Discrete Mathematics Module 4 project, we modeled Bengaluru's central emergency corridor as a directed street graph with **24,242 vertices** and **62,501 edges**, and an undirected simple graph of **45,556 edges**. We verified our topological integrity using **Euler's Handshake Lemma**: the sum of all vertex degrees $\sum \deg(v) = 91,112$, exactly equal to $2|E|$. Let's launch the simulator to see graph theory in real-time emergency dispatch."*
* **Action:** Click the primary button **"Launch Simulator"** $\to$ transitions seamlessly to `/app`.

---

### Minute 2 (1:00 – 2:00): Core Incident Dispatch & Structural Resilience Analysis

* **Screen Action:**
  1. Click near **Majestic / Anand Rao Circle** on the map to place an emergency incident marker (red pin).
  2. Observe the automatic dispatch: nearest station (Majestic Station) connects to incident, incident connects to optimal hospital (Victoria Hospital / BMCRI).
  3. Expand the **Resilience Score** widget in the side panel. Point out the badge (`Resilient` / `Moderate` / `Fragile`) and the metrics ($L, D, C$).
* **Speaker Script:**
  > *"The moment an incident is placed, our system runs a multi-source Dijkstra search across all active ambulance hubs to determine the fastest-responding station, and computes the shortest route to the primary trauma facility.*
  >
  > *Beyond finding the path, our backend runs **Tarjan's Low-Link DFS algorithm** ($O(V+E)$) on the undirected graph view to detect cut edges (strict bridges) and cut vertices (articulation points). Furthermore, we compute soft bridges—edges whose failure induces a detour ratio $\rho \ge 1.5$.*
  >
  > *We synthesize these into a composite **Resilience Score** $R = 100 \times (0.4L + 0.4D + 0.2C)$, where $L$ is Menger's max-flow edge connectivity, $D$ is the worst-case detour ratio, and $C$ is strict bridge exposure. This tells dispatchers whether this route is structurally fragile before an ambulance gets trapped."*

---

### Minute 3 (2:00 – 3:00): Dynamic Road Blockage & Multi-Route Planning

* **Screen Action:**
  1. Toggle **"Show Backup Routes"**: Plan B (orange polyline) and Plan C (green polyline) appear on the map.
  2. Click on a road segment on the primary route (Plan A) to trigger **Road Blockage Simulation** (`POST /block`).
  3. A red **"ROAD CLOSED"** cross appears. The route instantly recalculates around the blockage with a live updated travel time and added minutes banner.
  4. Click the **"Restore Blocked Roads"** button to reset.
* **Speaker Script:**
  > *"To ensure resilience against sudden roadblocks or waterlogging, we implement **Yen's K-Shortest Paths algorithm** ($K=3$) and **Menger's edge-disjoint paths**. Plan B and Plan C provide pre-computed fallback corridors.*
  >
  > *Notice what happens when I simulate a road closure by clicking this arterial segment. The system immediately removes that edge from our working graph instance, re-executes Dijkstra, and discovers an alternate corridor while dynamically reporting the exact time penalty and detour ratio. No civilian GPS app provides dispatchers with this instant what-if structural analysis."*

---

### Minute 4 (3:00 – 4:00): Multi-Accident Assignment & Hospital Triage Scoring

* **Screen Action:**
  1. Switch to the **Multi-Incident Tab** or place 3 distinct accidents on the map.
  2. Click **"Solve Optimal Assignment"**. Toggle between **"Minimum Total Time (Hungarian)"** and **"Bottleneck Assignment (Min-Max)"**.
  3. Show the distinct colored routes linking each ambulance to its assigned accident.
  4. Switch to the **Hospital Scoring Tab**: Adjust hospital status (toggle Victoria Hospital to 'Busy' or 'Full') and adjust the **Time of Day Slider** (Off-Peak vs Evening Peak).
* **Speaker Script:**
  > *"During mass-casualty events or simultaneous incidents, greedy dispatch leads to catastrophic delays. We model multi-incident response as a complete weighted bipartite graph $K_{n, m}$ and solve it using the **Hungarian algorithm (Kuhn-Munkres)** in $O(n^3)$ for minimum total response time, as well as a binary-search bottleneck assignment to minimize the maximum individual wait time.*
  >
  > *Simultaneously, our hospital scoring engine balances travel time against clinical capacity: $\text{Score} = \text{travel\_time} + P_{\text{trauma}} + P_{\text{load}}$. If our nearest hospital reaches capacity or lacks neuro-trauma specialization, the algorithm reroutes the patient to an apex center like NIMHANS or St. John's, preventing emergency department diversions."*

---

### Minute 5 (4:00 – 5:00): Algorithm Race: Dijkstra vs. Admissible A*

* **Screen Action:**
  1. Click the **"Algorithm Race"** button in the header.
  2. Pick the pre-set corridor: **Majestic Station to Victoria Hospital** (or Richmond Circle to St. John's).
  3. Click **"Start Race"**.
  4. Watch the side-by-side synchronized map animations:
     - Left panel (Dijkstra): Circular radial wavefront expanding outward ($4,521$ nodes).
     - Right panel ($A^*$): Highly focused elliptical beam guided directly toward the destination ($820$ nodes).
  5. Point to the metrics summary card: **Equal Path Cost ($443.2\text{ s}$)**, zero cost delta, and $\sim 82\%$ reduction in heap operations.
* **Speaker Script:**
  > *"To validate our algorithmic efficiency, we built an interactive head-to-head race between our self-implemented Dijkstra and $A^*$ algorithms.*
  >
  > *Notice the visual contrast: Dijkstra expands blindly in all directions like a circular wave, examining 4,521 vertices. In contrast, our $A^*$ search utilizes a domain-calibrated Euclidean-to-time heuristic: $h(u) = \frac{\text{haversine}(u, t)}{v_{\max}}$. Because no vehicle can exceed $v_{\max}$ ($60\text{ km/h}$), this heuristic is provably **admissible** and **consistent** ($h(u) \le t^*(u, t)$).*
  >
  > *As you can see on the metrics dashboard, both algorithms arrive at the exact same optimal cost—443 seconds—proving mathematical optimality, but $A^*$ prunes over 80% of the search space, executing in a fraction of the time.*
  >
  > *Thank you, and we welcome your questions!"*

---

## Likely Viva Questions & Defense Guide

| Question | Mathematical Answer / Code Defense |
| :--- | :--- |
| **Why did you verify the Handshake Lemma?** | Euler's Handshake Lemma ($\sum \deg(v) = 2|E|$) proves the undirected graph representation is clean, free of phantom edges, and has consistent bidirectional adjacency before running Tarjan's algorithm. |
| **Why must the $A^*$ heuristic divide by $v_{\max}$?** | Since edge costs represent travel time ($t = d/v$), a spatial distance heuristic $d(u, t)$ in meters has the wrong units. Dividing by $v_{\max}$ converts distance to seconds and guarantees $h(u) \le t^*(u, t)$, which is required for admissibility and optimal path guarantees. |
| **Why use Tarjan's low-link rather than naive edge removal?** | Naive bridge detection checks connectivity by removing each edge one by one, requiring $O(E \times (V+E))$, which on our $62,501$-edge graph would take minutes. Tarjan's low-link algorithm finds all bridges and articulation points in a single DFS pass in $O(V+E)$ ($<150\text{ ms}$). |
| **What is the difference between Hungarian and Bottleneck assignment?** | The Hungarian algorithm minimizes the sum $\sum c_{ij}$ (aggregate fleet time), which is socially optimal. The Bottleneck algorithm minimizes $\max(c_{ij})$ (worst-case individual patient wait time), which is critical for equity in emergency triage. |
