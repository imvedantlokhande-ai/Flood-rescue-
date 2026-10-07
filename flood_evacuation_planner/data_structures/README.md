# Data Structures Module

This folder provides all foundational Data Structures built completely from scratch in pure Python without using `networkx`, `heapq`, `queue.PriorityQueue`, or `collections.deque`.

---

## 1. What This Module Does

This module provides the core data structures used by all search and routing algorithms:
1. **`Graph` (`graph.py`)**: An adjacency-list representation of a city road network with support for dynamic edge blocking (flooded roads), risk penalties, and location metadata.
2. **`CustomQueue` (`queue.py`)**: A singly linked-list Queue with explicit `head` and `tail` pointers providing pure $O(1)$ First-In-First-Out (FIFO) enqueue and dequeue operations.
3. **`CustomStack` (`stack.py`)**: A singly linked-list Stack with an explicit `top` pointer providing pure $O(1)$ Last-In-First-Out (LIFO) push and pop operations.
4. **`MinHeap` (`min_heap.py`)**: A binary minimum-heap priority queue with $O(\log N)$ push, $O(\log N)$ pop, and $O(\log N)$ `decrease_key` enabled by a position index map.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

| Data Structure | Flood-Specific Reason |
| :--- | :--- |
| **Graph** | Roads get submerged dynamically as rain accumulates. We need an adjacency list that allows instantaneous edge blocking (`block_edge`) when a road exceeds safe water depth, and effective weight adjustment when roads become waterlogged. |
| **CustomQueue** | Used by **Breadth-First Search (BFS)** to explore city neighborhoods radially layer-by-layer. Ensures that the nearest locations by road count (hops) are discovered first. |
| **CustomStack** | Used by **Depth-First Search (DFS)** to trace deep connectivity, find isolated components, and detect stranded pockets of population cut off by floodwaters. |
| **MinHeap** | Used by **Dijkstra's Algorithm** to always pick the globally closest reachable intersection next. Crucial for saving lives by guaranteeing the absolute shortest evacuation distance to safety under crisis conditions. |

---

## 3. How They Work, Step by Step

### A. CustomQueue (FIFO)
- **Enqueue**: Appends a new node to `tail`. If queue was empty, sets both `head` and `tail`. Takes $O(1)$.
- **Dequeue**: Reads `head.value`, advances `head = head.next`. If `head` becomes `None`, `tail` is reset to `None`. Takes $O(1)$.

### B. CustomStack (LIFO)
- **Push**: Creates a node with `next = top`, updates `top = new_node`. Takes $O(1)$.
- **Pop**: Reads `top.value`, moves `top = top.next`. Takes $O(1)$.

### C. MinHeap (Priority Queue)
- Internal array represents a complete binary tree where node $i$ has children at $2i+1$ and $2i+2$, and parent at $(i-1)//2$.
- **Push**: Placed at array end, then `_sift_up` swaps with parent while child priority < parent priority.
- **Pop**: Minimum element at index 0 is removed. The last element in array is moved to index 0, followed by `_sift_down` which repeatedly swaps with the smaller child until heap property is restored.
- **Decrease-Key**: Uses `_pos_map[item]` to find the item's index in $O(1)$ and immediately sifts it upward.

### D. Graph (Adjacency List)
- Stores vertices in a dictionary `_nodes`.
- Stores outgoing roads in `_adjacency[node_id] = [Edge, ...]`.
- Each `Edge` tracks: `is_blocked` (True if water level $\ge 0.5$ m) and `effective_weight` (base km $\times$ risk penalty).

---

## 4. Small Worked Example

```text
City Intersections:
  [Downtown (A)] ---- 2.0 km ---- [Market (B)] ---- 3.5 km ---- [Shelter (SZ)]
         |                                                       ^
         +----------------------- 7.0 km ------------------------+

When Market road floods:
  RD_1 (A <-> B) is BLOCKED.
  Adjacency list of A:
    Unblocked: [ (SZ, 7.0 km) ]
    Blocked:   [ (B, 2.0 km, BLOCKED) ]
```

---

## 5. Pseudocode

### MinHeap `_sift_up` and `_sift_down`:
```text
FUNCTION sift_up(idx):
    WHILE idx > 0:
        parent = (idx - 1) // 2
        IF heap[idx].priority < heap[parent].priority:
            SWAP(heap[idx], heap[parent])
            UPDATE pos_map
            idx = parent
        ELSE:
            BREAK

FUNCTION sift_down(idx):
    WHILE TRUE:
        smallest = idx
        left = 2 * idx + 1
        right = 2 * idx + 2
        IF left < size AND heap[left].priority < heap[smallest].priority:
            smallest = left
        IF right < size AND heap[right].priority < heap[smallest].priority:
            smallest = right
        IF smallest != idx:
            SWAP(heap[idx], heap[smallest])
            UPDATE pos_map
            idx = smallest
        ELSE:
            BREAK
```

---

## 6. Time and Space Complexity

| Operation | CustomQueue | CustomStack | MinHeap | Graph |
| :--- | :--- | :--- | :--- | :--- |
| **Insert / Push** | $O(1)$ | $O(1)$ | $O(\log N)$ | $O(1)$ (add node/edge) |
| **Delete / Pop** | $O(1)$ | $O(1)$ | $O(\log N)$ | $O(1)$ (block edge) |
| **Lookup / Peek** | $O(1)$ | $O(1)$ | $O(1)$ peek | $O(\text{deg}(V))$ neighbors |
| **Decrease-Key** | N/A | N/A | $O(\log N)$ | N/A |
| **Space Complexity** | $O(N)$ | $O(N)$ | $O(N)$ | $O(V + E)$ |

---

## 7. Input and Output Format

- **Queue / Stack**: Accepts any Python object/string identifier (`str`, `tuple`).
- **MinHeap**: Accepts `push(priority: float, item: T)`. Returns `(priority, item)` upon `pop()`.
- **Graph**: Accepts node IDs (`"LOC_01"`), edges with `weight: float` in km. Outputs neighbor tuples `(neighbor_id, effective_weight, Edge)`.

---

## 8. How to Run and Test Individually

```bash
# Test Queue
python3 data_structures/queue.py

# Test Stack
python3 data_structures/stack.py

# Test Min-Heap
python3 data_structures/min_heap.py

# Test Graph
python3 data_structures/graph.py
```

---

## 9. Limitations and Possible Improvements

1. **Fixed Memory Locality**: The linked-list Queue and Stack use dynamic heap node allocations. While strictly $O(1)$, array circular buffers provide tighter CPU cache line locality.
2. **Multi-Graph Support**: Current Graph supports at most one primary edge between any pair of nodes. Future extensions could support multiple parallel roadways (e.g., lower road vs. elevated express overpass).
