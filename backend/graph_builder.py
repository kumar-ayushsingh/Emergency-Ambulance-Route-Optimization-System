r"""Graph Data Layer for Emergency Ambulance Route Optimization System.

Builds, cleans, attributes, and caches the drivable road network using NetworkX
and preprocessed compact graph data.

Mathematical Concepts:
- Directed Graph G = (V, E): Models one-way streets, turns, and directed road segments.
- Undirected Simple Graph G_undir = (V, E'): Used for structural bridge/articulation analysis.
- Strongly Connected Component (SCC): Ensures every junction can reach every other junction.
- Vertex Degree deg(v): Number of incident edges (dead-ends: 1, bends: 2, intersections: >=3).
- Handshake Lemma: \sum_{v \in V} deg(v) = 2|E| (fundamental theorem of graph theory).
- Travel Time Weight w(e): Traversal time in seconds, w(e) = length(m) / speed(m/s).
"""

from __future__ import annotations

import json
import logging
import pickle
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
from scipy.spatial import cKDTree

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Project root paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
GRAPH_PKL_FILE = DATA_DIR / "graph.pkl"
DEFAULT_CACHE_FILE = (
    DATA_DIR / "srinagar.graphml"
    if (DATA_DIR / "srinagar.graphml").exists()
    else DATA_DIR / "bengaluru.graphml"
)
HOSPITALS_FILE = DATA_DIR / "hospitals.json"
STATIONS_FILE = DATA_DIR / "stations.json"

# In-memory graph singleton to ensure graph is loaded only once
_LOADED_GRAPH_CACHE: Optional[nx.DiGraph] = None
_SPATIAL_TREE: Optional[cKDTree] = None
_SPATIAL_NODES: Optional[List[int]] = None

# Central/Emergency Corridor Bounding Box for Bengaluru (EPSG:4326)
DEFAULT_BBOX: Tuple[float, float, float, float] = (77.560, 12.920, 77.660, 13.010)

# Default urban speeds for road hierarchy (km/h)
DEFAULT_SPEEDS_KPH: Dict[str, float] = {
    "motorway": 60.0,
    "motorway_link": 40.0,
    "trunk": 50.0,
    "trunk_link": 35.0,
    "primary": 40.0,
    "primary_link": 30.0,
    "secondary": 30.0,
    "secondary_link": 25.0,
    "tertiary": 25.0,
    "tertiary_link": 20.0,
    "residential": 20.0,
    "living_street": 15.0,
    "unclassified": 20.0,
    "road": 20.0,
}
FALLBACK_SPEED_KPH: float = 20.0


def parse_speed_kph(raw_speed: Any, highway_type: Any) -> float:
    """Parse raw OpenStreetMap maxspeed tag into float km/h."""
    if isinstance(raw_speed, (int, float)):
        return float(raw_speed)

    if isinstance(raw_speed, list) and raw_speed:
        return parse_speed_kph(raw_speed[0], highway_type)

    if isinstance(raw_speed, str):
        cleaned = "".join(c for c in raw_speed.split()[0] if c.isdigit() or c == ".")
        try:
            val = float(cleaned)
            if val > 0:
                return val
        except ValueError:
            pass

    hw = highway_type[0] if isinstance(highway_type, list) else highway_type
    if isinstance(hw, str):
        return DEFAULT_SPEEDS_KPH.get(hw.lower(), FALLBACK_SPEED_KPH)

    return FALLBACK_SPEED_KPH


def get_spatial_index(G: nx.DiGraph | nx.Graph) -> Tuple[cKDTree, List[int]]:
    """Build or retrieve fast scipy cKDTree for spatial nearest-node queries without osmnx."""
    global _SPATIAL_TREE, _SPATIAL_NODES
    if _SPATIAL_TREE is not None and _SPATIAL_NODES is not None:
        return _SPATIAL_TREE, _SPATIAL_NODES

    node_ids = [int(n) for n in G.nodes]
    coords = np.array(
        [[float(G.nodes[n]["y"]), float(G.nodes[n]["x"])] for n in node_ids],
        dtype=np.float64,
    )
    _SPATIAL_TREE = cKDTree(coords)
    _SPATIAL_NODES = node_ids
    return _SPATIAL_TREE, _SPATIAL_NODES


def find_nearest_node(G: nx.DiGraph | nx.Graph, lat: float, lng: float) -> int:
    """Find the nearest graph junction to (lat, lng) using cKDTree."""
    tree, node_ids = get_spatial_index(G)
    _, idx = tree.query([lat, lng])
    return node_ids[idx]


def nearest_node(G: Any, X: float, Y: float) -> int:
    """Drop-in replacement for ox.distance.nearest_nodes(G, X=lng, Y=lat)."""
    return find_nearest_node(G, lat=Y, lng=X)


def get_undirected_simple_graph(G_directed: nx.DiGraph | nx.Graph) -> nx.Graph:
    """Convert directed graph into undirected simple graph for Tarjan bridge/articulation analysis.

    Builds lazily only when requested.
    """
    if not G_directed.is_directed():
        return G_directed

    G_undir = nx.Graph()

    # Copy vertex coordinates
    for node, attrs in G_directed.nodes(data=True):
        G_undir.add_node(node, x=attrs.get("x", 0.0), y=attrs.get("y", 0.0))

    # Add edges, preserving minimum travel time between u and v
    for u, v, data in G_directed.edges(data=True):
        if u == v:
            continue

        travel_time = float(data.get("travel_time", 1.0))
        length = float(data.get("length", 1.0))
        name = str(data.get("name", ""))
        highway = str(data.get("highway", ""))

        if G_undir.has_edge(u, v):
            if travel_time < G_undir[u][v]["travel_time"]:
                G_undir[u][v]["travel_time"] = travel_time
                G_undir[u][v]["length"] = length
        else:
            G_undir.add_edge(
                u,
                v,
                travel_time=travel_time,
                length=length,
                name=name,
                highway=highway,
            )

    return G_undir


