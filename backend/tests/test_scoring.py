"""Unit Tests for Hospital Triage Scoring, Traffic Multipliers, and Route Divergence.

Academic Context:
Discrete Mathematics · Module 4: Graph Theory · Multi-Criteria Facility Selection
"""

import json
from pathlib import Path

import networkx as nx
import pytest

from backend.algorithms.dijkstra import dijkstra_shortest_path
from backend.algorithms.scoring import (
    DEFAULT_PENALTIES,
    compare_offpeak_vs_peak_route,
    compute_hospital_penalties,
    evaluate_hospital_scores,
    generate_scoring_explanation,
)
from backend.algorithms.traffic import (
    attach_traffic_weights_to_graph,
    get_edge_traffic_multiplier,
    get_traffic_config,
    load_traffic_config,
)
from backend.graph_builder import load_graph, load_hospitals


def test_traffic_json_structure_and_corridors():
    """Verify data/traffic.json contains all required periods and named corridors."""
    cfg = load_traffic_config()

    periods = cfg["time_periods"]
    assert "off_peak" in periods
    assert "morning_peak" in periods
    assert "evening_peak" in periods
    assert "night" in periods

    # Verify standard base multipliers
    assert periods["off_peak"]["default_multiplier"] == 1.0
    assert periods["morning_peak"]["default_multiplier"] == 1.6
    assert periods["evening_peak"]["default_multiplier"] == 1.8
    assert periods["night"]["default_multiplier"] == 0.8

    # Verify road class hierarchy multipliers exist
    for p in ["off_peak", "morning_peak", "evening_peak", "night"]:
        assert "primary" in periods[p]["road_multipliers"]
        assert "secondary" in periods[p]["road_multipliers"]
        assert "residential" in periods[p]["road_multipliers"]

    # Verify required corridors from assignment specification
    corridors = cfg["special_corridors"]
    corridor_names = [c["name"].lower() for c in corridors.values()]

    assert any("karan nagar to smhs" in n for n in corridor_names), "Karan Nagar to SMHS corridor must be present"
    assert any("jehangir chowk" in n for n in corridor_names), "Jehangir Chowk must be present"
    assert any("skims soura chowk" in n for n in corridor_names), "SKIMS Soura chowk must be present"


def test_edge_traffic_multiplier_calculation():
    """Test individual edge traffic multiplier with road class and corridor matching."""
    config = get_traffic_config()

    # Regular residential road in off-peak
    edge_res = {"highway": "residential", "name": "5th Cross Road"}
    m_res_off = get_edge_traffic_multiplier(edge_res, period="off_peak", config=config)
    assert m_res_off == 1.0

    # Primary road in evening peak
    edge_pri = {"highway": "primary", "name": "MG Road"}
    m_pri_eve = get_edge_traffic_multiplier(edge_pri, period="evening_peak", config=config)
    assert m_pri_eve >= 1.8

    # Corridor matching Karan Nagar / SMHS
    edge_corr_smhs = {"highway": "primary", "name": "Karan Nagar Road"}
    m_smhs_peak = get_edge_traffic_multiplier(edge_corr_smhs, period="evening_peak", config=config)
    # Extra multiplier 1.5 applied to primary multiplier 2.0 -> 3.0
    assert m_smhs_peak >= 2.5

    # Night period reduces travel time
    m_res_night = get_edge_traffic_multiplier(edge_res, period="night", config=config)
    assert m_res_night < 1.0


