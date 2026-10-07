# Priority Rescue Dispatcher & NGO Assignment Algorithm

This module implements automated multi-criteria prioritization and resource allocation from scratch using our custom `MinHeap` and `Dijkstra` shortest path implementations.

---

## 1. What This Algorithm Does

1. **Calculates Multi-Criteria Priority Score**: Evaluates the emergency severity of each isolated neighborhood cut off by floodwaters using:
   $$\text{Priority Metric} = \text{Risk Score} \times \text{Population}$$
2. **Min-Heap Prioritization**: Inserts all cut-off zones into our custom `MinHeap` using negative priorities:
   $$\text{Priority Key} = -(\text{Risk Score} \times \text{Population})$$
   Because a min-heap extracts the smallest numeric value, the most negative key (the zone with highest population $\times$ risk) pops first in $O(\log K)$ time.
3. **Shortest Passable Path NGO Assignment**: Runs our custom `dijkstra_shortest_path` algorithm from every stationed emergency response NGO base on non-submerged roads to compute the true passable distance to the cut-off zone.
4. **Automated Escalation**: If no ground NGO base can reach the stranded zone due to road submersion across all perimeter edges, the mission is escalated immediately to `"NEEDS AIRLIFT/BOAT"`.
5. **Deduplication & State Tracking**: Prevents duplicate mission dispatches for already active zones and updates delivery channels.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

- **Triage Under Resource Constraints**: In a municipal flood crisis (e.g. Pavana River Basin in PCMC Pune), dozens of neighborhoods can become simultaneously cut off while emergency rescue units (NDRF, Civil Defense, Red Cross) have finite vehicle capacities. Rescuers cannot dispatch arbitrarily; they must prioritize densely populated lowlands over smaller isolated pockets.
- **Dynamic Ground Passability**: Straight-line distance (Euclidean or Haversine) is dangerously misleading during floods—an NGO base 1 km away across a submerged bridge is useless. Only a Dijkstra search over verified unblocked road edges guarantees that the assigned emergency vehicle can physically arrive.
- **Automatic Airborne Escalation**: When water depths exceed 0.50m across all ingress and egress roads, ground vehicles are useless. The algorithm detects this topological isolation and escalates to helicopter/airlift units instantly.

---

## 3. How It Works, Step by Step

1. **Identify Stranded Nodes**: Receive the list of isolated vertices from the Connected Components analysis ($0$ reachable safe zones).
2. **Push to MinHeap**:
   - For each stranded node $u$, lookup its population $P_u$ and the municipal hydrologic risk score $R$.
   - Calculate $\text{priority} = -(R \times P_u)$.
   - Push into custom `MinHeap(priority, node_id)`.
3. **Extract in Priority Order**:
   - While `MinHeap` is not empty, pop $(-M, u)$. The popped node has the highest triage urgency.
   - Assign priority rank $1, 2, 3, \dots$
4. **Evaluate NGO Bases via Dijkstra**:
   - For each NGO base $B$ located at node $N_B$:
     - Run `dijkstra_shortest_path(graph, start_node=N_B, risk_adjusted=True)` skipping blocked edges.
     - Check if $u$ is reachable: `dijkstra_res.is_reachable(u)`.
     - Record the minimum distance $D(B, u)$ and path.
5. **Assign or Escalate**:
   - If an accessible NGO base exists:
     - Assign the closest NGO base.
     - Compute vehicle ETA: $\text{ETA} = \frac{\text{Distance}}{30\text{ km/h}} \times 60$.
     - Set status to `"Sent"`.
   - Else:
     - Flag `needs_airlift = True`.
     - Set status to `"NEEDS AIRLIFT/BOAT"`.
6. **Alert Notification**:
   - Transmit mission details (waypoints, ETA, Google Maps link) to assigned NGO through configured channel (`DEMO`, `EMAIL`, or `TELEGRAM`).

---

## 4. Small Worked Example

