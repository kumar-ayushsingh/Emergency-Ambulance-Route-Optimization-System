r"""Emergency Hospital Triage & Facility Scoring Engine.

Academic Context:
Discrete Mathematics · Multi-Criteria Facility Selection · Operations Research

Problem Formulation:
Given an emergency accident site A \in V, a set of candidate hospitals H = {H_1, ..., H_m},
an emergency trauma requirement \tau \in {general, major_trauma}, and operational capacity
states S(H_i) \in {normal, busy, full}.

Facility Evaluation Objective:
    Score(H_i) = T(A, H_i) + P_trauma(H_i, \tau) + P_load(H_i)

Where:
- T(A, H_i): Shortest-path driving time in seconds from incident A to hospital gate H_i,
  computed via Dijkstra's algorithm under the active time-of-day traffic model.
- P_trauma(H_i, \tau): Clinical trauma capability mismatch penalty:
    - If \tau == "major_trauma":
        - Level-1 Trauma Center: P_trauma = 0.0 s (0.0 min)
        - Level-2 / General Hospital: P_trauma = 900.0 s (15.0 min transfer delay risk)
    - If \tau == "general":
        - Any Trauma Level: P_trauma = 0.0 s (0.0 min)
- P_load(H_i): Operational congestion & bed availability delay penalty:
    - "normal": P_load = 0.0 s (immediate triage bay admission)
    - "busy":   P_load = 480.0 s (8.0 min emergency queue & initial resuscitation delay)
    - "full":   P_load = 1800.0 s (30.0 min ambulance offload delay / diversion risk)

Decision Rule:
    H* = \arg\min_{H_i \in H} Score(H_i)
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from backend.algorithms.dijkstra import dijkstra_shortest_path
from backend.algorithms.traffic import get_weight_attribute_for_period

logger = logging.getLogger(__name__)

# Standard penalty values (in seconds)
DEFAULT_PENALTIES = {
    "trauma": {
        "major_trauma": {
            "Level-1": 0.0,
            "Level-2": 900.0,  # 15 min penalty for secondary transfer
        },
        "general": {
            "Level-1": 0.0,
            "Level-2": 0.0,
        },
    },
    "load": {
        "normal": 0.0,
        "busy": 480.0,  # 8 min triage delay
        "full": 1800.0,  # 30 min offload / diversion delay
    },
}


@dataclass
class HospitalScoreDetail:
    """Detailed score breakdown for an evaluated hospital."""

    rank: int
    id: str
    name: str
    short_name: str
    trauma_level: str
    status: str
    travel_time_sec: float
    travel_time_min: float
    distance_m: float
    distance_km: float
    p_trauma_sec: float
    p_trauma_min: float
    p_load_sec: float
    p_load_min: float
    score_sec: float
    score_min: float
    is_winner: bool
    is_nearest: bool
    path: List[int]


def compute_hospital_penalties(
    trauma_level: str,
    status: str,
    trauma_requirement: str = "general",
    penalties_config: Optional[Dict[str, Any]] = None,
) -> Tuple[float, float]:
    """Calculate clinical trauma and operational load penalties in seconds.

    Args:
        trauma_level: Hospital classification ('Level-1' or 'Level-2').
        status: Operational capacity status ('normal', 'busy', 'full').
        trauma_requirement: Incident trauma severity ('general' or 'major_trauma').
        penalties_config: Optional override configuration dictionary.

    Returns:
        Tuple of (p_trauma_sec, p_load_sec).
    """
    cfg = penalties_config or DEFAULT_PENALTIES

    # Normalize requirement
    req_key = "major_trauma" if "major" in trauma_requirement.lower() else "general"

    # Trauma penalty
    trauma_dict = cfg.get("trauma", {}).get(req_key, {})
    level_key = "Level-1" if "1" in str(trauma_level) else "Level-2"
    p_trauma = float(trauma_dict.get(level_key, 0.0))

    # Load penalty
    status_dict = cfg.get("load", {})
    status_key = str(status).lower()
    p_load = float(status_dict.get(status_key, 0.0))

    return p_trauma, p_load


def evaluate_hospital_scores(
    G: nx.MultiDiGraph,
    accident_node: int,
    hospitals: List[Dict[str, Any]],
    hospital_node_map: Dict[str, int],
    trauma_requirement: str = "general",
    hospital_statuses: Optional[Dict[str, str]] = None,
    time_of_day: str = "off_peak",
) -> Tuple[List[HospitalScoreDetail], Optional[HospitalScoreDetail], Optional[HospitalScoreDetail], str]:
    """Evaluate and rank all candidate hospitals from accident site.

    Calculates:
        Score = travel_time + P_trauma + P_load

    Args:
        G: Directed road graph with travel time weights.
        accident_node: Graph node ID where the incident occurred.
        hospitals: List of hospital metadata dicts.
        hospital_node_map: Mapping hospital_id -> graph_node.
        trauma_requirement: 'general' or 'major_trauma'.
        hospital_statuses: Optional dict overriding hospital statuses.
        time_of_day: Active traffic period ('off_peak', 'morning_peak', 'evening_peak', 'night').

    Returns:
        Tuple of:
        - ranked_hospitals: List of HospitalScoreDetail sorted by score ascending.
        - winner: Top-ranked HospitalScoreDetail.
        - nearest: HospitalScoreDetail with minimum pure travel time.
        - winner_explanation: Text explanation detailing why the winner was selected.
    """
    weight_attr = get_weight_attribute_for_period(time_of_day)
    statuses = hospital_statuses or {}

    evaluations: List[Dict[str, Any]] = []

    for h in hospitals:
        h_id = h["id"]
        h_node = hospital_node_map.get(h_id)
        if h_node is None or h_node not in G:
            continue

        current_status = str(statuses.get(h_id, h.get("status", "normal"))).lower()
        trauma_level = h.get("trauma_level", "Level-2")

        # Run Dijkstra to compute road travel time
        route_res = dijkstra_shortest_path(G, source=accident_node, target=h_node, weight=weight_attr)
        if route_res is None:
            # Unreachable
            travel_time_sec = float("inf")
            dist_m = float("inf")
            path = []
        else:
            travel_time_sec = route_res.cost
            dist_m = route_res.distance
            path = route_res.path

        p_trauma, p_load = compute_hospital_penalties(
            trauma_level=trauma_level,
            status=current_status,
            trauma_requirement=trauma_requirement,
        )

        total_score_sec = travel_time_sec + p_trauma + p_load

        evaluations.append(
            {
                "id": h_id,
                "name": h["name"],
                "short_name": h.get("short_name", h["name"]),
                "trauma_level": trauma_level,
                "status": current_status,
                "travel_time_sec": travel_time_sec,
                "travel_time_min": travel_time_sec / 60.0 if travel_time_sec != float("inf") else float("inf"),
                "distance_m": dist_m,
                "distance_km": dist_m / 1000.0 if dist_m != float("inf") else float("inf"),
                "p_trauma_sec": p_trauma,
                "p_trauma_min": p_trauma / 60.0,
                "p_load_sec": p_load,
                "p_load_min": p_load / 60.0,
                "score_sec": total_score_sec,
                "score_min": total_score_sec / 60.0 if total_score_sec != float("inf") else float("inf"),
                "path": path,
            }
        )

    if not evaluations:
        return [], None, None, "No candidate hospitals available."

    # Identify nearest hospital by pure travel time
    nearest_item = min(evaluations, key=lambda x: x["travel_time_sec"])
    nearest_id = nearest_item["id"]

    # Sort all hospitals by composite score ascending (Rank 1 = Winner)
    evaluations.sort(key=lambda x: x["score_sec"])

    winner_id = evaluations[0]["id"]

    # Convert to structured dataclasses
    ranked: List[HospitalScoreDetail] = []
    winner_detail: Optional[HospitalScoreDetail] = None
    nearest_detail: Optional[HospitalScoreDetail] = None

    for idx, item in enumerate(evaluations, start=1):
        is_win = item["id"] == winner_id
        is_near = item["id"] == nearest_id

        detail = HospitalScoreDetail(
            rank=idx,
            id=item["id"],
            name=item["name"],
            short_name=item["short_name"],
            trauma_level=item["trauma_level"],
            status=item["status"],
            travel_time_sec=round(item["travel_time_sec"], 2),
            travel_time_min=round(item["travel_time_min"], 2),
            distance_m=round(item["distance_m"], 1),
            distance_km=round(item["distance_km"], 2),
            p_trauma_sec=round(item["p_trauma_sec"], 2),
            p_trauma_min=round(item["p_trauma_min"], 2),
            p_load_sec=round(item["p_load_sec"], 2),
            p_load_min=round(item["p_load_min"], 2),
            score_sec=round(item["score_sec"], 2),
            score_min=round(item["score_min"], 2),
            is_winner=is_win,
            is_nearest=is_near,
            path=item["path"],
        )
        ranked.append(detail)
        if is_win:
            winner_detail = detail
        if is_near:
            nearest_detail = detail

    # Generate explanatory rationale
    explanation = generate_scoring_explanation(winner_detail, nearest_detail, trauma_requirement)

    return ranked, winner_detail, nearest_detail, explanation


def generate_scoring_explanation(
    winner: Optional[HospitalScoreDetail],
    nearest: Optional[HospitalScoreDetail],
    trauma_requirement: str,
) -> str:
    """Generate textual explanation detailing why the winning hospital beat the nearest facility.

    Args:
        winner: Winning HospitalScoreDetail.
        nearest: Nearest HospitalScoreDetail.
        trauma_requirement: 'general' or 'major_trauma'.

    Returns:
        Formatted explanation string.
    """
    if winner is None or nearest is None:
        return "Unable to determine winner or nearest hospital."

    is_major = "major" in trauma_requirement.lower()
    req_label = "Major Trauma (Level-1 Required)" if is_major else "General Emergency"

    if winner.id == nearest.id:
        return (
            f"**{winner.short_name}** is the optimal destination across all criteria. "
            f"It is both the nearest hospital ({winner.travel_time_min:.1f} min travel time, {winner.distance_km:.2f} km) "
            f"and fully qualified with zero operational delay (Status: {winner.status.upper()}, "
            f"Trauma: {winner.trauma_level}). Total triage score: **{winner.score_min:.1f} min**."
        )

    # Winner beat nearest hospital!
    time_diff_min = winner.travel_time_min - nearest.travel_time_min
    score_advantage_min = nearest.score_min - winner.score_min

    reasons = []
    if nearest.p_load_min > 0:
        reasons.append(
            f"its **'{nearest.status.upper()}'** status incurs an operational triage delay of **+{nearest.p_load_min:.1f} min**"
        )
    if nearest.p_trauma_min > 0:
        reasons.append(
            f"being a **{nearest.trauma_level}** facility incurs a clinical mismatch penalty of **+{nearest.p_trauma_min:.1f} min** for {req_label}"
        )

    penalty_str = " and ".join(reasons) if reasons else "cumulative triage penalties"

    return (
        f"**{winner.short_name} (Score: {winner.score_min:.1f} min)** won over nearest facility "
        f"**{nearest.short_name} (Score: {nearest.score_min:.1f} min)**. "
        f"Although {nearest.short_name} is {abs(time_diff_min):.1f} min closer by road ({nearest.travel_time_min:.1f} min vs {winner.travel_time_min:.1f} min), "
        f"{penalty_str}. "
        f"Routing to {winner.short_name} delivers a net time savings of **{score_advantage_min:.1f} minutes** in effective emergency medical intervention."
    )


def compare_offpeak_vs_peak_route(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
) -> Dict[str, Any]:
    """Compare optimal shortest path under off-peak vs peak traffic conditions.

    Demonstrates how congestion on arterial corridors causes the optimal Dijkstra route
    to diverge and select alternate bypass roads.

    Args:
        G: Road network graph with attached travel_time_off_peak and travel_time_evening_peak.
        source: Origin node ID.
        target: Destination node ID.

    Returns:
        Dictionary with route details, path differences, and travel time comparison.
    """
    res_offpeak = dijkstra_shortest_path(G, source, target, weight="travel_time_off_peak")
    res_peak = dijkstra_shortest_path(G, source, target, weight="travel_time_evening_peak")

    if res_offpeak is None or res_peak is None:
        return {
            "diverged": False,
            "message": "One or both routes are unreachable.",
        }

    is_divergent = res_offpeak.path != res_peak.path

    # Compute what off-peak route would take if driven during peak hours
    offpeak_path_time_at_peak = 0.0
    for i in range(len(res_offpeak.path) - 1):
        u, v = res_offpeak.path[i], res_offpeak.path[i + 1]
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            if G.is_multigraph():
                min_w = min(d.get("travel_time_evening_peak", d.get("travel_time", 1.0) * 1.8) for d in edge_data.values())
            else:
                min_w = edge_data.get("travel_time_evening_peak", edge_data.get("travel_time", 1.0) * 1.8)
            offpeak_path_time_at_peak += min_w

    savings_sec = max(0.0, offpeak_path_time_at_peak - res_peak.cost)

    return {
        "diverged": is_divergent,
        "source": source,
        "target": target,
        "off_peak": {
            "path": res_offpeak.path,
            "travel_time_sec": round(res_offpeak.cost, 2),
            "travel_time_min": round(res_offpeak.cost / 60.0, 2),
            "distance_m": round(res_offpeak.distance, 1),
            "distance_km": round(res_offpeak.distance / 1000.0, 2),
            "time_if_driven_at_peak_sec": round(offpeak_path_time_at_peak, 2),
            "time_if_driven_at_peak_min": round(offpeak_path_time_at_peak / 60.0, 2),
        },
        "peak": {
            "path": res_peak.path,
            "travel_time_sec": round(res_peak.cost, 2),
            "travel_time_min": round(res_peak.cost / 60.0, 2),
            "distance_m": round(res_peak.distance, 1),
            "distance_km": round(res_peak.distance / 1000.0, 2),
        },
        "peak_bypass_savings_sec": round(savings_sec, 2),
        "peak_bypass_savings_min": round(savings_sec / 60.0, 2),
        "explanation": (
            f"During off-peak hours, the ambulance follows major arterials ({res_offpeak.cost / 60.0:.1f} min). "
            f"During evening peak traffic, arterial congestion would increase that path to {offpeak_path_time_at_peak / 60.0:.1f} min. "
            f"The dynamic router identifies a bypass route taking secondary streets ({res_peak.cost / 60.0:.1f} min), "
            f"saving {savings_sec / 60.0:.1f} minutes over staying on the congested arterial."
            if is_divergent
            else "Both off-peak and peak conditions follow the identical topological corridor."
        ),
    }
