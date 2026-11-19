"""FastAPI Backend Application for Emergency Ambulance Route Optimization System.

Exposes RESTful endpoints returning GeoJSON (RFC 7946 compliant) for:
- Routing (POST /route): Finds nearest ambulance station and optimal hospital
- Graph metadata (GET /graph/info)
- Facility layers (GET /hospitals, GET /stations)

Rule 5: Return GeoJSON from every API.
Rule 6: Never hard-code API keys.
"""

from __future__ import annotations

import functools
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import psutil
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.algorithms.dijkstra import (
    DijkstraResult,
    dijkstra_shortest_path,
    find_nearest_hospital_from_accident,
    find_nearest_station_to_accident,
)
from backend.algorithms.critical import (
    analyze_route_resilience,
    tarjan_bridges_and_articulation_points,
)
from backend.algorithms.backup import (
    generate_backup_plans,
)
from backend.algorithms.placement import (
    CoverageResult,
    PlacementResult,
    compute_candidate_demand_matrix,
    compute_eccentricity_and_center,
    compute_multi_source_coverage,
    get_candidate_junctions,
    greedy_k_center,
    sample_demand_grid,
    swap_p_median,
)
from backend.algorithms.assignment import (
    AccidentSite,
    AmbulanceUnit,
    build_ambulance_fleet,
    dispatch_and_route_assignment,
)
from backend.algorithms.traffic import (
    attach_traffic_weights_to_graph,
    get_traffic_config,
    get_weight_attribute_for_period,
)
from backend.algorithms.scoring import (
    evaluate_hospital_scores,
    compare_offpeak_vs_peak_route,
)
from backend.algorithms.astar import (
    astar_shortest_path,
    dijkstra_race_search,
    run_algorithm_race,
)
from backend.graph_builder import (
    get_undirected_simple_graph,
    load_graph,
    load_hospitals,
    load_stations,
    nearest_node,
    verify_handshake_lemma,
)

logger = logging.getLogger("uvicorn.error")

# Global state loaded on startup
app_state: Dict[str, Any] = {
    "graph": None,  # Original read-only DiGraph with float attributes
    "undirected_graph": None,  # Lazily built undirected graph for /critical
    "blocked_edges": set(),  # Set of blocked (u, v) and (v, u) pairs
    "blocked_edges_data": {},
    "global_bridges": None,  # Lazily computed global bridges
    "global_aps": None,  # Lazily computed articulation points
    "hospitals": [],
    "stations": [],
    "hospital_node_map": {},  # hospital_id -> graph_node
    "station_node_map": {},  # station_id -> graph_node
    "node_hospital_map": {},  # graph_node -> hospital dict
    "node_station_map": {},  # graph_node -> station dict
    "fleet": [],  # Available physical ambulance units
    "traffic_config": None,  # Traffic multiplier configuration by period and road class
}


def get_undirected_graph() -> nx.Graph:
    """Lazily construct and cache the undirected graph view only when requested."""
    if app_state.get("undirected_graph") is None:
        logger.info("Lazily building undirected graph for topological resilience...")
        app_state["undirected_graph"] = get_undirected_simple_graph(app_state["graph"])
    return app_state["undirected_graph"]


def get_global_bridges():
    """Lazily compute global topological bridges and articulation points."""
    if app_state.get("global_bridges") is None or app_state.get("global_aps") is None:
        logger.info("Lazily computing global bridges & articulation points via Tarjan's DFS...")
        G_undir = get_undirected_graph()
        g_bridges, g_aps = tarjan_bridges_and_articulation_points(G_undir)
        app_state["global_bridges"] = g_bridges
        app_state["global_aps"] = g_aps
        logger.info("Identified %d global bridges and %d articulation points.", len(g_bridges), len(g_aps))
    return app_state["global_bridges"], app_state["global_aps"]


@functools.lru_cache(maxsize=4)
def get_cached_demand_nodes(num_rows: int = 18, num_cols: int = 18) -> List[int]:
    """Sample demand nodes on first request and cache up to 4 entries (capped at 300)."""
    G = app_state["graph"]
    return [int(n) for n in sample_demand_grid(G, num_rows=num_rows, num_cols=num_cols)][:300]


@functools.lru_cache(maxsize=4)
def get_cached_candidate_nodes() -> List[int]:
    """Candidate sites for ambulance placement (deg >= 3 + hospital gates)."""
    G = app_state["graph"]
    hospital_nodes = [int(n) for n in app_state["hospital_node_map"].values()]
    return [int(n) for n in get_candidate_junctions(G, hospital_nodes, num_rows=12, num_cols=12)]


