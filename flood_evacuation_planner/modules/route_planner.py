"""
Flood Evacuation Route Planner.

Master coordinator combining:
1. Flood Risk Assessment
2. Flood Road Marking
3. BFS Reachability & Fewest-Hops Analysis
4. DFS Connected Components & Stranded Zone Detection
5. Dijkstra Shortest-Path & Risk-Adjusted Optimization
6. Safe Zone Capacity & Evacuation Travel Time Estimation
"""

from typing import Dict, List, Optional, Tuple, Set, Any, NamedTuple
from data_structures.graph import Graph
from algorithms.flood_risk.risk_calculator import calculate_flood_risk, RiskAssessment, RISK_LOW
from modules.flood_marker import mark_flooded_roads, FloodMarkingSummary
from algorithms.bfs.bfs import breadth_first_search, BFSResult
from algorithms.connected_components.components import find_connected_components, ComponentAnalysisResult
from algorithms.dijkstra.dijkstra import dijkstra_shortest_path, DijkstraResult


# Evacuation Speed Estimates
SPEED_WALKING_KMH = 4.5       # Walking speed for pedestrians/families
SPEED_VEHICLE_KMH = 25.0      # Emergency convoy / urban evacuation vehicle speed under rain


class RouteOption(NamedTuple):
    """Details of a candidate evacuation path."""
    mode_name: str
    target_safe_zone: str
    target_name: str
    path: List[str]
    path_names: List[str]
    distance_km: float
    effective_risk_distance: float
    hops: int
    est_walking_minutes: float
    est_vehicle_minutes: float
    capacity: int
    traversed_roads: List[str]


class PlanningResult:
    """Complete diagnostic output of the evacuation route planner."""

    def __init__(
        self,
        start_node: str,
        start_name: str,
        risk_assessment: RiskAssessment,
        flood_summary: Optional[FloodMarkingSummary],
        component_analysis: Optional[ComponentAnalysisResult],
        bfs_result: Optional[BFSResult],
        primary_route: Optional[RouteOption],
        risk_adjusted_route: Optional[RouteOption],
        fewest_hops_route: Optional[RouteOption],
        is_stranded: bool = False,
        stranded_areas: Optional[List[str]] = None,
        accessible_shelters: Optional[List[Dict[str, Any]]] = None,
        status_message: str = "",
    ) -> None:
        self.start_node = start_node
        self.start_name = start_name
        self.risk_assessment = risk_assessment
        self.flood_summary = flood_summary
        self.component_analysis = component_analysis
        self.bfs_result = bfs_result
        self.primary_route = primary_route
        self.risk_adjusted_route = risk_adjusted_route
        self.fewest_hops_route = fewest_hops_route
        self.is_stranded = is_stranded
        self.stranded_areas = stranded_areas if stranded_areas is not None else []
        self.accessible_shelters = accessible_shelters if accessible_shelters is not None else []
        self.status_message = status_message


def _build_route_option(
    graph: Graph,
    mode_name: str,
    target_sz: str,
    path: List[str],
) -> RouteOption:
    """Helper to compute physical distances, speeds, and road names for a given path."""
    total_km = 0.0
    effective_km = 0.0
    traversed_roads: List[str] = []
    path_names: List[str] = []

    for i, node_id in enumerate(path):
        node_data = graph.get_node_data(node_id)
        path_names.append(node_data.get("name", node_id))

        if i > 0:
            u, v = path[i - 1], path[i]
            edge = graph.get_edge(u, v)
            if edge:
                total_km += edge.weight
                effective_km += edge.effective_weight
                traversed_roads.append(edge.road_id)

    target_data = graph.get_node_data(target_sz)
    capacity = int(target_data.get("capacity", 1000))
    target_name = target_data.get("name", target_sz)

    walk_mins = (total_km / SPEED_WALKING_KMH) * 60.0
    veh_mins = (total_km / SPEED_VEHICLE_KMH) * 60.0

    return RouteOption(
        mode_name=mode_name,
        target_safe_zone=target_sz,
        target_name=target_name,
        path=path,
        path_names=path_names,
        distance_km=round(total_km, 2),
        effective_risk_distance=round(effective_km, 2),
        hops=len(path) - 1,
        est_walking_minutes=round(walk_mins, 1),
        est_vehicle_minutes=round(veh_mins, 1),
        capacity=capacity,
        traversed_roads=traversed_roads,
    )


