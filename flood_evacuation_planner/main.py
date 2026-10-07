"""
Main CLI Entry Point for Flood Evacuation Route Planner.

Runs the complete data structures & algorithms pipeline:
1. Hydrological Telemetry & Flood Risk Scoring
2. Graph Modeling & Road Inundation Blocking
3. BFS Reachability & Fewest Intersections Route
4. DFS Connected Components & Stranded Zone Rescue Alerts
5. Dijkstra Shortest Safe Path & Risk-Penalized Comparison
6. Travel Time Estimations & Safe Zone Capacity
7. Step-by-Step Explain Mode for DSA Viva & Examinations
"""

import sys
import os
import argparse
from typing import Optional, List, Dict, Any

# Ensure project root in module lookup path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data_structures.graph import Graph
from utils.loader import load_city_graph, load_rainfall_data
from modules.route_planner import plan_evacuation, PlanningResult
from modules.simulation import run_flood_simulation
from utils.visualizer import render_graph_matplotlib, print_ascii_graph


BANNER = """
======================================================================
     FLOOD EVACUATION ROUTE PLANNER (DSA IMPLEMENTATION)
     Municipal Emergency Navigation & Graph Cut-Off Analysis System
======================================================================
"""


def format_table_row(col1: str, col2: str, col3: str = "", width1: int = 24, width2: int = 28) -> str:
    return f"  {col1.ljust(width1)} | {col2.ljust(width2)} | {col3}"


def display_explain_trace(plan_result: PlanningResult) -> None:
    """Print step-by-step trace of scratch DSA operations (Queue, Stack, MinHeap)."""
    print("\n" + "=" * 70)
    print("      STEP-BY-STEP DSA EXPLAIN MODE (VIVA / DEFENSE LOGS)")
    print("=" * 70)

    # 1. BFS CustomQueue Trace
    if plan_result.bfs_result and plan_result.bfs_result.step_logs:
        print("\n[1] BREADTH-FIRST SEARCH (Custom Singly Linked-List Queue Trace):")
        print("    " + "-" * 62)
        for log in plan_result.bfs_result.step_logs[:12]:
            step_no = log["step"]
            action = log["action"]
            queue_str = str(log["queue_state"])
            print(f"    Step {step_no:2d} [{action}]: {log['explanation']}")
        if len(plan_result.bfs_result.step_logs) > 12:
            print(f"    ... [{len(plan_result.bfs_result.step_logs) - 12} additional BFS steps omitted for brevity]")

    # 2. Dijkstra Custom MinHeap Trace
    if plan_result.primary_route and hasattr(plan_result, "bfs_result"):
        # Run small explain Dijkstra to extract trace
        from algorithms.dijkstra.dijkstra import dijkstra_shortest_path
        dijk_explain = dijkstra_shortest_path(
            graph=load_city_graph(os.path.join(PROJECT_ROOT, "data", "city_graph.json")),
            start_node=plan_result.start_node,
            explain=True,
        )
        print("\n[2] DIJKSTRA'S ALGORITHM (Custom Binary MinHeap & Priority Sift Trace):")
        print("    " + "-" * 62)
        for log in dijk_explain.heap_trace[:12]:
            step_no = log["step"]
            action = log["action"]
            node = log.get("settled_node", "")
            dist = log.get("dist", 0.0)
            heap_items = log.get("heap_snapshot", [])
            print(f"    Step {step_no:2d} [{action}]: Settled '{node}' at {dist:.2f} km. MinHeap: {heap_items[:4]}")
        if len(dijk_explain.heap_trace) > 12:
            print(f"    ... [{len(dijk_explain.heap_trace) - 12} additional Dijkstra steps omitted for brevity]")

    print("=" * 70 + "\n")


