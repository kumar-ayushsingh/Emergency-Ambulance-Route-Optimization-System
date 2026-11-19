"""Unit Tests for A* Search and Algorithm Race against Dijkstra.

Academic Context:
Discrete Mathematics · Module 4: Graph Theory · A* Admissibility & Optimality
Requirement: Confirm identical shortest-path costs on 100 random pairs.
"""

import random
import networkx as nx
import pytest

from backend.algorithms.astar import (
    astar_shortest_path,
    dijkstra_race_search,
    get_max_network_speed_mps,
    haversine_distance,
    haversine_heuristic,
    run_algorithm_race,
)
from backend.graph_builder import load_graph


@pytest.fixture(scope="module")
def graph():
    """Load cached road network graph."""
    return load_graph()


def test_haversine_formula():
    """Verify haversine distance against known reference coordinates."""
    # Distance between Bengaluru Majestic (12.9775, 77.5715) and MG Road (12.9750, 77.6100)
    # Approx straight-line distance is ~4.18 km
    dist = haversine_distance(12.9775, 77.5715, 12.9750, 77.6100)
    assert 4000.0 <= dist <= 4400.0

    # Distance to identical point is 0
    assert haversine_distance(12.9775, 77.5715, 12.9775, 77.5715) == 0.0


def test_heuristic_admissibility(graph):
    """Verify that h(u) <= true_cost(u, target) for all sampled nodes (admissibility)."""
    G = graph
    nodes = list(G.nodes)
    random.seed(42)
    sample_nodes = random.sample(nodes, 20)
    target = sample_nodes[-1]
    max_speed = get_max_network_speed_mps(G)

    for u in sample_nodes[:-1]:
        h_val = haversine_heuristic(u, target, G, max_speed)
        dijkstra_res = dijkstra_race_search(G, u, target)
        if dijkstra_res is not None:
            # Admissibility condition: h(u) <= true_shortest_cost
            assert h_val <= dijkstra_res.cost + 1e-4, (
                f"Heuristic violation: h({u})={h_val:.2f} > true_cost={dijkstra_res.cost:.2f}"
            )


def test_dijkstra_vs_astar_equal_costs_100_random_pairs(graph):
    """Verify that Dijkstra and A* produce mathematically equal costs on 100 random pairs."""
    G = graph
    nodes = list(G.nodes)
    random.seed(2026)  # Deterministic seed for reproducible testing

    pairs_tested = 0
    max_speed = get_max_network_speed_mps(G)

    # Sample random node pairs
    candidate_sources = random.sample(nodes, 120)
    candidate_targets = random.sample(nodes, 120)

    for s, t in zip(candidate_sources, candidate_targets):
        if s == t:
            continue

        dijkstra_res = dijkstra_race_search(G, s, t)
        astar_res = astar_shortest_path(G, s, t, max_speed_mps=max_speed)

        # Both should either find a path or both find None
        if dijkstra_res is None or astar_res is None:
            assert dijkstra_res is None and astar_res is None
            continue

        # 1. Critical Assertion: Exact cost equality within 1 millisecond
        cost_diff = abs(dijkstra_res.cost - astar_res.cost)
        assert cost_diff < 1e-3, (
            f"Cost mismatch between Dijkstra ({dijkstra_res.cost:.4f}s) and A* ({astar_res.cost:.4f}s) for pair ({s}, {t})"
        )

        # 2. Pruning efficiency: A* should expand <= nodes than Dijkstra
        assert astar_res.nodes_expanded <= dijkstra_res.nodes_expanded, (
            f"A* expanded more nodes ({astar_res.nodes_expanded}) than Dijkstra ({dijkstra_res.nodes_expanded})"
        )

        # 3. Path validity: starts at s, ends at t
        assert astar_res.path[0] == s
        assert astar_res.path[-1] == t

        pairs_tested += 1
        if pairs_tested >= 100:
            break

    assert pairs_tested == 100, f"Expected 100 tested pairs, but completed {pairs_tested}"


def test_run_algorithm_race_helper(graph):
    """Verify run_algorithm_race returns telemetry, downsampled animation coords, and comparisons."""
    G = graph
    nodes = list(G.nodes)
    s, t = nodes[100], nodes[500]

    race = run_algorithm_race(G, s, t, animation_sample_limit=500)
    assert race["success"] is True
    assert race["costs_equal"] is True
    assert "dijkstra" in race
    assert "astar" in race
    assert race["dijkstra"]["nodes_expanded"] >= race["astar"]["nodes_expanded"]
    assert len(race["dijkstra"]["anim_coords"]) <= 500
    assert len(race["astar"]["anim_coords"]) <= 500
