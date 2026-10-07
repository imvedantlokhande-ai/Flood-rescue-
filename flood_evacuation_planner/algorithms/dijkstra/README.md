# Dijkstra's Shortest Path Algorithm

This module implements Dijkstra's Single-Source Shortest Path algorithm from scratch using our custom `MinHeap` priority queue.

---

## 1. What This Algorithm Does

1. Calculates the minimum metric distance (in kilometers) from an evacuee's starting location to every accessible intersection in the city.
2. Dynamically excludes flooded and impassable roads.
3. Automatically identifies the globally closest reachable emergency safe zone (shelter/hospital/stadium).
4. Supports both:
   - **True Metric Mode**: Minimizes physical distance in kilometers.
   - **Risk-Adjusted Mode**: Incorporates water depth multipliers into road edge costs, guiding evacuees away from water-pooled routes onto higher-elevation alternatives.
5. Emits an educational heap trace for each priority queue extraction and relaxation step.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

In flood evacuation, time is of the essence. Driving or walking an extra 3 kilometers when flash flood waters are rising at 10 cm every 15 minutes can lead to entrapment. Dijkstra's algorithm guarantees finding the mathematically optimal shortest route along open roads. By avoiding flooded edges and penalizing risky water-logged segments, it provides the safest and fastest route to high-ground safety.

---

## 3. How It Works, Step by Step

1. **Initialization**:
   - Set $\text{dist}[v] = \infty$ for all vertices $v$, and $\text{dist}[\text{start}] = 0$.
   - Push $(0.0, \text{start})$ into the `MinHeap`.
2. **Greedy Settlement**:
   - While `MinHeap` is not empty:
     - Pop $(d, u)$ having the lowest distance from the heap.
     - If $u$ is already settled, continue.
     - Mark $u$ as settled.
     - For each unblocked incident road $(u, v)$ with weight $w$:
       - If $v$ is not yet settled and $\text{dist}[u] + w < \text{dist}[v]$:
         - $\text{dist}[v] \leftarrow \text{dist}[u] + w$
         - $\text{parent}[v] \leftarrow u$
         - Push $(\text{dist}[v], v)$ into `MinHeap` (or decrease-key).
3. **Route Construction**:
   - From the destination safe zone, traverse backwards via $\text{parent}$ pointers to the origin.

---

## 4. Small Worked Example

```text
City Intersections:
      [A (Start)]
     /           \
  2 km            7 km
   /               \
 [B]                [SZ_2 (High School)]
  |
 3 km
  |
 [SZ_1 (Hospital)]

Dijkstra Execution:
  1. Insert (0.0, A). Heap = [(0.0, A)].
  2. Pop (0.0, A). Relax B: dist[B] = 2.0; Relax SZ_2: dist[SZ_2] = 7.0.
     Heap = [(2.0, B), (7.0, SZ_2)].
  3. Pop (2.0, B). Relax SZ_1: dist[SZ_1] = 2.0 + 3.0 = 5.0.
     Heap = [(5.0, SZ_1), (7.0, SZ_2)].
  4. Pop (5.0, SZ_1). Target SZ_1 reached with dist = 5.0 km.
  5. Pop (7.0, SZ_2). Target SZ_2 reached with dist = 7.0 km.

Nearest Safe Zone: SZ_1 (5.0 km) via Path: [A, B, SZ_1]
```

---

## 5. Pseudocode

```text
FUNCTION dijkstra_shortest_path(graph, start_node, risk_adjusted):
    FOR EACH node IN graph.get_nodes():
        dist[node] = INFINITY
        parent[node] = NULL

    dist[start_node] = 0.0
    heap = MinHeap()
    heap.push(0.0, start_node)
    settled = SET()

    WHILE NOT heap.is_empty():
        (curr_dist, u) = heap.pop()
        IF u IN settled:
            CONTINUE
        settled.add(u)

        FOR EACH (v, weight, edge) IN graph.get_neighbors(u):
            IF edge.is_blocked OR v IN settled:
                CONTINUE
            edge_cost = edge.effective_weight IF risk_adjusted ELSE edge.weight
            new_dist = curr_dist + edge_cost

            IF new_dist < dist[v]:
                dist[v] = new_dist
                parent[v] = u
                heap.push(new_dist, v)

    RETURN dist, parent
```

---

## 6. Time and Space Complexity

- **Time Complexity**: $O((V + E) \log V)$
  - Each of the $V$ vertices is popped from the min-heap at most once: $O(V \log V)$.
  - Each of the $E$ unblocked edges is relaxed at most once, performing a heap insertion: $O(E \log V)$.
  - Using our custom binary heap, overall time is strictly bounded by $O((V + E) \log V)$.
- **Space Complexity**: $O(V)$
  - `MinHeap`, `dist` table, `parent` pointers, and `settled` set each occupy $O(V)$ memory.

---

## 7. Input and Output Format

- **Input**:
  - `graph: Graph`: The road network instance.
  - `start_node: str`: Origin node identifier.
  - `risk_adjusted: bool`: Whether to use flood-risk penalized edge weights.
  - `explain: bool`: Whether to generate heap transition trace logs.
- **Output**:
  - `DijkstraResult` object with `.distances`, `.parents`, `.settled_order`, `.reconstruct_path(target)`.

---

## 8. How to Run / Test Individually

```bash
python3 algorithms/dijkstra/dijkstra.py
```

---

## 9. Limitations and Possible Improvements

1. **Static Edge Weights**: Floodwaters rise dynamically during evacuation. Time-dependent Dijkstra or $A^*$ search with dynamic heuristic estimates could plan against predicted future road closures.
2. **Bidirectional Search**: Bidirectional Dijkstra can halve the search space when navigating to a single fixed destination.
