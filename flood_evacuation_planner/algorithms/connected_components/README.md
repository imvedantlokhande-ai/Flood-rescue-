# Connected Components & Stranded Zone Analysis

This module uses our scratch-built Depth-First Search algorithm to decompose the road graph into disconnected clusters and detect isolated cut-off zones.

---

## 1. What This Algorithm Does

1. Partitions the unblocked road graph into mutually exclusive connected components:
   $$G = C_1 \cup C_2 \cup \dots \cup C_k$$
2. Maps which emergency shelters (safe zones) reside in which component.
3. Classifies any component containing **zero reachable shelters** as a **Stranded Zone**.
4. Outputs the specific list of stranded neighborhoods for urgent emergency boat/helicopter dispatch.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

In severe floods, rivers crest and submerge primary bridges, dividing a contiguous city into several isolated islands. If a neighborhood is completely cut off from all shelters, Dijkstra's algorithm will simply fail to find a path. Rather than reporting a generic failure, this module explicitly identifies:
- That the user is located in an isolated pocket.
- The entire list of co-isolated neighborhoods.
- Informs first responders which zones require boat/airlift rescue assets rather than self-evacuation routing.

---

## 3. How It Works, Step by Step

1. **Global Tracking**: Maintain a `visited_global` set initialized to empty.
2. **Iterate Vertices**: For each vertex $v \in V$:
   - If $v \notin \text{visited\_global}$:
     - Run `depth_first_search_iterative(graph, start_node=v, include_blocked=False)`.
     - The returned `visited_nodes` set forms a new connected component $C_i$.
     - Add all nodes in $C_i$ to `visited_global`.
3. **Safety Evaluation**:
   - For each component $C_i$, intersect with the set of safe zones:
     $$S_i = C_i \cap \text{SafeZones}$$
   - If $|S_i| = 0$, mark $C_i$ as a **Stranded Component**.

---

## 4. Small Worked Example

```text
Graph State (Flooded bridge between B and C):

  [A] --- [SafeZone_1]       [B]  (No shelter)
                                   |
                             (Flooded Bridge)
                                   X
                             [C] --- [D]  (No shelter)

Components Found:
  Component 1: {A, SafeZone_1}  -> Has shelter [SafeZone_1]  (ACCESSIBLE)
  Component 2: {B}               -> Shelters: NONE            (STRANDED!)
  Component 3: {C, D}            -> Shelters: NONE            (STRANDED!)

Report: Areas {B, C, D} are completely cut off.
```

---

## 5. Pseudocode

```text
FUNCTION find_connected_components(graph):
    visited_global = SET()
    components = LIST()
    stranded_nodes = LIST()

    FOR EACH node IN graph.get_nodes():
        IF node NOT IN visited_global:
            dfs_res = depth_first_search_iterative(graph, start_node=node)
            cluster = dfs_res.visited_nodes
            visited_global.UPDATE(cluster)
            components.APPEND(cluster)

            shelters = cluster INTERSECTION graph.get_safe_zones()
            IF shelters IS EMPTY:
                stranded_nodes.EXTEND(cluster)

    RETURN ComponentAnalysisResult(components, stranded_nodes)
```

---

## 6. Time and Space Complexity

- **Time Complexity**: $O(V + E)$
  - Each vertex and each unblocked edge is visited exactly once across all DFS executions.
- **Space Complexity**: $O(V)$
  - Stores component sets and global tracking arrays totaling $V$ nodes.

---

## 7. Input and Output Format

- **Input**: `graph: Graph`, `include_blocked: bool = False`.
- **Output**: `ComponentAnalysisResult` containing:
  - `.components`: `List[Set[str]]`
  - `.stranded_components`: `List[Set[str]]`
  - `.stranded_nodes`: `List[str]`
  - `.is_node_stranded(node_id)`: `bool`

---

## 8. How to Run / Test Individually

```bash
python3 algorithms/connected_components/components.py
```

---

## 9. Limitations and Possible Improvements

1. **Bridge Vulnerability Analysis**: Can be expanded with Tarjan's Bridge-Finding algorithm to proactively identify critical single-point-of-failure roads before they flood.
2. **Dynamic Water Level Forecasting**: Anticipate upcoming disconnects by evaluating rates of water level rise.