def run_full_pipeline(
    start_node: str = "LOC_01",
    explain: bool = False,
    compare: bool = False,
    visualize: bool = False,
) -> PlanningResult:
    """Execute the primary evacuation route planning pipeline."""
    graph_path = os.path.join(PROJECT_ROOT, "data", "city_graph.json")
    rain_path = os.path.join(PROJECT_ROOT, "data", "rainfall_data.json")

    graph = load_city_graph(graph_path)
    rainfall_info = load_rainfall_data(rain_path)

    rain_hr = float(rainfall_info.get("rainfall_mm_per_hr", 45.0))
    rain_24 = float(rainfall_info.get("rainfall_last_24h_mm", 120.0))
    water_readings = rainfall_info.get("water_levels_by_road", {})
    river_swell = float(rainfall_info.get("river_level_above_normal_m", 2.0))

    print(BANNER)
    print(f"Scenario: {rainfall_info.get('scenario_name', 'Severe Flash Flood')}")
    print(f"Origin Location: {start_node} ({graph.get_node_data(start_node).get('name', 'Unknown')})")
    print(f"Telemetry: {rain_hr} mm/hr current rain | {rain_24} mm in past 24h | River swell: +{river_swell}m")
    print("-" * 70)

    # Execute core planning module
    plan_result = plan_evacuation(
        graph=graph,
        start_node=start_node,
        rainfall_mm_per_hr=rain_hr,
        rainfall_last_24h_mm=rain_24,
        water_levels=water_readings,
        river_level_above_normal_m=river_swell,
        explain=explain,
    )

    # 1. Print Risk Assessment
    risk = plan_result.risk_assessment
    print(f"\n[PHASE 1] FLOOD RISK ASSESSMENT: {risk.risk_level} (Score: {risk.score}/100)")
    print(f"Summary: {risk.summary}")
    for r in risk.reasons:
        print(f"  * {r}")

    if not risk.is_dangerous:
        print("\n>>> CONCLUSION: No evacuation needed. Safe to shelter at current location.")
        return plan_result

    # 2. Road Network Conditions
    if plan_result.flood_summary:
        fs = plan_result.flood_summary
        print(f"\n[PHASE 2] ROAD INUNDATION ANALYSIS:")
        print(f"  * Total Road Segments Analyzed: {fs.total_roads}")
        print(f"  * Impassable / Flooded Roads:   {len(fs.blocked_roads)} (depth >= 0.50m)")
        print(f"  * Waterlogged / Risky Roads:    {len(fs.risky_roads)} (depth 0.20m - 0.49m)")
        print(f"  * Open Clear Roads:             {len(fs.normal_roads)}")
        print(f"  * Peak Road Water Depth:        {fs.max_water_level_m:.2f} meters")

    # 3. Component & Stranded Check
    if plan_result.is_stranded:
        print("\n" + "!" * 70)
        print("  CRITICAL EMERGENCY ALERT: NO SAFE ROAD ROUTE EXISTS!")
        print("  The evacuee's location is inside a completely cut-off / stranded zone.")
        print("  All bridges and road corridors connecting to shelters are submerged.")
        print("  Immediate water rescue / helicopter airlift dispatch required.")
        print("!" * 70)
        print("\nCut-off Communities in This Stranded Component:")
        for area in plan_result.stranded_areas:
            print(f"  - {area}")
        return plan_result

    # 4. Primary Route
    route = plan_result.primary_route
    if route:
        print(f"\n[PHASE 3] RECOMMENDED EVACUATION ROUTE (DIJKSTRA MIN-HEAP):")
        print(f"  * Destination Shelter:   {route.target_name} ({route.target_safe_zone})")
        print(f"  * Shelter Capacity:      {route.capacity} people")
        print(f"  * Metric Distance:       {route.distance_km:.2f} km ({route.hops} road intersections)")
        print(f"  * Estimated Evac Time:   Walking: {route.est_walking_minutes:.1f} mins | Vehicle: {route.est_vehicle_minutes:.1f} mins")
        print(f"  * Traversed Route Path:")
        print("    " + "  ===>  ".join(route.path))
        print("    " + "  ===>  ".join(route.path_names))

    # 5. Route Comparison Mode
    if compare and plan_result.primary_route:
        print("\n[PHASE 4] MULTI-CRITERIA ROUTE COMPARISON (DSA TRADE-OFFS):")
        print(format_table_row("Routing Strategy", "Target Shelter", "Dist (km) / Intersections / Veh Time"))
        print("  " + "-" * 68)

        # Primary Dijkstra
        d_info = f"{route.distance_km:.1f} km | {route.hops} hops | {route.est_vehicle_minutes:.1f} min"
        print(format_table_row("1. Shortest Dist (Dijkstra)", route.target_name, d_info))

        # Risk-Adjusted Dijkstra
        if plan_result.risk_adjusted_route:
            rr = plan_result.risk_adjusted_route
            r_info = f"{rr.distance_km:.1f} km (eff: {rr.effective_risk_distance:.1f}k) | {rr.hops} hops | {rr.est_vehicle_minutes:.1f} min"
            print(format_table_row("2. Risk-Penalized Path", rr.target_name, r_info))

        # BFS Fewest Hops
        if plan_result.fewest_hops_route:
            br = plan_result.fewest_hops_route
            b_info = f"{br.distance_km:.1f} km | {br.hops} hops | {br.est_vehicle_minutes:.1f} min"
            print(format_table_row("3. Fewest Turns (BFS)", br.target_name, b_info))

    # 6. Step-by-Step Explain Mode
    if explain:
        display_explain_trace(plan_result)

    # 7. Visualization Mode
    if visualize:
        print("\n[PHASE 5] GRAPH CARTOGRAPHIC VISUALIZATION:")
        out_img = os.path.join(PROJECT_ROOT, "flood_evacuation_map.png")
        path_nodes = plan_result.primary_route.path if plan_result.primary_route else []
        fig = render_graph_matplotlib(
            graph=graph,
            evacuation_path=path_nodes,
            start_node=start_node,
            stranded_nodes=plan_result.component_analysis.stranded_nodes if plan_result.component_analysis else [],
            output_image_path=out_img,
            title=f"Riverdale City Evacuation - Origin: {start_node}",
        )
        if fig is None:
            print_ascii_graph(graph, path_nodes, start_node)

    return plan_result


