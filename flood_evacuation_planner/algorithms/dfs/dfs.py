"""
Depth-First Search (DFS) Implementation.

Strict Rule Compliance:
Provides both iterative traversal using our custom `CustomStack` (from scratch)
and a recursive traversal without any external graph libraries.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from data_structures.stack import CustomStack
from data_structures.graph import Graph


class DFSResult:
    """Encapsulates the output of a Depth-First Search traversal."""

    def __init__(
        self,
        start_node: str,
        visited_nodes: Set[str],
        traversal_order: List[str],
        parent_map: Dict[str, Optional[str]],
        step_logs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.start_node = start_node
        self.visited_nodes = visited_nodes
        self.traversal_order = traversal_order
        self.parent_map = parent_map
        self.step_logs = step_logs if step_logs is not None else []

    def reconstruct_path(self, target_node: str) -> Optional[List[str]]:
        """Reconstruct DFS path from start_node to target_node."""
        if target_node not in self.visited_nodes:
            return None
        path: List[str] = []
        curr: Optional[str] = target_node
        while curr is not None:
            path.append(curr)
            curr = self.parent_map.get(curr)
        path.reverse()
        return path


def depth_first_search_iterative(
    graph: Graph,
    start_node: str,
    include_blocked: bool = False,
    explain: bool = False,
) -> DFSResult:
    """
    Perform Depth-First Search iteratively using custom CustomStack.

    Args:
        graph: Custom Graph instance.
        start_node: Starting location ID.
        include_blocked: If True, traverses flooded roads.
        explain: If True, logs stack frames and expansion actions.

    Returns:
        DFSResult with visited set, order, and parent links.
    """
    stack: CustomStack[Tuple[str, Optional[str]]] = CustomStack()
    visited: Set[str] = set()
    parent_map: Dict[str, Optional[str]] = {}
    traversal_order: List[str] = []
    step_logs: List[Dict[str, Any]] = []

    if start_node not in graph.get_nodes():
        return DFSResult(start_node, visited, traversal_order, parent_map, step_logs)

    # Push tuple: (current_node, parent_node)
    stack.push((start_node, None))
    step = 0

    if explain:
        step_logs.append({
            "step": step,
            "action": "INIT",
            "node": start_node,
            "stack_state": [item[0] for item in stack.to_list()],
            "explanation": f"Pushed start location '{start_node}' onto CustomStack.",
        })

    while not stack.is_empty():
        curr_node, parent = stack.pop()
        step += 1

        if curr_node in visited:
            continue

        visited.add(curr_node)
        traversal_order.append(curr_node)
        parent_map[curr_node] = parent

        pushed_neighbors: List[str] = []
        # Get neighbors and push unvisited ones to stack
        neighbors = graph.get_neighbors(curr_node, include_blocked=include_blocked)
        # Reverse to visit in intuitive alphabetical/natural order if desired
        for neighbor, _, edge in reversed(neighbors):
            if neighbor not in visited:
                stack.push((neighbor, curr_node))
                pushed_neighbors.append(neighbor)

        if explain:
            step_logs.append({
                "step": step,
                "action": "POP_AND_EXPAND",
                "node": curr_node,
                "parent": parent,
                "pushed": pushed_neighbors,
                "stack_state": [item[0] for item in stack.to_list()],
                "explanation": (
                    f"Popped '{curr_node}'. Added to visited. Pushed unvisited neighbors: {pushed_neighbors}. "
                    f"Stack top -> {stack.to_list()}"
                ),
            })

    return DFSResult(start_node, visited, traversal_order, parent_map, step_logs)


def depth_first_search_recursive(
    graph: Graph,
    start_node: str,
    include_blocked: bool = False,
    visited: Optional[Set[str]] = None,
    traversal_order: Optional[List[str]] = None,
    parent_map: Optional[Dict[str, Optional[str]]] = None,
) -> DFSResult:
    """
    Perform Depth-First Search recursively using the runtime call stack.

    Args:
        graph: Custom Graph instance.
        start_node: Starting node.
        include_blocked: If True, explores flooded edges.
        visited: Accumulated visited set.
        traversal_order: Accumulated traversal sequence.
        parent_map: Accumulated parent link map.

    Returns:
        DFSResult instance.
    """
    if visited is None:
        visited = set()
    if traversal_order is None:
        traversal_order = []
    if parent_map is None:
        parent_map = {start_node: None}

    if start_node not in visited and start_node in graph.get_nodes():
        visited.add(start_node)
        traversal_order.append(start_node)

        for neighbor, _, edge in graph.get_neighbors(start_node, include_blocked=include_blocked):
            if neighbor not in visited:
                parent_map[neighbor] = start_node
                depth_first_search_recursive(
                    graph=graph,
                    start_node=neighbor,
                    include_blocked=include_blocked,
                    visited=visited,
                    traversal_order=traversal_order,
                    parent_map=parent_map,
                )

    return DFSResult(start_node, visited, traversal_order, parent_map)


if __name__ == "__main__":
    g = Graph()
    g.add_edge("A", "B", 1.0)
    g.add_edge("B", "C", 2.0)
    g.add_edge("A", "D", 4.0)
    g.add_edge("D", "E", 1.5)

    print("Iterative DFS from A:")
    iter_res = depth_first_search_iterative(g, "A", explain=True)
    print("Traversal:", iter_res.traversal_order)
    for log in iter_res.step_logs:
        print(f"  [{log['step']}] {log['explanation']}")

    print("\nRecursive DFS from A:")
    rec_res = depth_first_search_recursive(g, "A")
    print("Traversal:", rec_res.traversal_order)
