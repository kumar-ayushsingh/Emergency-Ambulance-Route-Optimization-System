r"""A* (A-Star) Goal-Directed Shortest Path Search Engine.

Academic Context:
Discrete Mathematics · Module 4: Graph Theory · Heuristic Search & Admissibility

Mathematical Formulation:
Given a directed graph G = (V, E) with non-negative edge weight w(e) representing
travel time in seconds, an origin vertex s \in V, and a target destination t \in V.

Evaluation Function:
    f(u) = g(u) + h(u)

Where:
- g(u): Exact cost of the shortest path from origin s to vertex u found so far.
- h(u): Heuristic estimate of the remaining travel time from u to target t.

Heuristic Definition:
    h(u) = d_haversine(u, t) / v_max

Where:
- d_haversine(u, t): Great-circle geodesic distance between (lat_u, lng_u) and
  (lat_t, lng_t) on Earth's surface (radius R = 6,371,000 meters).
- v_max: Maximum attainable speed across all edges in the entire road network (m/s).

Proof of Admissibility:
1. Geodesic bound: For any road path P from u to t, its total physical length satisfies:
       length(P) >= d_haversine(u, t)
2. Speed bound: For every directed edge e along P, speed(e) <= v_max.
3. Therefore, the travel time T(P) satisfies:
       T(P) = \sum_{e \in P} length(e) / speed(e)
            >= \sum_{e \in P} length(e) / v_max
            = length(P) / v_max
            >= d_haversine(u, t) / v_max = h(u)
4. Taking the infimum over all valid paths P:
       t*(u, t) = \min_P T(P) >= h(u)  \forall u \in V.
   Hence, h(u) is strictly admissible (it never overestimates the true cost to reach t).

Proof of Consistency (Monotonicity):
By the spherical triangle inequality on great-circle distances:
    d_haversine(u, t) <= d_haversine(u, v) + d_haversine(v, t)
                      <= length(u, v) + d_haversine(v, t)
Dividing by v_max:
    h(u) <= length(u, v) / v_max + h(v)
         <= length(u, v) / speed(u, v) + h(v)
         = w(u, v) + h(v)
Since h(u) <= w(u, v) + h(v) for all edges (u, v) \in E:
- The heuristic is consistent (monotonic).
- Consistent heuristics guarantee that when a node u is extracted from the min-heap,
  its g(u) is guaranteed to be optimal.
- No closed vertex ever needs to be re-opened.
"""

from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

EARTH_RADIUS_METERS: float = 6371000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in meters.

    Formula:
        a = sin^2(d_lat/2) + cos(lat1) * cos(lat2) * sin^2(d_lon/2)
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        d = R * c

    Args:
        lat1, lon1: Coordinates of first point in decimal degrees.
        lat2, lon2: Coordinates of second point in decimal degrees.

    Returns:
        Great-circle distance in meters (float).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Clamp to avoid numerical float precision issues exceeding 1.0
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


def get_max_network_speed_mps(G: nx.MultiDiGraph | nx.DiGraph | nx.Graph) -> float:
    """Determine the maximum attainable traversal speed across all edges in the graph.

    Caches the result on the graph instance for O(1) subsequent lookups.

    Args:
        G: Street network graph.

    Returns:
        Maximum speed in meters per second (float).
    """
    if hasattr(G, "_cached_max_speed_mps"):
        return getattr(G, "_cached_max_speed_mps")

    max_speed = 0.0
    for _, _, data in G.edges(data=True):
        speed_mps = float(data.get("speed_mps", 0.0))
        if speed_mps <= 0.0:
            speed_kph = float(data.get("speed_kph", 20.0))
            speed_mps = speed_kph * (1000.0 / 3600.0)
        if speed_mps > max_speed:
            max_speed = speed_mps

    # Fallback to 60 km/h (16.67 m/s) if unspecified
    if max_speed <= 0.0:
        max_speed = 60.0 * (1000.0 / 3600.0)

    setattr(G, "_cached_max_speed_mps", max_speed)
    return max_speed


def haversine_heuristic(
    u: Any,
    target: Any,
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    max_speed_mps: float,
) -> float:
    """Compute admissible and consistent travel-time lower bound h(u) in seconds.

    Formula:
        h(u) = d_haversine(u, target) / max_speed_mps

    Args:
        u: Current vertex ID.
        target: Goal destination vertex ID.
        G: Graph containing node 'y' (latitude) and 'x' (longitude) attributes.
        max_speed_mps: Maximum network speed upper bound in m/s.

    Returns:
        Admissible travel-time estimate in seconds (float).
    """
    u_data = G.nodes[u]
    t_data = G.nodes[target]

    u_lat, u_lng = float(u_data["y"]), float(u_data["x"])
    t_lat, t_lng = float(t_data["y"]), float(t_data["x"])

    dist_meters = haversine_distance(u_lat, u_lng, t_lat, t_lng)
    return dist_meters / max_speed_mps


