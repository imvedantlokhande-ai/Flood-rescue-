# Depth-First Search (DFS) Algorithm

This module implements Depth-First Search from scratch, providing both an iterative implementation using our custom `CustomStack` and a recursive call-stack implementation.

---

## 1. What This Algorithm Does

Explores branch paths deeply before backtracking. It:
1. Identifies the full extent of reachable territory from an evacuation starting point.
2. Serves as the computational engine for decomposing the city graph into disconnected components and detecting cut-off / stranded population zones.
3. Provides an iterative mode that explicitly tracks LIFO stack frames.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

- **Isolated Island Detection**: When severe floods submerge bridges and valley causeways, municipal road networks fracture into isolated topological components. DFS rapidly navigates deep dead-end corridors and perimeter boundaries to discover complete isolated clusters of roads without crossing flooded edges.
- **Backtracking Path Traversal**: In search-and-rescue reconnaissance, rescue teams must exhaustively sweep a corridor to its terminus before retreating to the next junction.

---

## 3. How It Works, Step by Step

### Iterative Version (using `CustomStack`):
1. **Push**: Push `(start_node, None)` onto the `CustomStack`.
2. **Loop**: While the stack is not empty:
   - Pop top tuple `(curr, parent)`.
   - If `curr` is already in `visited`, discard.
   - Add `curr` to `visited`, append to `traversal_order`, record `parent_map[curr] = parent`.
   - For each unblocked neighbor $v$ of `curr`:
     - If $v$ is not yet visited, push `(v, curr)` onto `CustomStack`.
3. **Finish**: When stack empties, all nodes in the connected component have been exhaustively discovered.

---

## 4. Small Worked Example

```text
Graph:
      [A]
     /   \
   [B]   [C]
    |
   [D]

Stack Execution (Iterative):
  1. Push (A, None)          Stack: [A]
  2. Pop A -> Visit A. Push B, C. Stack: [C, B]
  3. Pop B -> Visit B. Push D.    Stack: [C, D]
  4. Pop D -> Visit D. No unvisited neighbors. Stack: [C]
  5. Pop C -> Visit C. Stack: [] -> Finished.

Traversal Sequence: A -> B -> D -> C
```

---

## 5. Pseudocode

```text
FUNCTION depth_first_search_iterative(graph, start_node):
    stack = CustomStack()
    visited = SET()
    parent = MAP()
    order = LIST()

    stack.push(start_node, parent=NULL)

    WHILE NOT stack.is_empty():
        (u, p) = stack.pop()
        IF u IN visited:
            CONTINUE
        visited.add(u)
        order.append(u)
        parent[u] = p

        FOR EACH (v, weight, edge) IN graph.get_neighbors(u):
            IF NOT edge.is_blocked AND v NOT IN visited:
                stack.push(v, parent=u)

    RETURN DFSResult(visited, order, parent)
```

---

## 6. Time and Space Complexity

- **Time Complexity**: $O(V + E)$
  - Each vertex is pushed and popped at most once per path branch.
  - Each road edge is evaluated twice (once from each vertex).
- **Space Complexity**: $O(V)$
  - CustomStack and visited set hold at most $V$ elements simultaneously.

---

## 7. Input and Output Format

- **Input**: `graph: Graph`, `start_node: str`, `include_blocked: bool = False`, `explain: bool = False`.
- **Output**: `DFSResult` object containing `.visited_nodes`, `.traversal_order`, and `.parent_map`.

---

## 8. How to Run / Test Individually

```bash
python3 algorithms/dfs/dfs.py
```

---

## 9. Limitations and Possible Improvements

1. **Suboptimal Metric Paths**: DFS follows deep branches arbitrarily and does not guarantee shortest distance or fewest hops. It should never be used for primary evacuation routing (Dijkstra is used instead).
2. **Recursive Stack Depth**: In large cities with $> 10,000$ vertices, recursive DFS can trigger Python's recursion limit. The included iterative version with `CustomStack` avoids recursion limits completely.
