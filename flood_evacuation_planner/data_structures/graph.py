"""
Custom Graph Data Structure using an Adjacency List.

Strict Rule Compliance:
Implemented completely from scratch without using networkx, scipy, or any
external graph library. Supports dynamic edge blocking/unblocking, edge penalty weights,
and node attributes.
"""

from typing import Dict, List, Optional, Tuple, Any, Set


class Edge:
    """Represents a connection (road) between two graph nodes."""

    def __init__(
        self,
        u: str,
        v: str,
        weight: float,
        road_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.u: str = u
        self.v: str = v
        self.weight: float = weight  # Base distance in kilometers
        self.effective_weight: float = weight  # Distance adjusted for flood risk penalty
        self.road_id: str = road_id if road_id else f"{u}_{v}"
        self.is_blocked: bool = False  # True if road is submerged/impassable
        self.is_risky: bool = False  # True if road has moderate water depth
        self.water_level_m: float = 0.0
        self.attributes: Dict[str, Any] = attributes if attributes is not None else {}

    def __repr__(self) -> str:
        status = "BLOCKED" if self.is_blocked else ("RISKY" if self.is_risky else "OPEN")
        return (
            f"Edge({self.u} <-> {self.v}, base_wt={self.weight:.2f}km, "
            f"eff_wt={self.effective_weight:.2f}km, [{status}], water={self.water_level_m:.2f}m)"
        )


class Graph:
    """
    Undirected / Directed Graph implemented with an Adjacency List.

    Structure:
    - _nodes: Dict[node_id, Dict[str, Any]] storing node metadata (name, elevation, is_safe_zone, capacity, coordinates).
    - _adjacency: Dict[node_id, List[Edge]] storing outgoing/incident edges.
    - _edge_lookup: Dict[Tuple[str, str], Edge] for O(1) edge retrieval.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._adjacency: Dict[str, List[Edge]] = {}
        self._edge_lookup: Dict[Tuple[str, str], Edge] = {}

    def add_node(self, node_id: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a location node to the graph.

        Args:
            node_id: Unique string identifier (e.g. 'LOC_01', 'SZ_01').
            attributes: Optional metadata such as name, elevation_m, is_safe_zone, capacity, x, y.
        """
        if node_id not in self._nodes:
            self._nodes[node_id] = attributes if attributes is not None else {}
            self._adjacency[node_id] = []
        else:
            if attributes:
                self._nodes[node_id].update(attributes)

    def add_edge(
        self,
        u: str,
        v: str,
        weight: float,
        road_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        bidirectional: bool = True,
    ) -> None:
        """
        Add a weighted edge (road) between two nodes.

        Args:
            u: First node ID.
            v: Second node ID.
            weight: Distance in kilometers (must be positive).
            road_id: Unique ID for the road.
            attributes: Road metadata (name, baseline_water_level, etc.).
            bidirectional: If True, adds edge in both directions (undirected road).
        """
        if u not in self._nodes:
            self.add_node(u)
        if v not in self._nodes:
            self.add_node(v)

        edge_fwd = Edge(u, v, weight, road_id=road_id, attributes=attributes)
        self._adjacency[u].append(edge_fwd)
        self._edge_lookup[(u, v)] = edge_fwd

        if bidirectional:
            edge_rev = Edge(v, u, weight, road_id=road_id, attributes=attributes)
            self._adjacency[v].append(edge_rev)
            self._edge_lookup[(v, u)] = edge_rev

    def get_neighbors(
        self, node_id: str, include_blocked: bool = False
    ) -> List[Tuple[str, float, Edge]]:
        """
        Get all accessible neighbors of a node.

        Args:
            node_id: Node to inspect.
            include_blocked: If False, skips flooded/blocked roads.

        Returns:
            List of tuples: (neighbor_node_id, effective_weight, Edge_instance)
        """
        if node_id not in self._adjacency:
            return []

        neighbors: List[Tuple[str, float, Edge]] = []
        for edge in self._adjacency[node_id]:
            if not include_blocked and edge.is_blocked:
                continue
            neighbors.append((edge.v, edge.effective_weight, edge))
        return neighbors

    def block_edge(self, u: str, v: str) -> bool:
        """
        Mark a road between u and v as impassable (flooded).
        Blocks both (u, v) and (v, u) if bidirectional.
        """
        found = False
        if (u, v) in self._edge_lookup:
            self._edge_lookup[(u, v)].is_blocked = True
            found = True
        if (v, u) in self._edge_lookup:
            self._edge_lookup[(v, u)].is_blocked = True
            found = True
        return found

    def unblock_edge(self, u: str, v: str) -> bool:
        """Unblock a road between u and v."""
        found = False
        if (u, v) in self._edge_lookup:
            self._edge_lookup[(u, v)].is_blocked = False
            found = True
        if (v, u) in self._edge_lookup:
            self._edge_lookup[(v, u)].is_blocked = False
            found = True
        return found

    def is_edge_blocked(self, u: str, v: str) -> bool:
        """Check if road between u and v is blocked."""
        edge = self._edge_lookup.get((u, v))
        return edge.is_blocked if edge else False

    def get_edge(self, u: str, v: str) -> Optional[Edge]:
        """Return the Edge instance between u and v, or None."""
        return self._edge_lookup.get((u, v))

    def get_edge_weight(self, u: str, v: str, risk_adjusted: bool = False) -> Optional[float]:
        """Return the weight (base or risk-adjusted effective weight) of an edge."""
        edge = self.get_edge(u, v)
        if not edge:
            return None
        return edge.effective_weight if risk_adjusted else edge.weight

    def get_node_data(self, node_id: str) -> Dict[str, Any]:
        """Return metadata dictionary for a node."""
        return self._nodes.get(node_id, {})

    def get_nodes(self) -> List[str]:
        """Return list of all node IDs in the graph."""
        return list(self._nodes.keys())

    def get_safe_zones(self) -> List[str]:
        """Return list of node IDs marked as safe zones / evacuation shelters."""
        return [
            node_id
            for node_id, data in self._nodes.items()
            if data.get("is_safe_zone", False)
        ]

    def get_all_edges(self, unique_undirected: bool = True) -> List[Edge]:
        """
        Return list of edges in the graph.
        If unique_undirected is True, returns only one representation for undirected pairs.
        """
        if not unique_undirected:
            return list(self._edge_lookup.values())

        seen_pairs: Set[Tuple[str, str]] = set()
        unique_edges: List[Edge] = []
        for (u, v), edge in self._edge_lookup.items():
            pair_key = (min(u, v), max(u, v))
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                unique_edges.append(edge)
        return unique_edges

    def reset_all_blocks(self) -> None:
        """Reset all edges to unblocked status and reset effective weights to base weights."""
        for edge in self._edge_lookup.values():
            edge.is_blocked = False
            edge.is_risky = False
            edge.water_level_m = 0.0
            edge.effective_weight = edge.weight

    def clone(self) -> "Graph":
        """Create a deep copy of the graph with identical nodes and edges."""
        new_g = Graph()
        for node_id, attrs in self._nodes.items():
            new_g.add_node(node_id, dict(attrs))

        seen: Set[Tuple[str, str]] = set()
        for (u, v), edge in self._edge_lookup.items():
            pair = (min(u, v), max(u, v))
            if pair not in seen:
                seen.add(pair)
                new_g.add_edge(
                    u,
                    v,
                    edge.weight,
                    road_id=edge.road_id,
                    attributes=dict(edge.attributes),
                    bidirectional=True,
                )
                new_edge_fwd = new_g.get_edge(u, v)
                new_edge_rev = new_g.get_edge(v, u)
                for e in (new_edge_fwd, new_edge_rev):
                    if e:
                        e.is_blocked = edge.is_blocked
                        e.is_risky = edge.is_risky
                        e.water_level_m = edge.water_level_m
                        e.effective_weight = edge.effective_weight
        return new_g

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self) -> str:
        return f"Graph(nodes={len(self._nodes)}, edges={len(self.get_all_edges())})"


if __name__ == "__main__":
    g = Graph()
    g.add_node("A", {"name": "Downtown", "elevation_m": 12.0})
    g.add_node("B", {"name": "Market", "elevation_m": 8.0})
    g.add_node("SZ", {"name": "Shelter", "is_safe_zone": True, "elevation_m": 50.0})
    g.add_edge("A", "B", 2.0, road_id="RD_1")
    g.add_edge("B", "SZ", 3.5, road_id="RD_2")

    print("Created graph:", g)
    print("Neighbors of A:", g.get_neighbors("A"))
    print("Blocking RD_1 (A <-> B)...")
    g.block_edge("A", "B")
    print("Neighbors of A after block (unblocked only):", g.get_neighbors("A"))
    print("Neighbors of A including blocked:", g.get_neighbors("A", include_blocked=True))
