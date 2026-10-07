"""
Streamlit Web UI for Flood Evacuation Route Planner.

Run with:
    streamlit run flood_evacuation_planner/app.py
"""

import sys
import os
from typing import Dict, List, Any

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import streamlit as st
except ImportError:
    print("[Error] Streamlit is not installed. Run: pip install streamlit")
    sys.exit(1)

from data_structures.graph import Graph
from utils.loader import load_city_graph, load_rainfall_data
from modules.route_planner import plan_evacuation, PlanningResult
from modules.simulation import run_flood_simulation
from utils.visualizer import render_graph_matplotlib


def get_base_data():
    """Load baseline graph and rainfall telemetry."""
    graph_path = os.path.join(PROJECT_ROOT, "data", "city_graph.json")
    rain_path = os.path.join(PROJECT_ROOT, "data", "rainfall_data.json")
    graph = load_city_graph(graph_path)
    rainfall_info = load_rainfall_data(rain_path)
    return graph, rainfall_info


def main():
    st.set_page_config(
        page_title="Flood Evacuation Route Planner",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom Header Style
    st.markdown(
        """
        <style>
        .metric-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }
        .shelter-badge {
            background-color: #1d4ed8;
            color: #ffffff;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🌊 Flood Evacuation Route Planner")
    st.caption("Custom DSA Implementation: Adjacency Graph • Singly Linked-List Queue • Binary Min-Heap • BFS • DFS • Dijkstra")

    base_graph, base_rainfall = get_base_data()
    all_node_ids = base_graph.get_nodes()
    node_labels = {nid: f"{nid} - {base_graph.get_node_data(nid).get('name', nid)}" for nid in all_node_ids}

    # ==========================================
    # SIDEBAR CONTROLS
    # ==========================================
    st.sidebar.header("🕹️ Simulation Parameters")

    selected_origin = st.sidebar.selectbox(
        "Evacuee Origin Location:",
        options=all_node_ids,
        format_func=lambda nid: node_labels[nid],
        index=0,
    )

    st.sidebar.subheader("🌧️ Weather & Hydrologic Telemetry")
    sim_rain_hr = st.sidebar.slider(
        "Current Rainfall Rate (mm/hr):",
        min_value=0.0,
        max_value=120.0,
        value=float(base_rainfall.get("rainfall_mm_per_hr", 48.5)),
        step=2.5,
    )

    sim_rain_24h = st.sidebar.slider(
        "Cumulative 24h Rain (mm):",
        min_value=0.0,
        max_value=300.0,
        value=float(base_rainfall.get("rainfall_last_24h_mm", 135.0)),
        step=5.0,
    )

    sim_river = st.sidebar.slider(
        "River Datum Swell (m above normal):",
        min_value=0.0,
        max_value=5.0,
        value=float(base_rainfall.get("river_level_above_normal_m", 2.6)),
        step=0.2,
    )

    flood_multiplier = st.sidebar.slider(
        "Road Water Depth Multiplier:",
        min_value=0.0,
        max_value=3.0,
        value=1.0,
        step=0.1,
    )

    st.sidebar.markdown("---")
    explain_mode = st.sidebar.checkbox("🔍 Step-by-Step DSA Explain Mode", value=False)
    show_compare = st.sidebar.checkbox("📊 Compare Strategies (Dijkstra vs BFS)", value=True)

    # Scale water levels according to multiplier
    base_water_dict = base_rainfall.get("water_levels_by_road", {})
    scaled_water_dict = {rid: round(val * flood_multiplier, 2) for rid, val in base_water_dict.items()}

    # Run Planning Pipeline
    active_graph = base_graph.clone()
    plan_result = plan_evacuation(
        graph=active_graph,
        start_node=selected_origin,
        rainfall_mm_per_hr=sim_rain_hr,
        rainfall_last_24h_mm=sim_rain_24h,
        water_levels=scaled_water_dict,
        river_level_above_normal_m=sim_river,
        explain=explain_mode,
    )

    # ==========================================
    # MAIN DASHBOARD PANELS
    # ==========================================
    risk = plan_result.risk_assessment

    col_risk1, col_risk2, col_risk3 = st.columns([1.2, 1, 1])
    with col_risk1:
        if risk.risk_level == "SEVERE":
            st.error(f"🚨 Flood Risk Level: **{risk.risk_level}** (Score: {risk.score}/100)")
        elif risk.risk_level == "HIGH":
            st.warning(f"⚠️ Flood Risk Level: **{risk.risk_level}** (Score: {risk.score}/100)")
        elif risk.risk_level == "MODERATE":
            st.info(f"📢 Flood Risk Level: **{risk.risk_level}** (Score: {risk.score}/100)")
        else:
            st.success(f"✅ Flood Risk Level: **{risk.risk_level}** (Score: {risk.score}/100)")
        st.write(risk.summary)

    with col_risk2:
        if plan_result.flood_summary:
            fs = plan_result.flood_summary
            st.metric("Flooded Roads (Closed)", len(fs.blocked_roads), f"Max depth: {fs.max_water_level_m:.2f}m")
            st.metric("Risky Roads (Penalized)", len(fs.risky_roads))
        else:
            st.metric("Road Status", "All Open", "Normal conditions")

    with col_risk3:
        if plan_result.is_stranded:
            st.metric("Reachability Status", "STRANDED", "0 Shelters accessible")
        elif plan_result.primary_route:
            st.metric(
                "Shortest Evac Distance",
                f"{plan_result.primary_route.distance_km:.2f} km",
                f"{plan_result.primary_route.hops} intersections",
            )
        else:
            st.metric("Reachability Status", "Safe / In Shelter", "0 km")

    # ==========================================
    # STRANDED / EVACUATION STATUS
    # ==========================================
    if not risk.is_dangerous:
        st.success("🟢 **No Evacuation Needed**: Weather conditions are within municipal drainage tolerances. Stay tuned to local advisories.")
    elif plan_result.is_stranded:
        st.error("🆘 **CRITICAL ALERT: NO SAFE ROAD ROUTE EXISTS!**")
        st.error("The selected origin is cut off by submerged roads. Immediate watercraft/air rescue required.")
        with st.expander("📍 View Cut-Off / Stranded Communities in this Isolated Pocket", expanded=True):
            for area in plan_result.stranded_areas:
                st.write(f"- 🔴 {area}")
    else:
        route = plan_result.primary_route
        if route:
            st.subheader(f"🛡️ Recommended Evacuation Route: {route.target_name}")
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            col_r1.metric("Destination Shelter", route.target_name)
            col_r2.metric("Shelter Capacity", f"{route.capacity:,} evacuees")
            col_r3.metric("Est. Walking Time", f"{route.est_walking_minutes:.1f} mins", "at 4.5 km/h")
            col_r4.metric("Est. Vehicle Time", f"{route.est_vehicle_minutes:.1f} mins", "at 25.0 km/h")

            # Route visual breadcrumbs
            path_display = " ➔ ".join([f"**{name}**" for name in route.path_names])
            st.markdown(f"**Turn-by-Turn Route:** {path_display}")

    # ==========================================
    # GRAPH VISUALIZATION & MAP
    # ==========================================
    st.markdown("---")
    st.subheader("🗺️ City Road Network & Inundation Map")

    path_nodes = plan_result.primary_route.path if plan_result.primary_route else []
    stranded_list = plan_result.component_analysis.stranded_nodes if plan_result.component_analysis else []

    fig = render_graph_matplotlib(
        graph=active_graph,
        evacuation_path=path_nodes,
        start_node=selected_origin,
        stranded_nodes=stranded_list,
        output_image_path=None,
        title=f"Riverdale City Road Graph • Origin: {node_labels[selected_origin]}",
    )
    if fig is not None:
        st.pyplot(fig, use_container_width=True)

    # ==========================================
    # STRATEGY COMPARISON TAB
    # ==========================================
    if show_compare and plan_result.primary_route:
        st.markdown("---")
        st.subheader("📊 Evacuation Strategy Comparison (DSA Trade-Offs)")

        rows = []
        # Dijkstra Primary
        d = plan_result.primary_route
        rows.append({
            "Algorithm": "Dijkstra (Min-Heap)",
            "Strategy": "Shortest Physical Distance (km)",
            "Destination": d.target_name,
            "Distance (km)": d.distance_km,
            "Intersections": d.hops,
            "Vehicle Time": f"{d.est_vehicle_minutes:.1f} min",
            "Path": " ➔ ".join(d.path),
        })

        # Risk-Adjusted Dijkstra
        if plan_result.risk_adjusted_route:
            rr = plan_result.risk_adjusted_route
            rows.append({
                "Algorithm": "Risk-Penalized Dijkstra",
                "Strategy": "Waterlogged Road Avoidance",
                "Destination": rr.target_name,
                "Distance (km)": rr.distance_km,
                "Intersections": rr.hops,
                "Vehicle Time": f"{rr.est_vehicle_minutes:.1f} min",
                "Path": " ➔ ".join(rr.path),
            })

        # BFS Fewest Hops
        if plan_result.fewest_hops_route:
            br = plan_result.fewest_hops_route
            rows.append({
                "Algorithm": "Breadth-First Search (Queue)",
                "Strategy": "Fewest Road Segments / Turns",
                "Destination": br.target_name,
                "Distance (km)": br.distance_km,
                "Intersections": br.hops,
                "Vehicle Time": f"{br.est_vehicle_minutes:.1f} min",
                "Path": " ➔ ".join(br.path),
            })

        st.table(rows)

    # ==========================================
    # STEP-BY-STEP EXPLAIN MODE
    # ==========================================
    if explain_mode:
        st.markdown("---")
        st.subheader("🎓 Step-by-Step DSA Explain Mode (Viva Logs)")

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.markdown("#### 1. BFS Queue Operations (`CustomQueue`)")
            if plan_result.bfs_result and plan_result.bfs_result.step_logs:
                for log in plan_result.bfs_result.step_logs[:10]:
                    st.code(f"Step {log['step']}: {log['explanation']}\nQueue: {log['queue_state']}", language="text")
            else:
                st.write("BFS logs available during active search.")

        with col_ex2:
            st.markdown("#### 2. Dijkstra MinHeap Operations (`MinHeap`)")
            from algorithms.dijkstra.dijkstra import dijkstra_shortest_path
            d_trace = dijkstra_shortest_path(active_graph, selected_origin, explain=True)
            for log in d_trace.heap_trace[:10]:
                st.code(f"Step {log['step']}: Settled '{log.get('settled_node')}' ({log.get('dist')} km)\nMinHeap: {log.get('heap_snapshot')[:3]}", language="text")

    # ==========================================
    # MULTI-TIMESTEP SIMULATION SECTION
    # ==========================================
    st.markdown("---")
    st.subheader("⏱️ Dynamic Multi-Timestep Flood Escalation Simulation")
    if st.button("▶️ Run 5-Timestep Escalation Simulation (T+0h to T+4h)"):
        sim_reports = run_flood_simulation(base_graph, selected_origin, base_rainfall)
        for rep in sim_reports:
            with st.expander(f"Step #{rep.step_index}: {rep.time_label} • Risk: {rep.risk_level}", expanded=(rep.step_index in [0, 2, 4])):
                st.write(f"**Rainfall Rate:** {rep.rainfall_mm_per_hr} mm/hr | **24h:** {rep.rainfall_last_24h_mm} mm")
                st.write(f"**Hydrologic Note:** {rep.description}")
                st.write(f"**Blocked Road Count:** {rep.blocked_roads_count}")
                if rep.is_stranded:
                    st.error("🚨 Evacuee became stranded! No open route to shelter.")
                else:
                    st.success(f"Route: {' ➔ '.join(rep.route_path)} to **{rep.target_shelter_name}** ({rep.route_distance_km:.2f} km)")


if __name__ == "__main__":
    main()