```text
Stranded Neighborhoods:
- Zone A: Population = 12,000, Risk Score = 80 -> Metric = 960,000 -> Key = -960,000
- Zone B: Population =  3,000, Risk Score = 80 -> Metric = 240,000 -> Key = -240,000
- Zone C: Population =  8,500, Risk Score = 80 -> Metric = 680,000 -> Key = -680,000

MinHeap Insertion & Extraction:
  Heap State: [-960,000: Zone A, -240,000: Zone B, -680,000: Zone C]
  1st Pop: -960,000 -> Zone A (Rank #1, highest triage urgency)
  2nd Pop: -680,000 -> Zone C (Rank #2)
  3rd Pop: -240,000 -> Zone B (Rank #3)

NGO Base Dijkstra Evaluation for Zone A:
  - NGO 1 (Kasarwadi): Distance = 4.2 km (Passable) -> Assigned! ETA: 8.4 mins
  - NGO 2 (Bhosari MIDC): Distance = 7.8 km

Evaluation for Zone B:
  - All roads leading to Zone B have water depth >= 0.50m (Blocked).
  - Dijkstra returns distance = INFINITY from all NGO bases.
  - Action: ESCALATE to "NEEDS AIRLIFT/BOAT"!
```

---

## 5. Pseudocode

```text
FUNCTION dispatch_stranded_areas(graph, stranded_nodes, risk_score, locations, ngo_bases):
    heap = MinHeap()

    FOR EACH node IN stranded_nodes:
        pop = locations[node].population
        metric = risk_score * pop
        heap.push(-metric, node)

    rank = 1
    requests = []

    WHILE NOT heap.is_empty():
        (neg_metric, node) = heap.pop()
        best_ngo = NULL
        min_dist = INFINITY
        best_path = NULL

        FOR EACH ngo IN ngo_bases:
            dijkstra_res = dijkstra_shortest_path(graph, start_node=ngo.node, risk_adjusted=True)
            IF dijkstra_res.is_reachable(node):
                dist = dijkstra_res.get_distance(node)
                IF dist < min_dist:
                    min_dist = dist
                    best_ngo = ngo
                    best_path = dijkstra_res.reconstruct_path(node)

        IF best_ngo IS NOT NULL:
            req = CreateRescueRequest(
                stranded_node=node,
                priority_rank=rank,
                ngo=best_ngo,
                route=best_path,
                distance=min_dist,
                status="Sent",
                needs_airlift=FALSE
            )
        ELSE:
            req = CreateRescueRequest(
                stranded_node=node,
                priority_rank=rank,
                status="NEEDS AIRLIFT/BOAT",
                needs_airlift=TRUE
            )

        requests.append(req)
        rank = rank + 1

    RETURN requests
```

---

## 6. Time and Space Complexity

- **Min-Heap Prioritization**:
  - Pushing $K$ stranded nodes: $K \times O(\log K) = O(K \log K)$
  - Popping $K$ stranded nodes: $K \times O(\log K) = O(K \log K)$
- **Dijkstra Assignment**:
  - Running Dijkstra from $B$ NGO bases: $B \times O((V + E) \log V)$
- **Overall Time Complexity**: $O(K \log K + B \cdot (V + E) \log V)$
  - With $V \approx 20$, $E \approx 35$, $B = 4$, execution takes under $2$ milliseconds in pure Python.
- **Space Complexity**: $O(K + V + E)$
  - Heap storage bounded by $K$ stranded vertices.

---

## 7. Input and Output Format

- **Input**:
  - `graph`: Custom `Graph` instance with submerged road edges flagged.
  - `stranded_nodes`: `List[str]` of cut-off node IDs.
  - `risk_score`: `float` (0.0 to 100.0).
  - `locations_by_id`: `Dict[str, Dict]` containing node metadata and `population`.
  - `ngo_bases`: `List[Dict]` containing NGO base nodes, contacts, and vehicle capacities.
- **Output**:
  - `List[RescueRequest]` containing `id`, `priority_rank`, `stranded_node`, `ngo_assigned`, `distance_km`, `eta_minutes`, `status`, and `needs_airlift`.

---

## 8. How to Run / Test Individually

```bash
python3 -m unittest flood_evacuation_planner/tests/test_rescue_dispatcher.py
```

---

## 9. Limitations and Possible Improvements

1. **Fleet Capacity Tracking**: Currently assigns the nearest passable NGO; can be extended to decrement `vehicle_capacity` as requests are acknowledged.
2. **Multi-Vehicle Rendezvous**: For areas with populations exceeding single-trip limits (>10,000), support multi-unit joint dispatches.
