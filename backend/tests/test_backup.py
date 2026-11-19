"""Unit Tests for Backup Routes (Yen's K-Shortest Paths & Edge-Disjoint Paths).

Verifies:
1. Yen's K=3 shortest simple paths on a handcrafted multigraph
2. Edge-disjoint backup paths sharing zero edges with Plan A
3. Time differences and monotonicity: cost(Plan A) <= cost(Plan B) <= cost(Plan C)
"""

import networkx as nx
import pytest

from backend.algorithms.backup import (
    compute_edge_disjoint_backup_paths,
    generate_backup_plans,
    yen_k_shortest_paths,
)


@pytest.fixture
def sample_diamond_graph() -> nx.MultiDiGraph:
    """Create a multigraph with multiple distinct s-t paths.

    Topology:
        (S) --[10s]--> (A) --[10s]--> (T)  (Path 1: S-A-T, cost=20)
        (S) --[12s]--> (B) --[12s]--> (T)  (Path 2: S-B-T, cost=24)
        (S) --[15s]--> (C) --[15s]--> (T)  (Path 3: S-C-T, cost=30)
        (A) --[2s]--> (B)                  (Path 4: S-A-B-T, cost=24)
    """
    G = nx.MultiDiGraph()
    G.add_edge("S", "A", key=0, travel_time=10.0, length=100.0)
    G.add_edge("A", "T", key=0, travel_time=10.0, length=100.0)

    G.add_edge("S", "B", key=0, travel_time=12.0, length=120.0)
    G.add_edge("B", "T", key=0, travel_time=12.0, length=120.0)

    G.add_edge("S", "C", key=0, travel_time=15.0, length=150.0)
    G.add_edge("C", "T", key=0, travel_time=15.0, length=150.0)

    G.add_edge("A", "B", key=0, travel_time=2.0, length=20.0)
    return G


def test_yen_k_shortest_paths_monotonicity(sample_diamond_graph: nx.MultiDiGraph):
    """Verify Yen's algorithm returns K simple loopless paths in strictly non-decreasing order of cost."""
    G = sample_diamond_graph
    results = yen_k_shortest_paths(G, source="S", target="T", K=3, weight="travel_time")

    assert len(results) == 3, f"Expected 3 paths, got {len(results)}"
    # Monotonicity check
    assert results[0].cost <= results[1].cost <= results[2].cost
    assert results[0].cost == 20.0  # S -> A -> T
    assert results[1].cost == 24.0  # S -> B -> T or S -> A -> B -> T


def test_edge_disjoint_paths(sample_diamond_graph: nx.MultiDiGraph):
    """Verify edge-disjoint paths share zero road segments with the primary path."""
    G = sample_diamond_graph
    primary_path = ["S", "A", "T"]
    primary_edges = {("S", "A"), ("A", "T")}

    disjoint_results = compute_edge_disjoint_backup_paths(
        G, source="S", target="T", primary_path=primary_path, max_paths=2, weight="travel_time"
    )

    assert len(disjoint_results) >= 1
    for res in disjoint_results:
        # Check no overlap with primary edges
        path = res.path
        for i in range(len(path) - 1):
            e = (path[i], path[i + 1])
            assert e not in primary_edges, f"Disjoint path contains edge {e} from primary route!"


def test_generate_backup_plans(sample_diamond_graph: nx.MultiDiGraph):
    """Verify generation of Plan A, Plan B, and Plan C with correct time differences."""
    G = sample_diamond_graph
    plans = generate_backup_plans(G, source="S", target="T", weight="travel_time")

    assert len(plans) == 3
    plan_a, plan_b, plan_c = plans[0], plans[1], plans[2]

    assert plan_a.plan_name == "Plan A (Primary)"
    assert plan_a.time_diff_sec == 0.0
    assert plan_b.time_diff_sec >= 0.0
    assert plan_c.time_diff_sec >= plan_b.time_diff_sec