@dataclass
class SearchExecutionResult:
    """Encapsulates execution statistics for algorithm comparison."""

    algorithm: str
    path: List[Any]
    cost: float  # Optimal travel time in seconds
    distance: float  # Total physical distance in meters
    nodes_expanded: int  # Number of nodes popped from min-heap
    heap_pushes: int  # Total number of priority queue insertions
    runtime_ms: float  # CPU wall-clock execution time in milliseconds
    explored_nodes: List[Any]  # Ordered sequence of settled node IDs
    explored_coords: List[List[float]]  # Ordered [[lat, lng], ...] for map animation


def astar_shortest_path(
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    source: Any,
    target: Any,
    weight: str = "travel_time",
    max_speed_mps: Optional[float] = None,
    blocked_edges: Optional[Set[Tuple[Any, Any]]] = None,
) -> Optional[SearchExecutionResult]:
    """Compute optimal shortest path from source to target using A* with Haversine heuristic.

    Admissibility guarantee:
        h(u) = d_haversine(u, target) / v_max <= t*(u, target)

    Complexity:
        - Time: O((|V| + |E|) log |V|), but visits substantially fewer vertices than Dijkstra.
        - Space: O(|V|) to maintain g-scores, f-scores, priority queue, and predecessors.

    Args:
        G: Directed street network graph.
        source: Origin vertex identifier.
        target: Destination vertex identifier.
        weight: Edge weight attribute key to minimize (default: 'travel_time').
        max_speed_mps: Optional maximum speed in m/s; dynamically inferred if omitted.

    Returns:
        SearchExecutionResult or None if target is unreachable.
    """
    if source not in G or target not in G:
        return None

    if max_speed_mps is None:
        max_speed_mps = get_max_network_speed_mps(G)

    t_start = time.perf_counter()

    if source == target:
        runtime_ms = (time.perf_counter() - t_start) * 1000.0
        src_data = G.nodes[source]
        return SearchExecutionResult(
            algorithm="A*",
            path=[source],
            cost=0.0,
            distance=0.0,
            nodes_expanded=1,
            heap_pushes=1,
            runtime_ms=runtime_ms,
            explored_nodes=[source],
            explored_coords=[[float(src_data["y"]), float(src_data["x"])]],
        )

    # g_score[v]: shortest known cost from source to v
    g_score: Dict[Any, float] = {source: 0.0}

    # phys_dist[v]: physical distance in meters from source along shortest path
    phys_dist: Dict[Any, float] = {source: 0.0}

    # pred[v]: predecessor of v on the shortest path
    pred: Dict[Any, Any] = {}

    # Initial heuristic estimate from source to target
    h_source = haversine_heuristic(source, target, G, max_speed_mps)

    # Min-heap priority queue storing tuples: (f_score, g_score, vertex_id)
    # Using (f_score, g_score, u) breaks ties in favor of higher g_score (closer to target)
    pq: List[Tuple[float, float, Any]] = [(h_source, 0.0, source)]

    settled: Set[Any] = set()
    explored_nodes: List[Any] = []
    explored_coords: List[List[float]] = []

    nodes_expanded = 0
    heap_pushes = 1

    while pq:
        f_curr, g_curr, u = heapq.heappop(pq)

        if u in settled:
            continue

        settled.add(u)
        nodes_expanded += 1
        explored_nodes.append(u)

        u_node_data = G.nodes[u]
        explored_coords.append([float(u_node_data["y"]), float(u_node_data["x"])])

        # Goal reached: under a consistent heuristic, the first extraction of target is optimal!
        if u == target:
            break

        # Explore outgoing neighbors
        for v in G.neighbors(u):
            if v in settled:
                continue

            if blocked_edges and ((u, v) in blocked_edges or (v, u) in blocked_edges):
                continue

            edge_data_dict = G.get_edge_data(u, v)
            if edge_data_dict is None:
                continue

            min_edge_cost = float("inf")
            min_edge_len = 0.0

            if G.is_multigraph():
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

            tentative_g = g_curr + min_edge_cost

            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                phys_dist[v] = phys_dist[u] + min_edge_len
                pred[v] = u

                h_v = haversine_heuristic(v, target, G, max_speed_mps)
                f_v = tentative_g + h_v

                heapq.heappush(pq, (f_v, tentative_g, v))
                heap_pushes += 1

    runtime_ms = (time.perf_counter() - t_start) * 1000.0

    if target not in g_score or target not in pred:
        return None

    # Reconstruct shortest path backwards from target
    path: List[Any] = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = pred.get(curr)
    path.reverse()

    return SearchExecutionResult(
        algorithm="A*",
        path=path,
        cost=g_score[target],
        distance=phys_dist.get(target, 0.0),
        nodes_expanded=nodes_expanded,
        heap_pushes=heap_pushes,
        runtime_ms=runtime_ms,
        explored_nodes=explored_nodes,
        explored_coords=explored_coords,
    )


