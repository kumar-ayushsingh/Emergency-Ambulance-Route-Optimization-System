"""Unit Tests and NetworkX Cross-Validation for Custom Dijkstra Implementation.

Verifies:
1. Ground-truth correctness on small handcrafted test graphs
2. Boundary conditions (source == target, unreachable nodes)
3. Cross-check against NetworkX on 100 random node pairs on the loaded road network
"""

import random
import networkx as nx
import pytest

from backend.algorithms.dijkstra import dijkstra_shortest_path, multi_source_dijkstra
from backend.graph_builder import load_graph


@pytest.fixture(scope="module")
def road_graph() -> nx.MultiDiGraph:
    """Load cached road network once for cross-validation tests."""
    return load_graph()


def test_handcrafted_graph_ground_truth():
    """Verify Dijkstra on a known directed graph with 5 vertices and known shortest paths.

    Graph Topology:
        (A) --[time=2, len=100]--> (B) --[time=3, len=150]--> (D)
         |                          ^                          |
      [time=4, len=200]          [time=1, len=50]          [time=1, len=40]
         v                          |                          v
        (C) ------------------------+-----------------------> (E)
                   (to B: time=1; to E: time=7)
    """
    G = nx.DiGraph()
    G.add_edge("A", "B", travel_time=2.0, length=100.0)
    G.add_edge("A", "C", travel_time=4.0, length=200.0)
    G.add_edge("C", "B", travel_time=1.0, length=50.0)
    G.add_edge("B", "D", travel_time=3.0, length=150.0)
    G.add_edge("D", "E", travel_time=1.0, length=40.0)
    G.add_edge("C", "E", travel_time=7.0, length=300.0)

    # Route A -> E:
    # Path 1: A -> B -> D -> E: 2 + 3 + 1 = 6s, dist = 290m
    # Path 2: A -> C -> B -> D -> E: 4 + 1 + 3 + 1 = 9s
    # Path 3: A -> C -> E: 4 + 7 = 11s
    res = dijkstra_shortest_path(G, "A", "E")
    assert res is not None
    assert res.path == ["A", "B", "D", "E"]
    assert pytest.approx(res.cost, 1e-5) == 6.0
    assert pytest.approx(res.distance, 1e-5) == 290.0
    assert res.nodes_expanded > 0


def test_source_equals_target():
    """Verify trivial case where source is identical to target."""
    G = nx.DiGraph()
    G.add_edge("A", "B", travel_time=5.0, length=100.0)

    res = dijkstra_shortest_path(G, "A", "A")
    assert res is not None
    assert res.path == ["A"]
    assert res.cost == 0.0
    assert res.distance == 0.0
    assert res.nodes_expanded == 1


def test_unreachable_node():
    """Verify that an unreachable node returns None."""
    G = nx.DiGraph()
    G.add_edge("A", "B", travel_time=2.0, length=50.0)
    G.add_node("C")  # Disconnected node

    res = dijkstra_shortest_path(G, "A", "C")
    assert res is None


def test_multi_source_dijkstra():
    """Verify multi-source Dijkstra finds closest station and exact travel time."""
    G = nx.DiGraph()
    # Stations: S1, S2
    G.add_edge("S1", "X", travel_time=10.0)
    G.add_edge("S2", "X", travel_time=4.0)  # S2 is closer to X
    G.add_edge("X", "Y", travel_time=2.0)

    dist, pred, nearest_src = multi_source_dijkstra(G, sources=["S1", "S2"])
    assert dist["X"] == 4.0
    assert nearest_src["X"] == "S2"
    assert dist["Y"] == 6.0
    assert nearest_src["Y"] == "S2"


def test_cross_check_against_networkx_100_pairs(road_graph: nx.MultiDiGraph):
    """Rigorous academic verification: cross-check our Dijkstra against NetworkX on 100 random pairs.

    Rule 1: Cross-check custom implementations against NetworkX in tests.
    """
    nodes = list(road_graph.nodes())
    assert len(nodes) >= 1000

    random.seed(42)  # Deterministic reproducibility
    sample_size = 100

    for i in range(sample_size):
        u = random.choice(nodes)
        v = random.choice(nodes)

        # Compute with custom Dijkstra
        our_result = dijkstra_shortest_path(road_graph, source=u, target=v, weight="travel_time")

        # Compute with NetworkX ground truth
        try:
            nx_cost, nx_path = nx.single_source_dijkstra(
                road_graph, source=u, target=v, weight="travel_time"
            )
            # Both must agree
            assert our_result is not None, f"Our Dijkstra failed to find path from {u} to {v} on pair #{i}"
            assert pytest.approx(our_result.cost, rel=1e-4) == nx_cost, (
                f"Cost mismatch on pair #{i}: Our={our_result.cost}, NX={nx_cost}"
            )
            assert our_result.path[0] == u
            assert our_result.path[-1] == v

        except nx.NetworkXNoPath:
            # If NetworkX finds no path, our Dijkstra must also return None
            assert our_result is None, f"Our Dijkstra returned a path where NetworkX found none on pair #{i}"
