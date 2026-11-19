r"""Graph Data Layer for Emergency Ambulance Route Optimization System.

Builds, cleans, attributes, and caches the drivable road network of Bengaluru
using OpenStreetMap (via OSMnx) and NetworkX.

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
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import networkx as nx
import osmnx as ox

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Project root paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_CACHE_FILE = (
    DATA_DIR / "srinagar.graphml"
    if (DATA_DIR / "srinagar.graphml").exists()
    else DATA_DIR / "bengaluru.graphml"
)
HOSPITALS_FILE = DATA_DIR / "hospitals.json"
STATIONS_FILE = DATA_DIR / "stations.json"

# In-memory graph singleton to ensure graph is loaded only once
_LOADED_GRAPH_CACHE: Optional[nx.MultiDiGraph] = None

# Central/Emergency Corridor Bounding Box for Bengaluru (EPSG:4326)
# Covers Victoria Hospital, NIMHANS, Bowring, St. John's, Manipal, and KC General
# In OSMnx 2.x, bbox format is (left/west, bottom/south, right/east, top/north)
DEFAULT_BBOX: Tuple[float, float, float, float] = (77.560, 12.920, 77.660, 13.010)

# Default urban speeds for Bengaluru road hierarchy (km/h)
# Conservative estimates reflecting Bengaluru city traffic conditions
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
    """Parse speed limit from OSM maxspeed tag or fallback to road hierarchy default.

    Args:
        raw_speed: Raw value of 'maxspeed' tag from OpenStreetMap.
        highway_type: OSM 'highway' classification (e.g., 'primary', 'residential').

    Returns:
        Speed limit in kilometers per hour (float).
    """
    if raw_speed is not None:
        try:
            if isinstance(raw_speed, list):
                raw_speed = raw_speed[0]
            if isinstance(raw_speed, str):
                cleaned = raw_speed.lower().replace("km/h", "").replace("kph", "").replace("mph", "").strip()
                val = float(cleaned)
                if "mph" in str(raw_speed).lower():
                    val *= 1.60934
                if val > 5.0:
                    return val
            elif isinstance(raw_speed, (int, float)) and raw_speed > 5.0:
                return float(raw_speed)
        except (ValueError, TypeError):
            pass

    # Fallback to road class default
    if isinstance(highway_type, list):
        highway_type = highway_type[0]
    return DEFAULT_SPEEDS_KPH.get(str(highway_type), FALLBACK_SPEED_KPH)


def add_travel_time_weights(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Calculate and attach travel time in seconds to every edge in the graph.

    Rule 3: All edge weights are strictly travel time in seconds.
    Formula: w(e) = length (meters) / speed (meters/second).

    Args:
        G: Directed street multigraph from OSMnx.

    Returns:
        Graph G with 'speed_kph', 'speed_mps', and 'travel_time' attributes on all edges.
    """
    for _, _, _, data in G.edges(keys=True, data=True):
        length_m = float(data.get("length", 1.0))
        highway = data.get("highway", "unclassified")
        maxspeed = data.get("maxspeed", None)

        speed_kph = parse_speed_kph(maxspeed, highway)
        speed_mps = speed_kph * (1000.0 / 3600.0)

        # Travel time in seconds (minimum 0.1s to avoid divide-by-zero or zero-weight paths)
        travel_time = max(0.1, length_m / speed_mps)

        data["speed_kph"] = speed_kph
        data["speed_mps"] = speed_mps
        data["travel_time"] = travel_time
        data["length"] = length_m

    return G


