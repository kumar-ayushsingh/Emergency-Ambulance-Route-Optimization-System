r"""Backup Route Generation & Road Blockage Engine.

Academic Context:
Discrete Mathematics · Module 4: Graph Theory
Problem Statement: K-Shortest Simple Paths, Edge-Disjoint Paths, and Dynamic Graph Modifications.

Mathematical Formulations:
1. Yen's K-Shortest Simple Paths Algorithm (Jin Y. Yen, 1971):
   Finds the loopless paths A = [A_0, A_1, ..., A_{K-1}] in strictly non-decreasing cost:
       w(A_0) <= w(A_1) <= ... <= w(A_{K-1})
   - A_0 is the standard Dijkstra shortest path (Plan A).
   - For k = 1 to K - 1:
     Iterate through all spur nodes v_i along A_{k-1}:
     - Root path R = A_{k-1}[0 : i]
     - Temporarily remove edges incident to v_i that share the same root path in previous paths.
     - Temporarily remove all vertices in R except v_i.
     - Run Dijkstra from spur node v_i to target t.
     - If a spur path exists, concatenate R[:-1] + spur_path as candidate path in B.
     - Restore removed vertices and edges.
     Pick candidate in B with minimum weight as A_k.
   Complexity:
   - Time Complexity: O(K * |V| * (|E| + |V| \log |V|))
   - Space Complexity: O(K * |V|)

2. Edge-Disjoint Backup Paths (Plan B & Plan C via Menger):
   Finds paths that share zero road segments with Plan A:
       E(Plan B) \cap E(Plan A) = \emptyset
   By removing all edges of Plan A from a working copy of G and finding the shortest path,
   we guarantee true physical independence—essential if a corridor is blocked by flood,
   landslide, or gridlock.
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from backend.algorithms.dijkstra import DijkstraResult, dijkstra_shortest_path

logger = logging.getLogger(__name__)


@dataclass
class BackupPlan:
    """Represents an alternative backup route (Plan B or Plan C)."""

    plan_name: str  # 'Plan A (Primary)', 'Plan B', 'Plan C'
    path: List[Any]  # Sequence of node IDs
    cost: float  # Travel time in seconds
    distance: float  # Distance in meters
    time_diff_sec: float  # Difference in seconds compared to Plan A
    time_diff_min: float  # Difference in minutes compared to Plan A
    color: str  # Display color for Leaflet polyline
    is_disjoint: bool  # True if strictly edge-disjoint from Plan A


def yen_k_shortest_paths(
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    source: Any,
    target: Any,
    K: int = 3,
    weight: str = "travel_time",
    blocked_edges: Optional[Set[Tuple[Any, Any]]] = None,
) -> List[DijkstraResult]:
    r"""Compute the K-shortest simple (loopless) paths from source to target using Yen's algorithm.

    Args:
        G: Directed or undirected graph.
        source: Source vertex.
        target: Target vertex.
        K: Number of paths to retrieve (default: 3 for Plan A, Plan B, Plan C).
        weight: Edge weight attribute (default: 'travel_time').
        blocked_edges: Optional pre-existing blocked edges to avoid.

    Returns:
        List of up to K DijkstraResult objects sorted by non-decreasing travel time.
    """
    if source not in G or target not in G or K <= 0:
        return []

    # 1. Compute primary shortest path A[0] (Plan A)
    first_path_res = dijkstra_shortest_path(G, source, target, weight=weight, blocked_edges=blocked_edges)
    if first_path_res is None:
        return []

    # List of confirmed shortest simple paths
    A: List[DijkstraResult] = [first_path_res]

    # Candidate set B: min-heap storing tuples (cost, path_list)
    B: List[Tuple[float, List[Any]]] = []
    seen_in_B: Set[Tuple[Any, ...]] = {tuple(first_path_res.path)}

    base_blocked = set(blocked_edges) if blocked_edges else set()

    for k in range(1, K):
        prev_path = A[k - 1].path

        # The spur node ranges from the first node up to the second-to-last node
        for i in range(len(prev_path) - 1):
            spur_node = prev_path[i]
            root_path = prev_path[: i + 1]

            # 1. Edges to block: edges incident to spur_node shared by previous paths with same root
            step_blocked_edges = set(base_blocked)
            for path_res in A:
                p = path_res.path
                if len(p) > i and p[: i + 1] == root_path:
                    u, v = p[i], p[i + 1]
                    step_blocked_edges.add((u, v))

            # 2. Nodes to block: all nodes in root_path except spur_node
            step_blocked_nodes = set(root_path[:-1])

            # 3. Compute spur path from spur_node to target without copying the graph
            spur_res = dijkstra_shortest_path(
                G,
                source=spur_node,
                target=target,
                weight=weight,
                blocked_edges=step_blocked_edges,
                blocked_nodes=step_blocked_nodes,
            )

            if spur_res is not None:
                # Concatenate root path and spur path
                total_candidate_path = root_path[:-1] + spur_res.path
                path_tuple = tuple(total_candidate_path)

                if path_tuple not in seen_in_B:
                    seen_in_B.add(path_tuple)
                    c_cost, c_dist = compute_path_cost_and_distance(G, total_candidate_path, weight=weight)
                    heapq.heappush(B, (c_cost, total_candidate_path))

        if not B:
            break

        # Extract path with minimum cost from B
        best_cost, best_path = heapq.heappop(B)
        _, best_dist = compute_path_cost_and_distance(G, best_path, weight=weight)

        A.append(
            DijkstraResult(
                path=best_path,
                cost=best_cost,
                distance=best_dist,
                nodes_expanded=0,
                visited_nodes=[],
            )
        )

    return A


def compute_path_cost_and_distance(
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    path: List[Any],
    weight: str = "travel_time",
) -> Tuple[float, float]:
    """Calculate the total travel time cost and physical distance along a path."""
    total_cost = 0.0
    total_dist = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = G.get_edge_data(u, v)
        if edge_data is None:
            continue

        if G.is_multigraph():
            min_w = float("inf")
            min_len = 0.0
            for attrs in edge_data.values():
                w = float(attrs.get(weight, float("inf")))
                if w < min_w:
                    min_w = w
                    min_len = float(attrs.get("length", 0.0))
            total_cost += min_w
            total_dist += min_len
        else:
            total_cost += float(edge_data.get(weight, 0.0))
            total_dist += float(edge_data.get("length", 0.0))

    return total_cost, total_dist


def compute_edge_disjoint_backup_paths(
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    source: Any,
    target: Any,
    primary_path: List[Any],
    max_paths: int = 2,
    weight: str = "travel_time",
    blocked_edges: Optional[Set[Tuple[Any, Any]]] = None,
) -> List[DijkstraResult]:
    r"""Compute backup paths that share strictly zero road segments with the primary route.

    Formula:
        E(Backup) \cap E(Primary) = \emptyset

    Skips every edge traversed in the primary path without copying G.

    Args:
        G: Directed road graph.
        source: Source station node ID.
        target: Target destination node ID.
        primary_path: Primary route node sequence [v_0, v_1, ..., v_k].
        max_paths: Maximum number of disjoint alternatives to compute (default: 2).
        weight: Edge weight attribute.
        blocked_edges: Optional pre-existing blocked edges to avoid.

    Returns:
        List of edge-disjoint DijkstraResult objects.
    """
    disjoint_edges: Set[Tuple[Any, Any]] = set(blocked_edges) if blocked_edges else set()
    disjoint_paths: List[DijkstraResult] = []

    # Block all directed edges used by the primary path (both directions for corridor independence)
    for i in range(len(primary_path) - 1):
        u, v = primary_path[i], primary_path[i + 1]
        disjoint_edges.add((u, v))
        disjoint_edges.add((v, u))

    for _ in range(max_paths):
        res = dijkstra_shortest_path(
            G, source=source, target=target, weight=weight, blocked_edges=disjoint_edges
        )
        if res is None:
            break

        disjoint_paths.append(res)

        # Block edges of this newly found disjoint path to find subsequent disjoint paths
        for i in range(len(res.path) - 1):
            u, v = res.path[i], res.path[i + 1]
            disjoint_edges.add((u, v))
            disjoint_edges.add((v, u))

    return disjoint_paths


def generate_backup_plans(
    G: nx.MultiDiGraph | nx.DiGraph | nx.Graph,
    source: Any,
    target: Any,
    primary_path: Optional[List[Any]] = None,
    primary_time: Optional[float] = None,
    weight: str = "travel_time",
    blocked_edges: Optional[Set[Tuple[Any, Any]]] = None,
) -> List[BackupPlan]:
    """Generate consolidated Plan B and Plan C backup alternatives using Yen's and edge-disjoint search.

    Color scheme:
    - Plan A: Primary (#38bdf8 / #ef4444)
    - Plan B: Violet / Purple (#a855f7)
    - Plan C: Teal / Cyan (#06b6d4)

    Args:
        G: Directed road graph.
        source: Starting node ID.
        target: Destination node ID.
        primary_path: Optional precomputed primary path.
        primary_time: Optional precomputed primary time.
        weight: Edge weight attribute.
        blocked_edges: Optional pre-existing blocked edges to avoid.

    Returns:
        List of BackupPlan objects (Plan A, Plan B, Plan C).
    """
    plans: List[BackupPlan] = []

    # Compute Yen's K=3 shortest paths
    yen_results = yen_k_shortest_paths(
        G, source, target, K=3, weight=weight, blocked_edges=blocked_edges
    )
    if not yen_results:
        return []

    plan_a = yen_results[0]
    base_time = primary_time if primary_time is not None else plan_a.cost

    plans.append(
        BackupPlan(
            plan_name="Plan A (Primary)",
            path=plan_a.path,
            cost=plan_a.cost,
            distance=plan_a.distance,
            time_diff_sec=0.0,
            time_diff_min=0.0,
            color="#38bdf8",  # Sky Blue
            is_disjoint=False,
        )
    )

    # Check for completely edge-disjoint alternatives
    disjoint_results = compute_edge_disjoint_backup_paths(
        G,
        source=source,
        target=target,
        primary_path=plan_a.path,
        max_paths=2,
        weight=weight,
        blocked_edges=blocked_edges,
    )

    # Assign Plan B: Prefer edge-disjoint if available, otherwise Yen's 2nd path
    if len(yen_results) >= 2:
        plan_b = yen_results[1]
        diff_sec = plan_b.cost - base_time
        plans.append(
            BackupPlan(
                plan_name="Plan B (Yen K=2)",
                path=plan_b.path,
                cost=plan_b.cost,
                distance=plan_b.distance,
                time_diff_sec=round(diff_sec, 1),
                time_diff_min=round(diff_sec / 60.0, 2),
                color="#a855f7",  # Purple
                is_disjoint=False,
            )
        )
    elif disjoint_results:
        plan_b = disjoint_results[0]
        diff_sec = plan_b.cost - base_time
        plans.append(
            BackupPlan(
                plan_name="Plan B (Edge-Disjoint)",
                path=plan_b.path,
                cost=plan_b.cost,
                distance=plan_b.distance,
                time_diff_sec=round(diff_sec, 1),
                time_diff_min=round(diff_sec / 60.0, 2),
                color="#a855f7",
                is_disjoint=True,
            )
        )

    # Assign Plan C: Prefer edge-disjoint alternative, otherwise Yen's 3rd path
    if len(yen_results) >= 3:
        plan_c = yen_results[2]
        diff_sec = plan_c.cost - base_time
        plans.append(
            BackupPlan(
                plan_name="Plan C (Yen K=3)",
                path=plan_c.path,
                cost=plan_c.cost,
                distance=plan_c.distance,
                time_diff_sec=round(diff_sec, 1),
                time_diff_min=round(diff_sec / 60.0, 2),
                color="#06b6d4",  # Cyan
                is_disjoint=False,
            )
        )
    elif len(disjoint_results) >= 2:
        plan_c = disjoint_results[1]
        diff_sec = plan_c.cost - base_time
        plans.append(
            BackupPlan(
                plan_name="Plan C (Edge-Disjoint)",
                path=plan_c.path,
                cost=plan_c.cost,
                distance=plan_c.distance,
                time_diff_sec=round(diff_sec, 1),
                time_diff_min=round(diff_sec / 60.0, 2),
                color="#06b6d4",
                is_disjoint=True,
            )
        )

    return plans
