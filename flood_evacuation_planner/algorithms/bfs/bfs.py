"""
Breadth-First Search (BFS) Implementation using CustomQueue.

Strict Rule Compliance:
Implemented completely from scratch using `data_structures.queue.CustomQueue`.
No `collections.deque` or external libraries used.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from data_structures.queue import CustomQueue
from data_structures.graph import Graph


class BFSResult:
    """Encapsulates the output of a Breadth-First Search traversal."""

    def __init__(
        self,
        start_node: str,
        reachable_nodes: Set[str],
        hop_distances: Dict[str, int],
        parent_map: Dict[str, Optional[str]],
        traversal_order: List[str],
        step_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.start_node = start_node
        self.reachable_nodes = reachable_nodes
        self.hop_distances = hop_distances
        self.parent_map = parent_map
        self.traversal_order = traversal_order
        self.step_logs = step_logs if step_logs is not None else []

    def reconstruct_path(self, target_node: str) -> Optional[List[str]]:
        """
        Reconstruct the fewest-hops path from start_node to target_node.
        Returns None if target_node is unreachable.
        """
        if target_node not in self.reachable_nodes:
            return None

        path: List[str] = []
        curr: Optional[str] = target_node
        while curr is not None:
            path.append(curr)
            curr = self.parent_map.get(curr)

        path.reverse()
        return path


def breadth_first_search(
    graph: Graph,
    start_node: str,
    include_blocked: bool = False,
    explain: bool = False,
) -> BFSResult:
    """
    Perform Breadth-First Search from start_node using CustomQueue.

    Args:
        graph: Custom Graph instance.
        start_node: Origin location identifier.
        include_blocked: If False, skips flooded roads.
        explain: If True, records step-by-step queue transitions for DSA viva/inspection.

    Returns:
        BFSResult containing reachability set, hop distances, parent tree, and log steps.
    """
    queue: CustomQueue[str] = CustomQueue()
    reachable_nodes: Set[str] = set()
    hop_distances: Dict[str, int] = {}
    parent_map: Dict[str, Optional[str]] = {}
    traversal_order: List[str] = []
    step_logs: List[Dict[str, Any]] = []

    if start_node not in graph.get_nodes():
        return BFSResult(start_node, reachable_nodes, hop_distances, parent_map, traversal_order, step_logs)

    # Initialize start node
    queue.enqueue(start_node)
    reachable_nodes.add(start_node)
    hop_distances[start_node] = 0
    parent_map[start_node] = None

    step_counter = 0

    if explain:
        step_logs.append({
            "step": step_counter,
            "action": "INIT",
            "current_node": start_node,
            "queue_state": queue.to_list(),
            "explanation": f"Enqueued start location '{start_node}' at hop distance 0.",
        })

    while not queue.is_empty():
        curr_node = queue.dequeue()
        traversal_order.append(curr_node)
        curr_hops = hop_distances[curr_node]
        step_counter += 1

        discovered_in_step: List[str] = []

        # Explore incident unblocked roads
        for neighbor, _, edge in graph.get_neighbors(curr_node, include_blocked=include_blocked):
            if neighbor not in reachable_nodes:
                reachable_nodes.add(neighbor)
                hop_distances[neighbor] = curr_hops + 1
                parent_map[neighbor] = curr_node
                queue.enqueue(neighbor)
                discovered_in_step.append(neighbor)

        if explain:
            step_logs.append({
                "step": step_counter,
                "action": "DEQUEUE_AND_EXPAND",
                "current_node": curr_node,
                "current_hops": curr_hops,
                "discovered": discovered_in_step,
                "queue_state": queue.to_list(),
                "explanation": (
                    f"Visited '{curr_node}' (hops: {curr_hops}). "
                    f"Discovered {len(discovered_in_step)} unvisited neighbor(s): {discovered_in_step}. "
                    f"Current Queue: {queue.to_list()}"
                ),
            })

    return BFSResult(
        start_node=start_node,
        reachable_nodes=reachable_nodes,
        hop_distances=hop_distances,
        parent_map=parent_map,
        traversal_order=traversal_order,
        step_logs=step_logs,
    )


def get_fewest_hops_path(
    graph: Graph,
    start_node: str,
    target_node: str,
    include_blocked: bool = False,
) -> Optional[Tuple[List[str], int]]:
    """
    Find unweighted path with minimum number of road segments (fewest intersections/turns).

    Returns:
        Tuple of (path_list, hop_count), or None if unreachable.
    """
    bfs_res = breadth_first_search(graph, start_node, include_blocked=include_blocked)
    path = bfs_res.reconstruct_path(target_node)
    if path is None:
        return None
    return path, bfs_res.hop_distances[target_node]


if __name__ == "__main__":
    # Self-test demonstration
    g = Graph()
    g.add_edge("A", "B", 2.0)
    g.add_edge("A", "C", 5.0)
    g.add_edge("B", "D", 1.5)
    g.add_edge("C", "D", 2.2)
    g.add_edge("D", "SZ", 3.0)

    print("Running BFS with explain=True from 'A':")
    res = breadth_first_search(g, "A", explain=True)
    print("Traversal Order:", res.traversal_order)
    print("Hop Distances:", res.hop_distances)
    print("Reconstructed Path to SZ:", res.reconstruct_path("SZ"))
    print("\nExplain Steps:")
    for log in res.step_logs:
        print(f"  Step {log['step']}: {log['explanation']}")
