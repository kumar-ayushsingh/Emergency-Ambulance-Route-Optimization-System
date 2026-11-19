"""API Integration Tests for FastAPI backend.

Verifies:
- GET / and GET /graph/info
- GET /hospitals and GET /stations GeoJSON endpoints
- POST /route: End-to-end ambulance dispatch and hospital routing
"""

import pytest
from fastapi.testclient import TestClient

from backend.api import app


@pytest.fixture(scope="module")
def client():
    """Create test client with lifespan startup execution."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_serves_frontend(client: TestClient):
    """Verify root endpoint serves frontend static index.html or fallback."""
    response = client.get("/")
    assert response.status_code == 200
    assert ("<!DOCTYPE html>" in response.text) or ("html" in response.text) or ("status" in response.text)


def test_api_health_endpoint(client: TestClient):
    """Verify /api/health endpoint returns operational status and graph counts."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["city"] == "Bengaluru"
    assert data["vertices"] > 5000
    assert data["directed_edges"] > 10000


def test_graph_info_endpoint(client: TestClient):
    """Verify graph metadata and Handshake Lemma verification."""
    response = client.get("/graph/info")
    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Bengaluru"
    assert data["vertices"] > 5000
    assert data["handshake_lemma"]["verified"] is True
    assert data["handshake_lemma"]["sum_degrees"] == data["handshake_lemma"]["twice_edges"]