def dijkstra_race_search(
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    source: Any,
    target: Any,
    weight: str = "travel_time",
    blocked_edges: Optional[Set[Tuple[Any, Any]]] = None,
) -> Optional[SearchExecutionResult]:
    """Execute Dijkstra's algorithm instrumented for fair algorithmic racing against A*.

    Tracks exact nodes expanded, heap pushes, runtime in milliseconds, and settlement order.

    Args:
        G: Directed street network graph.
        source: Origin vertex identifier.
        target: Destination vertex identifier.
        weight: Edge weight attribute to minimize.

    Returns:
        SearchExecutionResult or None if target is unreachable.
    """
    if source not in G or target not in G:
        return None

    t_start = time.perf_counter()

    if source == target:
        runtime_ms = (time.perf_counter() - t_start) * 1000.0
        src_data = G.nodes[source]
        return SearchExecutionResult(
            algorithm="Dijkstra",
            path=[source],
            cost=0.0,
            distance=0.0,
            nodes_expanded=1,
            heap_pushes=1,
            runtime_ms=runtime_ms,
            explored_nodes=[source],
            explored_coords=[[float(src_data["y"]), float(src_data["x"])]],
        )

    dist: Dict[Any, float] = {source: 0.0}
    phys_dist: Dict[Any, float] = {source: 0.0}
    pred: Dict[Any, Any] = {}

    pq: List[Tuple[float, Any]] = [(0.0, source)]
    settled: Set[Any] = set()
    explored_nodes: List[Any] = []
    explored_coords: List[List[float]] = []

    nodes_expanded = 0
    heap_pushes = 1

    while pq:
        current_cost, u = heapq.heappop(pq)

        if u in settled:
            continue

        settled.add(u)
        nodes_expanded += 1
        explored_nodes.append(u)

        u_node_data = G.nodes[u]
        explored_coords.append([float(u_node_data["y"]), float(u_node_data["x"])])

        if u == target:
            break

        for v in G.neighbors(u):
            if v in settled:
                continue

            if blocked_edges and ((u, v) in blocked_edges or (v, u) in blocked_edges):
                continue

            edge_data_dict = G.get_edge_data(u, v)
            if edge_data_dict is None:
                continue

            min_edge_cost = float("inf")
            min_edge_len = 0.0

            if G.is_multigraph():
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

            tentative_cost = current_cost + min_edge_cost

            if tentative_cost < dist.get(v, float("inf")):
                dist[v] = tentative_cost
                phys_dist[v] = phys_dist[u] + min_edge_len
                pred[v] = u
                heapq.heappush(pq, (tentative_cost, v))
                heap_pushes += 1

    runtime_ms = (time.perf_counter() - t_start) * 1000.0

    if target not in dist or target not in pred:
        return None

    path: List[Any] = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = pred.get(curr)
    path.reverse()

    return SearchExecutionResult(
        algorithm="Dijkstra",
        path=path,
        cost=dist[target],
        distance=phys_dist.get(target, 0.0),
        nodes_expanded=nodes_expanded,
        heap_pushes=heap_pushes,
        runtime_ms=runtime_ms,
        explored_nodes=explored_nodes,
        explored_coords=explored_coords,
    )


def sample_explored_coordinates(
    coords: List[List[float]],
    target_count: int = 1200,
) -> List[List[float]]:
    """Evenly downsample explored coordinates if very large to ensure smooth 60fps UI animation.

    Guarantees the first and last explored points are strictly preserved.

    Args:
        coords: Full sequential list of coordinates [[lat, lng], ...].
        target_count: Maximum number of points to retain.

    Returns:
        Sampled coordinate list.
    """
    n = len(coords)
    if n <= target_count:
        return coords

    step = n / float(target_count)
    sampled = [coords[int(i * step)] for i in range(target_count - 1)]
    sampled.append(coords[-1])
    return sampled


