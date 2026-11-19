r"""Unit Tests for Critical Road Detection & Resilience Scoring.

Verifies:
1. Custom iterative Tarjan implementation matches NetworkX on hand-made graphs (barbell, star, trees)
2. Custom iterative Tarjan matches NetworkX on 20 random graphs
3. Resilience score calculation ($R = 100 \times (0.4L + 0.4D + 0.2C)$)
4. Soft bridge detection and detour ratio computations
"""

import networkx as nx
import pytest

from backend.algorithms.critical import (
    calculate_resilience_score,
    find_soft_bridges_on_route,
    tarjan_bridges_and_articulation_points,
)


def test_handcrafted_graph_tarjan():
    """Verify Tarjan's low-link algorithm on a handcrafted barbell graph with 2 complete graphs joined by a bridge."""
    # Barbell graph: K4 - P2 - K4
    # Nodes: 0,1,2,3 (K4) and 6,7,8,9 (K4) joined by path 3 - 4 - 5 - 6
    G = nx.barbell_graph(4, 2)

    our_bridges, our_aps = tarjan_bridges_and_articulation_points(G)
    nx_bridges = set(tuple(sorted(e)) for e in nx.bridges(G))
    nx_aps = set(nx.articulation_points(G))

    assert our_bridges == nx_bridges, f"Bridges mismatch: {our_bridges} != {nx_bridges}"
    assert our_aps == nx_aps, f"Articulation points mismatch: {our_aps} != {nx_aps}"
    assert our_bridges == {(3, 4), (4, 5), (5, 6)}
    assert our_aps == {3, 4, 5, 6}


def test_star_graph_tarjan():
    """Verify star graph where center node is the unique articulation point and all edges are bridges."""
    G = nx.star_graph(6)  # Node 0 is center, nodes 1..6 are leaves

    our_bridges, our_aps = tarjan_bridges_and_articulation_points(G)
    nx_bridges = set(tuple(sorted(e)) for e in nx.bridges(G))
    nx_aps = set(nx.articulation_points(G))

    assert our_bridges == nx_bridges
    assert our_aps == nx_aps
    assert len(our_bridges) == 6
    assert our_aps == {0}


def test_cycle_graph_tarjan():
    """Verify cycle graph (2-connected) has zero bridges and zero articulation points."""
    G = nx.cycle_graph(8)

    our_bridges, our_aps = tarjan_bridges_and_articulation_points(G)
    nx_bridges = set(tuple(sorted(e)) for e in nx.bridges(G))
    nx_aps = set(nx.articulation_points(G))

    assert our_bridges == nx_bridges == set()
    assert our_aps == nx_aps == set()


def test_random_graphs_tarjan_20_seeds():
    """Verify Tarjan's algorithm against NetworkX on 20 random graphs of varying densities."""
    for seed in range(20):
        # Generate random graph with 30 nodes and varying edge probabilities
        p = 0.08 + (seed % 5) * 0.04
        G = nx.gnp_random_graph(30, p, seed=seed)

        our_bridges, our_aps = tarjan_bridges_and_articulation_points(G)
        nx_bridges = set(tuple(sorted(e)) for e in nx.bridges(G))
        nx_aps = set(nx.articulation_points(G))

        assert our_bridges == nx_bridges, f"Bridges mismatch on seed {seed}"
        assert our_aps == nx_aps, f"Articulation points mismatch on seed {seed}"


def test_resilience_score_formula_bounds():
    """Verify boundary conditions of Resilience Score formula: R = 100 * (0.4L + 0.4D + 0.2C)."""
    # Case 1: Ideal network (\lambda >= 3, \rho_max = 1.0, 0 strict bridges) -> R = 100
    score, rating, color, comp = calculate_resilience_score(
        lambda_val=3, rho_max=1.0, strict_bridge_length_m=0.0, total_route_length_m=1000.0
    )
    assert score == 100.0
    assert rating == "Resilient"
    assert comp["L"] == 1.0
    assert comp["D"] == 1.0
    assert comp["C"] == 1.0

    # Case 2: Catastrophic bottleneck (\lambda = 1, \rho_max = 3.0, 50% strict bridges)
    # L = 1/3 = 0.333, D = 1 - (3-1)/2 = 0.0, C = 1 - 0.5 = 0.5
    # R = 100 * (0.4 * 0.3333 + 0 + 0.2 * 0.5) = 100 * (0.1333 + 0.1) = 23.3
    score2, rating2, color2, comp2 = calculate_resilience_score(
        lambda_val=1, rho_max=3.0, strict_bridge_length_m=500.0, total_route_length_m=1000.0
    )
    assert score2 < 50.0
    assert rating2 == "Fragile"
    assert pytest.approx(comp2["D"], 1e-3) == 0.0
    assert pytest.approx(comp2["C"], 1e-3) == 0.5


def test_soft_bridge_detour_ratio():
    """Verify detection of soft bridges where edge removal causes significant detour (> 1.5x)."""
    # Graph with a direct highway (time = 10s) vs a very long detour (time = 50s)
    G = nx.MultiDiGraph()
    G.add_edge("S", "A", key=0, travel_time=10.0, length=100.0, name="Direct Corridor", highway="primary")
    G.add_edge("A", "T", key=0, travel_time=10.0, length=100.0, name="Hospital Gate", highway="primary")

    # Long alternative detour around the lake/railway
    G.add_edge("S", "D1", key=0, travel_time=25.0, length=400.0, name="Detour Outer Road", highway="secondary")
    G.add_edge("D1", "D2", key=0, travel_time=25.0, length=400.0, name="Detour Ring Road", highway="secondary")
    G.add_edge("D2", "T", key=0, travel_time=25.0, length=400.0, name="Detour Inner Link", highway="secondary")

    route_nodes = ["S", "A", "T"]
    base_time = 20.0  # 10 + 10

    soft_bridges, rho_max = find_soft_bridges_on_route(
        G, route_nodes=route_nodes, base_travel_time=base_time, detour_threshold=1.5
    )

    # When S->A is blocked, the alternate route is S->D1->D2->T = 75s. Detour ratio = 75 / 20 = 3.75 >= 1.5
    assert len(soft_bridges) >= 1
    flagged_edges = [(sb["u"], sb["v"]) for sb in soft_bridges]
    assert ("S", "A") in flagged_edges
    assert rho_max >= 1.5
