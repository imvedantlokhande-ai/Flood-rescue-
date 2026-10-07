"""
Dijkstra's Algorithm Implementation using Custom MinHeap.

Strict Rule Compliance:
Implemented completely from scratch using `data_structures.min_heap.MinHeap`.
No `heapq`, `queue.PriorityQueue`, or external libraries.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
from data_structures.min_heap import MinHeap
from data_structures.graph import Graph


class DijkstraResult:
    """Encapsulates output of Dijkstra's Single-Source Shortest Path algorithm."""

    def __init__(
        self,
        start_node: str,
        distances: Dict[str, float],
        parents: Dict[str, Optional[str]],
        settled_order: List[str],
        heap_trace: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.start_node = start_node
        self.distances = distances
        self.parents = parents
        self.settled_order = settled_order
        self.heap_trace = heap_trace if heap_trace is not None else []

    def get_distance(self, target_node: str) -> float:
        """Return the shortest distance to target_node (float('inf') if unreachable)."""
        return self.distances.get(target_node, float("inf"))

    def is_reachable(self, target_node: str) -> bool:
        """Check if target_node was reached with finite distance."""
        return self.get_distance(target_node) < float("inf")

    def reconstruct_path(self, target_node: str) -> Optional[List[str]]:
        """
        Backtrack through parent pointers to construct the shortest path list.
        Returns None if target is unreachable.
        """
        if not self.is_reachable(target_node):
            return None

        path: List[str] = []
        curr: Optional[str] = target_node
        while curr is not None:
            path.append(curr)
            curr = self.parents.get(curr)

        path.reverse()
        return path


def dijkstra_shortest_path(
    graph: Graph,
    start_node: str,
    target_nodes: Optional[Set[str]] = None,
    risk_adjusted: bool = False,
    explain: bool = False,
) -> DijkstraResult:
    """
    Compute shortest paths from start_node to all reachable nodes using MinHeap.

    Args:
        graph: Graph instance representing the road network.
        start_node: Origin location ID.
        target_nodes: Optional set of target node IDs. If provided, allows early termination
                      once all targets in this set have been settled.
        risk_adjusted: If True, uses effective_weight (with flood risk penalty) instead of base km.
        explain: If True, logs step-by-step heap operations for viva examination and UI trace.

    Returns:
        DijkstraResult containing distance map, parent map, settlement order, and trace logs.
    """
    distances: Dict[str, float] = {}
    parents: Dict[str, Optional[str]] = {}
    settled: Set[str] = set()
    settled_order: List[str] = []
    heap_trace: List[Dict[str, Any]] = []

    all_nodes = graph.get_nodes()
    if start_node not in all_nodes:
        return DijkstraResult(start_node, distances, parents, settled_order, heap_trace)

    # Initialize all distances to infinity
    for node in all_nodes:
        distances[node] = float("inf")
        parents[node] = None

    distances[start_node] = 0.0

    # Custom Min-Heap priority queue storing (priority, item)
    pq: MinHeap[str] = MinHeap()
    pq.push(0.0, start_node)

    step_counter = 0

    if explain:
        heap_trace.append({
            "step": step_counter,
            "action": "INIT",
            "settled_node": start_node,
            "dist": 0.0,
            "heap_snapshot": pq.snapshot(),
            "explanation": f"Initialized source '{start_node}' with distance 0.0 km. Inserted into MinHeap.",
        })

    # Main Dijkstra loop
    while not pq.is_empty():
        curr_dist, curr_node = pq.pop()

        # If already finalized with a shorter distance, skip (standard heap optimization)
        if curr_node in settled:
            continue

        settled.add(curr_node)
        settled_order.append(curr_node)
        step_counter += 1

        relaxed_edges: List[Dict[str, Any]] = []

        # Early exit check if all target destinations have been settled
        if target_nodes and target_nodes.issubset(settled):
            if explain:
                heap_trace.append({
                    "step": step_counter,
                    "action": "EARLY_EXIT",
                    "settled_node": curr_node,
                    "dist": curr_dist,
                    "heap_snapshot": pq.snapshot(),
                    "explanation": f"All target destinations {target_nodes} have been settled. Halting Dijkstra.",
                })
            break

        # Relax incident unblocked edges
        for neighbor, base_or_eff_weight, edge in graph.get_neighbors(curr_node, include_blocked=False):
            if neighbor in settled:
                continue

            # Pick edge weight according to mode
            edge_weight = edge.effective_weight if risk_adjusted else edge.weight
            tentative_dist = curr_dist + edge_weight

            if tentative_dist < distances[neighbor]:
                old_dist = distances[neighbor]
                distances[neighbor] = tentative_dist
                parents[neighbor] = curr_node

                # Insert or decrease key in our custom MinHeap
                pq.push(tentative_dist, neighbor)

                relaxed_edges.append({
                    "neighbor": neighbor,
                    "old_dist": old_dist if old_dist < float("inf") else "INF",
                    "new_dist": round(tentative_dist, 2),
                    "edge_weight": round(edge_weight, 2),
                })

        if explain:
            heap_trace.append({
                "step": step_counter,
                "action": "SETTLE_AND_RELAX",
                "settled_node": curr_node,
                "dist": round(curr_dist, 2),
                "relaxed": relaxed_edges,
                "heap_snapshot": [(round(p, 2), item) for p, item in pq.snapshot()],
                "explanation": (
                    f"Settled '{curr_node}' at final distance {curr_dist:.2f} km. "
                    f"Relaxed {len(relaxed_edges)} neighbor edge(s). "
                    f"MinHeap currently has {pq.size()} elements."
                ),
            })

    return DijkstraResult(
        start_node=start_node,
        distances=distances,
        parents=parents,
        settled_order=settled_order,
        heap_trace=heap_trace,
    )


def find_nearest_safe_zone(
    graph: Graph,
    start_node: str,
    risk_adjusted: bool = False,
    explain: bool = False,
) -> Tuple[Optional[str], Optional[List[str]], float, DijkstraResult]:
    """
    Run Dijkstra to find the nearest reachable safe zone from start_node.

    Returns:
        Tuple: (best_safe_zone_id, best_path, best_distance_km, dijkstra_result)
        If no safe zone is reachable, returns (None, None, float('inf'), dijkstra_result).
    """
    safe_zones = graph.get_safe_zones()
    if not safe_zones:
        empty_res = DijkstraResult(start_node, {}, {}, [])
        return None, None, float("inf"), empty_res

    # Check if start node is already a safe zone
    if start_node in safe_zones:
        res = dijkstra_shortest_path(graph, start_node, risk_adjusted=risk_adjusted, explain=explain)
        return start_node, [start_node], 0.0, res

    dijkstra_res = dijkstra_shortest_path(
        graph,
        start_node=start_node,
        target_nodes=set(safe_zones),
        risk_adjusted=risk_adjusted,
        explain=explain,
    )

    best_safe_zone: Optional[str] = None
    best_dist = float("inf")

    for sz in safe_zones:
        d = dijkstra_res.get_distance(sz)
        if d < best_dist:
            best_dist = d
            best_safe_zone = sz

    if best_safe_zone is not None and best_dist < float("inf"):
        best_path = dijkstra_res.reconstruct_path(best_safe_zone)
        return best_safe_zone, best_path, best_dist, dijkstra_res

    return None, None, float("inf"), dijkstra_res


if __name__ == "__main__":
    g = Graph()
    g.add_node("LOC_1", {"name": "Market Square"})
    g.add_node("LOC_2", {"name": "River Avenue"})
    g.add_node("SZ_1", {"name": "Hospital Shelter", "is_safe_zone": True})
    g.add_node("SZ_2", {"name": "Hilltop Shelter", "is_safe_zone": True})

    g.add_edge("LOC_1", "LOC_2", 2.0)
    g.add_edge("LOC_2", "SZ_1", 3.0)
    g.add_edge("LOC_1", "SZ_2", 7.0)

    print("Running Dijkstra from LOC_1 to find nearest safe zone:")
    sz, path, dist, res = find_nearest_safe_zone(g, "LOC_1", explain=True)
    print(f"Nearest Safe Zone: {sz}")
    print(f"Path: {path}")
    print(f"Distance: {dist} km")
    print(f"Settled Order: {res.settled_order}")
    print("\nExplain trace count:", len(res.heap_trace))
