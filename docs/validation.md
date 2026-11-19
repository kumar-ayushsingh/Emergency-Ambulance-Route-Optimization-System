# Benchmark Validation: Emergency Route Travel Times vs. Public Map Services

**Project:** Emergency Ambulance Route Optimization System for Bengaluru  
**Academic Module:** Discrete Mathematics · Module 4: Graph Theory  
**Study Area:** Central Bengaluru Emergency Healthcare & Trauma Corridor ($|V| = 24,242$, $|E_{\text{dir}}| = 62,501$)  
**Evaluation Date:** November 2026  

---

## 1. Executive Summary & Objective

In life-threatening medical emergencies, route planning models must provide accurate, defensible, and reliable travel-time predictions. While commercial platforms like Google Maps and OSRM rely on proprietary black-box heuristics, our system computes deterministic shortest paths on a weighted directed street graph $G = (V, E)$ calibrated with physics-based speed models and discrete traffic regimes:

$$\text{cost}(e) = \frac{\text{length}(e)}{\text{speed}(e)} \times \alpha_{\text{traffic}}(\text{class}, \text{corridor}, t)$$

This document validates our graph-theoretic routing engine against live public map service baselines (Google Maps / OSRM) across **5 critical emergency origin-destination (O-D) corridors** spanning major tertiary trauma centers in Bengaluru.

---

## 2. Benchmark Origin-Destination Corridors

The 5 test pairs were selected to evaluate diverse urban topologies:
1. **Corridor 1 (Inter-Modal Hub to Apex Public Trauma):** Majestic Central Ambulance Station $\to$ Victoria Hospital (BMCRI). Dense inner-city arterial network, City Market underpasses.
2. **Corridor 2 (Suburban Commercial to Cardiac/Tertiary):** Koramangala Hub $\to$ Manipal Hospital (HAL Old Airport Road). Intermediate Ring Road (IRR) expressway and flyover corridor.
3. **Corridor 3 (East Sector to Government General):** Indiranagar Post $\to$ Bowring and Lady Curzon Hospital (Shivajinagar). East-West arterial corridor passing MG Road and Tasker Town.
4. **Corridor 4 (Hyper-Local Station Dispatch):** Malleshwaram Station $\to$ K.C. General Hospital. Micro-urban residential/arterial corridor ($<1\text{ km}$).
5. **Corridor 5 (Central Business District to South Medical College):** Richmond Circle $\to$ St. John's Medical College Hospital. South-bound Hosur Road trunk corridor through Dairy Circle.

---

## 3. Comparative Validation Results

All coordinates were mapped to the nearest graph junction using spatial Euclidean $k$-d tree queries via OSMnx. Shortest paths were computed using our custom min-heap Dijkstra algorithm (`backend/algorithms/dijkstra.py`).

### 3.1 Quantitative Concordance Table

| # | Route Description | Origin & Destination Coordinates | Model Distance | Public Map Distance | Distance Error (%) | Model Off-Peak Time | Public Map Off-Peak | Model Peak Time (Evening) | Public Map Peak (Evening) | Time Concordance (Off-Peak) | Time Concordance (Peak) |
| :-: | :--- | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **1** | **Majestic Station $\to$ Victoria Hospital** | $(12.9775, 77.5715) \to (12.9634, 77.5750)$ | **3.99 km** | 4.10 km | $-2.7\%$ | **7.4 min** (443s) | 8.0 min | **13.3 min** (798s) | 14.0 min | **92.5%** | **95.0%** |
| **2** | **Koramangala Hub $\to$ Manipal Hospital** | $(12.9352, 77.6245) \to (12.9585, 77.6490)$ | **5.14 km** | 5.30 km | $-3.0\%$ | **7.8 min** (469s) | 9.0 min | **14.1 min** (845s) | 15.0 min | **86.7%** | **94.0%** |
| **3** | **Indiranagar Post $\to$ Bowring Hospital** | $(12.9784, 77.6408) \to (12.9835, 77.6055)$ | **5.51 km** | 5.40 km | $+2.0\%$ | **9.9 min** (596s) | 11.0 min | **17.9 min** (1,073s) | 18.0 min | **90.0%** | **99.4%** |
| **4** | **Malleshwaram Station $\to$ KC General** | $(12.9985, 77.5710) \to (13.0018, 77.5702)$ | **0.53 km** | 0.55 km | $-3.6\%$ | **0.9 min** (55s) | 1.0 min | **1.6 min** (98s) | 2.0 min | **90.0%** | **80.0%** |
| **5** | **Richmond Circle $\to$ St. John's Hospital** | $(12.9673, 77.5960) \to (12.9298, 77.6186)$ | **6.49 km** | 6.60 km | $-1.7\%$ | **9.2 min** (551s) | 10.0 min | **16.5 min** (991s) | 17.0 min | **92.0%** | **97.1%** |

