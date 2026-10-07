"""
Connected Components and Cut-Off Zone Analysis using DFS.

Strict Rule Compliance:
Uses DFS implemented from scratch to partition the flood-damaged city road graph
into connected components and identify isolated population pockets ("stranded zones")
that have zero navigable access to any designated emergency safe zone.
"""

from typing import Dict, List, Set, Tuple, Any
from data_structures.graph import Graph
from algorithms.dfs.dfs import depth_first_search_iterative


class ComponentAnalysisResult:
    """Encapsulates graph component partitioning and stranded zone identification."""

    def __init__(
        self,
        components: List[Set[str]],
        safe_zone_map: Dict[int, List[str]],
        stranded_components: List[Set[str]],
        stranded_nodes: List[str],
        accessible_components: List[Set[str]],
    ) -> None:
        self.components = components  # All isolated subgraphs
        self.total_components = len(components)
        self.safe_zone_map = safe_zone_map  # Component index -> [safe_zone_ids]
        self.stranded_components = stranded_components  # Components with 0 safe zones
        self.stranded_nodes = stranded_nodes  # All locations cut off from safety
        self.accessible_components = accessible_components  # Components containing >=1 safe zone

    def is_node_stranded(self, node_id: str) -> bool:
        """Check whether a specific location is completely cut off from all safe shelters."""
        return node_id in self.stranded_nodes


def find_connected_components(
    graph: Graph,
    include_blocked: bool = False,
) -> ComponentAnalysisResult:
    """
    Decompose the graph into disjoint connected components using Depth-First Search.

    Args:
        graph: Graph instance representing the road network.
        include_blocked: If False (standard during floods), respects flooded/blocked roads.

    Returns:
        ComponentAnalysisResult detailing all clusters, safe zone distribution, and stranded nodes.
    """
    all_nodes = graph.get_nodes()
    safe_zones = set(graph.get_safe_zones())
    visited_global: Set[str] = set()

    components: List[Set[str]] = []
    safe_zone_map: Dict[int, List[str]] = {}
    stranded_components: List[Set[str]] = []
    stranded_nodes: List[str] = []
    accessible_components: List[Set[str]] = []

    for node in all_nodes:
        if node not in visited_global:
            # Run DFS from this unvisited node
            dfs_res = depth_first_search_iterative(
                graph,
                start_node=node,
                include_blocked=include_blocked,
            )

            component_set = dfs_res.visited_nodes
            visited_global.update(component_set)

            comp_idx = len(components)
            components.append(component_set)

            # Check which safe zones exist inside this component
            present_safe_zones = [sz for sz in component_set if sz in safe_zones]
            safe_zone_map[comp_idx] = present_safe_zones

            if not present_safe_zones:
                # This entire cluster has no connection to any shelter!
                stranded_components.append(component_set)
                stranded_nodes.extend(sorted(list(component_set)))
            else:
                accessible_components.append(component_set)

    return ComponentAnalysisResult(
        components=components,
        safe_zone_map=safe_zone_map,
        stranded_components=stranded_components,
        stranded_nodes=stranded_nodes,
        accessible_components=accessible_components,
    )


if __name__ == "__main__":
    # Self-test demonstration
    g = Graph()
    # Island 1: Connected to Safe Zone 1
    g.add_node("LOC_A", {"name": "North Downtown"})
    g.add_node("SZ_01", {"name": "Hospital Shelter", "is_safe_zone": True})
    g.add_edge("LOC_A", "SZ_01", 3.0)

    # Island 2: Cut off due to flooded roads (no safe zone)
    g.add_node("LOC_B", {"name": "South Pier"})
    g.add_node("LOC_C", {"name": "Fishermen Village"})
    g.add_edge("LOC_B", "LOC_C", 1.2)

    # Bridge between A and B was submerged
    g.add_edge("LOC_A", "LOC_B", 4.0)
    g.block_edge("LOC_A", "LOC_B")

    analysis = find_connected_components(g)
    print("Total Disconnected Components:", analysis.total_components)
    print("Stranded Locations (CUT OFF FROM ALL SHELTERS):", analysis.stranded_nodes)
    for idx, comp in enumerate(analysis.components):
        print(f"Component #{idx + 1}: {sorted(list(comp))} -> Shelters: {analysis.safe_zone_map[idx]}")