def run_cli_simulation(start_node: str = "LOC_01") -> None:
    """Run progressive time-step flood simulation in CLI."""
    graph_path = os.path.join(PROJECT_ROOT, "data", "city_graph.json")
    rain_path = os.path.join(PROJECT_ROOT, "data", "rainfall_data.json")

    graph = load_city_graph(graph_path)
    rainfall_info = load_rainfall_data(rain_path)

    print(BANNER)
    print(f"STARTING DYNAMIC 5-STEP FLOOD ESCALATION SIMULATION")
    print(f"Origin Location: {start_node} ({graph.get_node_data(start_node).get('name', 'Origin')})")
    print("=" * 70)

    reports = run_flood_simulation(graph, start_node, rainfall_info)

    for rep in reports:
        print(f"\n>>> TIMESTEP #{rep.step_index}: {rep.time_label}")
        print(f"    Rainfall Intensity: {rep.rainfall_mm_per_hr} mm/hr (24h Total: {rep.rainfall_last_24h_mm} mm)")
        print(f"    Hydrologic Note:    {rep.description}")
        print(f"    Flood Risk Level:   {rep.risk_level} | Blocked Roads: {rep.blocked_roads_count}")

        if rep.is_stranded:
            print(f"    STATUS: [CRITICAL ENTRAPMENT] Location is stranded! All roads out are submerged.")
        else:
            route_str = " -> ".join(rep.route_path) if rep.route_path else "None"
            print(f"    EVACUATION ROUTE:   {route_str}")
            print(f"    DESTINATION:        {rep.target_shelter_name} ({rep.route_distance_km:.2f} km)")

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETED: Demonstrates dynamic path degradation during severe storm.")
    print("=" * 70 + "\n")


