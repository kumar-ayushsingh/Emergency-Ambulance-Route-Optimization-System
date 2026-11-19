"""Unit & Integration Tests for Multi-Ambulance Assignment (Prompt 6).

Academic Context:
Discrete Mathematics · Module 4: Graph Theory & Operations Research
Cross-validation requirement:
"Add a test comparing the result with brute force for sizes up to 6x6."
"""

import numpy as np
import pytest

from backend.algorithms.assignment import (
    AccidentSite,
    AmbulanceUnit,
    brute_force_assignment,
    build_ambulance_fleet,
    build_cost_matrix,
    dispatch_and_route_assignment,
    pad_cost_matrix,
    solve_bottleneck_assignment,
    solve_min_sum_assignment,
)
from backend.graph_builder import load_graph, load_stations


def test_pad_cost_matrix():
    """Verify matrix padding logic for unequal dimensions (M != N)."""
    # Case 1: M > N (4 ambulances, 2 accidents)
    C_rect = np.array([[10.0, 20.0], [15.0, 12.0], [8.0, 25.0], [30.0, 40.0]])
    padded, m, n = pad_cost_matrix(C_rect, pad_value=0.0)

    assert padded.shape == (4, 4)
    assert m == 4
    assert n == 2
    # Verify original values are preserved
    np.testing.assert_array_equal(padded[:4, :2], C_rect)
    # Verify dummy columns have cost 0.0
    np.testing.assert_array_equal(padded[:, 2:], 0.0)

    # Case 2: M == N (already square)
    C_sq = np.array([[5.0, 8.0], [9.0, 3.0]])
    padded_sq, m2, n2 = pad_cost_matrix(C_sq)
    assert padded_sq.shape == (2, 2)
    assert m2 == 2
    assert n2 == 2


@pytest.mark.parametrize("size", [2, 3, 4, 5, 6])
def test_min_sum_vs_brute_force_square(size: int):
    """Cross-check Hungarian algorithm against brute-force permutation search for sizes 2x2 to 6x6."""
    np.random.seed(42 + size)

    # Test 5 distinct random cost matrices for each matrix size
    for trial in range(5):
        # Generate random travel times between 60s (1 min) and 1800s (30 mins)
        cost_matrix = np.random.uniform(60.0, 1800.0, size=(size, size))

        # 1. Brute-force exact optimal
        bf_res = brute_force_assignment(cost_matrix)
        expected_min_sum = bf_res["min_sum"]

        # 2. Hungarian algorithm (with padding)
        rows, cols, actual_min_sum = solve_min_sum_assignment(cost_matrix, pad=True)

        # Confirm equal sum
        assert np.isclose(
            actual_min_sum, expected_min_sum, atol=1e-3
        ), f"Failed size {size}x{size} trial {trial}: Hungarian sum {actual_min_sum} != Brute sum {expected_min_sum}"
        assert len(rows) == size
        assert len(set(rows)) == size, "Each ambulance must be uniquely assigned"
        assert len(set(cols)) == size, "Each accident must be uniquely assigned"


@pytest.mark.parametrize("size", [2, 3, 4, 5, 6])
def test_bottleneck_vs_brute_force_square(size: int):
    """Cross-check Bottleneck Assignment (minimax worst-case) against brute force for sizes 2x2 to 6x6."""
    np.random.seed(100 + size)

    for trial in range(5):
        cost_matrix = np.random.uniform(60.0, 1800.0, size=(size, size))

        # 1. Brute-force exact optimal minimax
        bf_res = brute_force_assignment(cost_matrix)
        expected_bottleneck = bf_res["bottleneck"]

        # 2. Bottleneck threshold binary search algorithm
        rows, cols, actual_bottleneck = solve_bottleneck_assignment(cost_matrix, pad=True)

        assert np.isclose(
            actual_bottleneck, expected_bottleneck, atol=1e-3
        ), f"Failed size {size}x{size} trial {trial}: Bottleneck {actual_bottleneck} != Brute {expected_bottleneck}"
        assert len(rows) == size
        assert len(set(rows)) == size
        assert len(set(cols)) == size


