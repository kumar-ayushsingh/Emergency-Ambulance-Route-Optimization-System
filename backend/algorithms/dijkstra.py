r"""Dijkstra's Shortest Path Algorithm (Priority-Queue / Min-Heap Implementation).

Academic Context:
Discrete Mathematics · Module 4: Graph Theory
Problem Statement: Single-Source Shortest Path (SSSP) on non-negative weighted graphs.

Mathematical Formulation:
Given a weighted directed graph G = (V, E) with a non-negative weight function
w: E -> R_>=0 (representing travel time in seconds), and a source vertex s in V.
Dijkstra's algorithm finds the path P = (v_0, v_1, ..., v_k) from s to target t
such that the total weight:
    w(P) = \sum_{i=1}^k w(v_{i-1}, v_i)
is minimized.

Complexity Analysis:
- Time Complexity: O((|V| + |E|) \log |V|) using a binary min-heap.
  Each vertex is extracted from the heap at most once: |V| * O(\log |V|).
  Each directed edge is relaxed at most once: |E| * O(\log |V|) pushes to heap.
- Space Complexity: O(|V|) to maintain distances, predecessors, and the priority queue.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx


@dataclass
class DijkstraResult:
    """Encapsulates the result of a Dijkstra shortest-path computation."""

    path: List[Any]
    cost: float  # Total travel time in seconds
    distance: float  # Total physical length in meters
    nodes_expanded: int  # Number of vertices settled (extracted from min-heap)
    visited_nodes: List[Any]  # Order of node settlement (for algorithm visualization)


def dijkstra_shortest_path(
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    source: Any,
    target: Any,
    weight: str = "travel_time",
) -> Optional[DijkstraResult]:
    r"""Compute the single-pair shortest path from source to target using a min-heap.

    Algorithm Steps:
    1. Initialize distance to source as 0.0, and all other vertices as \infty.
    2. Maintain a priority queue (min-heap) of pairs (dist, vertex).
    3. Greedily extract vertex u with minimum tentative distance (settled vertex).
    4. If u == target, terminate early (goal-directed search).
    5. For each outgoing edge (u, v):
       Relax edge: if dist[u] + w(u, v) < dist[v], update dist[v] and push to heap.
    6. Reconstruct the shortest path backwards from target using predecessor map.

    Args:
        G: NetworkX graph (MultiDiGraph, DiGraph, or Graph).
        source: Starting vertex identifier in V.
        target: Destination vertex identifier in V.
        weight: Edge attribute key to minimize (default: 'travel_time').

    Returns:
        DijkstraResult containing path, total time (cost), physical distance,
        and nodes_expanded count; or None if target is unreachable.
    """
    if source not in G or target not in G:
        return None

    if source == target:
        return DijkstraResult(
            path=[source],
            cost=0.0,
            distance=0.0,
            nodes_expanded=1,
            visited_nodes=[source],
        )

    # Tentative distance dictionary: dist[v] = shortest known distance from source to v
    dist: Dict[Any, float] = {source: 0.0}

    # Predecessor dictionary for path reconstruction: pred[v] = predecessor of v on shortest path
    pred: Dict[Any, Any] = {}

    # Physical distance accumulator in meters along the shortest path
    phys_dist: Dict[Any, float] = {source: 0.0}

    # Min-heap priority queue storing tuples: (tentative_cost, node_id)
    pq: List[Tuple[float, Any]] = [(0.0, source)]

    # Set of settled vertices whose optimal shortest path is finalized
    settled: Set[Any] = set()

    # Track order of settled nodes for algorithm visualization / inspection
    visited_order: List[Any] = []
    nodes_expanded = 0

    while pq:
        current_cost, u = heapq.heappop(pq)

        # Skip obsolete heap entries (since Python heapq does not support decrease-key,
        # we push new entries and discard lazy duplicates when popped)
        if u in settled:
            continue

        settled.add(u)
        nodes_expanded += 1
        visited_order.append(u)

        # Early termination: once target is extracted from min-heap, its shortest path is guaranteed
        if u == target:
            break

        # Explore outgoing neighbors of u
        for v in G.neighbors(u):
            if v in settled:
                continue

            # Determine minimum edge weight between u and v
            # Handles MultiDiGraph (parallel edges) as well as simple DiGraph/Graph
            edge_data_dict = G.get_edge_data(u, v)
            if edge_data_dict is None:
                continue

            min_edge_cost = float("inf")
            min_edge_len = 0.0

            if G.is_multigraph():
                # In a MultiDiGraph, pick the parallel edge with minimum weight
                for _, edge_attrs in edge_data_dict.items():
                    w = float(edge_attrs.get(weight, float("inf")))
                    if w < min_edge_cost:
                        min_edge_cost = w
                        min_edge_len = float(edge_attrs.get("length", 0.0))
            else:
                min_edge_cost = float(edge_data_dict.get(weight, float("inf")))
                min_edge_len = float(edge_data_dict.get("length", 0.0))

            if min_edge_cost == float("inf"):
                continue

            # Relaxation step: if the path to v through u is strictly shorter
            tentative_cost = current_cost + min_edge_cost
            if tentative_cost < dist.get(v, float("inf")):
                dist[v] = tentative_cost
                phys_dist[v] = phys_dist[u] + min_edge_len
                pred[v] = u
                heapq.heappush(pq, (tentative_cost, v))

    # If target was never reached, no path exists
    if target not in dist or target not in pred:
        return None

    # Reconstruct optimal path from target back to source
    path: List[Any] = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = pred.get(curr)
    path.reverse()

    return DijkstraResult(
        path=path,
        cost=dist[target],
        distance=phys_dist.get(target, 0.0),
        nodes_expanded=nodes_expanded,
        visited_nodes=visited_order,
    )


def multi_source_dijkstra(
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    sources: List[Any],
    weight: str = "travel_time",
    cutoff: Optional[float] = None,
) -> Tuple[Dict[Any, float], Dict[Any, Any], Dict[Any, Any]]:
    r"""Compute shortest distances and predecessors from multiple sources simultaneously.

    Initializes the min-heap with all source vertices at distance 0.
    Simulates a virtual super-source connected to every source vertex with 0-weight edges.

    Complexity:
    - O((|V| + |E|) \log |V|) in a single unified sweep across all sources.

    Args:
        G: NetworkX graph.
        sources: List of source vertex identifiers (e.g., all ambulance stations).
        weight: Edge weight attribute (default: 'travel_time').
        cutoff: Optional maximum distance to explore.

    Returns:
        Tuple of:
        - dist: Dict mapping node -> shortest distance from the closest source
        - pred: Dict mapping node -> predecessor node on the shortest path
        - nearest_source: Dict mapping node -> which source vertex attained this minimum
    """
    dist: Dict[Any, float] = {}
    pred: Dict[Any, Any] = {}
    nearest_source: Dict[Any, Any] = {}
    pq: List[Tuple[float, Any, Any]] = []  # (cost, node, original_source)
    settled: Set[Any] = set()

    for s in sources:
        if s in G:
            dist[s] = 0.0
            nearest_source[s] = s
            heapq.heappush(pq, (0.0, s, s))

    while pq:
        current_cost, u, src = heapq.heappop(pq)

        if u in settled:
            continue
        settled.add(u)

        if cutoff is not None and current_cost > cutoff:
            continue

        for v in G.neighbors(u):
            if v in settled:
                continue

            edge_data_dict = G.get_edge_data(u, v)
            if edge_data_dict is None:
                continue

            min_edge_cost = float("inf")
            if G.is_multigraph():
                for _, edge_attrs in edge_data_dict.items():
                    w = float(edge_attrs.get(weight, float("inf")))
                    if w < min_edge_cost:
                        min_edge_cost = w
            else:
                min_edge_cost = float(edge_data_dict.get(weight, float("inf")))

            if min_edge_cost == float("inf"):
                continue

            tentative_cost = current_cost + min_edge_cost
            if tentative_cost < dist.get(v, float("inf")):
                dist[v] = tentative_cost
                pred[v] = u
                nearest_source[v] = src
                heapq.heappush(pq, (tentative_cost, v, src))

    return dist, pred, nearest_source


def find_nearest_station_to_accident(
    G: nx.MultiDiGraph,
    station_nodes: List[Any],
    accident_node: Any,
    weight: str = "travel_time",
) -> Tuple[Optional[Any], Optional[DijkstraResult]]:
    """Identify the optimal ambulance station that can reach the accident in minimum time.

    On a directed graph, the path travels from Station -> Accident.
    We compute the shortest path from each station to the accident node and select
    the station minimizing response time.

    Args:
        G: Directed road graph.
        station_nodes: List of ambulance station node IDs.
        accident_node: Incident junction node ID.
        weight: Edge weight attribute.

    Returns:
        Tuple of (best_station_node, dijkstra_result_for_best_station).
    """
    best_station = None
    best_result: Optional[DijkstraResult] = None
    min_time = float("inf")

    for s_node in station_nodes:
        result = dijkstra_shortest_path(G, source=s_node, target=accident_node, weight=weight)
        if result is not None and result.cost < min_time:
            min_time = result.cost
            best_station = s_node
            best_result = result

    return best_station, best_result


def find_nearest_hospital_from_accident(
    G: nx.MultiDiGraph,
    accident_node: Any,
    hospital_nodes: List[Any],
    weight: str = "travel_time",
) -> Tuple[Optional[Any], Optional[DijkstraResult]]:
    """Identify the optimal destination hospital from the accident site in minimum time.

    Computes the shortest path from Accident -> Hospital.

    Args:
        G: Directed road graph.
        accident_node: Incident junction node ID.
        hospital_nodes: List of hospital node IDs.
        weight: Edge weight attribute.

    Returns:
        Tuple of (best_hospital_node, dijkstra_result_for_best_hospital).
    """
    best_hospital = None
    best_result: Optional[DijkstraResult] = None
    min_time = float("inf")

    for h_node in hospital_nodes:
        result = dijkstra_shortest_path(G, source=accident_node, target=h_node, weight=weight)
        if result is not None and result.cost < min_time:
            min_time = result.cost
            best_hospital = h_node
            best_result = result

    return best_hospital, best_result
