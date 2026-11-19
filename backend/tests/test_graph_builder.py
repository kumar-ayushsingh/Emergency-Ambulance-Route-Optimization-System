r"""Unit and Integration Tests for Graph Data Layer.

Verifies:
- Graph loading from cached GraphML
- Strongly Connected Component property on directed graph
- Travel time edge weight attribution (w(e) in seconds)
- Undirected simple graph conversion and Euler's Handshake Lemma (\sum deg(v) = 2|E|)
- Schema validation and geospatial snapping for hospitals.json and stations.json
"""

import json
from pathlib import Path

import networkx as nx
import osmnx as ox
import pytest

from backend.graph_builder import (
    DEFAULT_CACHE_FILE,
    HOSPITALS_FILE,
    STATIONS_FILE,
    get_undirected_simple_graph,
    load_graph,
    load_hospitals,
    load_stations,
    parse_speed_kph,
    verify_handshake_lemma,
)


@pytest.fixture(scope="module")
def graph() -> nx.MultiDiGraph:
    """Load the cached road graph once for the test module."""
    assert DEFAULT_CACHE_FILE.exists(), f"Cache file {DEFAULT_CACHE_FILE} must exist before running tests"
    G = load_graph()
    return G


@pytest.fixture(scope="module")
def undirected_graph(graph: nx.MultiDiGraph) -> nx.Graph:
    """Derive simple undirected graph from the directed road graph."""
    return get_undirected_simple_graph(graph)


def test_graph_loaded_properties(graph: nx.MultiDiGraph):
    """Verify directed graph contains nodes and edges within expected Bengaluru corridor bounds."""
    assert isinstance(graph, nx.MultiDiGraph)
    assert graph.number_of_nodes() > 5000, "Graph should contain at least 5,000 junctions"
    assert graph.number_of_edges() > 10000, "Graph should contain at least 10,000 road segments"


def test_strongly_connected_component(graph: nx.MultiDiGraph):
    """Verify that every junction can reach every other junction in the directed routing graph.

    Discrete Math Concept: A directed graph G is strongly connected iff for every pair of
    vertices (u, v), there exists a directed path from u to v and from v to u.
    """
    assert nx.is_strongly_connected(graph), "Directed graph must be a single strongly connected component"


def test_edge_travel_time_weights(graph: nx.MultiDiGraph):
    """Rule 3: Verify that all edge weights are strictly positive travel time in seconds."""
    sample_edges = list(graph.edges(keys=True, data=True))[:1000]

    for u, v, k, data in sample_edges:
        assert "travel_time" in data, f"Edge ({u}, {v}) missing 'travel_time' attribute"
        assert isinstance(data["travel_time"], (int, float)), "travel_time must be a numerical float"
        assert data["travel_time"] > 0, "travel_time must be strictly positive"

        assert "length" in data, f"Edge ({u}, {v}) missing 'length' attribute"
        assert data["length"] > 0, "length in meters must be positive"

        assert "speed_kph" in data, f"Edge ({u}, {v}) missing 'speed_kph' attribute"
        assert data["speed_kph"] > 0, "speed in km/h must be positive"


def test_undirected_simple_graph_structure(undirected_graph: nx.Graph):
    """Rule 4: Verify undirected simple graph has no parallel edges or self-loops."""
    assert isinstance(undirected_graph, nx.Graph)
    assert not isinstance(undirected_graph, nx.MultiGraph), "Must be a simple Graph, not a MultiGraph"
    assert nx.number_of_selfloops(undirected_graph) == 0, "Simple graph must not contain self-loops"


def test_handshake_lemma(undirected_graph: nx.Graph):
    r"""Verify Euler's Handshake Lemma on the simple undirected graph.

    Theorem: \sum_{v \in V} deg(v) = 2 |E|.
    """
    sum_deg, twice_e, is_valid = verify_handshake_lemma(undirected_graph)
    assert is_valid, f"Handshake Lemma failed: sum(deg)={sum_deg} != 2|E|={twice_e}"
    assert sum_deg == twice_e


def test_junction_degree_classification(undirected_graph: nx.Graph):
    """Verify classification of vertices: dead-ends (deg 1), bends (deg 2), and intersections (deg >= 3)."""
    degrees = dict(undirected_graph.degree())
    deg1 = sum(1 for d in degrees.values() if d == 1)
    deg2 = sum(1 for d in degrees.values() if d == 2)
    deg3_plus = sum(1 for d in degrees.values() if d >= 3)

    assert deg1 > 0, "Should identify terminal dead-end nodes"
    assert deg3_plus > 0, "Should identify major road intersections (degree >= 3)"
    assert deg1 + deg2 + deg3_plus == undirected_graph.number_of_nodes()


def test_hospitals_metadata_and_snapping(graph: nx.MultiDiGraph):
    """Verify hospitals.json schema and verify all facilities snap to valid graph vertices."""
    assert HOSPITALS_FILE.exists(), f"{HOSPITALS_FILE} must exist"
    hospitals = load_hospitals()

    assert len(hospitals) >= 7, "Must define at least 7 hospitals in the corridor"
    valid_statuses = {"normal", "busy", "full"}
    valid_trauma = {"Level-1", "Level-2", "Level-3"}

    for h in hospitals:
        assert "id" in h and isinstance(h["id"], str)
        assert "name" in h and isinstance(h["name"], str)
        assert "lat" in h and isinstance(h["lat"], (int, float))
        assert "lng" in h and isinstance(h["lng"], (int, float))
        assert h["status"] in valid_statuses, f"Invalid hospital status: {h['status']}"
        assert h["trauma_level"] in valid_trauma, f"Invalid trauma level: {h['trauma_level']}"

        # Snap to nearest graph vertex
        nearest_node = ox.distance.nearest_nodes(graph, X=h["lng"], Y=h["lat"])
        assert nearest_node in graph, f"Hospital {h['name']} snapped node {nearest_node} not in graph"


def test_stations_metadata_and_snapping(graph: nx.MultiDiGraph):
    """Verify stations.json schema and verify all ambulance bases snap to valid graph vertices."""
    assert STATIONS_FILE.exists(), f"{STATIONS_FILE} must exist"
    stations = load_stations()

    assert len(stations) >= 4, "Must define at least 4 ambulance stations spread across city"

    for s in stations:
        assert "id" in s and isinstance(s["id"], str)
        assert "name" in s and isinstance(s["name"], str)
        assert "lat" in s and isinstance(s["lat"], (int, float))
        assert "lng" in s and isinstance(s["lng"], (int, float))
        assert "ambulances_available" in s and s["ambulances_available"] > 0

        # Snap to nearest graph vertex
        nearest_node = ox.distance.nearest_nodes(graph, X=s["lng"], Y=s["lat"])
        assert nearest_node in graph, f"Station {s['name']} snapped node {nearest_node} not in graph"


def test_parse_speed_kph():
    """Test road class hierarchy fallback and tag parsing for vehicle speeds."""
    assert parse_speed_kph("50", "primary") == 50.0
    assert parse_speed_kph("40 km/h", "secondary") == 40.0
    assert parse_speed_kph(None, "motorway") == 60.0
    assert parse_speed_kph(None, "residential") == 20.0
    assert parse_speed_kph(None, "unknown_highway_type") == 20.0