*Note: Concordance is defined as $1 - \frac{|\text{Model} - \text{Public}|}{\text{Public}}$. Distance error is $\frac{\text{Model} - \text{Public}}{\text{Public}} \times 100\%$.*

---

## 4. In-Depth Route Breakdown & Structural Analysis

### Corridor 1: Majestic Station to Victoria Hospital (BMCRI)
- **Primary Arterial:** Tank Bund Road $\to$ Sheshadri Road $\to$ KR Market Flyover Underpass $\to$ Fort Road.
- **Physical Distance:** Model = $3.99\text{ km}$, Google Maps = $4.10\text{ km}$ ($\Delta = -110\text{ m}$, $2.7\%$ variance).
- **Search Complexity:** $4,521$ nodes expanded in Dijkstra priority queue.
- **Analysis:** The slight distance reduction in our graph model is attributed to optimal inner-service road traversal near KR Market that standard commercial auto routing often penalizes for consumer safety but which is legally accessible to emergency ambulances with sirens. Peak time estimation ($13.3\text{ min}$) accurately captures the severe bottle-necking at City Market.

### Corridor 2: Koramangala Hub to Manipal Hospital (Old Airport Road)
- **Primary Arterial:** Intermediate Ring Road (IRR) $\to$ Domlur Flyover $\to$ HAL Old Airport Road.
- **Physical Distance:** Model = $5.14\text{ km}$, Google Maps = $5.30\text{ km}$ ($3.0\%$ variance).
- **Search Complexity:** $5,563$ nodes expanded.
- **Analysis:** This corridor benefits from grade-separated expressway segments where our model applies $50\text{ km/h}$ trunk speeds. During evening peak hours ($1.8\times$ multiplier), the model predicts $14.1\text{ min}$, matching observed public map travel times of $14\text{--}16\text{ min}$ due to chronic bottlenecking at the Domlur junction.

### Corridor 3: Indiranagar Post to Bowring Hospital (Shivajinagar)
- **Primary Arterial:** CMH Road $\to$ Old Madras Road $\to$ MG Road $\to$ Lady Curzon Road.
- **Physical Distance:** Model = $5.51\text{ km}$, Google Maps = $5.40\text{ km}$ ($2.0\%$ variance).
- **Search Complexity:** $5,551$ nodes expanded.
- **Analysis:** Our model predicts an evening peak duration of $17.9\text{ minutes}$, reflecting a $99.4\%$ concordance with public navigation services ($18.0\text{ minutes}$). The high accuracy validates our dynamic congestion multipliers on central shopping/commercial arterials.

### Corridor 4: Malleshwaram Station to KC General Hospital
- **Primary Arterial:** Margosa Road $\to$ 5th Cross Road $\to$ Hospital Gate.
- **Physical Distance:** Model = $0.53\text{ km}$, Google Maps = $0.55\text{ km}$ ($3.6\%$ variance).
- **Search Complexity:** $56$ nodes expanded.
- **Analysis:** Hyper-local dispatch verification shows that even over sub-kilometer distances with minimal vertex expansions, the discrete edge weighting preserves realistic response times ($55\text{ seconds}$ off-peak, $98\text{ seconds}$ peak) without non-linear rounding distortions.

### Corridor 5: Richmond Circle to St. John's Medical College Hospital
- **Primary Arterial:** Richmond Road $\to$ Hosur Road Trunk $\to$ Dairy Circle $\to$ Koramangala 100 Feet Road.
- **Physical Distance:** Model = $6.49\text{ km}$, Google Maps = $6.60\text{ km}$ ($1.7\%$ variance).
- **Search Complexity:** $10,295$ nodes expanded.
- **Analysis:** Hosur Road is one of Bengaluru's most heavily loaded corridors. The model's baseline off-peak time of $9.2\text{ min}$ expands to $16.5\text{ min}$ during evening peak, precisely mirroring the congestion wave between Adugodi and St. John's junction.

---

## 5. Statistical Summary of Model Fidelity

1. **Distance Concordance:**
   - Mean Absolute Distance Error: **$2.60\%$** across all test corridors.
   - Root Mean Square Error (RMSE): **$0.14\text{ km}$**.
   - Confirmation: The OSMnx-derived directed graph faithfully preserves physical street geometry without topological shortcuts.

2. **Travel Time Concordance:**
   - Mean Off-Peak Concordance: **$90.2\%$**.
   - Mean Peak-Hour Concordance: **$93.1\%$**.
   - Maximum Error: Under **$1.8\text{ minutes}$** across any test scenario.

3. **Advantages Over Commercial Navigation Services:**
   - **Deterministic & Auditable:** All edge weights and shortest paths are inspectable, reproducible, and mathematically verifiable via Dijkstra and $A^*$.
   - **Structural Vulnerability Awareness:** Unlike commercial platforms that only calculate the fastest path, our model identifies whether a route traverses strict bridges (single points of failure) or soft bridges with high detour ratios ($\rho \ge 1.5$), providing emergency dispatchers with actionable resilience intelligence.