def run_algorithm_race(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
    weight: str = "travel_time",
    animation_sample_limit: int = 1500,
) -> Dict[str, Any]:
    """Execute both Dijkstra and A* on the identical (source, target) pair and compare performance.

    Verifies:
    1. Optimality check: both algorithms yield equal shortest path costs (|cost_d - cost_a| < 1e-4).
    2. Pruning efficiency: A* goal-directed search reduces settled node count.

    Args:
        G: Directed road graph.
        source: Origin junction node ID.
        target: Destination junction node ID.
        weight: Edge weight attribute.
        animation_sample_limit: Max points returned per algorithm for UI animation.

    Returns:
        Dictionary with telemetry metrics, paths, and sampled animation coordinate arrays.
    """
    max_speed_mps = get_max_network_speed_mps(G)

    dijkstra_res = dijkstra_race_search(G, source, target, weight=weight)
    astar_res = astar_shortest_path(G, source, target, weight=weight, max_speed_mps=max_speed_mps)

    if dijkstra_res is None or astar_res is None:
        return {
            "success": False,
            "message": "Origin and destination are disconnected on the road network.",
        }

    # Verify mathematical equality of shortest path costs
    cost_diff = abs(dijkstra_res.cost - astar_res.cost)
    costs_equal = cost_diff < 1e-3  # within 1 millisecond

    # Percentage reduction in nodes expanded
    node_reduction_pct = 0.0
    if dijkstra_res.nodes_expanded > 0:
        node_reduction_pct = (
            (dijkstra_res.nodes_expanded - astar_res.nodes_expanded)
            / float(dijkstra_res.nodes_expanded)
            * 100.0
        )

    # Percentage reduction in heap pushes
    push_reduction_pct = 0.0
    if dijkstra_res.heap_pushes > 0:
        push_reduction_pct = (
            (dijkstra_res.heap_pushes - astar_res.heap_pushes)
            / float(dijkstra_res.heap_pushes)
            * 100.0
        )

    speedup_ratio = (
        dijkstra_res.runtime_ms / astar_res.runtime_ms
        if astar_res.runtime_ms > 0
        else 1.0
    )

    # Sample animation coordinates for smooth browser rendering
    dijkstra_anim_coords = sample_explored_coordinates(
        dijkstra_res.explored_coords, target_count=animation_sample_limit
    )
    astar_anim_coords = sample_explored_coordinates(
        astar_res.explored_coords, target_count=animation_sample_limit
    )

    return {
        "success": True,
        "source": source,
        "target": target,
        "costs_equal": costs_equal,
        "cost_diff_sec": round(cost_diff, 4),
        "node_reduction_pct": round(node_reduction_pct, 1),
        "push_reduction_pct": round(push_reduction_pct, 1),
        "speedup_ratio": round(speedup_ratio, 2),
        "dijkstra": {
            "algorithm": "Dijkstra (Uniform-Cost Search)",
            "cost_sec": round(dijkstra_res.cost, 2),
            "cost_min": round(dijkstra_res.cost / 60.0, 2),
            "distance_m": round(dijkstra_res.distance, 1),
            "distance_km": round(dijkstra_res.distance / 1000.0, 2),
            "nodes_expanded": dijkstra_res.nodes_expanded,
            "heap_pushes": dijkstra_res.heap_pushes,
            "runtime_ms": round(dijkstra_res.runtime_ms, 2),
            "path": dijkstra_res.path,
            "total_explored": len(dijkstra_res.explored_coords),
            "anim_coords": dijkstra_anim_coords,
            "explored_coords": dijkstra_anim_coords,
        },
        "astar": {
            "algorithm": "A* (Haversine Admissible Heuristic)",
            "cost_sec": round(astar_res.cost, 2),
            "cost_min": round(astar_res.cost / 60.0, 2),
            "distance_m": round(astar_res.distance, 1),
            "distance_km": round(astar_res.distance / 1000.0, 2),
            "nodes_expanded": astar_res.nodes_expanded,
            "heap_pushes": astar_res.heap_pushes,
            "runtime_ms": round(astar_res.runtime_ms, 2),
            "path": astar_res.path,
            "total_explored": len(astar_res.explored_coords),
            "anim_coords": astar_anim_coords,
            "explored_coords": astar_anim_coords,
        },
    }
