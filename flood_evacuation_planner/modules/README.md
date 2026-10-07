# Modules Overview: Flood Marker, Route Planner, and Simulation

This folder contains high-level integration modules coordinating hydrological sensing, graph updates, multi-algorithm pathfinding, and multi-timestep flood progression.

---

## 1. What These Modules Do

1. **`flood_marker.py`**:
   - Compares localized water level sensor readings against physical thresholds.
   - Roads $\ge 0.5$ m are marked **BLOCKED** ($w = \infty$).
   - Roads between $0.2$ m and $0.5$ m are marked **RISKY** (distance multiplied by $2.5\times$).
2. **`route_planner.py`**:
   - Master orchestrator connecting:
     $$\text{Telemetry} \longrightarrow \text{Risk Assessment} \longrightarrow \text{Flood Marker} \longrightarrow \text{BFS Reachability} \longrightarrow \text{DFS Stranded Check} \longrightarrow \text{Dijkstra Shortest Path}$$
   - Generates route options (Metric Shortest, Risk-Penalized, Fewest Intersections) and computes walking/vehicle evacuation times.
3. **`simulation.py`**:
   - Models dynamic flood expansion over time ($T+0\text{h} \dots T+4\text{h}$), cloning the graph and showing how escalating rain shuts down roads and cuts off neighborhoods.

---

## 2. Why They Are Used in This Project (Flood-Specific Reason)

Floods are non-static disasters. A road passable at 8:00 AM may be completely underwater with floating debris by 9:30 AM.
- The **Flood Marker** bridges raw telemetry sensors to graph weights.
- The **Route Planner** unifies pure DSA algorithms into an actionable life-saving decision support system.
- The **Simulation Module** prepares civil defense authorities for future road network failures before they occur.

---

## 3. How It Works, Step by Step

```text
               +----------------------------------+
               |  Rainfall & Water Depth Telemetry |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |  Flood Risk Assessment Engine    |
               +----------------------------------+
                     /                      \
            [Risk == LOW]             [Risk >= MODERATE]
                 |                                  |
                 v                                  v
      +--------------------+            +------------------------+
      | No Evacuation      |            | Apply Flood Marker:    |
      | Needed. Stand Down |            | Blocked (>=0.5m)       |
      +--------------------+            | Risky   (0.2m - 0.49m) |
                                        +------------------------+
                                                    |
                                                    v
                                        +------------------------+
                                        | BFS Reachability Scan  |
                                        | (Can we reach safety?) |
                                        +------------------------+
                                                    |
                                                    v
                                        +------------------------+
                                        | DFS Connected Clusters |
                                        | (Is area cut-off?)     |
                                        +------------------------+
                                              /            \
                                       [Stranded]      [Accessible]
                                           |                 |
                                           v                 v
                           +----------------------+   +-----------------------+
                           | ALERT: NO SAFE ROUTE |   | Run Dijkstra:         |
                           | Request Boat/Air     |   | 1. Metric Shortest    |
                           | Rescue Dispatch      |   | 2. Risk-Penalized     |
                           +----------------------+   | 3. BFS Fewest Hops    |
                                                      +-----------------------+
```

---

## 4. Small Worked Example

```text
Evacuee starting at: LOC_01 (Downtown Central)
Sensor Readings: 48.5 mm/hr, Max Water Depth: 0.75m
Flooded Roads: RD_02 (River Blvd), RD_06 (Canal St), RD_09 (River Underpass)

Pipeline Execution:
  1. Risk Assessment: SEVERE (Score: 82.5/100) -> Evacuation required.
  2. Flood Marker: 8 roads blocked, 5 roads marked risky.
  3. BFS: 11 of 18 locations reachable from LOC_01.
  4. DFS: User is in Component #1 containing Safe Zone SZ_01 and SZ_02 (Not stranded).
  5. Dijkstra:
     - Distance to SZ_01 (Hospital Shelter): 4.4 km -> Path: LOC_01 -> LOC_10 -> SZ_01
     - Distance to SZ_02 (High School):      7.2 km
     - Distance to SZ_03 (Sports Arena):     8.5 km
     * Winner: SZ_01 (4.4 km, Est Walking: 58.7 min, Est Driving: 10.6 min)
```

---

## 5. Pseudocode

```text
FUNCTION plan_evacuation(graph, start_node, rainfall_hr, water_levels):
    risk = calculate_flood_risk(rainfall_hr, water_levels)
    IF NOT risk.is_dangerous:
        RETURN "No evacuation needed"

    mark_flooded_roads(graph, water_levels)
    bfs_res = breadth_first_search(graph, start_node)
    comp_res = find_connected_components(graph)

    IF comp_res.is_node_stranded(start_node):
        RETURN "NO SAFE ROUTE - REQUEST RESCUE (Stranded Area)"

    best_route = dijkstra_shortest_path(graph, start_node, targets=safe_zones)
    risk_route = dijkstra_shortest_path(graph, start_node, targets=safe_zones, risk_adjusted=TRUE)

    RETURN PlanningResult(best_route, risk_route, evacuation_times)
```

---

## 6. Time and Space Complexity

- **Time Complexity**:
  - Flood Marker: $O(E)$
  - BFS: $O(V + E)$
  - DFS Connected Components: $O(V + E)$
  - Dijkstra: $O((V + E) \log V)$
  - **Overall Pipeline**: $O((V + E) \log V)$ bounded strictly by Dijkstra's algorithm.
- **Space Complexity**: $O(V + E)$ to store graph instances and routing tables.

---

## 7. Input and Output Format

- **Input**: `graph: Graph`, `start_node: str`, `rainfall_mm_per_hr: float`, `water_levels: dict`.
- **Output**: `PlanningResult` object with `primary_route`, `risk_adjusted_route`, `fewest_hops_route`, `is_stranded`, and travel time estimations.

---

## 8. How to Run / Test Individually

```bash
# Test Flood Marker
python3 modules/flood_marker.py

# Test Route Planner
python3 modules/route_planner.py

# Test Simulation Module
python3 modules/simulation.py
```

---

## 9. Limitations and Possible Improvements

1. **Traffic Congestion Queuing**: High-volume evacuation routes may experience bottleneck gridlock. Future improvements can add dynamic edge capacities and M/M/1 queuing delays.
2. **Fuel and Battery Feasibility**: Electric vehicle battery state-of-charge checks along steep elevation ramps.