def interactive_menu() -> None:
    """Interactive command-line interface menu."""
    graph_path = os.path.join(PROJECT_ROOT, "data", "city_graph.json")
    graph = load_city_graph(graph_path)
    nodes = graph.get_nodes()

    while True:
        print(BANNER)
        print("MAIN MENU:")
        print("  1. Plan Evacuation from Downtown Central (LOC_01)")
        print("  2. Select Origin Location from City Map")
        print("  3. Run Step-by-Step DSA Explain Mode (Queue & MinHeap inspection)")
        print("  4. Compare Routing Strategies (Dijkstra vs BFS vs Risk-Penalized)")
        print("  5. Run Multi-Timestep Flood Escalation Simulation (T+0h to T+4h)")
        print("  6. Generate and Save Graph Map (matplotlib PNG)")
        print("  7. Run Comprehensive Unit Tests")
        print("  0. Exit")

        choice = input("\nEnter selection [0-7]: ").strip()

        if choice == "0":
            print("Exiting Flood Evacuation Route Planner. Stay safe!")
            break
        elif choice == "1":
            run_full_pipeline("LOC_01", compare=True)
        elif choice == "2":
            print("\nAvailable Locations:")
            for i, nid in enumerate(nodes):
                data = graph.get_node_data(nid)
                sz_flag = "[SHELTER]" if data.get("is_safe_zone") else ""
                print(f"  [{i+1:2d}] {nid}: {data.get('name')} {sz_flag}")
            sub = input(f"Choose location number (1-{len(nodes)}) or enter Node ID: ").strip()
            if sub.isdigit() and 1 <= int(sub) <= len(nodes):
                selected_id = nodes[int(sub) - 1]
            else:
                selected_id = sub if sub in nodes else "LOC_01"
            run_full_pipeline(selected_id, compare=True)
        elif choice == "3":
            run_full_pipeline("LOC_01", explain=True)
        elif choice == "4":
            run_full_pipeline("LOC_01", compare=True)
        elif choice == "5":
            run_cli_simulation("LOC_01")
        elif choice == "6":
            run_full_pipeline("LOC_01", visualize=True)
        elif choice == "7":
            import unittest
            from tests.test_algorithms import (
                TestCustomQueue,
                TestCustomStack,
                TestCustomMinHeap,
                TestGraphStructure,
                TestFloodRiskCalculator,
                TestFloodMarker,
                TestBFSAlgorithm,
                TestDFSAndComponents,
                TestDijkstraShortestPath,
                TestEndToEndEdgeCases,
            )
            suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules["tests.test_algorithms"])
            runner = unittest.TextTestRunner(verbosity=2)
            runner.run(suite)
        else:
            print("Invalid selection. Please try again.")

        input("\nPress Enter to return to menu...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Flood Evacuation Route Planner (DSA Implementation)")
    parser.add_argument("--start", type=str, default=None, help="Origin location identifier (e.g., LOC_01, LOC_08)")
    parser.add_argument("--explain", action="store_true", help="Print step-by-step Queue and MinHeap operations")
    parser.add_argument("--compare", action="store_true", help="Display comparative metrics for Dijkstra vs BFS vs Risk-Penalized")
    parser.add_argument("--simulate", action="store_true", help="Execute 5-timestep flood escalation simulation")
    parser.add_argument("--visualize", action="store_true", help="Generate cartographic network diagram PNG")
    parser.add_argument("--menu", action="store_true", help="Launch interactive CLI menu")

    args = parser.parse_args()

    if args.simulate:
        start_id = args.start if args.start else "LOC_01"
        run_cli_simulation(start_id)
    elif args.start or args.explain or args.compare or args.visualize:
        start_id = args.start if args.start else "LOC_01"
        run_full_pipeline(
            start_node=start_id,
            explain=args.explain,
            compare=args.compare,
            visualize=args.visualize,
        )
    elif args.menu:
        interactive_menu()
    else:
        # Default run with comparison and banner
        run_full_pipeline("LOC_01", compare=True, explain=False, visualize=False)


if __name__ == "__main__":
    main()
