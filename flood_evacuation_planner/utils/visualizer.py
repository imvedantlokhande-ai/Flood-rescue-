"""
Graph Visualization Utility for Flood Evacuation Route Planner.

Generates cartographic network maps rendering:
- Flooded / blocked roads in dashed red (with submerged markers)
- Risky / waterlogged roads in amber/orange
- Open roads in subtle slate gray
- Active evacuation route highlighted in thick emerald green
- Safe shelters in large blue squares
- Evacuee start location in gold
- Stranded cut-off nodes in crimson alert
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import os
from data_structures.graph import Graph, Edge


def render_graph_matplotlib(
    graph: Graph,
    evacuation_path: Optional[List[str]] = None,
    start_node: Optional[str] = None,
    stranded_nodes: Optional[List[str]] = None,
    output_image_path: Optional[str] = "flood_evacuation_map.png",
    title: str = "Riverdale City - Flood Evacuation Route Map",
) -> Any:
    """
    Render graph map using matplotlib with non-interactive Agg backend.

    Args:
        graph: Custom Graph instance.
        evacuation_path: List of node IDs in the recommended evacuation path.
        start_node: Node ID of user's starting location.
        stranded_nodes: List of node IDs completely cut off from safety.
        output_image_path: File path to save PNG (if None, does not save to disk).
        title: Title string for the plot.

    Returns:
        matplotlib Figure object (can be passed directly to st.pyplot).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # Headless backend safe for CLI and servers
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("[Visualizer] matplotlib is not installed. Rendering text fallback representation.")
        return None

    fig, ax = plt.subplots(figsize=(12, 10), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    # Build node coordinate lookup
    coords: Dict[str, Tuple[float, float]] = {}
    for node_id in graph.get_nodes():
        node_data = graph.get_node_data(node_id)
        x = float(node_data.get("x", 50.0))
        y = float(node_data.get("y", 50.0))
        coords[node_id] = (x, y)

    # Convert evacuation path into set of edge tuples for fast lookup
    evac_edges: Set[Tuple[str, str]] = set()
    if evacuation_path and len(evacuation_path) > 1:
        for i in range(len(evacuation_path) - 1):
            u, v = evacuation_path[i], evacuation_path[i + 1]
            evac_edges.add((min(u, v), max(u, v)))

    # 1. DRAW EDGES
    all_edges = graph.get_all_edges(unique_undirected=True)

    # Draw normal open edges
    for edge in all_edges:
        pair_key = (min(edge.u, edge.v), max(edge.u, edge.v))
        if pair_key in evac_edges:
            continue  # Drawn in route layer

        if edge.u in coords and edge.v in coords:
            x1, y1 = coords[edge.u]
            x2, y2 = coords[edge.v]

            if edge.is_blocked:
                # Flooded / submerged road: RED DASHED
                ax.plot([x1, x2], [y1, y2], color="#ef4444", linestyle="--", linewidth=2.5, alpha=0.85, zorder=2)
                # Plot X mark in middle of road
                mid_x, mid_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                ax.plot(mid_x, mid_y, marker="x", markersize=8, color="#f87171", markeredgewidth=2, zorder=3)
            elif edge.is_risky:
                # Risky road: AMBER DASH-DOT
                ax.plot([x1, x2], [y1, y2], color="#f59e0b", linestyle="-.", linewidth=2.0, alpha=0.9, zorder=2)
            else:
                # Normal open road: SLATE SOLID
                ax.plot([x1, x2], [y1, y2], color="#475569", linestyle="-", linewidth=1.5, alpha=0.7, zorder=1)

    # Draw evacuation path edges: THICK GREEN
    if evacuation_path and len(evacuation_path) > 1:
        for i in range(len(evacuation_path) - 1):
            u, v = evacuation_path[i], evacuation_path[i + 1]
            if u in coords and v in coords:
                x1, y1 = coords[u]
                x2, y2 = coords[v]
                ax.plot([x1, x2], [y1, y2], color="#22c55e", linestyle="-", linewidth=4.5, alpha=0.95, zorder=4)

    # 2. DRAW NODES
    safe_zones = set(graph.get_safe_zones())
    stranded_set = set(stranded_nodes if stranded_nodes else [])

    for node_id, (x, y) in coords.items():
        node_data = graph.get_node_data(node_id)
        name = node_data.get("name", node_id)
        elev = node_data.get("elevation_m", 0.0)

        if node_id == start_node:
            # Starting location: GOLD STAR / DIAMOND
            ax.scatter(x, y, s=320, color="#fbbf24", edgecolors="#ffffff", linewidths=2.5, marker="D", zorder=6)
            ax.text(x, y + 2.8, f"START: {name}", color="#fde047", fontsize=9, fontweight="bold", ha="center", zorder=7)
        elif node_id in safe_zones:
            # Emergency Safe Shelter: BLUE SQUARE
            cap = node_data.get("capacity", "")
            ax.scatter(x, y, s=350, color="#3b82f6", edgecolors="#60a5fa", linewidths=2.5, marker="s", zorder=6)
            ax.text(x, y + 2.8, f"[SHELTER] {name}\n(Elev: {elev}m | Cap: {cap})", color="#93c5fd", fontsize=8.5, fontweight="bold", ha="center", zorder=7)
        elif node_id in stranded_set:
            # Cut-off / Stranded Zone: CRIMSON CIRCLE
            ax.scatter(x, y, s=200, color="#dc2626", edgecolors="#fca5a5", linewidths=2.0, marker="o", zorder=5)
            ax.text(x, y - 2.8, f"[CUT OFF] {name}", color="#fca5a5", fontsize=7.5, ha="center", zorder=7)
        else:
            # Standard Location: SLATE CIRCLE
            ax.scatter(x, y, s=160, color="#1e293b", edgecolors="#94a3b8", linewidths=1.5, marker="o", zorder=5)
            ax.text(x, y - 2.5, f"{name} ({elev}m)", color="#cbd5e1", fontsize=7.5, ha="center", zorder=7)

    # 3. LEGEND & DECORATION
    legend_elements = [
        mpatches.Patch(color="#22c55e", label="Safe Evacuation Route (Green)"),
        mpatches.Patch(color="#ef4444", label="Flooded / Blocked Road (Red Dashed)"),
        mpatches.Patch(color="#f59e0b", label="Risky Waterlogged Road (Amber)"),
        mpatches.Patch(color="#475569", label="Open Road (Slate Gray)"),
        mpatches.Patch(color="#3b82f6", label="Safe Zone / Shelter (Blue Square)"),
        mpatches.Patch(color="#fbbf24", label="Evacuee Starting Location (Gold Diamond)"),
        mpatches.Patch(color="#dc2626", label="Stranded / Cut-off Zone (Red Circle)"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper left",
        facecolor="#1e293b",
        edgecolor="#475569",
        fontsize=8.5,
        labelcolor="#e2e8f0",
    )

    ax.set_title(title, color="#f8fafc", fontsize=14, fontweight="bold", pad=15)
    ax.tick_params(colors="#64748b")
    ax.grid(True, color="#334155", linestyle=":", alpha=0.6)

    # Set margins
    xs = [pt[0] for pt in coords.values()]
    ys = [pt[1] for pt in coords.values()]
    if xs and ys:
        ax.set_xlim(min(xs) - 8, max(xs) + 12)
        ax.set_ylim(min(ys) - 8, max(ys) + 12)

    plt.tight_layout()

    if output_image_path:
        plt.savefig(output_image_path, dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
        print(f"[Visualizer] Map saved successfully to {output_image_path}")

    return fig


def print_ascii_graph(
    graph: Graph,
    evacuation_path: Optional[List[str]] = None,
    start_node: Optional[str] = None,
) -> None:
    """Print a clean CLI text representation of the route and blocked network status."""
    print("\n" + "=" * 65)
    print("           FLOOD EVACUATION TOPOLOGY REPORT")
    print("=" * 65)
    print(f"Origin Node: {start_node}")
    if evacuation_path:
        print(f"Evacuation Route Path ({len(evacuation_path) - 1} hops):")
        print("  " + "  ===>  ".join(evacuation_path))
    else:
        print("Evacuation Route: NONE (Location is cut off or no evacuation needed)")

    print("\nRoad Network Status:")
    blocked = [e for e in graph.get_all_edges() if e.is_blocked]
    risky = [e for e in graph.get_all_edges() if e.is_risky]
    print(f"  * Flooded / Closed Roads: {len(blocked)}")
    for b in blocked[:8]:
        print(f"      [BLOCKED] {b.road_id}: {b.u} <--> {b.v} (Depth: {b.water_level_m}m)")
    if len(blocked) > 8:
        print(f"      ... and {len(blocked) - 8} more blocked roads.")

    print(f"  * Risky Roads (Speed Penalty): {len(risky)}")
    for r in risky[:5]:
        print(f"      [RISKY]   {r.road_id}: {r.u} <--> {r.v} (Effective: {r.effective_weight:.1f}km)")

    print("=" * 65 + "\n")
