#!/usr/bin/env python3
"""Offline Graph Preprocessing Script for Emergency Ambulance Route Optimization.

Builds a compact, production-optimized DiGraph from OpenStreetMap GraphML cache,
collapsing parallel edges, simplifying geometries, stripping all Shapely objects,
and precomputing traffic weights to ensure the runtime server operates well under 200MB RSS.

Usage:
    python scripts/build_graph.py
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Tuple

import networkx as nx
import osmnx as ox

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_graph")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_PKL = DATA_DIR / "graph.pkl"
TRAFFIC_FILE = DATA_DIR / "traffic.json"

# Source GraphML candidate files
CANDIDATE_GRAPHML = [
    DATA_DIR / "srinagar.graphml",
    DATA_DIR / "bengaluru.graphml",
]


def load_traffic_config() -> Dict[str, Any]:
    """Load traffic multiplier configuration."""
    if TRAFFIC_FILE.exists():
        with open(TRAFFIC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def calculate_edge_traffic_time(
    base_time: float, highway: str, name: str, period: str, traffic_cfg: Dict[str, Any]
) -> float:
    """Calculate traffic-adjusted travel time for a specific time period."""
    if period == "off_peak" or not traffic_cfg:
        return base_time

    periods = traffic_cfg.get("periods", {})
    p_data = periods.get(period, {})
    default_mult = float(p_data.get("default_multiplier", 1.0))
    by_class = p_data.get("by_road_class", {})

    highway_class = highway.lower() if isinstance(highway, str) else "residential"
    multiplier = float(by_class.get(highway_class, default_mult))

    # Corridor specific boosts
    corridors = p_data.get("corridors", {})
    name_str = name.lower() if isinstance(name, str) else ""
    for corridor_name, c_mult in corridors.items():
        if any(keyword in name_str for keyword in corridor_name.lower().split("_")):
            multiplier = max(multiplier, float(c_mult))

    return round(base_time * multiplier, 3)


def simplify_geometry(geom: Any, tolerance_deg: float = 0.00005) -> List[List[float]]:
    """Simplify a Shapely LineString and convert to a plain list of [lng, lat] pairs.

    Tolerance of 0.00005 deg ~= 5.5 meters at Bengaluru/Srinagar latitude.
    """
    if geom is None:
        return []

    try:
        # If it's a Shapely geometry
        if hasattr(geom, "simplify"):
            simplified = geom.simplify(tolerance_deg, preserve_topology=True)
            return [[round(x, 6), round(y, 6)] for x, y in simplified.coords]
        elif isinstance(geom, str) and geom.startswith("LINESTRING"):
            import shapely.wkt
            parsed = shapely.wkt.loads(geom)
            simplified = parsed.simplify(tolerance_deg, preserve_topology=True)
            return [[round(x, 6), round(y, 6)] for x, y in simplified.coords]
    except Exception:
        pass
    return []


def build_compact_graph(source_path: Path, output_path: Path) -> nx.DiGraph:
    """Load GraphML, collapse parallel edges, strip unused attributes, and save graph.pkl."""
    logger.info("Loading source GraphML from %s...", source_path)
    G_raw = ox.load_graphml(filepath=source_path)
    logger.info("Raw graph loaded: %d nodes, %d edges", G_raw.number_of_nodes(), G_raw.number_of_edges())

    traffic_cfg = load_traffic_config()

    G_compact = nx.DiGraph()

    # 1. Populate nodes with float coordinates
    logger.info("Extracting node coordinates...")
    for node, data in G_raw.nodes(data=True):
        lat = float(data.get("y", 0.0))
        lng = float(data.get("x", 0.0))
        G_compact.add_node(int(node), y=lat, x=lng)

    # 2. Collapse parallel edges into minimum travel_time single directed edge
    logger.info("Collapsing parallel edges and simplifying geometry...")
    collapsed_count = 0

    for u_raw, v_raw, k, data in G_raw.edges(keys=True, data=True):
        u, v = int(u_raw), int(v_raw)
        if u == v:
            continue  # Drop self-loops

        length = float(data.get("length", 10.0))
        travel_time = float(data.get("travel_time", length / 11.11))
        speed_kph = float(data.get("speed_kph", 40.0))
        
        # Highway classification string
        hw = data.get("highway", "residential")
        if isinstance(hw, list):
            hw = hw[0]
        highway = str(hw) if hw else "residential"

        # Street name string
        nm = data.get("name", "")
        if isinstance(nm, list):
            nm = nm[0]
        name = str(nm) if nm else ""

        # Geometry extraction
        geom = data.get("geometry")
        coords = simplify_geometry(geom)

        # Traffic precomputed times
        t_morning = calculate_edge_traffic_time(travel_time, highway, name, "morning_peak", traffic_cfg)
        t_evening = calculate_edge_traffic_time(travel_time, highway, name, "evening_peak", traffic_cfg)
        t_night = calculate_edge_traffic_time(travel_time, highway, name, "night", traffic_cfg)

        edge_attrs = {
            "travel_time": travel_time,
            "length": length,
            "speed_kph": speed_kph,
            "highway": highway,
            "name": name,
            "travel_time_morning_peak": t_morning,
            "travel_time_evening_peak": t_evening,
            "travel_time_night": t_night,
        }
        if coords:
            edge_attrs["coords"] = coords

        if G_compact.has_edge(u, v):
            collapsed_count += 1
            # Retain the faster edge between u and v
            if travel_time < G_compact[u][v]["travel_time"]:
                G_compact[u][v].update(edge_attrs)
        else:
            G_compact.add_edge(u, v, **edge_attrs)

    logger.info(
        "Collapsing complete. Collapsed %d duplicate parallel segments. Compact graph: %d nodes, %d directed edges",
        collapsed_count,
        G_compact.number_of_nodes(),
        G_compact.number_of_edges(),
    )

    # 3. Save to data/graph.pkl
    logger.info("Writing compact graph to %s...", output_path)
    with open(output_path, "wb") as f:
        pickle.dump(G_compact, f, protocol=5)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("Success! Compact graph file created: %.2f MB", size_mb)

    return G_compact


def main():
    source_file = None
    for candidate in CANDIDATE_GRAPHML:
        if candidate.exists():
            source_file = candidate
            break

    if not source_file:
        raise FileNotFoundError(f"No source GraphML found in {CANDIDATE_GRAPHML}")

    build_compact_graph(source_file, OUTPUT_PKL)


if __name__ == "__main__":
    main()