def verify_handshake_lemma(G_undirected: nx.Graph) -> Tuple[int, int, bool]:
    r"""Verify Euler's Handshake Lemma on an undirected graph.

    \sum_{v \in V} deg(v) = 2 |E|
    """
    sum_degrees = sum(dict(G_undirected.degree()).values())
    twice_edges = 2 * G_undirected.number_of_edges()
    is_valid = sum_degrees == twice_edges
    return sum_degrees, twice_edges, is_valid


def print_graph_statistics(G_directed: nx.DiGraph, G_undirected: nx.Graph) -> Dict[str, Any]:
    """Calculate and return structural graph metrics and degree distribution."""
    num_nodes = G_directed.number_of_nodes()
    num_directed_edges = G_directed.number_of_edges()
    num_undirected_edges = G_undirected.number_of_edges()

    sum_deg, twice_e, handshake_passed = verify_handshake_lemma(G_undirected)
    degrees = [deg for _, deg in G_undirected.degree()]
    deg_counts = Counter(degrees)

    dead_ends = deg_counts.get(1, 0)
    simple_bends = deg_counts.get(2, 0)
    intersections = sum(count for deg, count in deg_counts.items() if deg >= 3)

    return {
        "vertices": num_nodes,
        "directed_edges": num_directed_edges,
        "undirected_edges": num_undirected_edges,
        "handshake_sum_degrees": sum_deg,
        "handshake_twice_edges": twice_e,
        "handshake_verified": handshake_passed,
        "dead_ends_deg1": dead_ends,
        "bends_deg2": simple_bends,
        "intersections_deg3_plus": intersections,
        "degree_histogram": dict(sorted(deg_counts.items())),
    }


def prune_graph_memory(G: nx.DiGraph | nx.MultiDiGraph) -> nx.DiGraph:
    """Drop all non-essential attributes to minimize memory footprint."""
    kept_edge_keys = {
        "travel_time",
        "length",
        "speed_kph",
        "name",
        "highway",
        "coords",
        "travel_time_morning_peak",
        "travel_time_evening_peak",
        "travel_time_night",
    }
    kept_node_keys = {"x", "y"}

    if G.is_multigraph():
        # Collapse into DiGraph
        G_simple = nx.DiGraph()
        for node, data in G.nodes(data=True):
            G_simple.add_node(node, x=float(data["x"]), y=float(data["y"]))
        for u, v, k, data in G.edges(keys=True, data=True):
            if u == v:
                continue
            tt = float(data.get("travel_time", 1.0))
            if G_simple.has_edge(u, v):
                if tt < G_simple[u][v]["travel_time"]:
                    G_simple[u][v]["travel_time"] = tt
                    G_simple[u][v]["length"] = float(data.get("length", 1.0))
            else:
                G_simple.add_edge(
                    u,
                    v,
                    travel_time=tt,
                    length=float(data.get("length", 1.0)),
                    speed_kph=float(data.get("speed_kph", 40.0)),
                    name=str(data.get("name", "")),
                    highway=str(data.get("highway", "residential")),
                )
        return G_simple

    for u, v, data in G.edges(data=True):
        for key in list(data.keys()):
            if key not in kept_edge_keys:
                del data[key]

    for node, data in G.nodes(data=True):
        for key in list(data.keys()):
            if key not in kept_node_keys:
                del data[key]

    return G


def load_graph(
    cache_path: Path = GRAPH_PKL_FILE,
    bbox: Tuple[float, float, float, float] = DEFAULT_BBOX,
    force_reload: bool = False,
) -> nx.DiGraph:
    """Load compact graph from data/graph.pkl if present; otherwise fallback to GraphML.

    Guarantees fast, low-memory startup (<100MB) without importing osmnx.
    """
    global _LOADED_GRAPH_CACHE

    if _LOADED_GRAPH_CACHE is not None and not force_reload:
        return _LOADED_GRAPH_CACHE

    # Priority 1: Compact pickle file (fastest, lowest memory)
    if GRAPH_PKL_FILE.exists() and not force_reload:
        logger.info("Loading compact graph from %s...", GRAPH_PKL_FILE)
        with open(GRAPH_PKL_FILE, "rb") as f:
            G = pickle.load(f)
        _LOADED_GRAPH_CACHE = G
        return G

    # Priority 2: GraphML fallback
    target_graphml = cache_path if cache_path.exists() else DEFAULT_CACHE_FILE
    if target_graphml.exists() and not force_reload:
        logger.info("Loading graph from GraphML fallback: %s...", target_graphml)
        import osmnx as ox  # Lazy import only if GraphML fallback needed
        G_raw = ox.load_graphml(filepath=target_graphml)
        G = prune_graph_memory(G_raw)
        _LOADED_GRAPH_CACHE = G
        return G

    logger.info("No cached graph found. Building compact graph...")
    from scripts.build_graph import build_compact_graph
    G = build_compact_graph(DEFAULT_CACHE_FILE, GRAPH_PKL_FILE)
    _LOADED_GRAPH_CACHE = G
    return G


def load_hospitals(file_path: Path = HOSPITALS_FILE) -> List[Dict[str, Any]]:
    """Load hospital metadata from JSON."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_stations(file_path: Path = STATIONS_FILE) -> List[Dict[str, Any]]:
    """Load ambulance base stations metadata from JSON."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
