"""
Flood Marker Module.

Dynamically inspects environmental water depth measurements for each road in the graph,
flags impassable segments as blocked, and applies penalty multipliers to waterlogged risky roads.
"""

from typing import Dict, List, Tuple, Set, NamedTuple, Any
from data_structures.graph import Graph, Edge


# Standard hydrological thresholds in meters
DEFAULT_FLOOD_BLOCK_THRESHOLD_M = 0.50   # >= 0.50m (approx 20 inches) stops standard vehicular travel
DEFAULT_RISKY_THRESHOLD_M = 0.20         # 0.20m to 0.49m: standing water, hazardous speed reduction
DEFAULT_RISK_PENALTY_MULTIPLIER = 2.5    # Multiplier applied to travel distance in risk-adjusted Dijkstra


class FloodMarkingSummary(NamedTuple):
    """Summary of road classification changes."""
    blocked_roads: List[Edge]
    risky_roads: List[Edge]
    normal_roads: List[Edge]
    max_water_level_m: float
    total_roads: int


def mark_flooded_roads(
    graph: Graph,
    water_levels: Dict[str, float],
    block_threshold_m: float = DEFAULT_FLOOD_BLOCK_THRESHOLD_M,
    risky_threshold_m: float = DEFAULT_RISKY_THRESHOLD_M,
    penalty_multiplier: float = DEFAULT_RISK_PENALTY_MULTIPLIER,
) -> FloodMarkingSummary:
    """
    Apply water level readings to all graph edges and update their traversal status.

    Args:
        graph: Custom Graph instance to update.
        water_levels: Mapping of road_id or (u, v) pair to water depth in meters.
        block_threshold_m: Water depth at which road becomes blocked (impassable).
        risky_threshold_m: Water depth at which road is flagged risky with penalty multiplier.
        penalty_multiplier: Factor multiplied to distance weight for risky roads.

    Returns:
        FloodMarkingSummary tuple listing classified edges and max recorded depth.
    """
    # Reset any prior flood markings
    graph.reset_all_blocks()

    blocked_edges: List[Edge] = []
    risky_edges: List[Edge] = []
    normal_edges: List[Edge] = []
    max_depth = 0.0

    all_unique_edges = graph.get_all_edges(unique_undirected=True)

    for edge in all_unique_edges:
        # Check water level by road_id or by endpoint names
        water_depth = 0.0
        if edge.road_id in water_levels:
            water_depth = water_levels[edge.road_id]
        elif (edge.u, edge.v) in water_levels:
            water_depth = water_levels[(edge.u, edge.v)]
        elif (edge.v, edge.u) in water_levels:
            water_depth = water_levels[(edge.v, edge.u)]
        elif "baseline_water_level" in edge.attributes:
            water_depth = float(edge.attributes["baseline_water_level"])

        if water_depth > max_depth:
            max_depth = water_depth

        # Update forward edge
        edge_fwd = graph.get_edge(edge.u, edge.v)
        edge_rev = graph.get_edge(edge.v, edge.u)
        pair = [e for e in (edge_fwd, edge_rev) if e is not None]

        for e in pair:
            e.water_level_m = water_depth
            if water_depth >= block_threshold_m:
                e.is_blocked = True
                e.is_risky = False
                e.effective_weight = float("inf")
            elif water_depth >= risky_threshold_m:
                e.is_blocked = False
                e.is_risky = True
                e.effective_weight = round(e.weight * penalty_multiplier, 2)
            else:
                e.is_blocked = False
                e.is_risky = False
                e.effective_weight = e.weight

        if water_depth >= block_threshold_m:
            blocked_edges.append(edge)
        elif water_depth >= risky_threshold_m:
            risky_edges.append(edge)
        else:
            normal_edges.append(edge)

    return FloodMarkingSummary(
        blocked_roads=blocked_edges,
        risky_roads=risky_edges,
        normal_roads=normal_edges,
        max_water_level_m=max_depth,
        total_roads=len(all_unique_edges),
    )


if __name__ == "__main__":
    g = Graph()
    g.add_edge("A", "B", 2.0, road_id="RD_01")
    g.add_edge("B", "C", 3.0, road_id="RD_02")
    g.add_edge("C", "D", 1.5, road_id="RD_03")

    readings = {
        "RD_01": 0.10,  # normal
        "RD_02": 0.35,  # risky
        "RD_03": 0.85,  # blocked
    }
    summary = mark_flooded_roads(g, readings)
    print("Flood Marking Summary:")
    print(f"Total Roads: {summary.total_roads}")
    print(f"Blocked: {len(summary.blocked_roads)} -> {[e.road_id for e in summary.blocked_roads]}")
    print(f"Risky:   {len(summary.risky_roads)} -> {[e.road_id for e in summary.risky_roads]}")
    print(f"Normal:  {len(summary.normal_roads)} -> {[e.road_id for e in summary.normal_roads]}")