def plan_evacuation(
    graph: Graph,
    start_node: str,
    rainfall_mm_per_hr: float,
    rainfall_last_24h_mm: float = 0.0,
    water_levels: Optional[Dict[str, float]] = None,
    river_level_above_normal_m: float = 0.0,
    explain: bool = False,
) -> PlanningResult:
    """
    Execute the full end-to-end evacuation route planning pipeline.

    Steps:
    1. Assess flood risk level (LOW -> No evacuation needed).
    2. Mark flooded roads (submerged edges blocked, risky edges penalized).
    3. Run BFS for reachability and hop analysis.
    4. Run DFS connected components to detect cut-off / stranded population zones.
    5. Run Dijkstra to locate the nearest accessible safe zone.
    6. Run Risk-Adjusted Dijkstra to evaluate waterlogged path avoidance.
    """
    water_levels_dict = water_levels if water_levels is not None else {}
    max_observed_water = max(water_levels_dict.values()) if water_levels_dict else 0.0

    # STEP 1: Calculate Flood Risk Threat
    risk_res = calculate_flood_risk(
        rainfall_mm_per_hr=rainfall_mm_per_hr,
        rainfall_last_24h_mm=rainfall_last_24h_mm,
        max_water_level_m=max_observed_water,
        river_level_above_normal_m=river_level_above_normal_m,
    )

    start_data = graph.get_node_data(start_node)
    start_name = start_data.get("name", start_node)

    # If risk is LOW and no water depth danger exists -> No evacuation needed
    if not risk_res.is_dangerous:
        return PlanningResult(
            start_node=start_node,
            start_name=start_name,
            risk_assessment=risk_res,
            flood_summary=None,
            component_analysis=None,
            bfs_result=None,
            primary_route=None,
            risk_adjusted_route=None,
            fewest_hops_route=None,
            is_stranded=False,
            status_message="No evacuation needed: Rainfall and water levels are within normal municipal drainage limits.",
        )

    # STEP 2: Mark Flooded Roads on the Graph
    flood_summary = mark_flooded_roads(graph, water_levels_dict)

    # Check if start node is already inside a designated safe zone
    if start_data.get("is_safe_zone", False):
        self_route = _build_route_option(graph, "Shelter in Place", start_node, [start_node])
        return PlanningResult(
            start_node=start_node,
            start_name=start_name,
            risk_assessment=risk_res,
            flood_summary=flood_summary,
            component_analysis=None,
            bfs_result=None,
            primary_route=self_route,
            risk_adjusted_route=self_route,
            fewest_hops_route=self_route,
            is_stranded=False,
            status_message=f"Location '{start_name}' is already an established emergency safe shelter. Shelter in place.",
        )

    # STEP 3: BFS for Reachability
    bfs_res = breadth_first_search(graph, start_node=start_node, include_blocked=False, explain=explain)

    # STEP 4: DFS Connected Components & Stranded Zone Detection
    comp_res = find_connected_components(graph, include_blocked=False)
    is_user_stranded = comp_res.is_node_stranded(start_node)

    all_safe_zones = graph.get_safe_zones()
    reachable_safe_zones = [sz for sz in all_safe_zones if sz in bfs_res.reachable_nodes]

    # If user is in a stranded component with zero reachable shelters:
    if is_user_stranded or not reachable_safe_zones:
        # Collect human-readable names of all stranded locations in user's pocket
        user_cluster: Set[str] = set()
        for c in comp_res.components:
            if start_node in c:
                user_cluster = c
                break

        stranded_area_names = [
            f"{node_id} ({graph.get_node_data(node_id).get('name', node_id)})"
            for node_id in sorted(list(user_cluster))
        ]

        return PlanningResult(
            start_node=start_node,
            start_name=start_name,
            risk_assessment=risk_res,
            flood_summary=flood_summary,
            component_analysis=comp_res,
            bfs_result=bfs_res,
            primary_route=None,
            risk_adjusted_route=None,
            fewest_hops_route=None,
            is_stranded=True,
            stranded_areas=stranded_area_names,
            status_message=(
                f"NO SAFE ROUTE - REQUEST RESCUE: Location '{start_name}' is cut off by flooded roads! "
                f"All road corridors to emergency shelters are submerged. "
                f"Emergency airlift / boat evacuation requested for {len(stranded_area_names)} stranded area(s)."
            ),
        )

    # STEP 5: Dijkstra for Metric Shortest Route
    dijkstra_metric = dijkstra_shortest_path(
        graph,
        start_node=start_node,
        target_nodes=set(reachable_safe_zones),
        risk_adjusted=False,
        explain=explain,
    )

    # Pick the closest reachable safe zone by physical distance (km)
    best_sz_metric: Optional[str] = None
    min_dist_km = float("inf")
    for sz in reachable_safe_zones:
        d = dijkstra_metric.get_distance(sz)
        if d < min_dist_km:
            min_dist_km = d
            best_sz_metric = sz

    assert best_sz_metric is not None
    path_metric = dijkstra_metric.reconstruct_path(best_sz_metric)
    assert path_metric is not None
    primary_route = _build_route_option(graph, "Shortest Safe Route (Dijkstra)", best_sz_metric, path_metric)

    # STEP 6: Risk-Adjusted Dijkstra Route (avoids risky waterlogged roads when alternative exists)
    dijkstra_risk = dijkstra_shortest_path(
        graph,
        start_node=start_node,
        target_nodes=set(reachable_safe_zones),
        risk_adjusted=True,
        explain=False,
    )
    best_sz_risk: Optional[str] = None
    min_risk_dist = float("inf")
    for sz in reachable_safe_zones:
        d = dijkstra_risk.get_distance(sz)
        if d < min_risk_dist:
            min_risk_dist = d
            best_sz_risk = sz

    risk_adj_route = None
    if best_sz_risk is not None:
        path_risk = dijkstra_risk.reconstruct_path(best_sz_risk)
        if path_risk:
            risk_adj_route = _build_route_option(graph, "Risk-Penalized Safe Route", best_sz_risk, path_risk)

    # STEP 7: BFS Fewest Hops / Intersections Route
    fewest_hops_route = None
    best_sz_hops = None
    min_hops = 999999
    for sz in reachable_safe_zones:
        h = bfs_res.hop_distances.get(sz, 999999)
        if h < min_hops:
            min_hops = h
            best_sz_hops = sz

    if best_sz_hops:
        path_hops = bfs_res.reconstruct_path(best_sz_hops)
        if path_hops:
            fewest_hops_route = _build_route_option(graph, "Fewest Intersections Route (BFS)", best_sz_hops, path_hops)

    # Compile Accessible Shelters Overview
    accessible_shelters = []
    for sz in reachable_safe_zones:
        sz_data = graph.get_node_data(sz)
        dist_km = dijkstra_metric.get_distance(sz)
        accessible_shelters.append({
            "id": sz,
            "name": sz_data.get("name", sz),
            "distance_km": round(dist_km, 2),
            "capacity": sz_data.get("capacity", 1000),
            "elevation_m": sz_data.get("elevation_m", 0.0),
            "type": sz_data.get("type", "shelter"),
        })

    accessible_shelters.sort(key=lambda x: x["distance_km"])

    return PlanningResult(
        start_node=start_node,
        start_name=start_name,
        risk_assessment=risk_res,
        flood_summary=flood_summary,
        component_analysis=comp_res,
        bfs_result=bfs_res,
        primary_route=primary_route,
        risk_adjusted_route=risk_adj_route,
        fewest_hops_route=fewest_hops_route,
        is_stranded=False,
        accessible_shelters=accessible_shelters,
        status_message=f"Optimal evacuation path computed to {primary_route.target_name} ({primary_route.distance_km} km).",
    )


if __name__ == "__main__":
    from utils.loader import create_sample_city_graph, create_sample_rainfall_data
    g = create_sample_city_graph()
    rf = create_sample_rainfall_data()

    print("Planning evacuation from Downtown (LOC_01)...")
    res = plan_evacuation(
        graph=g,
        start_node="LOC_01",
        rainfall_mm_per_hr=rf["rainfall_mm_per_hr"],
        rainfall_last_24h_mm=rf["rainfall_last_24h_mm"],
        water_levels=rf["water_levels_by_road"],
        river_level_above_normal_m=rf["river_level_above_normal_m"],
    )

    print("\nStatus:", res.status_message)
    print("Risk Level:", res.risk_assessment.risk_level, f"(Score: {res.risk_assessment.score})")
    if res.primary_route:
        print(f"Primary Route: {' -> '.join(res.primary_route.path)}")
        print(f"Distance: {res.primary_route.distance_km} km")
        print(f"Est Walking Time: {res.primary_route.est_walking_minutes} mins")
        print(f"Est Vehicle Time: {res.primary_route.est_vehicle_minutes} mins")
