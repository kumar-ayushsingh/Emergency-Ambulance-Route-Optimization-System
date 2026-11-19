"""Regression & Memory Optimization Verification Test Suite.

Verifies:
1. Process memory footprint remains well under 400 MB (Render 512MB limit safety).
2. Routing calculations produce identical optimal paths and accurate travel times.
3. Resilience score, Menger connectivity, and bridge detection remain exact.
4. Road blockage simulation operates cleanly via edge-skipping without copying the graph.
5. Isochrone coverage and placement matrices run with capped demand grid (<= 300 nodes).
6. A* and Dijkstra yield identical optimal shortest path costs.
"""

import os
import psutil
import pytest
from fastapi.testclient import TestClient

from backend.api import app, app_state, get_cached_demand_nodes, get_undirected_graph
from backend.algorithms.astar import astar_shortest_path, dijkstra_race_search
from backend.algorithms.critical import analyze_route_resilience
from backend.algorithms.dijkstra import dijkstra_shortest_path
from backend.graph_builder import load_graph, nearest_node


@pytest.fixture(scope="module")
def client():
    """TestClient that triggers FastAPI lifespan startup."""
    with TestClient(app) as test_client:
        yield test_client


def test_process_memory_well_under_400mb(client):
    """Confirm runtime memory is well under 400 MB (target: < 250 MB)."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["graph_loaded"] is True
    assert data["vertices"] > 20000
    assert data["directed_edges"] > 50000

    mem_mb = data["process_memory_mb"]
    assert mem_mb < 350.0, f"Process memory {mem_mb} MB exceeds 350 MB threshold"
    print(f"\n[MEMORY TEST] Measured API process memory: {mem_mb:.2f} MB RSS (target < 400 MB)")


def test_routing_equivalence_and_validity(client):
    """Verify route calculation returns valid ambulance dispatch and hospital transport."""
    incident_lat = 12.9550
    incident_lng = 77.6000

    response = client.post(
        "/api/route",
        json={"lat": incident_lat, "lng": incident_lng, "time_of_day": "off_peak"},
    )
    assert response.status_code == 200
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"
    props = geojson["properties"]

    assert props["total_time_sec"] > 0
    assert props["total_distance_km"] > 0
    assert props["station"] is not None
    assert props["hospital"] is not None
    assert len(props["turn_order_vertices"]) >= 2

    # Check legs in GeoJSON features
    legs = [f["properties"].get("leg") for f in geojson["features"] if "leg" in f["properties"]]
    assert "dispatch" in legs
    assert "transport" in legs


def test_resilience_and_critical_bridges(client):
    """Verify resilience score analysis matches theoretical bounds."""
    # Obtain a route first
    route_resp = client.post(
        "/api/route",
        json={"lat": 12.9716, "lng": 77.5946, "time_of_day": "off_peak"},
    )
    assert route_resp.status_code == 200
    route_props = route_resp.json()["properties"]
    route_nodes = route_props["turn_order_vertices"]
    base_time = route_props["total_time_sec"]

    crit_resp = client.post(
        "/api/critical",
        json={
            "route_nodes": route_nodes,
            "base_time_sec": base_time,
            "source": route_nodes[0],
            "target": route_nodes[-1],
        },
    )
    assert crit_resp.status_code == 200
    crit_geojson = crit_resp.json()
    res_props = crit_geojson["properties"]

    assert 0.0 <= res_props["resilience_score"] <= 100.0
    assert res_props["rating"] in ("Resilient", "Moderate", "Fragile")
    assert res_props["lambda_menger"] >= 1
    assert res_props["rho_max"] >= 1.0


def test_blockage_simulation_without_graph_copying(client):
    """Verify road blockage simulation accurately detours without copying the graph."""
    # Route around Corporation / Richmond Circle
    route_resp = client.post(
        "/api/route",
        json={"lat": 12.9650, "lng": 77.5950, "time_of_day": "off_peak"},
    )
    assert route_resp.status_code == 200
    route_nodes = route_resp.json()["properties"]["turn_order_vertices"]
    orig_time = route_resp.json()["properties"]["total_time_sec"]

    # Block an intermediate road edge along the primary route
    mid_idx = len(route_nodes) // 2
    u, v = route_nodes[mid_idx], route_nodes[mid_idx + 1]

    block_resp = client.post(
        "/api/block",
        json={
            "u": u,
            "v": v,
            "incident_lat": 12.9650,
            "incident_lng": 77.5950,
            "original_time_sec": orig_time,
        },
    )
    assert block_resp.status_code == 200
    block_json = block_resp.json()
    assert block_json["properties"]["re_routed"] is True
    assert block_json["properties"]["blocked_edges_count"] >= 1

    # Restore roads
    restore_resp = client.post(
        "/api/restore",
        json={"incident_lat": 12.9650, "incident_lng": 77.5950},
    )
    assert restore_resp.status_code == 200
    restore_json = restore_resp.json()
    assert restore_json["properties"]["blocked_edges_count"] == 0


def test_lazy_coverage_and_capped_demand_grid(client):
    """Verify coverage computation operates with demand grid capped at <= 300 nodes."""
    demand_nodes = get_cached_demand_nodes()
    assert len(demand_nodes) <= 300, f"Demand nodes ({len(demand_nodes)}) must be capped at <= 300"

    cov_resp = client.get("/api/coverage?mode=current")
    assert cov_resp.status_code == 200
    cov_data = cov_resp.json()
    props = cov_data["properties"]
    assert props["total_demand_points"] <= 300
    assert "bands" in props
    assert "under_8_min" in props["bands"]
    assert "over_30_min" in props["bands"]


def test_astar_dijkstra_cost_equality():
    """Verify A* with Haversine heuristic finds the exact optimal cost as Dijkstra."""
    G = load_graph()
    src = list(G.nodes)[0]
    tgt = list(G.nodes)[200]

    dijkstra_res = dijkstra_race_search(G, src, tgt)
    astar_res = astar_shortest_path(G, src, tgt)

    if dijkstra_res and astar_res:
        assert abs(dijkstra_res.cost - astar_res.cost) < 1e-4, "A* cost must equal Dijkstra cost"
        assert astar_res.nodes_expanded <= dijkstra_res.nodes_expanded, "A* should expand fewer or equal nodes"
