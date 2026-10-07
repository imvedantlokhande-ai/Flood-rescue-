"""
Data Loader Utility.

Parses municipal road network JSON and hydrological rainfall telemetry JSON files
into our custom Graph data structures.
"""

import json
import os
from typing import Dict, Any, Optional
from data_structures.graph import Graph
from algorithms.haversine.haversine import haversine_distance_km


def load_city_graph(json_path: str, recompute_with_haversine: bool = False) -> Graph:
    """
    Load a city network JSON file into a custom Graph instance.
    Computes or verifies edge distance weights using the manual Haversine formula
    when geographic coordinates are present.

    Args:
        json_path: Path to the city_graph.json file.
        recompute_with_haversine: If True, recalculates road weights using node lat/lng.

    Returns:
        Graph instance populated with location vertices and road edges.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"City graph file not found at: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = Graph()
    loc_coords: Dict[str, tuple[float, float]] = {}

    # Load locations
    for loc in data.get("locations", []):
        node_id = loc["id"]
        graph.add_node(node_id, loc)
        if "lat" in loc and "lng" in loc:
            loc_coords[node_id] = (float(loc["lat"]), float(loc["lng"]))

    # Load roads
    for road in data.get("roads", []):
        u = road["from"]
        v = road["to"]
        road_id = road.get("id")

        if (recompute_with_haversine or "distance_km" not in road) and u in loc_coords and v in loc_coords:
            lat1, lon1 = loc_coords[u]
            lat2, lon2 = loc_coords[v]
            distance_km = haversine_distance_km(lat1, lon1, lat2, lon2)
        else:
            distance_km = float(road.get("distance_km", 1.0))

        graph.add_edge(u, v, distance_km, road_id=road_id, attributes=road, bidirectional=True)

    return graph


def load_rainfall_data(json_path: str) -> Dict[str, Any]:
    """
    Load rainfall and water level telemetry JSON file.

    Args:
        json_path: Path to the rainfall_data.json file.

    Returns:
        Dictionary of meteorological telemetry and simulation timesteps.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Rainfall telemetry file not found at: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_sample_city_graph() -> Graph:
    """Helper fallback that loads city_graph.json or constructs programmatic fallback."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "..", "data", "city_graph.json")
    if os.path.exists(data_path):
        return load_city_graph(data_path)

    # Fallback programmatic construction if file moved
    g = Graph()
    g.add_node("LOC_01", {"name": "Downtown Central", "elevation_m": 12.0, "x": 42.0, "y": 50.0})
    g.add_node("LOC_02", {"name": "Central Market", "elevation_m": 10.5, "x": 38.0, "y": 42.0})
    g.add_node("SZ_01", {"name": "Hospital Shelter", "elevation_m": 38.0, "is_safe_zone": True, "capacity": 1500, "x": 56.0, "y": 78.0})
    g.add_edge("LOC_01", "LOC_02", 1.8, road_id="RD_01")
    g.add_edge("LOC_01", "SZ_01", 4.5, road_id="RD_05")
    return g


def create_sample_rainfall_data() -> Dict[str, Any]:
    """Helper fallback that loads rainfall_data.json or constructs programmatic fallback."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "..", "data", "rainfall_data.json")
    if os.path.exists(data_path):
        return load_rainfall_data(data_path)

    return {
        "rainfall_mm_per_hr": 48.5,
        "rainfall_last_24h_mm": 135.0,
        "river_level_above_normal_m": 2.4,
        "water_levels_by_road": {"RD_01": 0.25, "RD_05": 0.05},
        "simulation_timesteps": []
    }


if __name__ == "__main__":
    g = create_sample_city_graph()
    rf = create_sample_rainfall_data()
    print("Loaded City Graph with", len(g.get_nodes()), "nodes and", len(g.get_all_edges()), "roads.")
    print("Loaded Rainfall Telemetry:", rf.get("scenario_name", "Default Scenario"))