def test_hospital_penalties():
    """Verify clinical trauma and operational load penalty calculations."""
    # General emergency: zero trauma penalty for any level
    p_tr, p_ld = compute_hospital_penalties("Level-2", "normal", trauma_requirement="general")
    assert p_tr == 0.0
    assert p_ld == 0.0

    # Major trauma: Level-1 has zero penalty, Level-2 incurs 900s (15 min)
    p_tr_l1, _ = compute_hospital_penalties("Level-1", "normal", trauma_requirement="major_trauma")
    assert p_tr_l1 == 0.0

    p_tr_l2, _ = compute_hospital_penalties("Level-2", "normal", trauma_requirement="major_trauma")
    assert p_tr_l2 == 900.0  # 15 min penalty

    # Load penalties: normal=0s, busy=480s (8 min), full=1800s (30 min)
    _, p_ld_norm = compute_hospital_penalties("Level-1", "normal")
    assert p_ld_norm == 0.0

    _, p_ld_busy = compute_hospital_penalties("Level-1", "busy")
    assert p_ld_busy == 480.0

    _, p_ld_full = compute_hospital_penalties("Level-1", "full")
    assert p_ld_full == 1800.0


def test_hospital_scoring_formula_and_winner_selection():
    """Verify score = travel_time + P_trauma + P_load on a synthetic small graph."""
    # Construct synthetic graph with 1 accident node and 3 hospitals
    # A -> H_near (travel_time: 120s / 2 min, Level-2, status: busy)
    # A -> H_far  (travel_time: 300s / 5 min, Level-1, status: normal)
    # A -> H_full (travel_time: 150s / 2.5 min, Level-1, status: full)
    G = nx.MultiDiGraph()
    G.add_edge("acc", "h_near", travel_time=120.0, length=1000.0)
    G.add_edge("acc", "h_far", travel_time=300.0, length=2500.0)
    G.add_edge("acc", "h_full", travel_time=150.0, length=1200.0)

    # Attach period weights
    for _, _, d in G.edges(data=True):
        d["travel_time_off_peak"] = d["travel_time"]

    hospitals = [
        {"id": "h_near", "name": "Near Community Hospital", "trauma_level": "Level-2", "status": "busy"},
        {"id": "h_far", "name": "Far Apex Trauma Center", "trauma_level": "Level-1", "status": "normal"},
        {"id": "h_full", "name": "Full Central Hospital", "trauma_level": "Level-1", "status": "full"},
    ]
    h_map = {"h_near": "h_near", "h_far": "h_far", "h_full": "h_full"}

    # Scenario 1: Major trauma
    ranked, winner, nearest, explanation = evaluate_hospital_scores(
        G,
        accident_node="acc",
        hospitals=hospitals,
        hospital_node_map=h_map,
        trauma_requirement="major_trauma",
        time_of_day="off_peak",
    )

    # Nearest is h_near (120s)
    assert nearest.id == "h_near"
    assert nearest.travel_time_sec == 120.0

    # But h_near score = 120s + 900s (trauma) + 480s (busy) = 1500s (25 min)
    # h_full score = 150s + 0s + 1800s (full) = 1950s (32.5 min)
    # h_far score = 300s + 0s + 0s = 300s (5.0 min)
    # So WINNER must be h_far!
    assert winner.id == "h_far"
    assert winner.score_sec == 300.0
    assert ranked[0].id == "h_far"
    assert ranked[1].id == "h_near"
    assert ranked[2].id == "h_full"

    # Explanation must mention why winner beat nearest
    assert "won over nearest facility" in explanation
    assert "Level-2" in explanation
    assert "BUSY" in explanation


def test_route_divergence_offpeak_vs_peak():
    """Test that optimal route under peak congestion diverges from off-peak route."""
    G = load_graph()
    attach_traffic_weights_to_graph(G)

    # Test between Richmond Town area and Victoria Hospital
    from backend.graph_builder import nearest_node
    acc_node = nearest_node(G, X=77.6050, Y=12.9450)
    h_vic = nearest_node(G, X=77.5750, Y=12.9634)

    divergence = compare_offpeak_vs_peak_route(G, acc_node, h_vic)

    assert divergence["diverged"] is True, "Route under peak traffic should detour around congested corridors"
    assert divergence["off_peak"]["travel_time_sec"] < divergence["peak"]["travel_time_sec"]
    assert divergence["peak_bypass_savings_sec"] > 0
    assert "bypass route" in divergence["explanation"]
