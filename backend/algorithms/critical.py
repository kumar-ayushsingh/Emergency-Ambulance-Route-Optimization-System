r"""Critical Road Infrastructure Detection & Resilience Scoring Engine.

Academic Context:
Discrete Mathematics · Module 4: Graph Theory
Problem Statement: Graph Connectivity, Cut Elements, Menger's Theorem & Network Vulnerability.

Mathematical Foundations:
1. Tarjan's Low-Link DFS Algorithm:
   Computes discovery time tin[u] and low-link value low[u].
   - An edge {u, v} is a strict Bridge (cut edge) iff:
       low[v] > tin[u]
     Its removal strictly increases the number of connected components in G.
   - A vertex u is an Articulation Point (cut vertex) iff:
       (a) u is the root of the DFS tree with >= 2 tree children, OR
       (b) u is not root and has a child v such that low[v] >= tin[u].
     Its removal strictly increases the number of connected components.

2. Soft Bridges & Detour Ratio \rho(e):
   In dense road meshes, strict cut edges are rare. We define a soft bridge as an edge e
   whose closure forces a significant detour:
       \rho(e) = T'(e) / T >= 1.5
   where T is baseline shortest travel time and T'(e) is travel time without edge e.

3. Menger's Theorem (1927):
   The maximum number of edge-disjoint paths between s and t equals the minimum
   number of edges whose removal disconnects s and t:
       \lambda(s, t) = min edge cut size

4. Resilience Score R \in [0, 100]:
   R = 100 * (0.4 * L + 0.4 * D + 0.2 * C)
   where:
       L = min(\lambda, 3) / 3                           (Path redundancy)
       D = 1 - (min(\rho_max, 3) - 1) / 2                (Detour tolerance)
       C = 1 - (strict_bridge_length / total_route_length) (Cut-edge exposure)
   Ratings: R >= 75: Resilient, 50 <= R < 75: Moderate, R < 50: Fragile.

Complexity Analysis:
- Tarjan's Low-Link DFS: O(|V| + |E|) time, O(|V|) space (iterative DFS avoids recursion depth limits).
- Soft Bridge Scan: O(k * (|V| + |E|) \log |V|) where k is the number of edges on the route.
- Menger Edge Connectivity: Solved via max-flow min-cut algorithms in O(\lambda * |E|).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from backend.algorithms.dijkstra import dijkstra_shortest_path

logger = logging.getLogger(__name__)


@dataclass
class CriticalAnalysisResult:
    """Comprehensive resilience telemetry and critical infrastructure analysis."""

    resilience_score: float  # 0 to 100
    rating: str  # 'Resilient', 'Moderate', 'Fragile'
    rating_color: str  # Hex color for UI badge
    components: Dict[str, float]  # {'L': ..., 'D': ..., 'C': ...}
    lambda_menger: int  # Number of edge-disjoint s-t paths
    rho_max: float  # Worst detour ratio on route
    strict_bridges: List[Tuple[Any, Any]]  # Strict cut edges on route
    strict_bridge_length_m: float  # Cumulative length of strict bridges
    articulation_points: List[Any]  # Cut vertices on route
    soft_bridges: List[Dict[str, Any]]  # Edges with detour ratio >= 1.5
    explanation: str  # Academic and operational summary


def tarjan_bridges_and_articulation_points(
    G: nx.Graph,
) -> Tuple[Set[Tuple[Any, Any]], Set[Any]]:
    r"""Compute all bridges and articulation points on an undirected graph using iterative DFS.

    Avoids Python recursion depth limits on large road networks by using an explicit call stack.

    Algorithm:
    1. Iterate over every connected component of G.
    2. Maintain `tin[u]` (discovery time) and `low[u]` (lowest reachable ancestor time).
    3. Push state `[u, parent, neighbor_iterator, tree_children_count]` onto stack.
    4. Detect back-edges and tree-edges iteratively.
    5. On post-order return from child v to parent u:
       - Update low[u] = min(low[u], low[v])
       - If low[v] > tin[u], edge {u, v} is a bridge.
       - If u is not root and low[v] >= tin[u], u is an articulation point.
    6. If u is root and tree_children >= 2, u is an articulation point.

    Args:
        G: Undirected simple graph.

    Returns:
        Tuple of (bridges_set, articulation_points_set), where each bridge is (min(u,v), max(u,v)).
    """
    tin: Dict[Any, int] = {}
    low: Dict[Any, int] = {}
    timer = 0
    bridges: Set[Tuple[Any, Any]] = set()
    articulation_points: Set[Any] = set()

    for start_node in G.nodes():
        if start_node in tin:
            continue

        # Stack frame: [node, parent, neighbors_iterator, children_count]
        stack: List[List[Any]] = [
            [start_node, None, iter(list(G.neighbors(start_node))), 0]
        ]
        tin[start_node] = low[start_node] = timer
        timer += 1

        while stack:
            u, parent, nbr_iter, _ = stack[-1]

            advanced = False
            for v in nbr_iter:
                if v == parent:
                    continue
                if v in tin:
                    # Back-edge to an already visited ancestor
                    low[u] = min(low[u], tin[v])
                else:
                    # Tree-edge: advance DFS stack to child v
                    stack[-1][3] += 1  # Increment u's tree children count
                    tin[v] = low[v] = timer
                    timer += 1
                    stack.append([v, u, iter(list(G.neighbors(v))), 0])
                    advanced = True
                    break

            if advanced:
                continue

            # Post-order: all neighbors of u have been explored
            finished_u, finished_parent, _, finished_children = stack.pop()

            if finished_parent is not None:
                # Update parent's low-link value
                low[finished_parent] = min(low[finished_parent], low[finished_u])

                # Bridge condition: no back-edge from u's subtree to parent or above
                if low[finished_u] > tin[finished_parent]:
                    bridges.add(tuple(sorted((finished_parent, finished_u))))

                # Articulation point condition for non-root vertices
                if finished_parent != start_node:
                    if low[finished_u] >= tin[finished_parent]:
                        articulation_points.add(finished_parent)
            else:
                # Root of the DFS tree is an articulation point iff it has >= 2 children
                if finished_children >= 2:
                    articulation_points.add(finished_u)

    return bridges, articulation_points


def find_strict_critical_on_route(
    G_undirected: nx.Graph,
    route_nodes: List[Any],
    global_bridges: Optional[Set[Tuple[Any, Any]]] = None,
    global_aps: Optional[Set[Any]] = None,
) -> Tuple[List[Tuple[Any, Any]], float, List[Any]]:
    """Filter global bridges and articulation points to those lying along the given route.

    A bridge lying on a simple s-t path strictly separates s from t; removing it
    destroys the connection completely on the undirected topology.

    Args:
        G_undirected: Undirected simple road graph.
        route_nodes: Sequence of node IDs forming the primary route [v_0, v_1, ..., v_k].
        global_bridges: Optional precomputed set of all bridges in G_undirected.
        global_aps: Optional precomputed set of all articulation points in G_undirected.

    Returns:
        Tuple of (route_bridges, total_bridge_length_meters, route_articulation_points).
    """
    if global_bridges is None or global_aps is None:
        global_bridges, global_aps = tarjan_bridges_and_articulation_points(G_undirected)

    route_bridges: List[Tuple[Any, Any]] = []
    total_bridge_len = 0.0

    # Check each consecutive edge along the route
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i + 1]
        edge_key = tuple(sorted((u, v)))
        if edge_key in global_bridges:
            route_bridges.append(edge_key)
            edge_data = G_undirected.get_edge_data(u, v) or {}
            total_bridge_len += float(edge_data.get("length", 0.0))

    # Check which route nodes are articulation points (excluding source and target endpoints)
    interior_nodes = set(route_nodes[1:-1]) if len(route_nodes) > 2 else set()
    route_aps = [node for node in route_nodes if node in global_aps and node in interior_nodes]

    return route_bridges, total_bridge_len, route_aps


def find_soft_bridges_on_route(
    G_directed: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    route_nodes: List[Any],
    base_travel_time: float,
    detour_threshold: float = 1.5,
    blocked_edges: Optional[Set[Tuple[Any, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], float]:
    r"""Detect soft bridges along the route by simulating single-edge failures.

    For every consecutive edge e = (u, v) on the route:
    1. Temporarily skip edge e in Dijkstra search via blocked_edges (zero graph mutation).
    2. Recompute the shortest path from source (v_0) to target (v_k) via Dijkstra.
    3. Calculate detour ratio:
           \rho(e) = T'(e) / T
    4. If \rho(e) >= 1.5 or no path exists, flag as a soft bridge.

    Args:
        G_directed: Directed routing graph.
        route_nodes: Ordered sequence of vertices [v_0, v_1, ..., v_k].
        base_travel_time: Baseline optimal travel time in seconds.
        detour_threshold: Threshold ratio to flag as soft bridge (default: 1.5).
        blocked_edges: Pre-existing blocked edges to respect during simulation.

    Returns:
        Tuple of (soft_bridges_list, worst_detour_ratio_rho_max).
    """
    if len(route_nodes) < 2 or base_travel_time <= 0:
        return [], 1.0

    source = route_nodes[0]
    target = route_nodes[-1]
    soft_bridges: List[Dict[str, Any]] = []
    rho_max = 1.0
    base_blocked = set(blocked_edges) if blocked_edges else set()

    # Iterate through each directed step on the route
    for i in range(len(route_nodes) - 1):
        u = route_nodes[i]
        v = route_nodes[i + 1]

        edge_data = G_directed.get_edge_data(u, v)
        if not edge_data:
            continue

        if G_directed.is_multigraph():
            first_attrs = next(iter(edge_data.values())) if edge_data else {}
        else:
            first_attrs = edge_data

        # Simulate edge failure by adding (u, v) to blocked edges (no graph copy/mutation)
        step_blocked = set(base_blocked)
        step_blocked.add((u, v))

        reroute_result = dijkstra_shortest_path(
            G_directed, source=source, target=target, weight="travel_time", blocked_edges=step_blocked
        )

        if reroute_result is None:
            # Complete disconnect: no alternative path exists!
            detour_ratio = 99.0  # Sentinel for infinite detour
            detour_diff_sec = float("inf")
            detour_diff_min = float("inf")
            is_disconnected = True
            rho_max = max(rho_max, 3.0)  # Capped at max penalty
        else:
            detour_ratio = reroute_result.cost / base_travel_time
            detour_diff_sec = reroute_result.cost - base_travel_time
            detour_diff_min = detour_diff_sec / 60.0
            is_disconnected = False
            rho_max = max(rho_max, detour_ratio)

        if detour_ratio >= detour_threshold or is_disconnected:
            # Extract road name for clear dispatcher telemetry
            road_name = first_attrs.get("name", "Unnamed Road")
            if isinstance(road_name, list):
                road_name = road_name[0]

            soft_bridges.append(
                {
                    "u": u,
                    "v": v,
                    "road_name": str(road_name),
                    "highway": str(first_attrs.get("highway", "road")),
                    "length_m": float(first_attrs.get("length", 0.0)),
                    "detour_ratio": round(detour_ratio, 2),
                    "detour_delay_sec": round(detour_diff_sec, 1) if not is_disconnected else None,
                    "detour_delay_min": round(detour_diff_min, 2) if not is_disconnected else None,
                    "disconnected": is_disconnected,
                }
            )

    return soft_bridges, rho_max


def compute_edge_connectivity_menger(
    G_undirected: nx.Graph,
    source: Any,
    target: Any,
) -> int:
    r"""Compute Menger's edge connectivity \lambda between source and target.

    Menger's Theorem (1927):
    In any graph G, the maximum number of edge-disjoint s-t paths equals the
    minimum size of an edge cut separating s and t.

    Uses NetworkX's max-flow implementation with unit capacities.

    Args:
        G_undirected: Undirected simple road graph.
        source: Source vertex ID.
        target: Target vertex ID.

    Returns:
        Integer count of edge-disjoint paths \lambda \ge 0.
    """
    if source not in G_undirected or target not in G_undirected:
        return 0
    if source == target:
        return G_undirected.degree(source)

    try:
        # Computes minimum cut / edge connectivity via Edmonds-Karp max-flow
        lambda_val = nx.edge_connectivity(G_undirected, source, target)
        return int(lambda_val)
    except Exception as e:
        logger.warning("Menger connectivity computation error: %s", e)
        return 1


def calculate_resilience_score(
    lambda_val: int,
    rho_max: float,
    strict_bridge_length_m: float,
    total_route_length_m: float,
) -> Tuple[float, str, str, Dict[str, float]]:
    r"""Compute composite Resilience Score R \in [0, 100].

    Formula:
        R = 100 * (0.4 * L + 0.4 * D + 0.2 * C)

    Components:
        L = min(\lambda, 3) / 3                           (Path Redundancy)
        D = 1 - (min(\rho_max, 3) - 1) / 2                (Detour Tolerance)
        C = 1 - (strict_bridge_len / total_route_len)     (Strict Cut Exposure)

    Classification:
        R >= 75:        'Resilient' (Low vulnerability, strong backups)
        50 <= R < 75:   'Moderate'  (Acceptable, but has choke points)
        R < 50:         'Fragile'   (Critical bottlenecks or single points of failure)

    Returns:
        Tuple of (score_0_100, rating_text, hex_color, components_dict).
    """
    # 1. Path Redundancy L
    L = min(float(lambda_val), 3.0) / 3.0
    L = max(0.0, min(1.0, L))

    # 2. Detour Tolerance D
    rho_clamped = min(max(float(rho_max), 1.0), 3.0)
    D = 1.0 - (rho_clamped - 1.0) / 2.0
    D = max(0.0, min(1.0, D))

    # 3. Strict Bridge Exposure C
    if total_route_length_m > 0:
        ratio_bridge = min(1.0, strict_bridge_length_m / total_route_length_m)
        C = 1.0 - ratio_bridge
    else:
        C = 1.0
    C = max(0.0, min(1.0, C))

    # Composite weighted score
    score = 100.0 * (0.4 * L + 0.4 * D + 0.2 * C)
    score = round(max(0.0, min(100.0, score)), 1)

    if score >= 75.0:
        rating = "Resilient"
        color = "#10b981"  # Emerald green
    elif score >= 50.0:
        rating = "Moderate"
        color = "#f59e0b"  # Amber
    else:
        rating = "Fragile"
        color = "#ef4444"  # Crimson red

    components = {
        "L": round(L, 3),
        "D": round(D, 3),
        "C": round(C, 3),
        "weight_L": 0.4,
        "weight_D": 0.4,
        "weight_C": 0.2,
    }

    return score, rating, color, components


def analyze_route_resilience(
    G_directed: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    G_undirected: nx.Graph,
    route_nodes: List[Any],
    base_travel_time: float,
    source: Optional[Any] = None,
    target: Optional[Any] = None,
    global_bridges: Optional[Set[Tuple[Any, Any]]] = None,
    global_aps: Optional[Set[Any]] = None,
    blocked_edges: Optional[Set[Tuple[Any, Any]]] = None,
) -> CriticalAnalysisResult:
    """Full pipeline for Prompt 3: Analyze strict/soft bridges, connectivity, and score.

    Args:
        G_directed: Directed routing graph.
        G_undirected: Undirected simple graph.
        route_nodes: Sequence of node IDs along the route.
        base_travel_time: Optimal route duration in seconds.
        source: Starting vertex (defaults to route_nodes[0]).
        target: Destination vertex (defaults to route_nodes[-1]).
        global_bridges: Optional cached bridges.
        global_aps: Optional cached articulation points.

    Returns:
        CriticalAnalysisResult dataclass.
    """
    if len(route_nodes) < 2:
        return CriticalAnalysisResult(
            resilience_score=100.0,
            rating="Resilient",
            rating_color="#10b981",
            components={"L": 1.0, "D": 1.0, "C": 1.0, "weight_L": 0.4, "weight_D": 0.4, "weight_C": 0.2},
            lambda_menger=3,
            rho_max=1.0,
            strict_bridges=[],
            strict_bridge_length_m=0.0,
            articulation_points=[],
            soft_bridges=[],
            explanation="Single-node route: trivially resilient.",
        )

    s = source if source is not None else route_nodes[0]
    t = target if target is not None else route_nodes[-1]

    # Calculate total route physical length
    total_route_length = 0.0
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i + 1]
        e_data = G_undirected.get_edge_data(u, v) or {}
        total_route_length += float(e_data.get("length", 0.0))

    # 1. Strict Bridges & Articulation Points
    strict_bridges, strict_len, route_aps = find_strict_critical_on_route(
        G_undirected, route_nodes, global_bridges, global_aps
    )

    # 2. Soft Bridges with Detour Ratio >= 1.5
    soft_bridges, rho_max = find_soft_bridges_on_route(
        G_directed, route_nodes, base_travel_time, detour_threshold=1.5, blocked_edges=blocked_edges
    )

    # 3. Menger's Edge Connectivity (\lambda)
    lambda_val = compute_edge_connectivity_menger(G_undirected, s, t)

    # 4. Composite Resilience Score R
    score, rating, color, components = calculate_resilience_score(
        lambda_val=lambda_val,
        rho_max=rho_max,
        strict_bridge_length_m=strict_len,
        total_route_length_m=total_route_length,
    )

    # 5. Formulate plain-English educational explanation for viva defense
    explanation_parts = []
    if lambda_val >= 3:
        explanation_parts.append(f"Menger's theorem guarantees \u03bb = {lambda_val} edge-disjoint backup paths between station and hospital.")
    else:
        explanation_parts.append(f"Menger's connectivity is restricted to \u03bb = {lambda_val} edge-disjoint path(s), indicating bottleneck corridor risk.")

    if strict_bridges:
        explanation_parts.append(f"Route traverses {len(strict_bridges)} strict cut-edge(s) ({round(strict_len)}m), representing absolute single points of failure.")
    else:
        explanation_parts.append("Route contains zero strict topological cut-edges.")

    if soft_bridges:
        worst_soft = max(soft_bridges, key=lambda sb: sb["detour_ratio"])
        explanation_parts.append(
            f"Detected {len(soft_bridges)} soft bridge(s) where road blockage causes severe delay (worst: '{worst_soft['road_name']}', \u03c1 = {worst_soft['detour_ratio']}x baseline time)."
        )
    else:
        explanation_parts.append("No soft bridges detected; all segments allow fast local detours (\u03c1 < 1.5).")

    explanation = " ".join(explanation_parts)

    return CriticalAnalysisResult(
        resilience_score=score,
        rating=rating,
        rating_color=color,
        components=components,
        lambda_menger=lambda_val,
        rho_max=round(rho_max, 2),
        strict_bridges=strict_bridges,
        strict_bridge_length_m=round(strict_len, 1),
        articulation_points=route_aps,
        soft_bridges=soft_bridges,
        explanation=explanation,
    )
