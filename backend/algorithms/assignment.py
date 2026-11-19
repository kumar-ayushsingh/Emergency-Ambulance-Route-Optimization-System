r"""Emergency Ambulance Assignment Algorithms (Hungarian Min-Sum & Minimax Bottleneck).

Academic Context:
Discrete Mathematics · Module 4: Graph Theory & Operations Research
Problem Statement: Bipartite Matching and Multi-Agent Emergency Dispatch.

Mathematical Formulation:
Given a weighted road network G = (V, E, w) where edge weights w(e) represent travel
time in seconds. Let:
- A = {a_1, a_2, ..., a_M} denote the set of available emergency ambulances located
  at station vertices {s_1, s_2, ..., s_M} \subseteq V.
- B = {b_1, b_2, ..., b_N} denote the set of emergency accident locations snapped to
  graph vertices {u_1, u_2, ..., u_N} \subseteq V (with 1 <= N <= 5).

The Cost Matrix C \in \mathbb{R}_{\ge 0}^{M \times N} has entries:
    C_{i, j} = d_G(s_i, u_j) = \text{shortest travel time (seconds) from ambulance } a_i \text{ to accident } b_j
computed via Dijkstra's algorithm.

Matrix Padding for Unequal Dimensions (M != N):
Standard textbook Hungarian algorithm requires a square K x K matrix where K = max(M, N):
- If M > N (more ambulances than incidents):
  Pad with (M - N) dummy accident columns with cost 0. Ambulances assigned to dummy columns
  remain on standby at base with zero penalty.
- If M < N (fewer ambulances than incidents):
  Pad with (N - M) dummy ambulance rows with penalty cost 10^7.

Dual Assignment Objectives:
1. Min-Sum Assignment (Total Network Travel Time):
       \min_{\pi} \sum_{j=1}^N C_{\pi(j), j}
   Solved in O(K^3) time using Kuhn-Munkres (Hungarian) algorithm via
   scipy.optimize.linear_sum_assignment.

2. Bottleneck Assignment Problem (BAP - Minimax Worst-Case Travel Time):
       \min_{\pi} \max_{j=1}^N C_{\pi(j), j}
   Solves for social equity / fairness: ensures no single casualty waits longer than
   strictly necessary.
   Solved via Threshold Binary Search over unique cost values U = sorted(unique(C)):
   - Feasibility check at threshold \theta tests whether a full matching of size N exists
     in the bipartite subgraph with edges E_\theta = {(i, j) \mid C_{i, j} <= \theta}.
   - The minimal feasible threshold \theta^* is the exact bottleneck response time.
   - Secondary tie-breaker: among matchings with max <= \theta^*, Hungarian selects the one
     minimizing total sum.

Complexity Analysis:
- Distance Matrix Computation: O(min(M_stations, M) * (|V| + |E| \log |V|)) via Dijkstra.
- Hungarian Min-Sum: O(K^3) where K = max(M, N) <= 14.
- Bottleneck Assignment: O(\log(MN) * K^3) via binary search over unique entries.
- Brute Force Cross-Check (for tests): O(N! * N) testing all permutations up to 6x6.
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
from scipy.optimize import linear_sum_assignment

from backend.algorithms.dijkstra import dijkstra_shortest_path

logger = logging.getLogger(__name__)

# Standard palette for up to 6 distinct assigned routes
ASSIGNMENT_COLORS = [
    "#10b981",  # 1: Emerald Green
    "#f59e0b",  # 2: Amber / Orange
    "#3b82f6",  # 3: Electric Blue
    "#ec4899",  # 4: Hot Pink / Magenta
    "#8b5cf6",  # 5: Purple / Violet
    "#06b6d4",  # 6: Cyan
]


@dataclass
class AmbulanceUnit:
    """Represents an individual physical ambulance unit stationed at a base."""

    id: str
    name: str
    station_id: str
    station_name: str
    lat: float
    lng: float
    node_id: int
    ambulance_type: str = "ALS"


@dataclass
class AccidentSite:
    """Represents an emergency incident location."""

    id: str
    index: int  # 1-based index (1 to 5)
    lat: float
    lng: float
    snapped_node_id: int


@dataclass
class SingleAssignment:
    """Represents a matched ambulance-to-accident emergency assignment."""

    ambulance_id: str
    ambulance_name: str
    station_id: str
    station_name: str
    accident_id: str
    accident_index: int
    accident_lat: float
    accident_lng: float
    travel_time_sec: float
    travel_time_min: float
    distance_m: float
    distance_km: float
    color: str
    is_bottleneck: bool
    path_nodes: List[int]
    path_coordinates: List[List[float]]  # [[lng, lat], ...] for GeoJSON LineString


@dataclass
class AssignmentResult:
    """Complete multi-agent assignment solution."""

    objective: str  # "min_sum" or "bottleneck"
    total_time_sec: float
    total_time_min: float
    max_time_sec: float
    max_time_min: float
    mean_time_sec: float
    mean_time_min: float
    assignments: List[SingleAssignment]
    unassigned_ambulances: List[str]
    cost_matrix_sec: List[List[float]]
    cost_matrix_min: List[List[float]]
    ambulance_labels: List[str]
    accident_labels: List[str]
    padded_shape: Tuple[int, int]


def build_ambulance_fleet(stations_data: List[Dict[str, Any]], station_node_map: Dict[str, int]) -> List[AmbulanceUnit]:
    """Expand base stations into individual physical ambulance units.

    Each station in stations.json has 'ambulances_available' (e.g. 4 at Majestic, 4 at Koramangala, etc.).
    This function instantiates individual ambulance units for multi-agent assignment.

    Args:
        stations_data: List of station dictionaries loaded from stations.json.
        station_node_map: Mapping from station_id to nearest graph node ID.

    Returns:
        List of AmbulanceUnit objects (typically 14 available units across Bengaluru).
    """
    fleet: List[AmbulanceUnit] = []
    for stn in stations_data:
        stn_id = stn["id"]
        stn_name = stn["name"]
        lat = float(stn["lat"])
        lng = float(stn["lng"])
        node_id = int(station_node_map.get(stn_id, 0))
        count = int(stn.get("ambulances_available", 2))
        als_count = int(stn.get("als_ambulances", count // 2))

        short_code = stn_id.replace("station_", "").upper()[:3]

        for i in range(count):
            unit_num = i + 1
            amb_type = "ALS" if i < als_count else "BLS"
            fleet.append(
                AmbulanceUnit(
                    id=f"{stn_id}_unit_{unit_num}",
                    name=f"{stn.get('short_name', stn_name)} Unit {unit_num} ({amb_type})",
                    station_id=stn_id,
                    station_name=stn_name,
                    lat=lat,
                    lng=lng,
                    node_id=node_id,
                    ambulance_type=amb_type,
                )
            )

    logger.info("Instantiated %d ambulance units across %d base stations.", len(fleet), len(stations_data))
    return fleet


def build_cost_matrix(
    G: nx.MultiDiGraph,
    fleet: List[AmbulanceUnit],
    accidents: List[AccidentSite],
    weight: str = "travel_time",
) -> Tuple[np.ndarray, Dict[Tuple[int, int], Tuple[List[int], float, float]]]:
    r"""Compute the (|Fleet| x |Accidents|) Dijkstra travel-time cost matrix.

    Formula:
        C_{i, j} = d_G(s_i, u_j) \quad \text{for } a_i \in Fleet, b_j \in Accidents

    Optimization:
        Groups ambulances by distinct base station node so Dijkstra SSSP is run at most
        once per unique base station (at most 4 runs for Bengaluru).

    Args:
        G: Directed road network.
        fleet: List of available ambulance units (rows).
        accidents: List of accident incident sites (columns).
        weight: Edge weight attribute (default: 'travel_time').

    Returns:
        cost_matrix: (M, N) NumPy array of travel times in seconds.
        route_cache: Mapping (station_node, accident_node) -> (path, time_sec, dist_m).
    """
    num_ambulances = len(fleet)
    num_accidents = len(accidents)

    cost_matrix = np.zeros((num_ambulances, num_accidents), dtype=np.float64)
    route_cache: Dict[Tuple[int, int], Tuple[List[int], float, float]] = {}

    # Unique station vertices to minimize Dijkstra calls
    unique_station_nodes = list(dict.fromkeys(amb.node_id for amb in fleet))

    for stn_node in unique_station_nodes:
        for acc in accidents:
            acc_node = acc.snapped_node_id
            cache_key = (stn_node, acc_node)

            if cache_key not in route_cache:
                d_res = dijkstra_shortest_path(G, source=stn_node, target=acc_node, weight=weight)
                if d_res is not None:
                    route_cache[cache_key] = (d_res.path, float(d_res.cost), float(d_res.distance))
                else:
                    # In case of partitioned graph
                    route_cache[cache_key] = ([], 1e6, 1e6)

    # Populate cost matrix for each ambulance unit
    for i, amb in enumerate(fleet):
        for j, acc in enumerate(accidents):
            cache_key = (amb.node_id, acc.snapped_node_id)
            time_sec = route_cache[cache_key][1]
            cost_matrix[i, j] = time_sec

    return cost_matrix, route_cache


def pad_cost_matrix(cost_matrix: np.ndarray, pad_value: float = 0.0) -> Tuple[np.ndarray, int, int]:
    r"""Pad an (M x N) rectangular cost matrix to a square (K x K) matrix.

    In Discrete Mathematics, Kuhn-Munkres is formulated on square bipartite graphs:
    - If M > N: Pad with (M - N) dummy columns with cost 0.0 (idle ambulances).
    - If M < N: Pad with (N - M) dummy rows with penalty cost 10^7.
    - If M == N: No padding required.

    Args:
        cost_matrix: Original (M x N) cost matrix.
        pad_value: Fill value for dummy elements (default: 0.0 for extra ambulances).

    Returns:
        padded_matrix: (K x K) square matrix where K = max(M, N).
        orig_rows: Original row count M.
        orig_cols: Original column count N.
    """
    m, n = cost_matrix.shape
    k = max(m, n)

    if m == n:
        return cost_matrix.copy(), m, n

    padded = np.full((k, k), fill_value=pad_value, dtype=np.float64)
    padded[:m, :n] = cost_matrix

    # If dummy ambulances are needed (M < N), set high penalty so real ones are prioritized
    if m < n:
        padded[m:, :] = 1e7

    return padded, m, n


def solve_min_sum_assignment(cost_matrix: np.ndarray, pad: bool = True) -> Tuple[List[int], List[int], float]:
    r"""Solve the Linear Sum Assignment Problem (Min-Sum) using the Hungarian Algorithm.

    Objective:
        \min_{\pi} \sum_{j=0}^{N-1} C_{\pi(j), j}

    Args:
        cost_matrix: (M x N) travel times matrix.
        pad: If True, explicitly pads to K x K before solving per textbook specification.

    Returns:
        row_indices: Assigned ambulance row index for each accident.
        col_indices: Accident column index [0, 1, ..., N-1].
        total_cost: Sum of travel times across assigned accidents.
    """
    m, n = cost_matrix.shape

    if pad and m != n:
        padded, orig_m, orig_n = pad_cost_matrix(cost_matrix, pad_value=0.0)
        row_ind, col_ind = linear_sum_assignment(padded)

        # Filter out dummy assignments: keep only pairs matching original real accidents
        real_pairs = [(int(r), int(c)) for r, c in zip(row_ind, col_ind) if r < orig_m and c < orig_n]
        # Sort by accident column index
        real_pairs.sort(key=lambda p: p[1])

        sel_rows = [p[0] for p in real_pairs]
        sel_cols = [p[1] for p in real_pairs]
    else:
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        sel_rows = [int(r) for r in row_ind]
        sel_cols = [int(c) for c in col_ind]

    total_cost = float(sum(cost_matrix[r, c] for r, c in zip(sel_rows, sel_cols)))
    return sel_rows, sel_cols, total_cost


def solve_bottleneck_assignment(cost_matrix: np.ndarray, pad: bool = True) -> Tuple[List[int], List[int], float]:
    r"""Solve the Bottleneck Assignment Problem (BAP) minimizing worst-case travel time.

    Objective:
        \min_{\pi} \max_{j=0}^{N-1} C_{\pi(j), j}

    Method:
        1. Threshold Binary Search over sorted unique cost entries U = unique(C).
        2. Feasibility test at threshold \theta:
           Form binary indicator matrix B = (C <= \theta).
           Pad B to K x K and solve with linear_sum_assignment.
           If sum(B[r, c] == 0) == 0, then a complete matching exists with every edge <= \theta.
        3. Identify the minimal feasible threshold \theta^*.
        4. Secondary Optimization (Tie-Breaker):
           Build weight matrix W_{i, j} = C_{i, j} if C_{i, j} <= \theta^* else 10^8.
           Solve with Hungarian on W to choose the assignment that minimizes total sum
           while strictly adhering to the minimax bound \max <= \theta^*.

    Args:
        cost_matrix: (M x N) travel times matrix.
        pad: If True, pads cost matrix to square K x K.

    Returns:
        row_indices: Assigned ambulance row index for each accident.
        col_indices: Accident column index [0, 1, ..., N-1].
        bottleneck_cost: Exact worst-case travel time \theta^*.
    """
    m, n = cost_matrix.shape
    unique_costs = np.sort(np.unique(cost_matrix))

    def is_feasible(threshold: float) -> bool:
        """Check if all n accidents can be matched with edge costs <= threshold."""
        # 0 if valid (cost <= threshold), 1 if invalid
        indicator = np.where(cost_matrix <= threshold, 0.0, 1.0)
        padded_ind, _, _ = pad_cost_matrix(indicator, pad_value=0.0)
        r_ind, c_ind = linear_sum_assignment(padded_ind)

        # Count violations on real accident assignments
        violations = sum(indicator[r, c] for r, c in zip(r_ind, c_ind) if r < m and c < n)
        return bool(violations == 0)

    # Binary search over unique values
    low = 0
    high = len(unique_costs) - 1
    best_idx = high

    while low <= high:
        mid = (low + high) // 2
        cand_theta = float(unique_costs[mid])
        if is_feasible(cand_theta):
            best_idx = mid
            high = mid - 1  # Seek smaller bottleneck
        else:
            low = mid + 1

    optimal_bottleneck = float(unique_costs[best_idx])

    # Secondary tie-breaker: minimize total sum subject to cost <= optimal_bottleneck
    penalty_matrix = np.where(cost_matrix <= optimal_bottleneck, cost_matrix, 1e8)
    padded_pen, _, _ = pad_cost_matrix(penalty_matrix, pad_value=0.0)
    row_ind, col_ind = linear_sum_assignment(padded_pen)

    real_pairs = [(int(r), int(c)) for r, c in zip(row_ind, col_ind) if r < m and c < n]
    real_pairs.sort(key=lambda p: p[1])

    sel_rows = [p[0] for p in real_pairs]
    sel_cols = [p[1] for p in real_pairs]
    actual_max = float(max(cost_matrix[r, c] for r, c in zip(sel_rows, sel_cols)))

    return sel_rows, sel_cols, actual_max


def brute_force_assignment(cost_matrix: np.ndarray) -> Dict[str, Any]:
    r"""Brute-force assignment solver evaluating all possible permutations for validation.

    Complexity:
        O(P(M, N) * N) = O(M! / (M - N)! * N)
        For N <= 6, evaluates in <= 5 milliseconds.

    Used strictly for cross-validation in unit tests against Hungarian and Bottleneck solvers.

    Args:
        cost_matrix: (M x N) matrix with M >= N.

    Returns:
        Dictionary with exact optimal min_sum, min_sum_perm, bottleneck, bottleneck_perm.
    """
    m, n = cost_matrix.shape
    assert m >= n, "Brute force requires at least as many rows as columns (M >= N)."

    best_sum = float("inf")
    best_sum_perm: Optional[Tuple[int, ...]] = None

    best_bottleneck = float("inf")
    best_bot_perm: Optional[Tuple[int, ...]] = None
    best_bot_sum = float("inf")

    # Generate all ordered choices of n distinct ambulances from m candidates
    for perm in itertools.permutations(range(m), n):
        costs = [float(cost_matrix[perm[j], j]) for j in range(n)]
        curr_sum = sum(costs)
        curr_max = max(costs)

        if curr_sum < best_sum - 1e-9:
            best_sum = curr_sum
            best_sum_perm = perm

        if curr_max < best_bottleneck - 1e-9 or (abs(curr_max - best_bottleneck) <= 1e-9 and curr_sum < best_bot_sum):
            best_bottleneck = curr_max
            best_bot_perm = perm
            best_bot_sum = curr_sum

    return {
        "min_sum": round(best_sum, 4),
        "min_sum_perm": list(best_sum_perm) if best_sum_perm else [],
        "bottleneck": round(best_bottleneck, 4),
        "bottleneck_perm": list(best_bot_perm) if best_bot_perm else [],
    }


def dispatch_and_route_assignment(
    G: nx.MultiDiGraph,
    fleet: List[AmbulanceUnit],
    accidents: List[AccidentSite],
    objective: str = "min_sum",
) -> AssignmentResult:
    """Execute complete multi-agent assignment, build routes, and format GeoJSON metadata.

    Args:
        G: Directed road network.
        fleet: Available ambulance units.
        accidents: User placed accident sites (up to 5).
        objective: 'min_sum' (Hungarian) or 'bottleneck' (minimax worst-case).

    Returns:
        AssignmentResult dataclass with matched pairs, GeoJSON routes, and telemetry.
    """
    cost_matrix, route_cache = build_cost_matrix(G, fleet, accidents)

    if objective == "bottleneck":
        sel_rows, sel_cols, bottleneck_cost = solve_bottleneck_assignment(cost_matrix, pad=True)
    else:  # default min_sum
        sel_rows, sel_cols, _ = solve_min_sum_assignment(cost_matrix, pad=True)

    assigned_costs = [float(cost_matrix[r, c]) for r, c in zip(sel_rows, sel_cols)]
    total_time_sec = float(sum(assigned_costs))
    max_time_sec = float(max(assigned_costs)) if assigned_costs else 0.0
    mean_time_sec = float(np.mean(assigned_costs)) if assigned_costs else 0.0

    # Build individual assignments
    assignments: List[SingleAssignment] = []
    assigned_ambulance_ids = set()

    for rank, (r, c) in enumerate(zip(sel_rows, sel_cols)):
        amb = fleet[r]
        acc = accidents[c]
        time_sec = float(cost_matrix[r, c])
        cache_key = (amb.node_id, acc.snapped_node_id)
        path_nodes, _, dist_m = route_cache[cache_key]

        assigned_ambulance_ids.add(amb.id)
        is_bottleneck = abs(time_sec - max_time_sec) < 1e-4

        # Convert path nodes to [[lng, lat], ...] coordinates
        coords = []
        for node in path_nodes:
            if node in G:
                nd = G.nodes[node]
                coords.append([float(nd["x"]), float(nd["y"])])

        color = ASSIGNMENT_COLORS[rank % len(ASSIGNMENT_COLORS)]

        assignments.append(
            SingleAssignment(
                ambulance_id=amb.id,
                ambulance_name=amb.name,
                station_id=amb.station_id,
                station_name=amb.station_name,
                accident_id=acc.id,
                accident_index=acc.index,
                accident_lat=acc.lat,
                accident_lng=acc.lng,
                travel_time_sec=round(time_sec, 1),
                travel_time_min=round(time_sec / 60.0, 2),
                distance_m=round(dist_m, 1),
                distance_km=round(dist_m / 1000.0, 2),
                color=color,
                is_bottleneck=is_bottleneck,
                path_nodes=[int(n) for n in path_nodes],
                path_coordinates=coords,
            )
        )

    unassigned = [amb.id for amb in fleet if amb.id not in assigned_ambulance_ids]

    # Matrix for UI display
    matrix_sec = [[round(float(c), 1) for c in row] for row in cost_matrix]
    matrix_min = [[round(float(c) / 60.0, 2) for c in row] for row in cost_matrix]
    ambulance_labels = [amb.name for amb in fleet]
    accident_labels = [f"Accident #{acc.index}" for acc in accidents]

    return AssignmentResult(
        objective=objective,
        total_time_sec=round(total_time_sec, 1),
        total_time_min=round(total_time_sec / 60.0, 2),
        max_time_sec=round(max_time_sec, 1),
        max_time_min=round(max_time_sec / 60.0, 2),
        mean_time_sec=round(mean_time_sec, 1),
        mean_time_min=round(mean_time_sec / 60.0, 2),
        assignments=assignments,
        unassigned_ambulances=unassigned,
        cost_matrix_sec=matrix_sec,
        cost_matrix_min=matrix_min,
        ambulance_labels=ambulance_labels,
        accident_labels=accident_labels,
        padded_shape=(max(len(fleet), len(accidents)), max(len(fleet), len(accidents))),
    )