def test_hospitals_endpoint(client: TestClient):
    """Verify /hospitals returns valid GeoJSON FeatureCollection."""
    response = client.get("/hospitals")
    assert response.status_code == 200
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) >= 7

    for feature in geojson["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        assert len(feature["geometry"]["coordinates"]) == 2
        assert "trauma_level" in feature["properties"]
        assert "status" in feature["properties"]


def test_stations_endpoint(client: TestClient):
    """Verify /stations returns valid GeoJSON FeatureCollection."""
    response = client.get("/stations")
    assert response.status_code == 200
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) >= 4

    for feature in geojson["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        assert len(feature["geometry"]["coordinates"]) == 2
        assert "ambulances_available" in feature["properties"]


def test_route_endpoint(client: TestClient):
    """Verify POST /route returns dual-leg emergency routing GeoJSON."""
    # Accident placed near Chamrajpet / Victoria Hospital corridor
    payload = {"lat": 12.9600, "lng": 77.5750}
    response = client.post("/route", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"

    props = data["properties"]
    assert "station" in props
    assert "hospital" in props
    assert props["total_time_min"] > 0
    assert props["total_distance_km"] > 0
    assert props["dispatch_time_min"] > 0
    assert props["transport_time_min"] > 0
    assert len(props["turn_order_vertices"]) > 2

    # Check features in GeoJSON
    features = data["features"]
    legs = [f for f in features if f["geometry"]["type"] == "LineString"]
    assert len(legs) == 2, "Must return dispatch leg and transport leg LineStrings"

    points = [f for f in features if f["geometry"]["type"] == "Point"]
    assert len(points) == 3, "Must return Station, Accident, and Hospital Point features"


def test_prefixed_api_endpoints(client: TestClient):
    """Verify that endpoints under the /api prefix function identically."""
    hosp_res = client.get("/api/hospitals")
    assert hosp_res.status_code == 200
    assert hosp_res.json()["type"] == "FeatureCollection"

    route_res = client.post("/api/route", json={"lat": 12.9600, "lng": 77.5750})
    assert route_res.status_code == 200
    assert route_res.json()["type"] == "FeatureCollection"


def test_critical_endpoint(client: TestClient):
    """Verify POST /critical calculates bridges, articulation points, and Resilience Score."""
    # First compute a route
    route_res = client.post("/route", json={"lat": 12.9600, "lng": 77.5750})
    assert route_res.status_code == 200
    route_data = route_res.json()
    route_nodes = route_data["properties"]["turn_order_vertices"]
    base_time = route_data["properties"]["total_time_sec"]

    # Now call /critical
    crit_res = client.post(
        "/critical",
        json={
            "route_nodes": route_nodes,
            "base_time_sec": base_time,
            "source": route_nodes[0],
            "target": route_nodes[-1],
        },
    )
    assert crit_res.status_code == 200
    crit_data = crit_res.json()
    assert crit_data["type"] == "FeatureCollection"

    props = crit_data["properties"]
    assert "resilience_score" in props
    assert 0.0 <= props["resilience_score"] <= 100.0
    assert props["rating"] in {"Resilient", "Moderate", "Fragile"}
    assert "lambda_menger" in props
    assert props["lambda_menger"] >= 0
    assert "rho_max" in props
    assert props["rho_max"] >= 1.0
    assert "components" in props
    assert "L" in props["components"]
    assert "D" in props["components"]
    assert "C" in props["components"]
    assert "explanation" in props and len(props["explanation"]) > 20


def test_backup_endpoint(client: TestClient):
    """Verify POST /backup computes Yen K-shortest and edge-disjoint alternatives."""
    route_res = client.post("/route", json={"lat": 12.9600, "lng": 77.5750})
    assert route_res.status_code == 200
    route_data = route_res.json()
    turn_order = route_data["properties"]["turn_order_vertices"]
    base_time = route_data["properties"]["total_time_sec"]

    source = turn_order[0]
    target = turn_order[-1]

    backup_res = client.post(
        "/backup",
        json={
            "source": source,
            "target": target,
            "primary_path": turn_order,
            "base_time_sec": base_time,
        },
    )
    assert backup_res.status_code == 200
    backup_data = backup_res.json()
    assert backup_data["type"] == "FeatureCollection"
    props = backup_data["properties"]
    assert "plans" in props
    assert len(props["plans"]) >= 2, "Must return at least Plan A and Plan B"

    # Check Plan A
    plan_a = props["plans"][0]
    assert plan_a["plan_name"].startswith("Plan A")
    assert plan_a["time_diff_min"] == 0.0

    # Check Plan B
    plan_b = props["plans"][1]
    assert plan_b["plan_name"].startswith("Plan B")
    assert plan_b["color"] == "#a855f7"

    # Check GeoJSON features
    features = backup_data["features"]
    assert len(features) >= 2
    for f in features:
        assert f["type"] == "Feature"
        assert f["geometry"]["type"] == "LineString"
        assert len(f["geometry"]["coordinates"]) >= 2
        assert "plan_name" in f["properties"]


def test_block_and_reroute_endpoint(client: TestClient):
    """Verify POST /block deletes an edge, re-routes, adds delay, and updates resilience."""
    # Step 1: Base route
    lat, lng = 12.9600, 77.5750
    route_res = client.post("/route", json={"lat": lat, "lng": lng})
    assert route_res.status_code == 200
    orig_data = route_res.json()
    orig_time_sec = orig_data["properties"]["total_time_sec"]
    turn_order = orig_data["properties"]["turn_order_vertices"]
    assert len(turn_order) >= 5

    # Choose an intermediate edge on the route to block
    u = turn_order[2]
    v = turn_order[3]

    # Step 2: Block edge
    block_res = client.post(
        "/block",
        json={
            "u": u,
            "v": v,
            "incident_lat": lat,
            "incident_lng": lng,
            "original_time_sec": orig_time_sec,
        },
    )
    assert block_res.status_code == 200
    block_data = block_res.json()
    assert block_data["type"] == "FeatureCollection"
    props = block_data["properties"]
    assert props["re_routed"] is True
    assert props["blocked_edges_count"] >= 1
    assert "added_delay_min" in props
    assert props["resilience"] is not None
    assert "resilience_score" in props["resilience"]

    # Verify blocked edge feature is present with cross icon marker
    features = block_data["features"]
    blocked_edge_feats = [f for f in features if f["properties"].get("type") == "blocked_edge"]
    blocked_marker_feats = [f for f in features if f["properties"].get("type") == "blocked_marker"]
    assert len(blocked_edge_feats) >= 1
    assert len(blocked_marker_feats) >= 1

    # Step 3: Unblock the edge
    unblock_res = client.post(
        "/unblock",
        json={
            "u": u,
            "v": v,
            "incident_lat": lat,
            "incident_lng": lng,
        },
    )
    assert unblock_res.status_code == 200
    unblock_data = unblock_res.json()
    assert unblock_data["properties"]["blocked_edges_count"] == 0

    # Step 4: Restore all
    restore_res = client.post("/restore", json={"incident_lat": lat, "incident_lng": lng})
    assert restore_res.status_code == 200
    restore_data = restore_res.json()
    assert restore_data["properties"]["restored"] is True
    assert restore_data["properties"]["blocked_edges_count"] == 0


def test_coverage_endpoint(client: TestClient):
    """Verify GET /coverage returns isochrone bands GeoJSON from active ambulance stations."""
    res = client.get("/coverage")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"

    props = data["properties"]
    assert props["mode"] == "current"
    assert props["total_demand_points"] >= 300
    assert "bands" in props
    bands = props["bands"]
    assert "under_8_min" in bands
    assert "between_8_and_15" in bands
    assert "between_15_and_30" in bands
    assert "over_30_min" in bands

    # Verify percentages sum to ~100%
    total_pct = sum(b["pct"] for b in bands.values())
    assert 99.0 <= total_pct <= 101.0
    assert props["mean_time_min"] > 0
    assert props["max_time_min"] >= props["mean_time_min"]

    # Check demand point features
    features = data["features"]
    coverage_points = [f for f in features if f["properties"].get("type") == "coverage_point"]
    assert len(coverage_points) >= 300
    for cp in coverage_points:
        assert cp["geometry"]["type"] == "Point"
        assert len(cp["geometry"]["coordinates"]) == 2
        assert cp["properties"]["color"].startswith("#")
        assert "time_min" in cp["properties"]


def test_placement_suggest_endpoint(client: TestClient):
    """Verify POST /placement/suggest optimizes k stations and returns before/after comparison."""
    payload = {"k": 4, "algorithm": "p_median"}
    res = client.post("/placement/suggest", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"

    props = data["properties"]
    assert props["mode"] == "suggested"
    assert props["algorithm"] in ["p_median", "p-median"]
    assert props["k"] == 4
    assert len(props["suggested_stations"]) == 4

    # Verify baseline comparison metrics exist
    assert "baseline_comparison" in props
    comp = props["baseline_comparison"]
    assert "baseline_bands" in comp
    assert "baseline_mean_time_min" in comp
    assert "delta_8min_pct" in comp
    assert "delta_mean_time_min" in comp
    assert "is_improved" in comp

    # Verify suggested stations features exist
    features = data["features"]
    suggested_stations = [f for f in features if f["properties"].get("type") == "suggested_station"]
    assert len(suggested_stations) == 4
    for stn in suggested_stations:
        assert stn["properties"]["algorithm"] in ["p_median", "p-median"]
        assert "name" in stn["properties"]


def test_assign_endpoint_min_sum_and_bottleneck(client: TestClient):
    """Verify POST /assign computes Hungarian min-sum and bottleneck minimax assignments for up to 5 accidents."""
    accidents = [
        {"id": "acc-1", "lat": 12.9750, "lng": 77.5850},
        {"id": "acc-2", "lat": 12.9400, "lng": 77.6100},
        {"id": "acc-3", "lat": 12.9850, "lng": 77.6300},
    ]

    # 1. Test Min-Sum Hungarian assignment
    payload_ms = {"accidents": accidents, "objective": "min_sum"}
    res_ms = client.post("/assign", json=payload_ms)
    assert res_ms.status_code == 200
    data_ms = res_ms.json()
    assert data_ms["type"] == "FeatureCollection"

    props_ms = data_ms["properties"]
    assert props_ms["objective"] == "min_sum"
    assert props_ms["num_accidents"] == 3
    assert props_ms["num_assigned"] == 3
    assert len(props_ms["assignments"]) == 3
    assert props_ms["total_time_sec"] > 0
    assert "cost_matrix" in props_ms
    assert len(props_ms["cost_matrix"]["matrix_sec"]) == 14  # 14 ambulances available
    assert len(props_ms["cost_matrix"]["matrix_sec"][0]) == 3  # 3 accidents

    # Verify features (routes, accidents, stations)
    route_features = [f for f in data_ms["features"] if f["properties"].get("type") == "assigned_route"]
    assert len(route_features) == 3
    colors = set()
    for rf in route_features:
        assert rf["geometry"]["type"] == "LineString"
        assert len(rf["geometry"]["coordinates"]) > 1
        assert "color" in rf["properties"]
        colors.add(rf["properties"]["color"])
    assert len(colors) == 3, "Each assigned route must have its own distinct color"

    # 2. Test Bottleneck assignment
    payload_bn = {"accidents": accidents, "objective": "bottleneck"}
    res_bn = client.post("/assign", json=payload_bn)
    assert res_bn.status_code == 200
    data_bn = res_bn.json()
    props_bn = data_bn["properties"]
    assert props_bn["objective"] == "bottleneck"
    assert props_bn["num_assigned"] == 3
    # Bottleneck max time must be <= min-sum max time (or equal)
    assert props_bn["max_time_sec"] <= props_ms["max_time_sec"] + 0.5


def test_assign_endpoint_validation_errors(client: TestClient):
    """Verify POST /assign returns 400 for empty or > 5 accidents."""
    # 0 accidents
    res_0 = client.post("/assign", json={"accidents": [], "objective": "min_sum"})
    assert res_0.status_code == 400

    # > 5 accidents (6 accidents)
    too_many = [{"lat": 12.95 + i * 0.01, "lng": 77.58 + i * 0.01} for i in range(6)]
    res_6 = client.post("/assign", json={"accidents": too_many, "objective": "min_sum"})
    assert res_6.status_code == 400


def test_traffic_config_endpoint(client: TestClient):
    """Verify GET /traffic/config returns time periods and special corridors."""
    res = client.get("/traffic/config")
    assert res.status_code == 200
    data = res.json()
    assert "time_periods" in data
    assert "special_corridors" in data
    assert "off_peak" in data["time_periods"]
    assert "evening_peak" in data["time_periods"]
    assert data["time_periods"]["morning_peak"]["default_multiplier"] == 1.6


def test_hospitals_score_endpoint(client: TestClient):
    """Verify POST /hospitals/score evaluates candidate hospitals with score formula."""
    # Incident near Shivajinagar / Bowring Hospital
    payload = {
        "lat": 12.9800,
        "lng": 77.6000,
        "trauma_requirement": "major_trauma",
        "hospital_statuses": {
            "bowring": "busy",
            "victoria": "normal",
        },
        "time_of_day": "off_peak",
    }
    res = client.post("/hospitals/score", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"

    props = data["properties"]
    assert "ranked_hospitals" in props
    assert len(props["ranked_hospitals"]) >= 7
    assert "winner" in props
    assert "nearest" in props
    assert "winner_explanation" in props

    # Bowring is closest, but busy (+8 min) and Level-2 (+15 min), so winner is a Level-1 normal hospital
    ranked = props["ranked_hospitals"]
    assert ranked[0]["rank"] == 1
    assert ranked[0]["is_winner"] is True

    # Winner beat nearest test
    assert props["winner_beat_nearest"] is True
    assert "won over nearest facility" in props["winner_explanation"]

    # Verify features include winner route LineString and candidate hospital points
    route_features = [f for f in data["features"] if f["properties"].get("role") == "winner_route"]
    assert len(route_features) == 1
    assert route_features[0]["geometry"]["type"] == "LineString"

    hosp_features = [f for f in data["features"] if f["properties"].get("type") == "ranked_hospital"]
    assert len(hosp_features) >= 7


def test_route_endpoint_time_of_day_variation(client: TestClient):
    """Verify POST /route returns longer travel times under peak vs off-peak and night."""
    # Accident location
    loc = {"lat": 12.9650, "lng": 77.5850}

    # Night route
    res_night = client.post("/route", json={**loc, "time_of_day": "night"})
    assert res_night.status_code == 200
    night_time = res_night.json()["properties"]["total_time_sec"]

    # Off-peak route
    res_off = client.post("/route", json={**loc, "time_of_day": "off_peak"})
    assert res_off.status_code == 200
    off_time = res_off.json()["properties"]["total_time_sec"]

    # Evening peak route
    res_peak = client.post("/route", json={**loc, "time_of_day": "evening_peak"})
    assert res_peak.status_code == 200
    peak_time = res_peak.json()["properties"]["total_time_sec"]

    # night < off_peak < evening_peak
    assert night_time < off_time < peak_time


def test_route_compare_traffic_endpoint(client: TestClient):
    """Verify POST /route/compare-traffic demonstrates route divergence under peak congestion."""
    payload = {
        "lat": 12.9450,
        "lng": 77.6050,
        "hospital_id": "victoria",
    }
    res = client.post("/route/compare-traffic", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    props = data["properties"]

    assert props["diverged"] is True
    assert props["peak_bypass_savings_sec"] > 0
    assert "bypass route" in props["explanation"]

    # Verify both route LineStrings exist in features
    roles = [f["properties"].get("role") for f in data["features"]]
    assert "off_peak_route" in roles
    assert "peak_route" in roles


def test_race_endpoint(client: TestClient):
    """Verify POST /race executes Dijkstra vs A* and returns identical costs."""
    payload = {
        "time_of_day": "off_peak",
        "sample_limit": 500,
    }
    res = client.post("/race", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    props = data["properties"]

    assert props["costs_equal"] is True
    assert props["cost_diff_sec"] < 0.1
    assert props["node_reduction_pct"] >= 0.0

    dijkstra = props["dijkstra"]
    astar = props["astar"]

    assert dijkstra["nodes_expanded"] > 0
    assert astar["nodes_expanded"] > 0
    assert astar["nodes_expanded"] <= dijkstra["nodes_expanded"]
    assert len(dijkstra["explored_coords"]) > 0
    assert len(astar["explored_coords"]) > 0

    # Verify features contain Dijkstra path, A* path, origin and destination
    roles = [f["properties"].get("role") for f in data["features"]]
    assert "dijkstra_path" in roles
    assert "astar_path" in roles

    types = [f["properties"].get("type") for f in data["features"]]
    assert "origin" in types
    assert "destination" in types






