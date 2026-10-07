# Data Structures & Algorithms (DSA) Engine

Comprehensive scratch implementations of core computer science data structures and pathfinding algorithms for municipal flood evacuation route planning and emergency rescue dispatch.

Strict Rule: Built entirely in TypeScript with **zero external graph/routing/heap libraries** (no `networkx`, `heapq`, `deque`, or Google Directions API).

---

## Algorithms & Data Structures Overview

| Component | File | Role & Purpose | Time Complexity | Space Complexity |
|---|---|---|---|---|
| **Adjacency List Graph** | `graph.ts` | Models road networks, node coordinates, elevations, and dynamic flood blockages | $O(V + E)$ lookup/traversal | $O(V + E)$ |
| **Doubly-Linked Queue** | `queue.ts` | FIFO queue for Breadth-First Search (BFS) reachability frontier | $O(1)$ push / pop | $O(N)$ |
| **Linked Stack** | `stack.ts` | LIFO stack for Depth-First Search (DFS) component traversal | $O(1)$ push / pop | $O(N)$ |
| **Binary Min-Heap** | `minHeap.ts` | Priority queue powering Dijkstra's algorithm and urgent rescue dispatching | $O(\log N)$ push / pop | $O(N)$ |
| **Breadth-First Search** | `bfs.ts` | Identifies reachable municipal shelters and unweighted turn-minimum routes | $O(V + E)$ | $O(V)$ |
| **Depth-First Search** | `dfs.ts` | Traverses graph structure iteratively and recursively | $O(V + E)$ | $O(V)$ |
| **Connected Components** | `components.ts` | Partitions graph to isolate cut-off (stranded) flood zones | $O(V + E)$ | $O(V)$ |
| **Dijkstra's Algorithm** | `dijkstra.ts` | Computes shortest safe route from user to safe shelters using MinHeap | $O((V + E) \log V)$ | $O(V)$ |
| **Spherical Haversine** | `haversine.ts` | Computes true spherical distance across Earth's surface and snaps GPS | $O(1)$ per pair | $O(1)$ |
| **Flood Risk Calculator** | `floodRisk.ts` | Multi-factor hydraulic threat scoring (rainfall rate, 24h accumulation, depth) | $O(1)$ | $O(1)$ |
| **Priority Dispatcher** | `priorityDispatch.ts` | Orders stranded zones via MinHeap $-(risk \times pop)$ and assigns nearest NGO via Dijkstra | $O(K \log K + K \cdot NGO \cdot (V + E) \log V)$ | $O(V + K)$ |

---

## 1. Graph (`graph.ts`)

### Why It Is Used
Urban road networks are naturally modelled as graphs where intersections and civic centers are vertices ($V$) and roads are weighted edges ($E$). Floodwaters dynamically alter edge weights (penalizing waterlogged roads) or sever them entirely (submerged roads).

### Steps
1. Add vertices with attributes: coordinates, elevation, population, shelter status.
2. Add bidirectional edges with base weights computed from Haversine kilometers.
3. Dynamically set `isBlocked` when road water depth $\ge 0.50\text{ m}$.
4. Dynamically set `isRisky` and apply multiplier penalty $2.5\times$ when water depth is between $0.20\text{ m}$ and $0.50\text{ m}$.

### Pseudocode
```text
class Graph:
    nodes = Map<node_id, NodeAttributes>
    adjacency = Map<node_id, List<Edge>>

    function addEdge(u, v, weight):
        edge_uv = Edge(u, v, weight)
        adjacency[u].append(edge_uv)
        edge_vu = Edge(v, u, weight)
        adjacency[v].append(edge_vu)
```

---

## 2. Queue (`queue.ts`)

### Why It Is Used
Standard FIFO queue built with linked nodes providing true $O(1)$ `enqueue` and `dequeue`. Essential for Breadth-First Search level-by-level exploration.

---

## 3. Stack (`stack.ts`)

### Why It Is Used
LIFO stack built with linked nodes providing true $O(1)$ `push` and `pop`. Used in iterative DFS to prevent browser call-stack overflow during deep graph traversal.

---

## 4. Binary Min-Heap (`minHeap.ts`)

### Why It Is Used
Stores priority pairs `(key, value)` with minimum key at index 0. Essential for:
1. Extracting the minimum tentative distance vertex in Dijkstra's algorithm in $O(\log V)$ rather than $O(V)$ linear scan.
2. Popping the most urgent stranded zone in Priority Rescue Dispatch.

### Sift-Up & Sift-Down Pseudocode
```text
function siftUp(index):
    while index > 0:
        parent = floor((index - 1) / 2)
        if heap[index].key < heap[parent].key:
            swap(heap[index], heap[parent])
            index = parent
        else:
            break

function siftDown(index):
    while true:
        left = 2 * index + 1
        right = 2 * index + 2
        smallest = index
        if left < length and heap[left].key < heap[smallest].key:
            smallest = left
        if right < length and heap[right].key < heap[smallest].key:
            smallest = right
        if smallest != index:
            swap(heap[index], heap[smallest])
            index = smallest
        else:
            break
```

---

## 5. Breadth-First Search (`bfs.ts`)

### Why It Is Used
Explores the graph layer-by-layer starting from the evacuee's location. Finds paths with the minimum number of intersections (turns) and determines all reachable safe shelters.

---

## 6. Depth-First Search (`dfs.ts`)

### Why It Is Used
Explores as deep as possible along each branch before backtracking. Both iterative (stack-based) and recursive implementations are provided.

---

## 7. Connected Components (`components.ts`)

### Why It Is Used
When roads flood, the road graph splits into disconnected subgraphs. DFS partitions the graph: any component containing no safe shelters is categorized as **STRANDED**, triggering automated NGO rescue dispatch.

---

## 8. Dijkstra's Algorithm (`dijkstra.ts`)

### Why It Is Used
Calculates the single-source shortest path from the user's location to all reachable safe shelters over non-submerged roads. Allows both metric distance minimization and flood-risk-penalized avoidance routes.

---

## 9. Spherical Haversine (`haversine.ts`)

### Why It Is Used
Calculates real-world geodesic distances between GPS latitude/longitude coordinates accounting for Earth's spherical curvature ($R = 6371\text{ km}$). Snaps GPS user coordinates to the nearest graph intersection.

---

## 10. Priority Rescue Dispatcher (`priorityDispatch.ts`)

### Why It Is Used
When residents are stranded without any road exit:
1. Pushes each stranded zone into our `MinHeap` with key $= -(risk\_score \times population)$ so the most populous and threatened area pops first.
2. For each area, runs Dijkstra from every NGO base to assign the nearest responder unit with passable road access.
3. If no ground NGO can reach the area, marks the emergency request as **NEEDS AIRLIFT / BOAT RESCUE**.