@pytest.mark.parametrize("m, n", [(4, 2), (5, 3), (6, 4), (6, 5)])
def test_rectangular_assignment_vs_brute_force(m: int, n: int):
    """Cross-check Hungarian & Bottleneck against brute force for rectangular matrices (M > N)."""
    np.random.seed(200 + m * 10 + n)

    cost_matrix = np.random.uniform(100.0, 1500.0, size=(m, n))

    bf_res = brute_force_assignment(cost_matrix)

    # 1. Min-sum check
    rows_ms, cols_ms, sum_ms = solve_min_sum_assignment(cost_matrix, pad=True)
    assert np.isclose(sum_ms, bf_res["min_sum"], atol=1e-3)
    assert len(rows_ms) == n
    assert len(set(rows_ms)) == n

    # 2. Bottleneck check
    rows_bn, cols_bn, max_bn = solve_bottleneck_assignment(cost_matrix, pad=True)
    assert np.isclose(max_bn, bf_res["bottleneck"], atol=1e-3)
    assert len(rows_bn) == n
    assert len(set(rows_bn)) == n


def test_tradeoff_matrix_min_sum_vs_bottleneck():
    """Verify that Min-Sum and Bottleneck objectives exhibit the expected trade-off."""
    # Constructed trade-off matrix:
    # Row 0: [10, 20]
    # Row 1: [5,  18]
    # Permutation (1, 0): costs [20, 5], sum = 25 (min sum), worst-case = 20
    # Permutation (0, 1): costs [10, 18], sum = 28, worst-case = 18 (min bottleneck)
    C = np.array([[10.0, 20.0], [5.0, 18.0]])

    _, _, sum_cost = solve_min_sum_assignment(C, pad=True)
    _, _, bot_cost = solve_bottleneck_assignment(C, pad=True)

    assert sum_cost == 25.0
    assert bot_cost == 18.0
    # Bottleneck strictly improves worst-case (18 < 20)
    # Min-sum strictly improves total cost (25 < 28)
    assert bot_cost < 20.0
    assert sum_cost < 28.0


def test_bengaluru_multi_accident_dispatch_pipeline():
    """Verify end-to-end multi-accident dispatch on the Bengaluru road network graph."""
    G = load_graph()
    stations = load_stations()

    from backend.graph_builder import nearest_node

    station_node_map = {}
    for s in stations:
        station_node_map[s["id"]] = int(nearest_node(G, X=s["lng"], Y=s["lat"]))

    fleet = build_ambulance_fleet(stations, station_node_map)
    assert len(fleet) == 14

    # 3 user-placed emergency accidents
    sample_accidents = [
        AccidentSite(
            id="acc-1",
            index=1,
            lat=12.9750,
            lng=77.5850,
            snapped_node_id=int(nearest_node(G, X=77.5850, Y=12.9750)),
        ),
        AccidentSite(
            id="acc-2",
            index=2,
            lat=12.9400,
            lng=77.6100,
            snapped_node_id=int(nearest_node(G, X=77.6100, Y=12.9400)),
        ),
        AccidentSite(
            id="acc-3",
            index=3,
            lat=12.9850,
            lng=77.6300,
            snapped_node_id=int(nearest_node(G, X=77.6300, Y=12.9850)),
        ),
    ]

    # Run Min-Sum Assignment
    res_min_sum = dispatch_and_route_assignment(G, fleet, sample_accidents, objective="min_sum")
    assert res_min_sum.objective == "min_sum"
    assert len(res_min_sum.assignments) == 3
    assert len(res_min_sum.unassigned_ambulances) == 11

    for a in res_min_sum.assignments:
        assert a.travel_time_sec > 0
        assert a.travel_time_min > 0
        assert a.distance_km > 0
        assert len(a.path_nodes) > 1
        assert len(a.path_coordinates) > 1
        assert a.color.startswith("#")

    # Run Bottleneck Assignment
    res_bot = dispatch_and_route_assignment(G, fleet, sample_accidents, objective="bottleneck")
    assert res_bot.objective == "bottleneck"
    assert len(res_bot.assignments) == 3
    # Minimax property: Bottleneck max time <= Min-sum max time (or equal)
    assert res_bot.max_time_sec <= res_min_sum.max_time_sec + 1e-3
