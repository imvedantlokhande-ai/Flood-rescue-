"""
Multi-Timestep Flood Escalation Simulation Module.

Simulates progressive rainfall and rising flood levels over sequential time intervals
(e.g., T+0h through T+4h), re-evaluating road submersion, network partitioning,
and evacuation route viability at each step.
"""

from typing import Dict, List, Any, NamedTuple
from data_structures.graph import Graph
from modules.route_planner import plan_evacuation, PlanningResult


class SimulationStepReport(NamedTuple):
    """Snapshot report for a single simulation timestep."""
    step_index: int
    time_label: str
    rainfall_mm_per_hr: float
    rainfall_last_24h_mm: float
    description: str
    risk_level: str
    blocked_roads_count: int
    blocked_road_ids: List[str]
    is_stranded: bool
    target_shelter_name: str
    route_distance_km: float
    route_path: List[str]
    status_summary: str


def run_flood_simulation(
    base_graph: Graph,
    start_node: str,
    rainfall_scenario: Dict[str, Any],
) -> List[SimulationStepReport]:
    """
    Run multi-phase flood escalation simulation.

    Args:
        base_graph: Initial unflooded city graph.
        start_node: Evacuee's starting location ID.
        rainfall_scenario: Scenario dictionary loaded from rainfall_data.json.

    Returns:
        List of SimulationStepReport objects for each time step.
    """
    steps_data = rainfall_scenario.get("simulation_timesteps", [])
    base_water_levels = rainfall_scenario.get("water_levels_by_road", {})
    river_swell_base = rainfall_scenario.get("river_level_above_normal_m", 2.0)

    reports: List[SimulationStepReport] = []

    for step_info in steps_data:
        step_idx = step_info["step"]
        time_label = step_info["time_label"]
        rain_hr = float(step_info["rainfall_mm_per_hr"])
        rain_24 = float(step_info["rainfall_last_24h_mm"])
        multiplier = float(step_info.get("water_level_multiplier", 1.0))
        desc = step_info.get("description", "")

        # Compute scaled water level for every road at this timestep
        current_water_levels: Dict[str, float] = {}
        for road_id, base_depth in base_water_levels.items():
            current_water_levels[road_id] = round(base_depth * multiplier, 2)

        river_swell = round(river_swell_base * multiplier, 2)

        # Clone graph to run independent simulation step
        step_graph = base_graph.clone()

        plan_res = plan_evacuation(
            graph=step_graph,
            start_node=start_node,
            rainfall_mm_per_hr=rain_hr,
            rainfall_last_24h_mm=rain_24,
            water_levels=current_water_levels,
            river_level_above_normal_m=river_swell,
            explain=False,
        )

        blocked_ids = []
        if plan_res.flood_summary:
            blocked_ids = [e.road_id for e in plan_res.flood_summary.blocked_roads]

        target_name = "N/A"
        dist_km = 0.0
        path = []

        if plan_res.primary_route:
            target_name = plan_res.primary_route.target_name
            dist_km = plan_res.primary_route.distance_km
            path = plan_res.primary_route.path

        reports.append(
            SimulationStepReport(
                step_index=step_idx,
                time_label=time_label,
                rainfall_mm_per_hr=rain_hr,
                rainfall_last_24h_mm=rain_24,
                description=desc,
                risk_level=plan_res.risk_assessment.risk_level,
                blocked_roads_count=len(blocked_ids),
                blocked_road_ids=blocked_ids,
                is_stranded=plan_res.is_stranded,
                target_shelter_name=target_name,
                route_distance_km=dist_km,
                route_path=path,
                status_summary=plan_res.status_message,
            )
        )

    return reports


if __name__ == "__main__":
    from utils.loader import create_sample_city_graph, create_sample_rainfall_data
    g = create_sample_city_graph()
    rf = create_sample_rainfall_data()

    print("Running 5-step simulation for Downtown (LOC_01):")
    results = run_flood_simulation(g, "LOC_01", rf)
    for rep in results:
        print(f"\n[{rep.time_label}] Risk: {rep.risk_level} | Blocked Roads: {rep.blocked_roads_count}")
        print(f"  Description: {rep.description}")
        if rep.is_stranded:
            print("  ALERT: Evacuee is stranded! No open road to shelters.")
        else:
            print(f"  Route to {rep.target_shelter_name}: {' -> '.join(rep.route_path)} ({rep.route_distance_km} km)")
