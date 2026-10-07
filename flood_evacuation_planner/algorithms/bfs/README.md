# Breadth-First Search (BFS) Algorithm

This module implements Breadth-First Search from scratch using our custom `CustomQueue` data structure.

---

## 1. What This Algorithm Does

Performs a level-by-level layer traversal of the city graph starting from an evacuee's location. It:
1. Determines every intersection reachable without traversing flooded roads.
2. Calculates the exact unweighted hop distance (number of road transitions) to every node.
3. Constructs a BFS parent spanning tree to reconstruct the route with the minimum number of intersections/turns.
4. Emits step-by-step queue logs for inspection and educational defense.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

- **Guaranteed Reachability Check**: Before running distance calculations, emergency services need to know if an evacuee can escape *at all*. If BFS returns an empty intersection with safe zones, an alert is triggered immediately.
- **Turn Minimization**: In blinding torrential rain with low visibility, navigating complex highway sequences with multiple turns increases the probability of accidents or wrong turns into floodwater. BFS provides the route with the **fewest turns / road segments**, offering an alternative to the pure metric shortest path.

---

## 3. How It Works, Step by Step

1. **Initialize**: Create a FIFO `CustomQueue`. Enqueue `start_node`, mark it visited in `reachable_nodes`, set `hop_distances[start_node] = 0`.
2. **Loop**: While the queue is not empty:
   - Dequeue front node $u$.
   - For each adjacent road $(u, v)$:
     - If the road is flooded (`is_blocked == True`), skip it.
     - If neighbor $v$ has not yet been visited:
       - Mark $v$ visited.
       - Set `hop_distances[v] = hop_distances[u] + 1`.
       - Record `parent_map[v] = u`.
       - Enqueue $v$ into `CustomQueue`.
3. **Reconstruct**: Follow parent pointers backward from destination to origin and reverse.

---

## 4. Small Worked Example

```text
City Intersections:
      [A] (Start)
     /   \
  (1)     (1)
   v       v
  [B]     [C]
   \       /
  (1)     (1)
   v       v
      [D]
       |
      (1)
       v
     [SZ] (Shelter)

Queue Transitions:
  Initial:       Queue = [A],          Visited = {A}
  Pop A:         Queue = [B, C],       Visited = {A, B, C}
  Pop B:         Queue = [C, D],       Visited = {A, B, C, D}
  Pop C:         D already visited.    Queue = [D]
  Pop D:         Queue = [SZ],         Visited = {A, B, C, D, SZ}
  Pop SZ:        Queue = [] -> Complete.

Reconstructed Path to SZ: A -> B -> D -> SZ (3 hops)
```

---

## 5. Pseudocode

```text
FUNCTION breadth_first_search(graph, start_node):
    queue = CustomQueue()
    visited = SET()
    parent = MAP()
    hops = MAP()

    queue.enqueue(start_node)
    visited.add(start_node)
    hops[start_node] = 0
    parent[start_node] = NULL

    WHILE NOT queue.is_empty():
        u = queue.dequeue()
        FOR EACH (v, weight, edge) IN graph.get_neighbors(u):
            IF edge.is_blocked:
                CONTINUE
            IF v NOT IN visited:
                visited.add(v)
                hops[v] = hops[u] + 1
                parent[v] = u
                queue.enqueue(v)

    RETURN BFSResult(visited, hops, parent)
```

---

## 6. Time and Space Complexity

- **Time Complexity**: $O(V + E)$
  - Every reachable location vertex $V$ is enqueued and dequeued exactly once.
  - Every incident road edge $E$ is examined once per endpoint.
- **Space Complexity**: $O(V)$
  - `CustomQueue`, `visited` set, `hops` dictionary, and `parent` map all store at most $V$ elements.

---

## 7. Input and Output Format

- **Input**: `graph: Graph`, `start_node: str`, `include_blocked: bool = False`.
- **Output**: `BFSResult` object with `.reachable_nodes`, `.hop_distances`, `.parent_map`, and `.reconstruct_path(target)`.

---

## 8. How to Run / Test Individually

```bash
python3 algorithms/bfs/bfs.py
```

---

## 9. Limitations and Possible Improvements

1. **Unweighted Edge Assumption**: BFS assumes all edges have uniform cost (1 hop). It cannot guarantee the shortest physical distance in kilometers when road lengths differ significantly (handled by Dijkstra).
2. **Multi-Source BFS**: Can be extended to run simultaneously backward from all safe zones to generate an evacuation watershed map.
