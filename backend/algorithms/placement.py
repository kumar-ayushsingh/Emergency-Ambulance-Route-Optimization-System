r"""Station Placement & Coverage Isochrones Engine.

Academic Context:
Discrete Mathematics · Module 4: Graph Theory
Problem Statement: Graph Facility Location Problems, Network Eccentricity,
Center & Radius, Minimax K-Center, and Minisum P-Median Optimization.

Mathematical Formulations:
1. Demand Set Sampling:
   Let G = (V, E) be the directed road graph.
   D \subset V is a representative demand set of 300-500 vertices sampled
   uniformly on a 2D spatial grid [x_min, x_max] \times [y_min, y_max].
   Each grid intersection (x_i, y_j) is snapped to the nearest graph vertex v \in V:
       v = \arg\min_{u \in V} \text{dist}_{\text{haversine}}((x_i, y_j), (x_u, y_u))

2. Candidate Site Selection:
   C \subset V is the candidate facility set comprising:
   - High-degree intersections: deg(v) \ge 3 in the undirected topology.
   - Hospital gates: the nearest road vertices to all regional trauma hospitals.

3. Eccentricity, Graph Center, and Graph Radius (1-Ambulance Problem):
   For each candidate c \in C, its eccentricity with respect to demand set D is:
       e_D(c) = \max_{u \in D} d(c, u)
   where d(c, u) is the shortest path travel time from candidate c to demand point u.
   - Graph Center:
       c^* = \arg\min_{c \in C} e_D(c)
   - Graph Radius:
       \text{rad}_D(G) = \min_{c \in C} e_D(c) = e_D(c^*)
   Complexity:
       O(|C| \cdot (|E| + |V| \log |V|)) for distance matrix precomputation,
       O(|C| \cdot |D|) for center and radius resolution.

4. Greedy K-Center Algorithm (Minimax Facility Location):
   Objective: Minimize the maximum response time across all demand points:
       \min_{S \subseteq C, |S|=k} \max_{u \in D} \min_{s \in S} d(s, u)
   Algorithm (2-Approximation by Gonzalez / Hochbaum-Shmoys):
   - Step 1: Initialize S_1 = { c^* } (the 1-center).
   - Step 2: For j = 2 to k:
     Select c_j \in C \setminus S_{j-1} that minimizes the resulting maximum distance:
         c_j = \arg\min_{c \in C \setminus S_{j-1}} \max_{u \in D} \min_{s \in S_{j-1} \cup \{c\}} d(s, u)
     S_j = S_{j-1} \cup { c_j }
   Complexity: O(k \cdot |C| \cdot |D|).

5. Swap-based P-Median Algorithm (Minisum Facility Location):
   Objective: Minimize the total (or average) response travel time:
       \min_{S \subseteq C, |S|=k} \sum_{u \in D} \min_{s \in S} d(s, u)
   Algorithm (Teitz & Bart 1-Interchange Local Search, 1968):
   - Step 1: Start with initial seed set S_0 of size k (e.g. from greedy k-center).
   - Step 2: In each pass, for each s \in S and candidate c \in C \setminus S:
     Evaluate test set S' = (S \setminus {s}) \cup {c}.
     If \sum_{u \in D} \min_{s' \in S'} d(s', u) < \sum_{u \in D} \min_{s' \in S} d(s', u) - \epsilon:
         S \leftarrow S' (perform swap).
     Repeat until no single swap improves the minisum objective (local optimum).
   Complexity: O(\text{iterations} \cdot k \cdot |C| \cdot |D|).

6. Multi-Source Dijkstra Isochrone Coverage:
   Seeding all active stations S simultaneously with cost 0 into a min-heap priority queue:
       T(v) = \min_{s \in S} d(s, v) \quad \forall v \in V
   Classifies demand vertices into 4 international response isochrone tiers:
       - Tier 1 (Golden Hour Priority): T(v) < 8 min (< 480 s) - Green (#10b981)
       - Tier 2 (Standard Urban Delay): 8 \le T(v) < 15 min (480-900 s) - Amber (#f59e0b)
       - Tier 3 (Extended Transit): 15 \le T(v) < 30 min (900-1800 s) - Red (#ef4444)
       - Tier 4 (Coverage Deficit): T(v) \ge 30 min (\ge 1800 s) - Dark Grey (#475569)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np

from backend.graph_builder import get_spatial_index

logger = logging.getLogger(__name__)

# Cache file path for candidate-demand precomputed distance matrix
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MATRIX_CACHE_PATH = os.path.join(CACHE_DIR, "placement_matrix_cache.npz")


@dataclass
class IsochroneBands:
    """Breakdown of demand points across 4 emergency response time bands."""

    under_8_min_count: int
    under_8_min_pct: float
    between_8_and_15_count: int
    between_8_and_15_pct: float
    between_15_and_30_count: int
    between_15_and_30_pct: float
    over_30_min_count: int
    over_30_min_pct: float


@dataclass
class PlacementResult:
    """Results from facility location optimization (1-center, k-center, or p-median)."""

    algorithm: str  # '1-center', 'k-center', 'p-median'
    k: int  # Number of facilities placed
    selected_nodes: List[int]  # Graph vertex IDs
    facility_details: List[Dict[str, Any]]  # Metadata with lat, lng, street names
    radius_sec: float  # Maximum travel time to any demand point in seconds
    radius_min: float  # Maximum travel time in minutes
    mean_travel_time_sec: float  # Average travel time in seconds
    mean_travel_time_min: float  # Average travel time in minutes
    bands: IsochroneBands  # Coverage tier breakdown


@dataclass
class CoverageResult:
    """Complete multi-source Dijkstra coverage evaluation over demand vertices."""

    total_demand_points: int
    station_nodes: List[int]
    bands: IsochroneBands
    mean_time_sec: float
    mean_time_min: float
    max_time_sec: float
    max_time_min: float
    demand_points_data: List[Dict[str, Any]]  # GeoJSON ready point properties


def sample_demand_grid(
    G: nx.MultiDiGraph,
    num_rows: int = 21,
    num_cols: int = 21,
    bbox: Tuple[float, float, float, float] = (77.565, 12.925, 77.655, 13.005),
) -> List[int]:
    r"""Sample 300-500 demand vertices on a regular 2D spatial grid.

    Formula:
        Grid = \{ (x_i, y_j) \mid x_i = x_{\min} + i \cdot \Delta x, y_j = y_{\min} + j \cdot \Delta y \}
        d_k = \arg\min_{v \in V} \text{dist}((x_i, y_j), (x_v, y_v))

    Args:
        G: Directed road graph.
        num_rows: Number of grid rows (latitudes). Default: 21.
        num_cols: Number of grid columns (longitudes). Default: 21.
        bbox: (min_lng, min_lat, max_lng, max_lat) bounding box.

    Returns:
        List of 300-500 unique graph vertex IDs representing demand centers.
    """
    min_lng, min_lat, max_lng, max_lat = bbox
    lats = np.linspace(min_lat, max_lat, num_rows)
    lngs = np.linspace(min_lng, max_lng, num_cols)

    # Flatten coordinates
    grid_coords = [(lng, lat) for lat in lats for lng in lngs]
    xs = [pt[0] for pt in grid_coords]
    ys = [pt[1] for pt in grid_coords]

    # Snap to nearest graph vertices using fast cKDTree
    tree, node_ids = get_spatial_index(G)
    pts = np.column_stack([np.asarray(ys, dtype=np.float64), np.asarray(xs, dtype=np.float64)])
    _, idxs = tree.query(pts)
    nearest_nodes = [node_ids[i] for i in idxs]

    # Deduplicate while preserving deterministic order and ensure native int types
    demand_nodes = [int(n) for n in dict.fromkeys(nearest_nodes)]
    # Step 5: Cap the number of demand nodes at 300 to minimize memory
    if len(demand_nodes) > 300:
        demand_nodes = demand_nodes[:300]
    logger.info("Sampled %d unique demand vertices from %d grid points.", len(demand_nodes), len(grid_coords))
    return demand_nodes


def get_candidate_junctions(
    G: nx.MultiDiGraph,
    hospital_nodes: List[int],
    num_rows: int = 12,
    num_cols: int = 12,
    bbox: Tuple[float, float, float, float] = (77.565, 12.925, 77.655, 13.005),
) -> List[int]:
    """Identify candidate ambulance placement sites: major junctions (deg >= 3) + hospital gates.

    Args:
        G: Directed road graph.
        hospital_nodes: Precomputed graph vertex IDs for regional trauma hospitals.
        num_rows: Grid rows for spatial dispersion. Default: 12.
        num_cols: Grid columns for spatial dispersion. Default: 12.
        bbox: Bounding box coordinates.

    Returns:
        Deduplicated list of candidate vertex IDs.
    """
    min_lng, min_lat, max_lng, max_lat = bbox
    lats = np.linspace(min_lat, max_lat, num_rows)
    lngs = np.linspace(min_lng, max_lng, num_cols)

    grid_pts = [(lng, lat) for lat in lats for lng in lngs]
    xs = [pt[0] for pt in grid_pts]
    ys = [pt[1] for pt in grid_pts]

    # Snap to nearest vertices in graph using cKDTree
    tree, node_ids = get_spatial_index(G)
    pts = np.column_stack([np.asarray(ys, dtype=np.float64), np.asarray(xs, dtype=np.float64)])
    _, idxs = tree.query(pts)
    snapped = [node_ids[i] for i in idxs]

    # Filter to vertices with degree >= 3 or hospital gates
    candidates = list(hospital_nodes)
    for node in snapped:
        # Check degree in graph
        if G.degree(node) >= 3:
            candidates.append(node)
        else:
            # If snapped node has deg < 3, check immediate neighbors
            found = False
            for nbr in G.successors(node):
                if G.degree(nbr) >= 3:
                    candidates.append(nbr)
                    found = True
                    break
            if not found:
                candidates.append(node)

    deduped = [int(n) for n in dict.fromkeys(candidates)]
    logger.info("Identified %d candidate placement sites (%d hospital gates included).", len(deduped), len(hospital_nodes))
    return deduped


def compute_candidate_demand_matrix(
    G: nx.MultiDiGraph,
    candidates: List[int],
    demand_nodes: List[int],
    weight: str = "travel_time",
    use_cache: bool = True,
) -> np.ndarray:
    r"""Compute or load the |C| x |D| shortest path travel time matrix between candidates and demand.

    Formula:
        M_{i, j} = d_G(c_i, d_j) \quad \text{for } c_i \in C, d_j \in D

    Args:
        G: Directed road graph.
        candidates: List of candidate vertex IDs (size |C|).
        demand_nodes: List of demand vertex IDs (size |D|).
        weight: Edge weight attribute (default: 'travel_time').
        use_cache: If True, caches matrix to disk for instantaneous reloads.

    Returns:
        NumPy 2D float array of shape (|C|, |D|) containing travel times in seconds.
    """
    num_c = len(candidates)
    num_d = len(demand_nodes)

    # Check if cached matrix exists and matches candidate/demand dimensions
    if use_cache and os.path.exists(MATRIX_CACHE_PATH):
        try:
            data = np.load(MATRIX_CACHE_PATH, allow_pickle=True)
            cached_c = data["candidates"]
            cached_d = data["demand_nodes"]
            cached_matrix = data["matrix"]
            if np.array_equal(cached_c, candidates) and np.array_equal(cached_d, demand_nodes):
                logger.info("Loaded precomputed (%d x %d) placement cost matrix from cache.", num_c, num_d)
                return cached_matrix
        except Exception as e:
            logger.warning("Cache load failed, recomputing matrix: %s", e)

    logger.info("Computing (%d x %d) Dijkstra travel time matrix across network...", num_c, num_d)
    matrix = np.full((num_c, num_d), 1e6, dtype=np.float64)

    demand_idx_map = {node_id: idx for idx, node_id in enumerate(demand_nodes)}

    for i, c in enumerate(candidates):
        try:
            # Single-source Dijkstra from candidate to all reachable nodes in G
            lengths = nx.single_source_dijkstra_path_length(G, source=c, weight=weight)
            for d_node, d_idx in demand_idx_map.items():
                if d_node in lengths:
                    matrix[i, d_idx] = lengths[d_node]
        except Exception as e:
            logger.error("Dijkstra failed for candidate node %s: %s", c, e)

    # Save to disk cache
    if use_cache:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            np.savez_compressed(
                MATRIX_CACHE_PATH,
                candidates=np.array(candidates),
                demand_nodes=np.array(demand_nodes),
                matrix=matrix,
            )
            logger.info("Saved placement cost matrix to %s", MATRIX_CACHE_PATH)
        except Exception as e:
            logger.warning("Failed to save matrix cache: %s", e)

    return matrix


def evaluate_isochrone_bands(distances_sec: np.ndarray) -> IsochroneBands:
    """Categorize travel times into 4 standardized emergency response isochrone tiers.

    Tiers:
    - Under 8 min (< 480 s): Golden Hour Priority (Green)
    - 8 to 15 min (480-900 s): Moderate Response (Amber)
    - 15 to 30 min (900-1800 s): Extended Transit (Red)
    - Over 30 min (>= 1800 s): Coverage Deficit (Dark Grey)
    """
    total = len(distances_sec)
    if total == 0:
        return IsochroneBands(0, 0.0, 0, 0.0, 0, 0.0, 0, 0.0)

    u8 = int(np.sum(distances_sec < 480.0))
    b8_15 = int(np.sum((distances_sec >= 480.0) & (distances_sec < 900.0)))
    b15_30 = int(np.sum((distances_sec >= 900.0) & (distances_sec < 1800.0)))
    o30 = int(np.sum(distances_sec >= 1800.0))

    return IsochroneBands(
        under_8_min_count=u8,
        under_8_min_pct=round(u8 / total * 100.0, 1),
        between_8_and_15_count=b8_15,
        between_8_and_15_pct=round(b8_15 / total * 100.0, 1),
        between_15_and_30_count=b15_30,
        between_15_and_30_pct=round(b15_30 / total * 100.0, 1),
        over_30_min_count=o30,
        over_30_min_pct=round(o30 / total * 100.0, 1),
    )


def compute_eccentricity_and_center(
    G: nx.MultiDiGraph,
    candidates: List[int],
    demand_nodes: List[int],
    cost_matrix: Optional[np.ndarray] = None,
) -> PlacementResult:
    r"""Compute eccentricity over the demand set, returning the graph center and radius (k=1).

    Formula:
        e_D(c) = \max_{u \in D} d(c, u)
        c^* = \arg\min_{c \in C} e_D(c)
        \text{rad}_D(G) = e_D(c^*)

    Args:
        G: Directed road graph.
        candidates: Candidate placement vertices.
        demand_nodes: Demand vertices.
        cost_matrix: Precomputed (|C|, |D|) distance matrix.

    Returns:
        PlacementResult with the 1-center location, radius, and coverage breakdown.
    """
    if cost_matrix is None:
        cost_matrix = compute_candidate_demand_matrix(G, candidates, demand_nodes)

    # Eccentricity of each candidate = maximum distance to any demand point
    eccentricities = np.max(cost_matrix, axis=1)

    center_idx = int(np.argmin(eccentricities))
    center_node = int(candidates[center_idx])
    radius_sec = float(eccentricities[center_idx])

    center_distances = cost_matrix[center_idx, :]
    mean_sec = float(np.mean(center_distances))
    bands = evaluate_isochrone_bands(center_distances)

    node_data = G.nodes[center_node]
    facility_details = [
        {
            "id": f"center-1",
            "name": f"Optimal 1-Center Base (Node {center_node})",
            "node_id": int(center_node),
            "lat": float(node_data["y"]),
            "lng": float(node_data["x"]),
            "eccentricity_sec": round(radius_sec, 1),
            "eccentricity_min": round(radius_sec / 60.0, 2),
        }
    ]

    return PlacementResult(
        algorithm="1-center",
        k=1,
        selected_nodes=[int(center_node)],
        facility_details=facility_details,
        radius_sec=round(radius_sec, 1),
        radius_min=round(radius_sec / 60.0, 2),
        mean_travel_time_sec=round(mean_sec, 1),
        mean_travel_time_min=round(mean_sec / 60.0, 2),
        bands=bands,
    )


def greedy_k_center(
    G: nx.MultiDiGraph,
    candidates: List[int],
    demand_nodes: List[int],
    k: int = 4,
    cost_matrix: Optional[np.ndarray] = None,
) -> PlacementResult:
    r"""Compute optimal ambulance station sites using the Greedy K-Center algorithm (Minimax).

    Formula:
        \min_{S \subseteq C, |S|=k} \max_{u \in D} \min_{s \in S} d(s, u)

    Iteratively selects the candidate that minimizes the worst-case maximum distance to any demand point.

    Args:
        G: Directed road graph.
        candidates: Candidate placement vertices.
        demand_nodes: Demand vertices.
        k: Target number of ambulance stations to place.
        cost_matrix: Precomputed (|C|, |D|) distance matrix.

    Returns:
        PlacementResult with k selected stations and coverage metrics.
    """
    if cost_matrix is None:
        cost_matrix = compute_candidate_demand_matrix(G, candidates, demand_nodes)

    num_candidates = len(candidates)
    k = max(1, min(k, num_candidates))

    # Step 1: Start with 1-center
    eccentricities = np.max(cost_matrix, axis=1)
    first_center_idx = int(np.argmin(eccentricities))
    selected_indices: List[int] = [first_center_idx]

    # Step 2: Iteratively add candidate minimizing the maximum response time
    for _ in range(1, k):
        best_candidate: Optional[int] = None
        best_max_dist = float("inf")

        for c_idx in range(num_candidates):
            if c_idx in selected_indices:
                continue

            test_selection = selected_indices + [c_idx]
            # Minimum distance from any selected center to each demand point
            min_distances = np.min(cost_matrix[test_selection, :], axis=0)
            max_dist = float(np.max(min_distances))

            if max_dist < best_max_dist:
                best_max_dist = max_dist
                best_candidate = c_idx

        if best_candidate is not None:
            selected_indices.append(best_candidate)
        else:
            break

    selected_nodes = [int(candidates[idx]) for idx in selected_indices]
    final_distances = np.min(cost_matrix[selected_indices, :], axis=0)

    radius_sec = float(np.max(final_distances))
    mean_sec = float(np.mean(final_distances))
    bands = evaluate_isochrone_bands(final_distances)

    facility_details = []
    for rank, (c_idx, node_id) in enumerate(zip(selected_indices, selected_nodes)):
        node_data = G.nodes[node_id]
        facility_details.append(
            {
                "id": f"kcenter-{rank + 1}",
                "name": f"K-Center Station #{rank + 1} (Node {node_id})",
                "node_id": int(node_id),
                "lat": float(node_data["y"]),
                "lng": float(node_data["x"]),
                "rank": int(rank + 1),
            }
        )

    return PlacementResult(
        algorithm="k-center",
        k=len(selected_nodes),
        selected_nodes=selected_nodes,
        facility_details=facility_details,
        radius_sec=round(radius_sec, 1),
        radius_min=round(radius_sec / 60.0, 2),
        mean_travel_time_sec=round(mean_sec, 1),
        mean_travel_time_min=round(mean_sec / 60.0, 2),
        bands=bands,
    )


def swap_p_median(
    G: nx.MultiDiGraph,
    candidates: List[int],
    demand_nodes: List[int],
    k: int = 4,
    max_swaps: int = 30,
    cost_matrix: Optional[np.ndarray] = None,
) -> PlacementResult:
    r"""Compute optimal ambulance station sites using Teitz & Bart Swap-Based P-Median (Minisum).

    Formula:
        \min_{S \subseteq C, |S|=k} \sum_{u \in D} \min_{s \in S} d(s, u)

    Starts with greedy k-center seed and explores 1-interchange vertex swaps:
        S' = (S \setminus \{s\}) \cup \{c\}
    until reaching a local optimum where no single swap reduces total network travel time.

    Args:
        G: Directed road graph.
        candidates: Candidate placement vertices.
        demand_nodes: Demand vertices.
        k: Target number of ambulance stations to place.
        max_swaps: Maximum swap iterations. Default: 30.
        cost_matrix: Precomputed (|C|, |D|) distance matrix.

    Returns:
        PlacementResult with k selected stations optimizing average response time.
    """
    if cost_matrix is None:
        cost_matrix = compute_candidate_demand_matrix(G, candidates, demand_nodes)

    num_candidates = len(candidates)
    k = max(1, min(k, num_candidates))

    # Initialize with greedy k-center for fast convergence
    initial_kcenter = greedy_k_center(G, candidates, demand_nodes, k=k, cost_matrix=cost_matrix)
    current_selection = [candidates.index(n) for n in initial_kcenter.selected_nodes]

    current_sum = float(np.sum(np.min(cost_matrix[current_selection, :], axis=0)))

    # Teitz-Bart 1-swap local search
    for iteration in range(max_swaps):
        best_swap: Optional[Tuple[int, int]] = None
        best_sum = current_sum

        for s_idx_pos in range(len(current_selection)):
            for c_cand in range(num_candidates):
                if c_cand in current_selection:
                    continue

                # Construct trial set
                trial = list(current_selection)
                trial[s_idx_pos] = c_cand
                trial_sum = float(np.sum(np.min(cost_matrix[trial, :], axis=0)))

                if trial_sum < best_sum - 1.0:  # Minimum 1.0 second threshold to ensure progress
                    best_sum = trial_sum
                    best_swap = (s_idx_pos, c_cand)
                    break  # First-improvement heuristic for high speed
            if best_swap:
                break

        if best_swap is not None:
            pos, new_c = best_swap
            current_selection[pos] = new_c
            current_sum = best_sum
        else:
            # Reached local optimum
            break

    selected_nodes = [int(candidates[idx]) for idx in current_selection]
    final_distances = np.min(cost_matrix[current_selection, :], axis=0)

    radius_sec = float(np.max(final_distances))
    mean_sec = float(np.mean(final_distances))
    bands = evaluate_isochrone_bands(final_distances)

    facility_details = []
    for rank, (c_idx, node_id) in enumerate(zip(current_selection, selected_nodes)):
        node_data = G.nodes[node_id]
        facility_details.append(
            {
                "id": f"pmedian-{rank + 1}",
                "name": f"P-Median Station #{rank + 1} (Node {node_id})",
                "node_id": int(node_id),
                "lat": float(node_data["y"]),
                "lng": float(node_data["x"]),
                "rank": int(rank + 1),
            }
        )

    return PlacementResult(
        algorithm="p-median",
        k=len(selected_nodes),
        selected_nodes=selected_nodes,
        facility_details=facility_details,
        radius_sec=round(radius_sec, 1),
        radius_min=round(radius_sec / 60.0, 2),
        mean_travel_time_sec=round(mean_sec, 1),
        mean_travel_time_min=round(mean_sec / 60.0, 2),
        bands=bands,
    )


def compute_multi_source_coverage(
    G: nx.MultiDiGraph,
    station_nodes: List[int],
    demand_nodes: Optional[List[int]] = None,
    weight: str = "travel_time",
) -> CoverageResult:
    r"""Compute multi-source Dijkstra coverage from all active stations across demand points.

    Formula:
        T(u) = \min_{s \in S} d_G(s, u) \quad \forall u \in D

    Args:
        G: Directed road graph.
        station_nodes: List of ambulance base vertex IDs.
        demand_nodes: Optional list of demand vertices (if None, samples grid).
        weight: Edge weight attribute (default: 'travel_time').

    Returns:
        CoverageResult with isochrone bands and per-vertex travel times.
    """
    if demand_nodes is None:
        demand_nodes = sample_demand_grid(G)

    # Multi-source Dijkstra: seeds all stations at distance 0
    lengths = nx.multi_source_dijkstra_path_length(G, sources=station_nodes, weight=weight)

    distances = []
    demand_points_data = []

    for d_node in demand_nodes:
        if d_node not in G:
            continue
        time_sec = lengths.get(d_node, 1e6)
        time_min = round(time_sec / 60.0, 2)
        node_data = G.nodes[d_node]
        lat = float(node_data["y"])
        lng = float(node_data["x"])

        # Determine band
        if time_sec < 480.0:
            band_name = "under_8_min"
            band_label = "< 8 min (Golden Hour)"
            color = "#10b981"  # Green
        elif time_sec < 900.0:
            band_name = "8_to_15_min"
            band_label = "8 - 15 min"
            color = "#f59e0b"  # Amber
        elif time_sec < 1800.0:
            band_name = "15_to_30_min"
            band_label = "15 - 30 min"
            color = "#ef4444"  # Red
        else:
            band_name = "over_30_min"
            band_label = "> 30 min (Deficit)"
            color = "#475569"  # Dark Grey

        distances.append(time_sec)
        demand_points_data.append(
            {
                "node_id": int(d_node),
                "lat": float(lat),
                "lng": float(lng),
                "time_sec": float(round(time_sec, 1)),
                "time_min": float(time_min),
                "band": str(band_name),
                "band_label": str(band_label),
                "color": str(color),
            }
        )

    dist_arr = np.array(distances)
    bands = evaluate_isochrone_bands(dist_arr)
    mean_sec = float(np.mean(dist_arr[dist_arr < 1e5])) if len(dist_arr) > 0 else 0.0
    max_sec = float(np.max(dist_arr[dist_arr < 1e5])) if len(dist_arr) > 0 else 0.0

    return CoverageResult(
        total_demand_points=int(len(demand_points_data)),
        station_nodes=[int(n) for n in station_nodes],
        bands=bands,
        mean_time_sec=round(mean_sec, 1),
        mean_time_min=round(mean_sec / 60.0, 2),
        max_time_sec=round(max_sec, 1),
        max_time_min=round(max_sec / 60.0, 2),
        demand_points_data=demand_points_data,
    )
