r"""Traffic Congestion & Time-of-Day Multiplier Layer.

Academic Context:
Discrete Mathematics · Graph Theory · Dynamic Edge Weighting

Edge Weight Formulation:
Under static conditions, edge traversal time is:
    w_0(e) = length(e) / speed(e)

Under time-dependent traffic conditions with congestion multipliers:
    w(e, t) = w_0(e) * M_road(class(e), period(t)) * M_corridor(e, period(t))

Where:
- period(t) \in {off_peak (1.0), morning_peak (1.6), evening_peak (1.8), night (0.8)}
- M_road(class(e), period(t)) accounts for road hierarchy congestion (arterials suffer higher delays)
- M_corridor(e, period(t)) adds extra bottleneck multipliers on critical medical corridors
  (e.g., Karan Nagar to SMHS corridor, Jehangir Chowk, SKIMS Soura chowk, and Bengaluru equivalents)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TRAFFIC_FILE = BASE_DIR / "data" / "traffic.json"

DEFAULT_PERIOD = "off_peak"
VALID_PERIODS = ["off_peak", "morning_peak", "evening_peak", "night"]


def load_traffic_config(file_path: Path = TRAFFIC_FILE) -> Dict[str, Any]:
    """Load traffic multiplier configurations from JSON.

    Args:
        file_path: Path to traffic.json.

    Returns:
        Dictionary of traffic configuration.
    """
    if not file_path.exists():
        logger.warning("Traffic configuration file %s not found. Using fallback defaults.", file_path)
        return {
            "time_periods": {
                "off_peak": {"default_multiplier": 1.0, "road_multipliers": {}},
                "morning_peak": {"default_multiplier": 1.6, "road_multipliers": {}},
                "evening_peak": {"default_multiplier": 1.8, "road_multipliers": {}},
                "night": {"default_multiplier": 0.8, "road_multipliers": {}},
            },
            "special_corridors": {},
        }

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Cached configuration
_TRAFFIC_CONFIG: Optional[Dict[str, Any]] = None


def get_traffic_config() -> Dict[str, Any]:
    """Retrieve cached traffic config or load from disk."""
    global _TRAFFIC_CONFIG
    if _TRAFFIC_CONFIG is None:
        _TRAFFIC_CONFIG = load_traffic_config()
    return _TRAFFIC_CONFIG


def get_edge_traffic_multiplier(
    edge_data: Dict[str, Any],
    period: str = "off_peak",
    config: Optional[Dict[str, Any]] = None,
) -> float:
    """Calculate the cumulative traffic multiplier for a specific directed edge.

    Formula:
        M(e, period) = M_road(highway_class) * M_corridor(keywords)

    Args:
        edge_data: Edge attribute dictionary.
        period: Time-of-day period ('off_peak', 'morning_peak', 'evening_peak', 'night').
        config: Optional pre-loaded traffic configuration dict.

    Returns:
        Combined positive float multiplier (e.g., 0.8, 1.0, 1.6, 2.5).
    """
    if period not in VALID_PERIODS:
        period = "off_peak"

    if config is None:
        config = get_traffic_config()

    periods_cfg = config.get("time_periods", {})
    period_info = periods_cfg.get(period, {})
    default_mult = float(period_info.get("default_multiplier", 1.0))
    road_multipliers = period_info.get("road_multipliers", {})

    # 1. Determine road class multiplier
    highway = edge_data.get("highway", "unclassified")
    if isinstance(highway, list):
        highway = highway[0]
    highway_str = str(highway).lower()

    road_mult = float(road_multipliers.get(highway_str, default_mult))

    # 2. Check for special corridor bottleneck extra multiplier
    corridor_mult = 1.0
    if period in ["morning_peak", "evening_peak"]:
        edge_name = edge_data.get("name", "")
        if isinstance(edge_name, list):
            edge_name_str = " ".join(str(n) for n in edge_name).lower()
        else:
            edge_name_str = str(edge_name).lower()

        special_corridors = config.get("special_corridors", {})
        for _, corr in special_corridors.items():
            keywords = corr.get("keywords", [])
            if any(k.lower() in edge_name_str for k in keywords):
                extra = float(corr.get("extra_multiplier_peak", 1.5))
                # Take maximum extra if multiple match
                corridor_mult = max(corridor_mult, extra)

    return road_mult * corridor_mult


def attach_traffic_weights_to_graph(
    G: nx.MultiDiGraph,
    config: Optional[Dict[str, Any]] = None,
) -> nx.MultiDiGraph:
    """Compute and attach time-dependent travel time attributes to all edges in G.

    Edge attributes added:
    - travel_time_off_peak (s)
    - travel_time_morning_peak (s)
    - travel_time_evening_peak (s)
    - travel_time_night (s)

    Args:
        G: Directed street multigraph.
        config: Optional traffic configuration.

    Returns:
        Graph G with attached time-dependent travel times.
    """
    if config is None:
        config = get_traffic_config()

    if G.is_multigraph():
        for _, _, _, data in G.edges(keys=True, data=True):
            base_time = float(data.get("travel_time", 1.0))
            for p in VALID_PERIODS:
                mult = get_edge_traffic_multiplier(data, period=p, config=config)
                data[f"travel_time_{p}"] = max(0.1, base_time * mult)
    else:
        for _, _, data in G.edges(data=True):
            base_time = float(data.get("travel_time", 1.0))
            for p in VALID_PERIODS:
                mult = get_edge_traffic_multiplier(data, period=p, config=config)
                data[f"travel_time_{p}"] = max(0.1, base_time * mult)

    return G


def get_weight_attribute_for_period(period: str) -> str:
    """Return the edge weight attribute corresponding to a time period.

    Args:
        period: One of 'off_peak', 'morning_peak', 'evening_peak', 'night'.

    Returns:
        Attribute name string like 'travel_time_morning_peak' or 'travel_time'.
    """
    if period in VALID_PERIODS:
        return f"travel_time_{period}"
    return "travel_time"