@functools.lru_cache(maxsize=4)
def get_cached_placement_matrix():
    """Lazily load or compute candidate-to-demand placement cost matrix."""
    G = app_state["graph"]
    candidates = get_cached_candidate_nodes()
    demand_nodes = get_cached_demand_nodes()
    return compute_candidate_demand_matrix(G, candidates, demand_nodes, use_cache=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: Lean startup with zero heavy precomputations."""
    logger.info("Initializing Emergency Ambulance Router backend...")
    t0 = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)

    G = load_graph()
    attach_traffic_weights_to_graph(G)
    app_state["graph"] = G
    app_state["blocked_edges"] = set()
    app_state["blocked_edges_data"] = {}
    app_state["traffic_config"] = get_traffic_config()

    hospitals = load_hospitals()
    stations = load_stations()
    app_state["hospitals"] = hospitals
    app_state["stations"] = stations

    # Fast spatial snapping of facilities using cKDTree
    for h in hospitals:
        node = int(nearest_node(G, X=h["lng"], Y=h["lat"]))
        app_state["hospital_node_map"][h["id"]] = node
        app_state["node_hospital_map"][node] = h

    for s in stations:
        node = int(nearest_node(G, X=s["lng"], Y=s["lat"]))
        app_state["station_node_map"][s["id"]] = node
        app_state["node_station_map"][node] = s

    fleet = build_ambulance_fleet(stations, app_state["station_node_map"])
    app_state["fleet"] = fleet

    t_end = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    logger.info(
        "Startup complete: Graph (%d nodes, %d edges), %d hospitals, %d stations. Memory: %.2f MB RSS (added %.2f MB).",
        len(G.nodes),
        len(G.edges),
        len(hospitals),
        len(stations),
        t_end,
        t_end - t0,
    )
    yield
    logger.info("Shutting down Emergency Ambulance Router backend.")


app = FastAPI(
    title="Emergency Ambulance Route Optimization System API",
    description="Graph-Theoretic Emergency Ambulance Routing & Resilience Analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router for all /api endpoints
api_router = APIRouter()

# Static files directory for production SPA frontend
FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
ASSETS_DIR = FRONTEND_DIST_DIR / "assets"


# --- Request and Response Schemas ---


class RouteRequest(BaseModel):
    """Accident location input payload."""

    lat: float = Field(..., description="Latitude of accident in decimal degrees (e.g. 12.965)")
    lng: float = Field(..., description="Longitude of accident in decimal degrees (e.g. 77.585)")
    hospital_id: Optional[str] = Field(
        None, description="Optional destination hospital ID. If omitted, best hospital is computed."
    )
    time_of_day: str = Field(
        "off_peak", description="Active traffic time period ('off_peak', 'morning_peak', 'evening_peak', 'night')"
    )


class HospitalScoreRequest(BaseModel):
    """Payload for multi-criteria hospital scoring and smart triage."""

    lat: float = Field(..., description="Latitude of accident in decimal degrees")
    lng: float = Field(..., description="Longitude of accident in decimal degrees")
    trauma_requirement: str = Field(
        "general", description="Clinical trauma requirement: 'general' or 'major_trauma'"
    )
    hospital_statuses: Optional[Dict[str, str]] = Field(
        None, description="Optional map of hospital_id -> status ('normal', 'busy', 'full')"
    )
    time_of_day: str = Field(
        "off_peak", description="Traffic period: 'off_peak', 'morning_peak', 'evening_peak', 'night'"
    )


class TrafficCompareRequest(BaseModel):
    """Payload to compare off-peak vs peak route divergence."""

    lat: Optional[float] = Field(None, description="Accident latitude")
    lng: Optional[float] = Field(None, description="Accident longitude")
    hospital_id: Optional[str] = Field(None, description="Destination hospital ID")
    source: Optional[int] = Field(None, description="Optional source node ID")
    target: Optional[int] = Field(None, description="Optional target node ID")


class CriticalRequest(BaseModel):
    """Payload to trigger resilience analysis on a given route."""

    route_nodes: List[int] = Field(..., description="Ordered list of node IDs along the active route")
    base_time_sec: float = Field(..., description="Baseline travel time in seconds")
    source: Optional[int] = Field(None, description="Source station node ID")
    target: Optional[int] = Field(None, description="Target hospital node ID")


class BackupRequest(BaseModel):
    """Payload to request Plan B and Plan C backup routes."""

    source: int = Field(..., description="Source junction node ID")
    target: int = Field(..., description="Destination hospital node ID")
    primary_path: Optional[List[int]] = Field(None, description="Precomputed primary path")
    base_time_sec: Optional[float] = Field(None, description="Baseline optimal travel time in seconds")


class BlockRequest(BaseModel):
    """Payload to close / block a road segment in dynamic simulation."""

    u: int = Field(..., description="Start node ID of edge to block")
    v: int = Field(..., description="End node ID of edge to block")
    incident_lat: Optional[float] = Field(None, description="Current accident latitude to re-route")
    incident_lng: Optional[float] = Field(None, description="Current accident longitude to re-route")
    original_time_sec: Optional[float] = Field(None, description="Baseline response time in seconds")


class UnblockRequest(BaseModel):
    """Payload to unblock a previously closed road segment."""

    u: int = Field(..., description="Start node ID of edge to unblock")
    v: int = Field(..., description="End node ID of edge to unblock")
    incident_lat: Optional[float] = Field(None, description="Current accident latitude to re-route")
    incident_lng: Optional[float] = Field(None, description="Current accident longitude to re-route")


class RestoreRequest(BaseModel):
    """Payload to clear all road blockages and restore network to original baseline."""

    incident_lat: Optional[float] = Field(None, description="Current accident latitude to re-route")
    incident_lng: Optional[float] = Field(None, description="Current accident longitude to re-route")


class PlacementRequest(BaseModel):
    """Payload to request optimal ambulance station placement."""

    k: int = Field(4, ge=1, le=10, description="Target number of ambulance stations to place (1-10)")
    algorithm: str = Field(
        "p_median",
        description="Algorithm choice: 'p_median' (Minisum average time), 'k_center' (Minimax worst-case), or '1_center'",
    )


class AccidentLocationInput(BaseModel):
    """Single emergency accident location input for multi-agent dispatch."""

    id: Optional[str] = Field(None, description="Optional incident ID (e.g. 'acc-1')")
    lat: float = Field(..., description="Latitude of accident location")
    lng: float = Field(..., description="Longitude of accident location")


class AssignmentRequest(BaseModel):
    """Payload to assign available ambulances to up to 5 accidents."""

    accidents: List[AccidentLocationInput] = Field(..., description="List of 1 to 5 accident locations")
    objective: str = Field("min_sum", description="Assignment objective: 'min_sum' (Hungarian) or 'bottleneck'")


class RaceRequest(BaseModel):
    """Payload for Dijkstra vs A* Algorithm Race."""

    source: Optional[int] = Field(None, description="Origin node ID")
    target: Optional[int] = Field(None, description="Destination node ID")
    origin_lat: Optional[float] = Field(None, description="Origin latitude in decimal degrees")
    origin_lng: Optional[float] = Field(None, description="Origin longitude in decimal degrees")
    destination_lat: Optional[float] = Field(None, description="Destination latitude in decimal degrees")
    destination_lng: Optional[float] = Field(None, description="Destination longitude in decimal degrees")
    time_of_day: str = Field(
        "off_peak", description="Traffic period: 'off_peak', 'morning_peak', 'evening_peak', 'night'"
    )
    sample_limit: int = Field(1500, description="Max animation coordinates returned per algorithm")


# --- Helper Functions for GeoJSON Serialization ---


def node_path_to_coordinates(G: nx.MultiDiGraph, path: List[Any]) -> List[List[float]]:
    """Convert a sequence of node IDs to GeoJSON [longitude, latitude] coordinate pairs."""
    coords: List[List[float]] = []
    for node_id in path:
        node_data = G.nodes[node_id]
        # GeoJSON RFC 7946 strictly mandates [longitude, latitude] order
        coords.append([float(node_data["x"]), float(node_data["y"])])
    return coords


def extract_street_names_from_path(G: nx.MultiDiGraph, path: List[Any]) -> List[str]:
    """Extract ordered unique street names traversed along the path."""
    names: List[str] = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            # MultiDiGraph returns a dict of edges keyed by integer/string
            name = None
            if G.is_multigraph():
                first_edge = next(iter(edge_data.values()))
                name = first_edge.get("name")
            else:
                name = edge_data.get("name")

            if name:
                if isinstance(name, list):
                    name = name[0]
                if name and (not names or names[-1] != name):
                    names.append(str(name))
    return names


# --- API Endpoints ---


@api_router.get("/health")
def health_check():
    """Service health and diagnostic status."""
    G = app_state.get("graph")
    is_ready = G is not None
    mem_mb = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    return {
        "status": "operational" if is_ready else "initializing",
        "system": "Emergency Ambulance Route Optimization System",
        "city": "Bengaluru",
        "version": "1.0.0",
        "graph_loaded": is_ready,
        "vertices": len(G.nodes) if is_ready else 0,
        "directed_edges": len(G.edges) if is_ready else 0,
        "process_memory_mb": mem_mb,
    }


@api_router.get("/graph/info")
def get_graph_info():
    """Return structural topology metrics, Handshake Lemma verification, and degree histogram."""
    G = app_state.get("graph")
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is initializing")

    G_undir = get_undirected_graph()

    sum_deg, twice_e, handshake_verified = verify_handshake_lemma(G_undir)
    degrees = [d for _, d in G_undir.degree()]
    deg_counts: Dict[int, int] = {}
    for d in degrees:
        deg_counts[d] = deg_counts.get(d, 0) + 1

    return {
        "city": "Bengaluru",
        "vertices": G.number_of_nodes(),
        "directed_edges": G.number_of_edges(),
        "undirected_edges": G_undir.number_of_edges(),
        "handshake_lemma": {
            "sum_degrees": sum_deg,
            "twice_edges": twice_e,
            "verified": handshake_verified,
        },
        "junction_classification": {
            "dead_ends_deg1": deg_counts.get(1, 0),
            "bends_deg2": deg_counts.get(2, 0),
            "intersections_deg3_plus": sum(c for d, c in deg_counts.items() if d >= 3),
        },
        "degree_histogram": dict(sorted(deg_counts.items())),
    }


@api_router.get("/hospitals")
def get_hospitals_geojson():
    """Return all hospitals as a standardized GeoJSON FeatureCollection."""
    features = []
    for h in app_state["hospitals"]:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [h["lng"], h["lat"]],
                },
                "properties": {
                    "id": h["id"],
                    "name": h["name"],
                    "short_name": h.get("short_name", h["name"]),
                    "trauma_level": h["trauma_level"],
                    "status": h["status"],
                    "beds_available": h["beds_available"],
                    "total_icu_beds": h.get("total_icu_beds", 0),
                    "specialties": h.get("specialties", []),
                    "address": h.get("address", ""),
                    "graph_node": app_state["hospital_node_map"].get(h["id"]),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@api_router.get("/stations")
def get_stations_geojson():
    """Return all ambulance stations as a standardized GeoJSON FeatureCollection."""
    features = []
    for s in app_state["stations"]:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [s["lng"], s["lat"]],
                },
                "properties": {
                    "id": s["id"],
                    "name": s["name"],
                    "short_name": s.get("short_name", s["name"]),
                    "ambulances_available": s["ambulances_available"],
                    "als_ambulances": s.get("als_ambulances", 0),
                    "bls_ambulances": s.get("bls_ambulances", 0),
                    "address": s.get("address", ""),
                    "graph_node": app_state["station_node_map"].get(s["id"]),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def execute_route_calculation(
    lat: float,
    lng: float,
    hospital_id: Optional[str] = None,
    use_working_graph: bool = True,
    time_of_day: str = "off_peak",
) -> Dict[str, Any]:
    """Execute ambulance dispatch and hospital routing calculation on graph.

    Args:
        lat: Incident latitude.
        lng: Incident longitude.
        hospital_id: Optional preferred hospital ID.
        use_working_graph: If True, uses dynamic working copy with road blockages.
        time_of_day: Time-of-day traffic period ('off_peak', 'morning_peak', 'evening_peak', 'night').
    """
    G = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is not loaded")

    blocked_edges = app_state.get("blocked_edges") if use_working_graph else None
    weight_attr = get_weight_attribute_for_period(time_of_day)

    # 1. Snap accident to nearest graph vertex
    accident_node = int(nearest_node(G, X=lng, Y=lat))
    acc_node_data = G.nodes[accident_node]
    snapped_lat = float(acc_node_data["y"])
    snapped_lng = float(acc_node_data["x"])

    # 2. Find nearest ambulance station (Station -> Accident)
    station_nodes = list(app_state["station_node_map"].values())
    best_station_node, dispatch_result = find_nearest_station_to_accident(
        G, station_nodes=station_nodes, accident_node=accident_node, weight=weight_attr, blocked_edges=blocked_edges
    )

    if best_station_node is None or dispatch_result is None:
        raise HTTPException(
            status_code=404,
            detail="No reachable ambulance station could reach this location",
        )

    best_station_info = app_state["node_station_map"][best_station_node]

    # 3. Find optimal destination hospital (Accident -> Hospital)
    if hospital_id and hospital_id in app_state["hospital_node_map"]:
        target_hospital_node = app_state["hospital_node_map"][hospital_id]
        transport_result = dijkstra_shortest_path(
            G, source=accident_node, target=target_hospital_node, weight=weight_attr, blocked_edges=blocked_edges
        )
        if transport_result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Specified hospital {hospital_id} is currently unreachable from accident site",
            )
        best_hospital_node = target_hospital_node
    else:
        hospital_nodes = list(app_state["hospital_node_map"].values())
        best_hospital_node, transport_result = find_nearest_hospital_from_accident(
            G, accident_node=accident_node, hospital_nodes=hospital_nodes, weight=weight_attr, blocked_edges=blocked_edges
        )

    if best_hospital_node is None or transport_result is None:
        raise HTTPException(
            status_code=404,
            detail="No hospital is reachable from this accident location",
        )

    best_hospital_info = app_state["node_hospital_map"][best_hospital_node]

    # 4. Assemble dual-leg coordinates & properties
    dispatch_coords = node_path_to_coordinates(G, dispatch_result.path)
    transport_coords = node_path_to_coordinates(G, transport_result.path)

    dispatch_streets = extract_street_names_from_path(G, dispatch_result.path)
    transport_streets = extract_street_names_from_path(G, transport_result.path)

    # Combined full path (remove duplicate accident node at boundary)
    full_path_nodes = dispatch_result.path + transport_result.path[1:]
    total_cost_sec = dispatch_result.cost + transport_result.cost
    total_dist_m = dispatch_result.distance + transport_result.distance
    total_nodes_expanded = dispatch_result.nodes_expanded + transport_result.nodes_expanded

    features = [
        # Leg 1: Ambulance Dispatch (Station -> Accident)
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": dispatch_coords,
            },
            "properties": {
                "leg": "dispatch",
                "role": "Ambulance Pickup (Station to Accident)",
                "color": "#f59e0b",  # Amber
                "time_sec": round(dispatch_result.cost, 1),
                "time_min": round(dispatch_result.cost / 60.0, 2),
                "distance_m": round(dispatch_result.distance, 1),
                "distance_km": round(dispatch_result.distance / 1000.0, 2),
                "streets": dispatch_streets,
                "node_count": len(dispatch_result.path),
            },
        },
        # Leg 2: Patient Transport (Accident -> Hospital)
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": transport_coords,
            },
            "properties": {
                "leg": "transport",
                "role": "Emergency Transport (Accident to Hospital)",
                "color": "#ef4444",  # Crimson Red
                "time_sec": round(transport_result.cost, 1),
                "time_min": round(transport_result.cost / 60.0, 2),
                "distance_m": round(transport_result.distance, 1),
                "distance_km": round(transport_result.distance / 1000.0, 2),
                "streets": transport_streets,
                "node_count": len(transport_result.path),
            },
        },
        # Point Feature: Selected Ambulance Station
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [best_station_info["lng"], best_station_info["lat"]],
            },
            "properties": {
                "type": "station",
                "name": best_station_info["name"],
                "short_name": best_station_info.get("short_name"),
                "node_id": best_station_node,
            },
        },
        # Point Feature: Incident Location
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [snapped_lng, snapped_lat],
            },
            "properties": {
                "type": "accident",
                "name": "Accident Location",
                "original_lat": lat,
                "original_lng": lng,
                "snapped_node_id": accident_node,
            },
        },
        # Point Feature: Destination Hospital
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [best_hospital_info["lng"], best_hospital_info["lat"]],
            },
            "properties": {
                "type": "hospital",
                "name": best_hospital_info["name"],
                "short_name": best_hospital_info.get("short_name"),
                "trauma_level": best_hospital_info["trauma_level"],
                "status": best_hospital_info["status"],
                "node_id": best_hospital_node,
            },
        },
    ]

    return {
        "type": "FeatureCollection",
        "properties": {
            "station": best_station_info,
            "hospital": best_hospital_info,
            "accident": {
                "lat": lat,
                "lng": lng,
                "snapped_lat": snapped_lat,
                "snapped_lng": snapped_lng,
                "node_id": accident_node,
            },
            "dispatch_time_sec": round(dispatch_result.cost, 1),
            "dispatch_time_min": round(dispatch_result.cost / 60.0, 2),
            "dispatch_distance_km": round(dispatch_result.distance / 1000.0, 2),
            "transport_time_sec": round(transport_result.cost, 1),
            "transport_time_min": round(transport_result.cost / 60.0, 2),
            "transport_distance_km": round(transport_result.distance / 1000.0, 2),
            "total_time_sec": round(total_cost_sec, 1),
            "total_time_min": round(total_cost_sec / 60.0, 2),
            "total_distance_m": round(total_dist_m, 1),
            "total_distance_km": round(total_dist_m / 1000.0, 2),
            "nodes_expanded": total_nodes_expanded,
            "turn_order_vertices": full_path_nodes,
            "time_of_day": time_of_day,
            "weight_attribute": weight_attr,
        },
        "features": features,
    }






def get_blocked_edges_features(G: nx.MultiDiGraph) -> List[Dict[str, Any]]:
    """Generate GeoJSON LineString and Point features for all currently blocked edges."""
    features = []
    blocked_data_map = app_state.get("blocked_edges_data", {})
    for (u, v), b_info in blocked_data_map.items():
        if u not in G or v not in G:
            continue
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        x_u, y_u = float(u_data["x"]), float(u_data["y"])
        x_v, y_v = float(v_data["x"]), float(v_data["y"])
        mid_x = (x_u + x_v) / 2.0
        mid_y = (y_u + y_v) / 2.0
        road_name = b_info.get("name", "Closed Road Segment")

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[x_u, y_u], [x_v, y_v]],
                },
                "properties": {
                    "type": "blocked_edge",
                    "role": "Blocked Road Segment",
                    "u": u,
                    "v": v,
                    "road_name": str(road_name),
                    "color": "#991b1b",
                },
            }
        )

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [mid_x, mid_y],
                },
                "properties": {
                    "type": "blocked_marker",
                    "role": "Road Closure Barrier",
                    "u": u,
                    "v": v,
                    "road_name": str(road_name),
                    "icon": "cross",
                },
            }
        )
    return features


@api_router.post("/route")
def compute_route(payload: RouteRequest):
    """Compute optimal ambulance dispatch and hospital routing for an emergency call.

    Rule 5: Return GeoJSON from every API.
    """
    return execute_route_calculation(
        lat=payload.lat,
        lng=payload.lng,
        hospital_id=payload.hospital_id,
        use_working_graph=True,
        time_of_day=payload.time_of_day,
    )


@api_router.post("/critical")
def compute_critical(payload: CriticalRequest):
    """Analyze critical infrastructure, cut elements, and Resilience Score for a route.

    Rule 5: Return GeoJSON from every API.
    Computes:
    - Strict bridges and articulation points via Tarjan's low-link DFS
    - Soft bridges (detour ratio rho >= 1.5)
    - Menger edge-connectivity (lambda) via max-flow
    - Resilience Score R = 100 * (0.4L + 0.4D + 0.2C)
    """
    G = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is not loaded")

    G_undir = get_undirected_graph()
    g_bridges, g_aps = get_global_bridges()

    if len(payload.route_nodes) < 2:
        raise HTTPException(status_code=400, detail="Route must contain at least 2 nodes")

    # Run comprehensive resilience analysis
    result = analyze_route_resilience(
        G_directed=G,
        G_undirected=G_undir,
        route_nodes=payload.route_nodes,
        base_travel_time=payload.base_time_sec,
        source=payload.source,
        target=payload.target,
        global_bridges=g_bridges,
        global_aps=g_aps,
        blocked_edges=app_state.get("blocked_edges"),
    )

    features = []

    # 1. GeoJSON LineString features for Strict Bridges (Red)
    for u, v in result.strict_bridges:
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        edge_data = G_undir.get_edge_data(u, v) or {}
        road_name = edge_data.get("name", "Critical Cut-Edge Bridge")
        if isinstance(road_name, list):
            road_name = road_name[0]

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [float(u_data["x"]), float(u_data["y"])],
                        [float(v_data["x"]), float(v_data["y"])],
                    ],
                },
                "properties": {
                    "type": "strict_bridge",
                    "role": "Topological Cut-Edge (Strict Bridge)",
                    "color": "#dc2626",  # Red
                    "u": u,
                    "v": v,
                    "road_name": str(road_name),
                    "length_m": round(float(edge_data.get("length", 0.0)), 1),
                },
            }
        )

    # 2. GeoJSON LineString features for Soft Bridges (Orange)
    for sb in result.soft_bridges:
        u, v = sb["u"], sb["v"]
        u_data = G.nodes[u]
        v_data = G.nodes[v]

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [float(u_data["x"]), float(u_data["y"])],
                        [float(v_data["x"]), float(v_data["y"])],
                    ],
                },
                "properties": {
                    "type": "soft_bridge",
                    "role": "High-Detour Corridor (Soft Bridge)",
                    "color": "#f97316",  # Orange
                    "u": u,
                    "v": v,
                    "road_name": sb["road_name"],
                    "highway": sb["highway"],
                    "detour_ratio": sb["detour_ratio"],
                    "detour_delay_min": sb["detour_delay_min"],
                    "disconnected": sb["disconnected"],
                },
            }
        )

    # 3. GeoJSON Point features for Articulation Points
    for ap in result.articulation_points:
        ap_data = G.nodes[ap]
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(ap_data["x"]), float(ap_data["y"])],
                },
                "properties": {
                    "type": "articulation_point",
                    "role": "Cut Vertex (Articulation Point)",
                    "color": "#f59e0b",
                    "node_id": ap,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "properties": {
            "resilience_score": result.resilience_score,
            "rating": result.rating,
            "rating_color": result.rating_color,
            "components": result.components,
            "lambda_menger": result.lambda_menger,
            "rho_max": result.rho_max,
            "strict_bridges_count": len(result.strict_bridges),
            "strict_bridge_length_m": result.strict_bridge_length_m,
            "soft_bridges_count": len(result.soft_bridges),
            "articulation_points_count": len(result.articulation_points),
            "explanation": result.explanation,
        },
        "features": features,
    }






# --- Prompt 4: Backup Routes (Yen K-Shortest & Edge-Disjoint) & Dynamic Road Blockages ---


@api_router.post("/backup")
def compute_backup_routes(payload: BackupRequest):
    """Compute Plan B and Plan C backup alternatives using Yen's K=3 and edge-disjoint search.

    Academic Context:
    - Discrete Mathematics · Module 4: Graph Theory
    - Jin Y. Yen's K-Shortest Simple Paths (1971)
    - Menger's Theorem for Edge-Disjoint Physical Paths

    Rule 5: Return GeoJSON from every API.
    """
    G = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is not loaded")

    if payload.source not in G:
        raise HTTPException(status_code=404, detail=f"Source node {payload.source} not in graph")
    if payload.target not in G:
        raise HTTPException(status_code=404, detail=f"Target node {payload.target} not in graph")

    plans = generate_backup_plans(
        G=G,
        source=payload.source,
        target=payload.target,
        primary_path=payload.primary_path,
        primary_time=payload.base_time_sec,
        weight="travel_time",
        blocked_edges=app_state.get("blocked_edges"),
    )

    if not plans:
        raise HTTPException(status_code=404, detail="No backup routes could be found between specified nodes")

    features = []
    plan_summaries = []

    for plan in plans:
        coords = node_path_to_coordinates(G, plan.path)
        streets = extract_street_names_from_path(G, plan.path)
        summary = {
            "plan_name": plan.plan_name,
            "color": plan.color,
            "time_sec": round(plan.cost, 1),
            "time_min": round(plan.cost / 60.0, 2),
            "distance_m": round(plan.distance, 1),
            "distance_km": round(plan.distance / 1000.0, 2),
            "time_diff_sec": round(plan.time_diff_sec, 1),
            "time_diff_min": round(plan.time_diff_min, 2),
            "is_disjoint": plan.is_disjoint,
            "node_count": len(plan.path),
            "streets": streets,
        }
        plan_summaries.append(summary)

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
                "properties": {
                    "type": "backup_plan",
                    **summary,
                    "turn_order_vertices": plan.path,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "properties": {
            "plans": plan_summaries,
            "count": len(plans),
            "source": payload.source,
            "target": payload.target,
        },
        "features": features,
    }






@api_router.post("/block")
def block_road_segment(payload: BlockRequest):
    """Close/block a road segment (u, v) in the graph, recompute route & resilience.

    Dynamic Graph Theory Simulation:
    - Adds directed edge e=(u, v) and symmetric e=(v, u) to blocked_edges set (zero graph copies).
    - Triggers real-time Dijkstra shortest path re-routing skipping blocked edges.
    - Computes added detour penalty ΔT = T_new - T_old.
    - Re-evaluates topological resilience score R_new.

    Rule 5: Return GeoJSON from every API.
    """
    G: nx.DiGraph = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is not loaded")

    u, v = payload.u, payload.v
    edge_key_tuple = (min(u, v), max(u, v))

    if not (G.has_edge(u, v) or G.has_edge(v, u)):
        raise HTTPException(status_code=404, detail=f"Edge ({u}, {v}) does not exist in road network")

    road_name = "Closed Road Segment"
    e_data = G.get_edge_data(u, v) or G.get_edge_data(v, u) or {}
    if "name" in e_data and e_data["name"]:
        n = e_data["name"]
        road_name = n[0] if isinstance(n, list) else n

    app_state["blocked_edges"].add(edge_key_tuple)
    app_state["blocked_edges"].add((u, v))
    app_state["blocked_edges"].add((v, u))
    app_state["blocked_edges_data"][edge_key_tuple] = {
        "u": u,
        "v": v,
        "name": road_name,
    }

    re_route_result = None
    added_delay_sec = 0.0
    added_delay_min = 0.0
    resilience_info = None

    if payload.incident_lat is not None and payload.incident_lng is not None:
        try:
            re_route_result = execute_route_calculation(
                payload.incident_lat, payload.incident_lng, use_working_graph=True
            )
            new_total_time = re_route_result["properties"]["total_time_sec"]
            if payload.original_time_sec is not None:
                added_delay_sec = max(0.0, new_total_time - payload.original_time_sec)
                added_delay_min = round(added_delay_sec / 60.0, 2)

            turn_order = re_route_result["properties"]["turn_order_vertices"]
            G_undir = get_undirected_graph()
            g_bridges, g_aps = get_global_bridges()
            res_result = analyze_route_resilience(
                G_directed=G,
                G_undirected=G_undir,
                route_nodes=turn_order,
                base_travel_time=new_total_time,
                source=turn_order[0],
                target=turn_order[-1],
                global_bridges=g_bridges,
                global_aps=g_aps,
                blocked_edges=app_state["blocked_edges"],
            )
            resilience_info = {
                "resilience_score": res_result.resilience_score,
                "rating": res_result.rating,
                "rating_color": res_result.rating_color,
                "components": res_result.components,
                "lambda_menger": res_result.lambda_menger,
                "rho_max": res_result.rho_max,
                "explanation": res_result.explanation,
                "strict_bridges_count": len(res_result.strict_bridges),
                "soft_bridges_count": len(res_result.soft_bridges),
                "articulation_points_count": len(res_result.articulation_points),
            }
        except HTTPException:
            re_route_result = None

    blocked_features = get_blocked_edges_features(G)
    features = []
    if re_route_result:
        features.extend(re_route_result["features"])
    features.extend(blocked_features)

    return {
        "type": "FeatureCollection",
        "properties": {
            "re_routed": re_route_result is not None,
            "blocked_edge": {"u": u, "v": v, "name": road_name},
            "blocked_edges_count": len(app_state["blocked_edges_data"]),
            "added_delay_sec": round(added_delay_sec, 1),
            "added_delay_min": added_delay_min,
            "resilience": resilience_info,
            "route_properties": re_route_result["properties"] if re_route_result else None,
        },
        "features": features,
    }


@api_router.post("/unblock")
def unblock_road_segment(payload: UnblockRequest):
    """Restore a previously blocked road segment (u, v) in the working graph.

    Rule 5: Return GeoJSON from every API.
    """
    G: nx.DiGraph = app_state["graph"]
    u, v = payload.u, payload.v
    edge_key_tuple = (min(u, v), max(u, v))

    app_state["blocked_edges_data"].pop(edge_key_tuple, None)
    app_state["blocked_edges"].discard(edge_key_tuple)
    app_state["blocked_edges"].discard((u, v))
    app_state["blocked_edges"].discard((v, u))

    re_route_result = None
    resilience_info = None
    if payload.incident_lat is not None and payload.incident_lng is not None:
        try:
            re_route_result = execute_route_calculation(
                payload.incident_lat, payload.incident_lng, use_working_graph=True
            )
            turn_order = re_route_result["properties"]["turn_order_vertices"]
            G_undir = get_undirected_graph()
            g_bridges, g_aps = get_global_bridges()
            res_result = analyze_route_resilience(
                G_directed=G,
                G_undirected=G_undir,
                route_nodes=turn_order,
                base_travel_time=re_route_result["properties"]["total_time_sec"],
                source=turn_order[0],
                target=turn_order[-1],
                global_bridges=g_bridges,
                global_aps=g_aps,
                blocked_edges=app_state["blocked_edges"],
            )
            resilience_info = {
                "resilience_score": res_result.resilience_score,
                "rating": res_result.rating,
                "rating_color": res_result.rating_color,
                "components": res_result.components,
                "lambda_menger": res_result.lambda_menger,
                "rho_max": res_result.rho_max,
                "explanation": res_result.explanation,
                "strict_bridges_count": len(res_result.strict_bridges),
                "soft_bridges_count": len(res_result.soft_bridges),
                "articulation_points_count": len(res_result.articulation_points),
            }
        except HTTPException:
            re_route_result = None

    blocked_features = get_blocked_edges_features(G)
    features = []
    if re_route_result:
        features.extend(re_route_result["features"])
    features.extend(blocked_features)

    return {
        "type": "FeatureCollection",
        "properties": {
            "unblocked_edge": {"u": u, "v": v},
            "blocked_edges_count": len(app_state["blocked_edges_data"]),
            "resilience": resilience_info,
            "route_properties": re_route_result["properties"] if re_route_result else None,
        },
        "features": features,
    }


@api_router.post("/restore")
def restore_all_roads(payload: RestoreRequest):
    """Restore all blocked road segments and reset network to pristine state.

    Rule 5: Return GeoJSON from every API.
    """
    G: nx.DiGraph = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is not loaded")

    app_state["blocked_edges"].clear()
    app_state["blocked_edges_data"].clear()

    re_route_result = None
    resilience_info = None
    if payload.incident_lat is not None and payload.incident_lng is not None:
        re_route_result = execute_route_calculation(
            payload.incident_lat, payload.incident_lng, use_working_graph=True
        )
        turn_order = re_route_result["properties"]["turn_order_vertices"]
        G_undir = get_undirected_graph()
        g_bridges, g_aps = get_global_bridges()
        res_result = analyze_route_resilience(
            G_directed=G,
            G_undirected=G_undir,
            route_nodes=turn_order,
            base_travel_time=re_route_result["properties"]["total_time_sec"],
            source=turn_order[0],
            target=turn_order[-1],
            global_bridges=g_bridges,
            global_aps=g_aps,
            blocked_edges=app_state["blocked_edges"],
        )
        resilience_info = {
            "resilience_score": res_result.resilience_score,
            "rating": res_result.rating,
            "rating_color": res_result.rating_color,
            "components": res_result.components,
            "lambda_menger": res_result.lambda_menger,
            "rho_max": res_result.rho_max,
            "explanation": res_result.explanation,
            "strict_bridges_count": len(res_result.strict_bridges),
            "soft_bridges_count": len(res_result.soft_bridges),
            "articulation_points_count": len(res_result.articulation_points),
        }

    features = []
    if re_route_result:
        features.extend(re_route_result["features"])

    return {
        "type": "FeatureCollection",
        "properties": {
            "restored": True,
            "blocked_edges_count": 0,
            "resilience": resilience_info,
            "route_properties": re_route_result["properties"] if re_route_result else None,
        },
        "features": features,
    }


# --- Prompt 5: Station Placement (K-Center, P-Median, 1-Center) & Isochrone Coverage ---


def _format_isochrone_bands_dict(bands) -> Dict[str, Any]:
    """Helper to convert IsochroneBands dataclass to dict."""
    return {
        "under_8_min": {
            "count": int(bands.under_8_min_count),
            "pct": float(bands.under_8_min_pct),
            "label": "< 8 min (Golden Hour)",
            "color": "#10b981",
        },
        "between_8_and_15": {
            "count": int(bands.between_8_and_15_count),
            "pct": float(bands.between_8_and_15_pct),
            "label": "8 - 15 min (Standard)",
            "color": "#f59e0b",
        },
        "between_15_and_30": {
            "count": int(bands.between_15_and_30_count),
            "pct": float(bands.between_15_and_30_pct),
            "label": "15 - 30 min (Delayed)",
            "color": "#ef4444",
        },
        "over_30_min": {
            "count": int(bands.over_30_min_count),
            "pct": float(bands.over_30_min_pct),
            "label": "> 30 min (Deficit)",
            "color": "#475569",
        },
    }


@api_router.get("/coverage")
def get_coverage(
    mode: str = "current",
    k: int = 4,
    algorithm: str = "p_median",
):
    """Return multi-source Dijkstra coverage isochrone bands across demand points.

    Modes:
    - 'current': Computes coverage from the 4 currently deployed ambulance bases.
    - 'suggested': Runs graph placement optimization for k stations and evaluates coverage.

    Rule 5: Return GeoJSON from every API.
    """
    G = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine or demand grid is not loaded")

    demand_nodes = get_cached_demand_nodes()
    candidate_nodes = get_cached_candidate_nodes()
    placement_matrix = get_cached_placement_matrix() if mode != "current" else None

    # Mode 1: Current baseline deployment
    if mode == "current":
        current_station_nodes = list(app_state["station_node_map"].values())
        cov: CoverageResult = compute_multi_source_coverage(
            G, station_nodes=current_station_nodes, demand_nodes=demand_nodes
        )

        features = []
        # Add demand points with isochrone band styling
        for pt in cov.demand_points_data:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [pt["lng"], pt["lat"]],
                    },
                    "properties": {
                        "type": "coverage_point",
                        "node_id": pt["node_id"],
                        "time_sec": pt["time_sec"],
                        "time_min": pt["time_min"],
                        "band": pt["band"],
                        "band_label": pt["band_label"],
                        "color": pt["color"],
                    },
                }
            )

        # Add current station markers
        for s in app_state["stations"]:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [s["lng"], s["lat"]],
                    },
                    "properties": {
                        "type": "station",
                        "name": s["name"],
                        "short_name": s.get("short_name"),
                        "ambulances_available": s["ambulances_available"],
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "properties": {
                "mode": "current",
                "total_demand_points": cov.total_demand_points,
                "bands": _format_isochrone_bands_dict(cov.bands),
                "mean_time_min": cov.mean_time_min,
                "max_time_min": cov.max_time_min,
                "station_count": len(current_station_nodes),
            },
            "features": features,
        }

    # Mode 2: Suggested optimal placement
    if algorithm == "1_center" or k == 1:
        opt_res: PlacementResult = compute_eccentricity_and_center(
            G, candidate_nodes, demand_nodes, cost_matrix=placement_matrix
        )
    elif algorithm == "k_center":
        opt_res: PlacementResult = greedy_k_center(
            G, candidate_nodes, demand_nodes, k=k, cost_matrix=placement_matrix
        )
    else:  # 'p_median' default
        opt_res: PlacementResult = swap_p_median(
            G, candidate_nodes, demand_nodes, k=k, cost_matrix=placement_matrix
        )

    # Coverage from suggested locations
    prop_cov: CoverageResult = compute_multi_source_coverage(
        G, station_nodes=opt_res.selected_nodes, demand_nodes=demand_nodes
    )

    # Baseline coverage for before/after comparison
    current_station_nodes = list(app_state["station_node_map"].values())
    base_cov: CoverageResult = compute_multi_source_coverage(
        G, station_nodes=current_station_nodes, demand_nodes=demand_nodes
    )

    features = []
    # Demand points colored by proposed coverage
    for pt in prop_cov.demand_points_data:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [pt["lng"], pt["lat"]],
                },
                "properties": {
                    "type": "coverage_point",
                    "node_id": pt["node_id"],
                    "time_sec": pt["time_sec"],
                    "time_min": pt["time_min"],
                    "band": pt["band"],
                    "band_label": pt["band_label"],
                    "color": pt["color"],
                },
            }
        )

    # Suggested station markers (distinct glowing beacon styling)
    for fac in opt_res.facility_details:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [fac["lng"], fac["lat"]],
                },
                "properties": {
                    "type": "suggested_station",
                    "name": fac["name"],
                    "node_id": fac["node_id"],
                    "algorithm": opt_res.algorithm,
                    "color": "#a855f7",
                },
            }
        )

    # Calculate before/after comparison deltas
    delta_8min_pct = round(prop_cov.bands.under_8_min_pct - base_cov.bands.under_8_min_pct, 1)
    delta_mean_min = round(base_cov.mean_time_min - prop_cov.mean_time_min, 2)
    delta_max_min = round(base_cov.max_time_min - prop_cov.max_time_min, 2)

    return {
        "type": "FeatureCollection",
        "properties": {
            "mode": "suggested",
            "algorithm": opt_res.algorithm,
            "k": opt_res.k,
            "total_demand_points": prop_cov.total_demand_points,
            "bands": _format_isochrone_bands_dict(prop_cov.bands),
            "mean_time_min": prop_cov.mean_time_min,
            "max_time_min": prop_cov.max_time_min,
            "suggested_stations": opt_res.facility_details,
            "baseline_comparison": {
                "baseline_bands": _format_isochrone_bands_dict(base_cov.bands),
                "baseline_mean_time_min": base_cov.mean_time_min,
                "baseline_max_time_min": base_cov.max_time_min,
                "delta_8min_pct": delta_8min_pct,
                "delta_mean_time_min": delta_mean_min,
                "delta_max_time_min": delta_max_min,
                "is_improved": delta_8min_pct >= 0 or delta_mean_min >= 0,
            },
        },
        "features": features,
    }


@api_router.post("/placement/suggest")
def suggest_station_placement(payload: PlacementRequest):
    """Suggest optimal ambulance station locations using K-Center, P-Median, or 1-Center.

    Rule 5: Return GeoJSON from every API.
    """
    return get_coverage(mode="suggested", k=payload.k, algorithm=payload.algorithm)


@api_router.post("/assign")
def assign_ambulances(payload: AssignmentRequest):
    """Assign available ambulances to up to 5 accidents using Min-Sum (Hungarian) or Minimax Bottleneck.

    Rule 5: Return GeoJSON from every API.
    """
    G: nx.MultiDiGraph = app_state["graph"]
    fleet: List[AmbulanceUnit] = app_state.get("fleet", [])

    if G is None or not fleet:
        raise HTTPException(status_code=503, detail="Graph engine or ambulance fleet is not ready")

    if not payload.accidents or len(payload.accidents) == 0:
        raise HTTPException(status_code=400, detail="At least one accident location must be provided")

    if len(payload.accidents) > 5:
        raise HTTPException(status_code=400, detail="A maximum of 5 accidents can be placed simultaneously")

    obj = payload.objective.lower()
    if obj not in ("min_sum", "bottleneck"):
        raise HTTPException(status_code=400, detail="Objective must be 'min_sum' (Hungarian) or 'bottleneck'")

    # Snap accidents to graph vertices
    accident_sites: List[AccidentSite] = []
    for idx, acc in enumerate(payload.accidents):
        snapped = int(nearest_node(G, X=acc.lng, Y=acc.lat))
        acc_id = acc.id or f"accident_{idx + 1}"
        accident_sites.append(
            AccidentSite(
                id=acc_id,
                index=idx + 1,
                lat=float(acc.lat),
                lng=float(acc.lng),
                snapped_node_id=snapped,
            )
        )

    # Compute assignment
    res = dispatch_and_route_assignment(G, fleet, accident_sites, objective=obj)

    features = []
    # LineString features for each assigned dispatch route
    for a in res.assignments:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": a.path_coordinates,
                },
                "properties": {
                    "type": "assigned_route",
                    "ambulance_id": a.ambulance_id,
                    "ambulance_name": a.ambulance_name,
                    "station_id": a.station_id,
                    "station_name": a.station_name,
                    "accident_id": a.accident_id,
                    "accident_index": int(a.accident_index),
                    "travel_time_sec": float(a.travel_time_sec),
                    "travel_time_min": float(a.travel_time_min),
                    "distance_m": float(a.distance_m),
                    "distance_km": float(a.distance_km),
                    "color": str(a.color),
                    "is_bottleneck": bool(a.is_bottleneck),
                    "node_count": int(len(a.path_nodes)),
                },
            }
        )

    # Point features for each accident
    for a in res.assignments:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(a.accident_lng), float(a.accident_lat)],
                },
                "properties": {
                    "type": "assigned_accident",
                    "accident_id": a.accident_id,
                    "accident_index": int(a.accident_index),
                    "assigned_ambulance": a.ambulance_name,
                    "travel_time_min": float(a.travel_time_min),
                    "travel_time_sec": float(a.travel_time_sec),
                    "color": str(a.color),
                    "is_bottleneck": bool(a.is_bottleneck),
                },
            }
        )

    # Point features for dispatched stations
    dispatched_stn_ids = set()
    for a in res.assignments:
        if a.station_id not in dispatched_stn_ids:
            dispatched_stn_ids.add(a.station_id)
            stn_node = app_state["station_node_map"].get(a.station_id)
            stn_info = app_state["node_station_map"].get(stn_node)
            if stn_info:
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(stn_info["lng"]), float(stn_info["lat"])],
                        },
                        "properties": {
                            "type": "dispatched_station",
                            "station_id": a.station_id,
                            "name": stn_info["name"],
                            "short_name": stn_info.get("short_name"),
                            "color": str(a.color),
                        },
                    }
                )

    assignments_data = []
    for a in res.assignments:
        assignments_data.append(
            {
                "ambulance_id": a.ambulance_id,
                "ambulance_name": a.ambulance_name,
                "station_id": a.station_id,
                "station_name": a.station_name,
                "accident_id": a.accident_id,
                "accident_index": int(a.accident_index),
                "accident_lat": float(a.accident_lat),
                "accident_lng": float(a.accident_lng),
                "travel_time_sec": float(a.travel_time_sec),
                "travel_time_min": float(a.travel_time_min),
                "distance_m": float(a.distance_m),
                "distance_km": float(a.distance_km),
                "color": str(a.color),
                "is_bottleneck": bool(a.is_bottleneck),
                "path_nodes": [int(n) for n in a.path_nodes],
            }
        )

    return {
        "type": "FeatureCollection",
        "properties": {
            "objective": str(res.objective),
            "total_time_sec": float(res.total_time_sec),
            "total_time_min": float(res.total_time_min),
            "max_time_sec": float(res.max_time_sec),
            "max_time_min": float(res.max_time_min),
            "mean_time_sec": float(res.mean_time_sec),
            "mean_time_min": float(res.mean_time_min),
            "num_accidents": int(len(accident_sites)),
            "num_assigned": int(len(res.assignments)),
            "assignments": assignments_data,
            "unassigned_ambulances": [str(s) for s in res.unassigned_ambulances],
            "cost_matrix": {
                "ambulance_labels": res.ambulance_labels,
                "accident_labels": res.accident_labels,
                "matrix_sec": res.cost_matrix_sec,
                "matrix_min": res.cost_matrix_min,
            },
            "padded_shape": [int(res.padded_shape[0]), int(res.padded_shape[1])],
        },
        "features": features,
    }


@api_router.get("/traffic/config")
def get_traffic_config_endpoint():
    """Return traffic configuration with road class multipliers and corridors."""
    cfg = app_state.get("traffic_config")
    if cfg is None:
        cfg = get_traffic_config()
    return cfg


@api_router.post("/hospitals/score")
def score_hospitals_endpoint(payload: HospitalScoreRequest):
    """Implement POST /hospitals/score with score = travel_time + P_trauma + P_load.

    Rule 5: Return GeoJSON from every API.
    Evaluates candidate hospitals given trauma requirements, hospital operational load,
    and active time-of-day traffic conditions.
    Returns GeoJSON FeatureCollection with routes, hospital markers, and ranked table.
    """
    G = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is not loaded")

    # 1. Snap accident location to nearest graph junction
    accident_node = int(nearest_node(G, X=payload.lng, Y=payload.lat))
    acc_node_data = G.nodes[accident_node]
    snapped_lat = float(acc_node_data["y"])
    snapped_lng = float(acc_node_data["x"])

    hospitals = app_state["hospitals"]
    hospital_node_map = app_state["hospital_node_map"]

    ranked, winner, nearest, explanation = evaluate_hospital_scores(
        G=G,
        accident_node=accident_node,
        hospitals=hospitals,
        hospital_node_map=hospital_node_map,
        trauma_requirement=payload.trauma_requirement,
        hospital_statuses=payload.hospital_statuses,
        time_of_day=payload.time_of_day,
    )

    if not ranked or winner is None:
        raise HTTPException(status_code=404, detail="No reachable candidate hospitals found.")

    features = []

    # Route 1: Winner Hospital Route (LineString)
    if winner.path and len(winner.path) >= 2:
        winner_coords = node_path_to_coordinates(G, winner.path)
        winner_streets = extract_street_names_from_path(G, winner.path)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": winner_coords,
            },
            "properties": {
                "role": "winner_route",
                "hospital_id": str(winner.id),
                "hospital_name": str(winner.name),
                "short_name": str(winner.short_name),
                "trauma_level": str(winner.trauma_level),
                "status": str(winner.status),
                "travel_time_sec": float(winner.travel_time_sec),
                "travel_time_min": float(winner.travel_time_min),
                "distance_km": float(winner.distance_km),
                "score_sec": float(winner.score_sec),
                "score_min": float(winner.score_min),
                "color": "#10b981",  # Emerald Green
                "streets": winner_streets,
            }
        })

    # Route 2: Nearest Hospital Route (if different from winner, for visual comparison!)
    if nearest and nearest.id != winner.id and nearest.path and len(nearest.path) >= 2:
        nearest_coords = node_path_to_coordinates(G, nearest.path)
        nearest_streets = extract_street_names_from_path(G, nearest.path)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": nearest_coords,
            },
            "properties": {
                "role": "nearest_route",
                "hospital_id": str(nearest.id),
                "hospital_name": str(nearest.name),
                "short_name": str(nearest.short_name),
                "trauma_level": str(nearest.trauma_level),
                "status": str(nearest.status),
                "travel_time_sec": float(nearest.travel_time_sec),
                "travel_time_min": float(nearest.travel_time_min),
                "distance_km": float(nearest.distance_km),
                "score_sec": float(nearest.score_sec),
                "score_min": float(nearest.score_min),
                "color": "#f59e0b",  # Amber
                "dash_array": "6, 8",
                "streets": nearest_streets,
            }
        })

    # Point Features for all 7 candidate hospitals with their rankings and scores
    for r in ranked:
        h_info = app_state["node_hospital_map"].get(hospital_node_map.get(r.id))
        lat_coord = float(h_info["lat"]) if h_info else 0.0
        lng_coord = float(h_info["lng"]) if h_info else 0.0
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lng_coord, lat_coord],
            },
            "properties": {
                "type": "ranked_hospital",
                "rank": int(r.rank),
                "id": str(r.id),
                "name": str(r.name),
                "short_name": str(r.short_name),
                "trauma_level": str(r.trauma_level),
                "status": str(r.status),
                "travel_time_sec": float(r.travel_time_sec),
                "travel_time_min": float(r.travel_time_min),
                "distance_km": float(r.distance_km),
                "p_trauma_sec": float(r.p_trauma_sec),
                "p_trauma_min": float(r.p_trauma_min),
                "p_load_sec": float(r.p_load_sec),
                "p_load_min": float(r.p_load_min),
                "score_sec": float(r.score_sec),
                "score_min": float(r.score_min),
                "is_winner": bool(r.is_winner),
                "is_nearest": bool(r.is_nearest),
            }
        })

    # Point Feature for accident location
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [snapped_lng, snapped_lat],
        },
        "properties": {
            "type": "accident",
            "node_id": int(accident_node),
            "original_lat": float(payload.lat),
            "original_lng": float(payload.lng),
        }
    })

    # Build ranked list of dicts for frontend table
    ranked_table = [
        {
            "rank": int(r.rank),
            "id": str(r.id),
            "name": str(r.name),
            "short_name": str(r.short_name),
            "trauma_level": str(r.trauma_level),
            "status": str(r.status),
            "travel_time_sec": float(r.travel_time_sec),
            "travel_time_min": float(r.travel_time_min),
            "distance_m": float(r.distance_m),
            "distance_km": float(r.distance_km),
            "p_trauma_sec": float(r.p_trauma_sec),
            "p_trauma_min": float(r.p_trauma_min),
            "p_load_sec": float(r.p_load_sec),
            "p_load_min": float(r.p_load_min),
            "score_sec": float(r.score_sec),
            "score_min": float(r.score_min),
            "is_winner": bool(r.is_winner),
            "is_nearest": bool(r.is_nearest),
        }
        for r in ranked
    ]

    winner_beat_nearest = bool(nearest and nearest.id != winner.id)

    return {
        "type": "FeatureCollection",
        "properties": {
            "trauma_requirement": str(payload.trauma_requirement),
            "time_of_day": str(payload.time_of_day),
            "accident": {
                "lat": float(payload.lat),
                "lng": float(payload.lng),
                "snapped_lat": snapped_lat,
                "snapped_lng": snapped_lng,
                "node_id": int(accident_node),
            },
            "winner": {
                "rank": int(winner.rank),
                "id": str(winner.id),
                "name": str(winner.name),
                "short_name": str(winner.short_name),
                "trauma_level": str(winner.trauma_level),
                "status": str(winner.status),
                "travel_time_min": float(winner.travel_time_min),
                "p_trauma_min": float(winner.p_trauma_min),
                "p_load_min": float(winner.p_load_min),
                "score_min": float(winner.score_min),
                "distance_km": float(winner.distance_km),
            },
            "nearest": {
                "rank": int(nearest.rank) if nearest else 1,
                "id": str(nearest.id) if nearest else str(winner.id),
                "name": str(nearest.name) if nearest else str(winner.name),
                "short_name": str(nearest.short_name) if nearest else str(winner.short_name),
                "trauma_level": str(nearest.trauma_level) if nearest else str(winner.trauma_level),
                "status": str(nearest.status) if nearest else str(winner.status),
                "travel_time_min": float(nearest.travel_time_min) if nearest else float(winner.travel_time_min),
                "p_trauma_min": float(nearest.p_trauma_min) if nearest else 0.0,
                "p_load_min": float(nearest.p_load_min) if nearest else 0.0,
                "score_min": float(nearest.score_min) if nearest else float(winner.score_min),
                "distance_km": float(nearest.distance_km) if nearest else float(winner.distance_km),
            } if nearest else None,
            "winner_beat_nearest": winner_beat_nearest,
            "winner_explanation": str(explanation),
            "ranked_hospitals": ranked_table,
        },
        "features": features,
    }


@api_router.post("/route/compare-traffic")
def compare_traffic_route_endpoint(payload: TrafficCompareRequest):
    """Compare optimal shortest path under off-peak vs evening peak traffic.

    Demonstrates algorithmic route divergence when arterial corridors are congested.
    Rule 5: Return GeoJSON from every API.
    """
    G: nx.MultiDiGraph = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is not loaded")

    # Determine source and target nodes
    if payload.source is not None and payload.target is not None:
        source_node = int(payload.source)
        target_node = int(payload.target)
    elif payload.lat is not None and payload.lng is not None:
        source_node = int(nearest_node(G, X=payload.lng, Y=payload.lat))
        if payload.hospital_id and payload.hospital_id in app_state["hospital_node_map"]:
            target_node = int(app_state["hospital_node_map"][payload.hospital_id])
        else:
            target_node = int(app_state["hospital_node_map"].get("victoria", list(app_state["hospital_node_map"].values())[0]))
    else:
        # Default canonical demonstration incident (Richmond Town to Victoria Hospital)
        source_node = int(nearest_node(G, X=77.6050, Y=12.9450))
        target_node = int(app_state["hospital_node_map"]["victoria"])

    comparison = compare_offpeak_vs_peak_route(G, source=source_node, target=target_node)
    if not comparison.get("diverged") and "off_peak" not in comparison:
        raise HTTPException(status_code=404, detail=comparison.get("message", "Route comparison failed."))

    features = []

    # Off-peak route LineString (Cyan/Blue)
    off_path = comparison["off_peak"]["path"]
    off_coords = node_path_to_coordinates(G, off_path)
    off_streets = extract_street_names_from_path(G, off_path)
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": off_coords,
        },
        "properties": {
            "role": "off_peak_route",
            "name": "Off-Peak Route (Direct Arterial)",
            "travel_time_sec": float(comparison["off_peak"]["travel_time_sec"]),
            "travel_time_min": float(comparison["off_peak"]["travel_time_min"]),
            "time_if_driven_at_peak_min": float(comparison["off_peak"]["time_if_driven_at_peak_min"]),
            "distance_km": float(comparison["off_peak"]["distance_km"]),
            "color": "#0284c7",  # Sky Blue
            "streets": off_streets,
        }
    })

    # Peak route LineString (Amber/Orange)
    peak_path = comparison["peak"]["path"]
    peak_coords = node_path_to_coordinates(G, peak_path)
    peak_streets = extract_street_names_from_path(G, peak_path)
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": peak_coords,
        },
        "properties": {
            "role": "peak_route",
            "name": "Evening Peak Route (Congestion Bypass)",
            "travel_time_sec": float(comparison["peak"]["travel_time_sec"]),
            "travel_time_min": float(comparison["peak"]["travel_time_min"]),
            "distance_km": float(comparison["peak"]["distance_km"]),
            "color": "#f97316",  # Orange
            "streets": peak_streets,
        }
    })

    # Source and Target point features
    src_data = G.nodes[source_node]
    tgt_data = G.nodes[target_node]
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(src_data["x"]), float(src_data["y"])]},
        "properties": {"type": "origin", "name": "Incident Site", "node_id": source_node}
    })
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(tgt_data["x"]), float(tgt_data["y"])]},
        "properties": {"type": "destination", "name": "Destination Hospital", "node_id": target_node}
    })

    return {
        "type": "FeatureCollection",
        "properties": {
            "diverged": bool(comparison["diverged"]),
            "source_node": source_node,
            "target_node": target_node,
            "off_peak": comparison["off_peak"],
            "peak": comparison["peak"],
            "peak_bypass_savings_sec": float(comparison["peak_bypass_savings_sec"]),
            "peak_bypass_savings_min": float(comparison["peak_bypass_savings_min"]),
            "explanation": str(comparison["explanation"]),
        },
        "features": features,
    }


@api_router.post("/race")
def algorithm_race_endpoint(payload: RaceRequest):
    """Execute head-to-head algorithm race between Dijkstra and A* search.

    Returns nodes expanded, heap pushes, runtime, explored node order, and cost equality check.
    Rule 5: Return GeoJSON from every API.
    """
    G = app_state["graph"]
    if G is None:
        raise HTTPException(status_code=503, detail="Graph engine is not loaded")

    # Resolve source and target nodes
    if payload.source is not None and payload.target is not None:
        source_node = int(payload.source)
        target_node = int(payload.target)
    elif (
        payload.origin_lat is not None
        and payload.origin_lng is not None
        and payload.destination_lat is not None
        and payload.destination_lng is not None
    ):
        source_node = int(nearest_node(G, X=payload.origin_lng, Y=payload.origin_lat))
        target_node = int(nearest_node(G, X=payload.destination_lng, Y=payload.destination_lat))
    else:
        # Default canonical demonstration pair: Majestic Station to Manipal Hospital
        source_node = int(
            app_state["station_node_map"].get(
                "station_majestic", list(app_state["station_node_map"].values())[0]
            )
        )
        target_node = int(
            app_state["hospital_node_map"].get(
                "manipal", list(app_state["hospital_node_map"].values())[0]
            )
        )

    if source_node not in G or target_node not in G:
        raise HTTPException(status_code=404, detail="Selected origin or destination nodes not found in graph.")

    weight_attr = get_weight_attribute_for_period(payload.time_of_day)

    race = run_algorithm_race(
        G=G,
        source=source_node,
        target=target_node,
        weight=weight_attr,
        animation_sample_limit=payload.sample_limit,
    )

    if not race.get("success"):
        raise HTTPException(status_code=404, detail=race.get("message", "Target is unreachable from origin."))

    features = []

    # Dijkstra Path LineString (Blue #38bdf8)
    dijkstra_path = race["dijkstra"]["path"]
    dijkstra_coords = node_path_to_coordinates(G, dijkstra_path)
    dijkstra_streets = extract_street_names_from_path(G, dijkstra_path)
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": dijkstra_coords,
        },
        "properties": {
            "role": "dijkstra_path",
            "algorithm": "Dijkstra",
            "color": "#38bdf8",
            "cost_sec": float(race["dijkstra"]["cost_sec"]),
            "cost_min": float(race["dijkstra"]["cost_min"]),
            "distance_km": float(race["dijkstra"]["distance_km"]),
            "nodes_expanded": int(race["dijkstra"]["nodes_expanded"]),
            "heap_pushes": int(race["dijkstra"]["heap_pushes"]),
            "runtime_ms": float(race["dijkstra"]["runtime_ms"]),
            "streets": dijkstra_streets,
        }
    })

    # A* Path LineString (Emerald Green #10b981)
    astar_path = race["astar"]["path"]
    astar_coords = node_path_to_coordinates(G, astar_path)
    astar_streets = extract_street_names_from_path(G, astar_path)
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": astar_coords,
        },
        "properties": {
            "role": "astar_path",
            "algorithm": "A*",
            "color": "#10b981",
            "cost_sec": float(race["astar"]["cost_sec"]),
            "cost_min": float(race["astar"]["cost_min"]),
            "distance_km": float(race["astar"]["distance_km"]),
            "nodes_expanded": int(race["astar"]["nodes_expanded"]),
            "heap_pushes": int(race["astar"]["heap_pushes"]),
            "runtime_ms": float(race["astar"]["runtime_ms"]),
            "streets": astar_streets,
        }
    })

    # Origin and Destination points
    src_data = G.nodes[source_node]
    tgt_data = G.nodes[target_node]
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(src_data["x"]), float(src_data["y"])]},
        "properties": {"type": "origin", "name": "Race Origin", "node_id": int(source_node)}
    })
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(tgt_data["x"]), float(tgt_data["y"])]},
        "properties": {"type": "destination", "name": "Race Destination", "node_id": int(target_node)}
    })

    return {
        "type": "FeatureCollection",
        "properties": {
            "source_node": int(source_node),
            "target_node": int(target_node),
            "origin_coords": [float(src_data["y"]), float(src_data["x"])],
            "destination_coords": [float(tgt_data["y"]), float(tgt_data["x"])],
            "costs_equal": bool(race["costs_equal"]),
            "cost_diff_sec": float(race["cost_diff_sec"]),
            "node_reduction_pct": float(race["node_reduction_pct"]),
            "push_reduction_pct": float(race["push_reduction_pct"]),
            "speedup_ratio": float(race["speedup_ratio"]),
            "time_of_day": str(payload.time_of_day),
            "dijkstra": race["dijkstra"],
            "astar": race["astar"],
        },
        "features": features,
    }


# ==============================================================================
# ROUTER REGISTRATION & STATIC ASSETS DEPLOYMENT
# ==============================================================================

# 1. Primary API routes under /api prefix
app.include_router(api_router, prefix="/api")

# 2. Non-prefixed router for backward compatibility with automated test suites
app.include_router(api_router, include_in_schema=False)

# 3. Mount compiled static assets (/assets) from frontend/dist
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


# 4. Root & Client-side SPA routing fallback
@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve frontend landing page at /."""
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "status": "operational",
        "system": "Emergency Ambulance Route Optimization System",
        "city": "Bengaluru",
        "message": "Frontend static assets not built. Run 'npm run build' in frontend directory.",
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_fallback(full_path: str):
    """Serve frontend static files and fallback to index.html for client-side routing."""
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail=f"API endpoint '/{full_path}' not found")

    target_file = FRONTEND_DIST_DIR / full_path
    if target_file.is_file():
        return FileResponse(target_file)

    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Resource not found")