def keep_largest_strongly_connected_component(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Filter graph to its largest Strongly Connected Component (SCC).

    In a strongly connected directed graph, every vertex u has a directed path
    to every other vertex v (u ~> v and v ~> u). This prevents routing dead-ends.

    Args:
        G: Input directed street multigraph.

    Returns:
        Subgraph induced by the largest strongly connected component.
    """
    if not nx.is_strongly_connected(G):
        sccs = list(nx.strongly_connected_components(G))
        largest_scc = max(sccs, key=len)
        initial_nodes = len(G.nodes)
        G = G.subgraph(largest_scc).copy()
        logger.info(
            "Filtered to largest Strongly Connected Component: %d -> %d nodes (dropped %d disconnected nodes)",
            initial_nodes,
            len(G.nodes),
            initial_nodes - len(G.nodes),
        )
    return G


def get_undirected_simple_graph(G_directed: nx.MultiDiGraph) -> nx.Graph:
    """Convert a directed multigraph into an undirected simple graph.

    Rule 4: Maintain a directed graph for routing and an undirected simple
    graph for bridge and articulation-point theory.

    For parallel directed edges or opposing lanes between (u, v), the edge with
    the minimum travel time is preserved as the single undirected edge {u, v}.

    Args:
        G_directed: Directed MultiDiGraph used for routing.

    Returns:
        Undirected simple nx.Graph.
    """
    G_undir = nx.Graph()

    # Copy vertex attributes (coordinates x/lng, y/lat)
    for node, attrs in G_directed.nodes(data=True):
        G_undir.add_node(node, **attrs)

    # Collapse parallel / directional edges into minimum-cost simple undirected edges
    for u, v, _, data in G_directed.edges(keys=True, data=True):
        if u == v:
            # Self-loops cannot be bridges in simple connectivity
            continue

        travel_time = float(data.get("travel_time", 1.0))
        length = float(data.get("length", 1.0))

        if G_undir.has_edge(u, v):
            # If edge already exists, retain the faster connection
            if travel_time < G_undir[u][v]["travel_time"]:
                G_undir[u][v]["travel_time"] = travel_time
                G_undir[u][v]["length"] = length
                G_undir[u][v]["name"] = data.get("name", "")
                G_undir[u][v]["highway"] = data.get("highway", "")
        else:
            G_undir.add_edge(
                u,
                v,
                travel_time=travel_time,
                length=length,
                name=data.get("name", ""),
                highway=data.get("highway", ""),
            )

    return G_undir


def verify_handshake_lemma(G_undirected: nx.Graph) -> Tuple[int, int, bool]:
    r"""Verify Euler's Handshake Lemma on an undirected graph.

    Mathematical Theorem:
        \sum_{v \in V} deg(v) = 2 |E|

    Every edge contributes exactly 2 to the sum of vertex degrees because it has
    two incident endpoints.

    Args:
        G_undirected: Undirected graph.

    Returns:
        Tuple of (sum_of_degrees, twice_edges, is_valid).
    """
    sum_degrees = sum(dict(G_undirected.degree()).values())
    twice_edges = 2 * G_undirected.number_of_edges()
    is_valid = sum_degrees == twice_edges
    return sum_degrees, twice_edges, is_valid


def print_graph_statistics(G_directed: nx.MultiDiGraph, G_undirected: nx.Graph) -> Dict[str, Any]:
    """Calculate, log, and return structural graph metrics and degree distribution.

    Args:
        G_directed: Directed street multigraph.
        G_undirected: Simple undirected graph.

    Returns:
        Dictionary of summary statistics.
    """
    num_nodes = G_directed.number_of_nodes()
    num_directed_edges = G_directed.number_of_edges()
    num_undirected_edges = G_undirected.number_of_edges()

    # Handshake lemma verification
    sum_deg, twice_e, handshake_passed = verify_handshake_lemma(G_undirected)

    # Degree distribution on undirected simple graph
    degrees = [deg for _, deg in G_undirected.degree()]
    deg_counts = Counter(degrees)

    dead_ends = deg_counts.get(1, 0)
    simple_bends = deg_counts.get(2, 0)
    intersections = sum(count for deg, count in deg_counts.items() if deg >= 3)

    stats = {
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

    print("\n" + "=" * 65)
    print("      GRAPH TOPOLOGY & DISCRETE MATHEMATICS SUMMARY")
    print("=" * 65)
    print(f"Total Vertices (Junctions |V|):            {num_nodes:,}")
    print(f"Total Directed Edges (Routing Arcs |E_dir|): {num_directed_edges:,}")
    print(f"Total Undirected Edges (|E_undir|):         {num_undirected_edges:,}")
    print("-" * 65)
    print("HANDSHAKE LEMMA VERIFICATION:")
    print(f"  Sum of vertex degrees \u03a3 deg(v):          {sum_deg:,}")
    print(f"  Twice undirected edges 2|E|:             {twice_e:,}")
    print(f"  Handshake Lemma Satisfied:               {handshake_passed} (\u03a3 deg(v) == 2|E|)")
    print("-" * 65)
    print("JUNCTION CLASSIFICATION (Undirected Graph):")
    print(f"  Degree 1 (Dead Ends / Terminal Nodes):   {dead_ends:,} ({dead_ends / num_nodes * 100:.1f}%)")
    print(f"  Degree 2 (Through-ways / Road Bends):    {simple_bends:,} ({simple_bends / num_nodes * 100:.1f}%)")
    print(f"  Degree 3+ (Major Intersections):         {intersections:,} ({intersections / num_nodes * 100:.1f}%)")
    print("=" * 65 + "\n")

    return stats


def build_and_cache_graph(
    bbox: Tuple[float, float, float, float] = DEFAULT_BBOX,
    cache_path: Path = DEFAULT_CACHE_FILE,
) -> nx.MultiDiGraph:
    """Download drivable road network via OSMnx, clean SCC, weight edges, and cache to GraphML.

    Args:
        bbox: Bounding box tuple (west, south, east, north) in EPSG:4326.
        cache_path: Filepath where GraphML cache is written.

    Returns:
        Prepared directed MultiDiGraph.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading drivable road network from OpenStreetMap with bbox=%s...", bbox)

    # Download drivable street network
    G = ox.graph_from_bbox(bbox=bbox, network_type="drive", simplify=True)
    logger.info("Raw graph acquired: %d nodes, %d edges", len(G.nodes), len(G.edges))

    # Keep largest strongly connected component
    G = keep_largest_strongly_connected_component(G)

    # Compute and attach travel time in seconds to all edges
    G = add_travel_time_weights(G)

    # Save to GraphML cache
    logger.info("Caching graph to %s...", cache_path)
    ox.save_graphml(G, filepath=cache_path)
    logger.info("Graph cached successfully.")

    return G


def prune_graph_memory(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Drop unused attributes on nodes and edges to significantly minimize startup and runtime memory.

    Retains strictly required attributes:
    - Edges: travel_time, length, speed_kph, name, highway, and dynamic travel_time_* weights.
    - Nodes: x, y coordinates.
    Drops heavy attributes like Shapely geometries, osmid lists, oneway/reversed flags, and street counts.
    """
    kept_edge_keys = {"travel_time", "length", "speed_kph", "name", "highway"}
    kept_node_keys = {"x", "y"}

    for _, _, _, data in G.edges(keys=True, data=True):
        for key in list(data.keys()):
            if key not in kept_edge_keys and not key.startswith("travel_time_"):
                del data[key]

    for _, data in G.nodes(data=True):
        for key in list(data.keys()):
            if key not in kept_node_keys:
                del data[key]

    return G


def load_graph(
    cache_path: Path = DEFAULT_CACHE_FILE,
    bbox: Tuple[float, float, float, float] = DEFAULT_BBOX,
    force_reload: bool = False,
) -> nx.MultiDiGraph:
    """Load graph from local GraphML cache if present; otherwise download and cache.

    Guarantees all edge attributes (travel_time, length, speed_kph) are properly typed floats.
    Caches graph in memory so it is only loaded once, and prunes unused attributes to minimize memory.

    Args:
        cache_path: Path to GraphML file.
        bbox: Bounding box coordinates used if cache is missing or reload is forced.
        force_reload: If True, bypass cache and re-download.

    Returns:
        Directed MultiDiGraph ready for routing and analysis.
    """
    global _LOADED_GRAPH_CACHE

    if _LOADED_GRAPH_CACHE is not None and not force_reload:
        return _LOADED_GRAPH_CACHE

    # Check fallback paths if specified cache_path doesn't exist
    if not cache_path.exists():
        for candidate in [DATA_DIR / "srinagar.graphml", DATA_DIR / "bengaluru.graphml"]:
            if candidate.exists():
                cache_path = candidate
                break

    if cache_path.exists() and not force_reload:
        logger.info("Loading graph from cache: %s", cache_path)
        G = ox.load_graphml(filepath=cache_path)

        # GraphML serialization stores attributes as strings; cast numerical attributes
        for _, _, _, data in G.edges(keys=True, data=True):
            if "travel_time" in data:
                data["travel_time"] = float(data["travel_time"])
            if "length" in data:
                data["length"] = float(data["length"])
            if "speed_kph" in data:
                data["speed_kph"] = float(data["speed_kph"])

        # Also cast node lat/lng
        for _, data in G.nodes(data=True):
            if "y" in data:
                data["y"] = float(data["y"])
            if "x" in data:
                data["x"] = float(data["x"])

        # Prune unused attributes to minimize memory footprint
        G = prune_graph_memory(G)
        _LOADED_GRAPH_CACHE = G
        return G

    logger.info("Cache not found at %s. Building fresh graph...", cache_path)
    G = build_and_cache_graph(bbox=bbox, cache_path=cache_path)
    G = prune_graph_memory(G)
    _LOADED_GRAPH_CACHE = G
    return G


def load_hospitals(file_path: Path = HOSPITALS_FILE) -> List[Dict[str, Any]]:
    """Load hospital metadata from JSON.

    Args:
        file_path: Path to hospitals.json.

    Returns:
        List of hospital dictionaries.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_stations(file_path: Path = STATIONS_FILE) -> List[Dict[str, Any]]:
    """Load ambulance station metadata from JSON.

    Args:
        file_path: Path to stations.json.

    Returns:
        List of ambulance station dictionaries.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    # Execute full pipeline: load or build graph, print stats, verify handshake lemma
    graph = load_graph()
    undirected_graph = get_undirected_simple_graph(graph)
    stats = print_graph_statistics(graph, undirected_graph)

    # Verify snapping of all hospitals and stations
    hospitals = load_hospitals()
    stations = load_stations()

    print("GEOSPATIAL SNAPPING VERIFICATION:")
    for h in hospitals:
        nearest_node = ox.distance.nearest_nodes(graph, X=h["lng"], Y=h["lat"])
        node_data = graph.nodes[nearest_node]
        print(f"  [Hospital] {h['name']:<45} -> Graph Node {nearest_node} ({node_data['y']:.4f}, {node_data['x']:.4f})")

    for s in stations:
        nearest_node = ox.distance.nearest_nodes(graph, X=s["lng"], Y=s["lat"])
        node_data = graph.nodes[nearest_node]
        print(f"  [Station]  {s['name']:<45} -> Graph Node {nearest_node} ({node_data['y']:.4f}, {node_data['x']:.4f})")
    print("=" * 65)
