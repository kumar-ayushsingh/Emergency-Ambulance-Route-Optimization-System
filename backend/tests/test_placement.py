"""Unit and Integration Tests for Station Placement and Coverage Isochrones.

Verifies:
- Demand grid sampling (300-500 nodes within bounding box)
- Candidate sites generation (degree >= 3 plus hospital gates)
- Eccentricity, Graph Center, and Graph Radius (k=1)
- Greedy K-Center Minimax placement and monotonicity
- Swap-based P-Median Minisum placement
- Multi-Source Dijkstra Isochrone coverage and band sum conservation
"""

import numpy as np
import pytest

from backend.algorithms.placement import (
    compute_candidate_demand_matrix,
    compute_eccentricity_and_center,
    compute_multi_source_coverage,
    get_candidate_junctions,
    greedy_k_center,
    sample_demand_grid,
    swap_p_median,
)
from backend.graph_builder import load_graph, load_hospitals, load_stations, nearest_node


@pytest.fixture(scope="module")
def graph_and_facilities():
    """Load graph and precompute facility nodes once for test module."""
    G = load_graph()
    hospitals = load_hospitals()
    stations = load_stations()

    hospital_nodes = [nearest_node(G, X=h["lng"], Y=h["lat"]) for h in hospitals]
    station_nodes = [nearest_node(G, X=s["lng"], Y=s["lat"]) for s in stations]

    return {
        "G": G,
        "hospitals": hospitals,
        "stations": stations,
        "hospital_nodes": hospital_nodes,
        "station_nodes": station_nodes,
    }


def test_sample_demand_grid(graph_and_facilities):
    """Verify that spatial grid sampling produces 300-500 valid unique demand nodes."""
    G = graph_and_facilities["G"]
    demand_nodes = sample_demand_grid(G, num_rows=21, num_cols=21)

    assert 300 <= len(demand_nodes) <= 500, f"Expected 300-500 demand nodes, got {len(demand_nodes)}"

    # All demand vertices must exist in the directed graph
    for d in demand_nodes:
        assert d in G, f"Demand node {d} not in graph"
        node_data = G.nodes[d]
        assert 77.55 <= float(node_data["x"]) <= 77.67
        assert 12.91 <= float(node_data["y"]) <= 13.02


def test_candidate_junctions(graph_and_facilities):
    """Verify candidate sites include hospital gates and major junctions."""
    G = graph_and_facilities["G"]
    hospital_nodes = graph_and_facilities["hospital_nodes"]

    candidates = get_candidate_junctions(G, hospital_nodes, num_rows=10, num_cols=10)
    assert len(candidates) >= 50

    # Every hospital node must be included as a candidate site
    for h_node in hospital_nodes:
        assert h_node in candidates, f"Hospital gate {h_node} missing from candidate set"

    for c in candidates:
        assert c in G, f"Candidate {c} not in graph"


def test_eccentricity_and_1_center(graph_and_facilities):
    """Verify graph center and radius calculation over the demand set (k=1)."""
    G = graph_and_facilities["G"]
    hospital_nodes = graph_and_facilities["hospital_nodes"]

    candidates = get_candidate_junctions(G, hospital_nodes, num_rows=8, num_cols=8)
    demand_nodes = sample_demand_grid(G, num_rows=15, num_cols=15)

    res = compute_eccentricity_and_center(G, candidates, demand_nodes)

    assert res.algorithm == "1-center"
    assert res.k == 1
    assert len(res.selected_nodes) == 1
    assert res.selected_nodes[0] in candidates

    # Radius must be positive and reasonable for an urban corridor (< 35 mins)
    assert 0 < res.radius_min < 35.0
    assert 0 < res.mean_travel_time_min < res.radius_min
    assert res.bands.under_8_min_pct >= 0.0


def test_greedy_k_center_monotonicity(graph_and_facilities):
    """Verify K-Center selects k distinct centers and exhibits minimax monotonicity."""
    G = graph_and_facilities["G"]
    hospital_nodes = graph_and_facilities["hospital_nodes"]

    candidates = get_candidate_junctions(G, hospital_nodes, num_rows=8, num_cols=8)
    demand_nodes = sample_demand_grid(G, num_rows=15, num_cols=15)
    cost_matrix = compute_candidate_demand_matrix(G, candidates, demand_nodes, use_cache=False)

    k2_res = greedy_k_center(G, candidates, demand_nodes, k=2, cost_matrix=cost_matrix)
    k4_res = greedy_k_center(G, candidates, demand_nodes, k=4, cost_matrix=cost_matrix)

    assert len(k2_res.selected_nodes) == 2
    assert len(k4_res.selected_nodes) == 4
    assert len(set(k4_res.selected_nodes)) == 4, "All selected k-centers must be distinct"

    # Monotonicity of minimax radius: more centers must not increase the worst-case radius
    assert k4_res.radius_sec <= k2_res.radius_sec + 1e-4, (
        f"4-center radius ({k4_res.radius_sec}s) must be <= 2-center radius ({k2_res.radius_sec}s)"
    )


def test_swap_p_median_improvement(graph_and_facilities):
    """Verify Teitz-Bart P-Median optimizes minisum total/average response time."""
    G = graph_and_facilities["G"]
    hospital_nodes = graph_and_facilities["hospital_nodes"]

    candidates = get_candidate_junctions(G, hospital_nodes, num_rows=8, num_cols=8)
    demand_nodes = sample_demand_grid(G, num_rows=15, num_cols=15)
    cost_matrix = compute_candidate_demand_matrix(G, candidates, demand_nodes, use_cache=False)

    k_res = greedy_k_center(G, candidates, demand_nodes, k=4, cost_matrix=cost_matrix)
    p_res = swap_p_median(G, candidates, demand_nodes, k=4, cost_matrix=cost_matrix)

    assert len(p_res.selected_nodes) == 4
    assert len(set(p_res.selected_nodes)) == 4

    # P-median must have mean travel time <= or equal to initial seed (minisum objective)
    assert p_res.mean_travel_time_sec <= k_res.mean_travel_time_sec + 1.0


def test_multi_source_coverage_band_conservation(graph_and_facilities):
    """Verify multi-source coverage bands sum to 100% of demand points."""
    G = graph_and_facilities["G"]
    station_nodes = graph_and_facilities["station_nodes"]
    demand_nodes = sample_demand_grid(G, num_rows=21, num_cols=21)

    cov = compute_multi_source_coverage(G, station_nodes=station_nodes, demand_nodes=demand_nodes)

    assert cov.total_demand_points == len(demand_nodes)
    b = cov.bands

    # Total counts must equal total demand vertices
    total_band_counts = (
        b.under_8_min_count + b.between_8_and_15_count + b.between_15_and_30_count + b.over_30_min_count
    )
    assert total_band_counts == cov.total_demand_points

    # Total percentage must equal 100% (within rounding)
    total_pct = (
        b.under_8_min_pct + b.between_8_and_15_pct + b.between_15_and_30_pct + b.over_30_min_pct
    )
    assert 99.5 <= total_pct <= 100.5

    # Check properties of each demand point for frontend heatmap rendering
    for pt in cov.demand_points_data:
        assert "lat" in pt and "lng" in pt
        assert "time_min" in pt
        assert pt["band"] in {"under_8_min", "8_to_15_min", "15_to_30_min", "over_30_min"}
        assert pt["color"].startswith("#")
