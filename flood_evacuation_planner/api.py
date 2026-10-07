"""
FastAPI Server for Flood Evacuation Route Planner.

Wraps existing custom DSA modules:
- Graph (adjacency list)
- CustomQueue (BFS reachability)
- CustomStack (DFS cut-off zones)
- MinHeap (Dijkstra shortest path & NGO dispatch priority queue)
- Manual Haversine nearest-node snapping
- Multi-step storm simulation
- Real-time automated data feed with Server-Sent Events (SSE)
- Automated NGO rescue dispatch and alert notifications
"""

import os
import sys
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Load .env
load_dotenv()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from data_structures.graph import Graph
from utils.loader import load_city_graph, load_rainfall_data
from algorithms.haversine.haversine import haversine_distance_km, find_nearest_node
from modules.route_planner import plan_evacuation
from modules.simulation import run_flood_simulation
from algorithms.bfs.bfs import breadth_first_search
from algorithms.dfs.dfs import depth_first_search_iterative
from algorithms.dijkstra.dijkstra import dijkstra_shortest_path
from services.rescue_dispatcher import (
    dispatch_stranded_areas,
    get_all_requests,
    acknowledge_request,
)
from services.notifier import get_notification_logs, notify_ngo_dispatch
from services.data_feed import (
    add_sse_client,
    remove_sse_client,
    get_latest_snapshot,
    set_user_node,
    start_background_task,
    stop_background_task,
)

GRAPH_FILE = os.path.join(CURRENT_DIR, "data", "city_graph.json")
RAINFALL_FILE = os.path.join(CURRENT_DIR, "data", "rainfall_data.json")
FRONTEND_DIR = os.path.join(CURRENT_DIR, "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage lifecycle of background telemetry feeds."""
    start_background_task()
    yield
    stop_background_task()


app = FastAPI(
    title="Flood Evacuation Route Planner API",
    version="2.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static assets (style.css, app.js)
if os.path.exists(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================
class SnapInput(BaseModel):
    lat: float = Field(..., description="Latitude to snap")
    lng: float = Field(..., description="Longitude to snap")


class EvacuateInput(BaseModel):
    start_node: Optional[str] = Field(None, description="Graph node ID of starting location")
    user_lat: Optional[float] = Field(None, description="User latitude (snapped if start_node omitted)")
    user_lng: Optional[float] = Field(None, description="User longitude (snapped if start_node omitted)")
    rainfall_mm_per_hr: Optional[float] = Field(48.5, description="Rainfall rate in mm/hr")
    rainfall_last_24h_mm: Optional[float] = Field(135.0, description="24h rainfall total in mm")
    water_levels: Optional[Dict[str, float]] = Field(None, description="Road ID -> water depth in meters")
    river_level_above_normal_m: Optional[float] = Field(2.6, description="River swell in meters")


class SimulateInput(BaseModel):
    step_index: int = Field(..., ge=0, le=4, description="Timestep index (0 to 4)")
    start_node: Optional[str] = Field("LOC_01", description="Evacuee starting location ID")
    user_lat: Optional[float] = None
    user_lng: Optional[float] = None


# ==========================================
# ENDPOINT 1: GET /api/graph
# ==========================================
@app.get("/api/graph")
def get_graph():
    """Return nodes, edges, safe zones, NGO bases, and city metadata."""
    if not os.path.exists(GRAPH_FILE):
        raise HTTPException(status_code=404, detail="city_graph.json not found")
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ==========================================
# ENDPOINT 2: GET /api/stream (SSE Live Updates)
# ==========================================
@app.get("/api/stream")
async def stream_live_updates(request: Request):
    """
    Server-Sent Events endpoint pushing real-time environmental telemetry,
    evacuation route re-plans, and NGO dispatch updates.
    """
    async def event_generator():
        # Immediately send current state if ready
        current_state = get_latest_snapshot()
        if current_state:
            yield f"data: {json.dumps(current_state)}\n\n"

        queue: asyncio.Queue = asyncio.Queue()
        add_sse_client(queue)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=12.0)
                    yield f"data: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield ": ping\n\n"
        finally:
            remove_sse_client(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==========================================
# ENDPOINT 3: POST /api/snap
# ==========================================
@app.post("/api/snap")
def snap_coordinate(data: SnapInput):
    """
    Snap user coordinates to nearest road network intersection
    using pure manual Haversine distance.
    """
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        graph_raw = json.load(f)

    locations = graph_raw.get("locations", [])
    nearest_node, dist_km = find_nearest_node(locations, data.lat, data.lng)
    node_info = next((l for l in locations if l["id"] == nearest_node), {})
    set_user_node(nearest_node, data.lat, data.lng)

    return {
        "nearest_node": nearest_node,
        "nearest_name": node_info.get("name", nearest_node),
        "distance_km": round(dist_km, 3),
        "lat": node_info.get("lat", data.lat),
        "lng": node_info.get("lng", data.lng),
    }


# ==========================================
# ENDPOINT 4: GET /api/dispatch
# ==========================================
@app.get("/api/dispatch")
def get_dispatch():
    """Return all rescue missions and notification logs."""
    requests = get_all_requests()
    logs = get_notification_logs()
    active_count = sum(1 for r in requests if r.get("status") not in ("Resolved", "Closed"))
    airlift_count = sum(1 for r in requests if r.get("needs_airlift", False))

    return {
        "requests": requests,
        "total_count": len(requests),
        "active_count": active_count,
        "airlift_count": airlift_count,
        "notification_logs": logs,
    }


# ==========================================
# ENDPOINT 5: POST /api/dispatch/{request_id}/ack
# ==========================================
@app.post("/api/dispatch/{request_id}/ack")
def acknowledge_dispatch(request_id: str):
    """NGO responder acknowledges emergency rescue mission."""
    updated = acknowledge_request(request_id)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    return {
        "success": True,
        "message": f"Rescue mission {request_id} acknowledged by responding NGO",
        "request": updated,
    }


# ==========================================
# ENDPOINT 6: POST /api/evacuate
# ==========================================
@app.post("/api/evacuate")
def evacuate(data: EvacuateInput):
    """
    Compute evacuation route using custom DSA engine:
    1. Snaps user coordinate to nearest node using Haversine
    2. Calculates flood risk (LOW / MODERATE / HIGH / SEVERE)
    3. Marks flooded edges (>=0.5m) and risky edges (0.2-0.5m)
    4. Finds reachable and stranded areas using BFS/DFS
    5. Computes shortest safe route to nearest safe zone via MinHeap Dijkstra
    6. Triggers NGO dispatch for stranded zones
    7. Returns coordinates, distances, ETAs, and algorithm trace
    """
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        graph_raw = json.load(f)

    locations = graph_raw.get("locations", [])
    loc_by_id = {loc["id"]: loc for loc in locations}
    ngo_bases = graph_raw.get("ngo_bases", [])

    # Snap to nearest node if lat/lng supplied
    start_node = data.start_node
    snapped_dist_km = 0.0

    if not start_node or start_node not in loc_by_id:
        if data.user_lat is not None and data.user_lng is not None:
            start_node, snapped_dist_km = find_nearest_node(locations, data.user_lat, data.user_lng)
        else:
            start_node = "LOC_01"

    set_user_node(start_node, data.user_lat, data.user_lng)

    # Default water levels if omitted
    with open(RAINFALL_FILE, "r", encoding="utf-8") as f:
        rainfall_data = json.load(f)

    water_dict = data.water_levels if data.water_levels is not None else rainfall_data.get("water_levels_by_road", {})

    graph = load_city_graph(GRAPH_FILE)

    # Master planning pipeline
    plan_res = plan_evacuation(
        graph=graph,
        start_node=start_node,
        rainfall_mm_per_hr=data.rainfall_mm_per_hr,
        rainfall_last_24h_mm=data.rainfall_last_24h_mm,
        water_levels=water_dict,
        river_level_above_normal_m=data.river_level_above_normal_m,
        explain=True,
    )

    # Standalone trace collection
    bfs_res = breadth_first_search(graph, start_node=start_node, explain=True)
    dfs_res = depth_first_search_iterative(graph, start_node=start_node, explain=True)
    dijkstra_res = dijkstra_shortest_path(graph, start_node=start_node, explain=True)

    # Format route with geographic coordinates
    route_data = None
    if plan_res.primary_route:
        pr = plan_res.primary_route
        coords = [
            {
                "id": nid,
                "name": loc_by_id.get(nid, {}).get("name", nid),
                "lat": loc_by_id.get(nid, {}).get("lat", 0.0),
                "lng": loc_by_id.get(nid, {}).get("lng", 0.0),
                "elevation_m": loc_by_id.get(nid, {}).get("elevation_m", 0.0),
            }
            for nid in pr.path
        ]
        route_data = {
            "target_safe_zone": pr.target_safe_zone,
            "target_name": pr.target_name,
            "path": pr.path,
            "path_names": pr.path_names,
            "coordinates": coords,
            "distance_km": pr.distance_km,
            "hops": pr.hops,
            "est_walking_minutes": pr.est_walking_minutes,
            "est_vehicle_minutes": pr.est_vehicle_minutes,
            "capacity": pr.capacity,
        }

    flooded_edges = []
    risky_edges = []
    if plan_res.flood_summary:
        for e in plan_res.flood_summary.blocked_roads:
            flooded_edges.append({"road_id": e.road_id, "from": e.u, "to": e.v, "water_depth_m": e.water_level_m})
        for e in plan_res.flood_summary.risky_roads:
            risky_edges.append({"road_id": e.road_id, "from": e.u, "to": e.v, "water_depth_m": e.water_level_m})

    # Auto NGO Dispatch for stranded areas
    dispatches = dispatch_stranded_areas(
        graph=graph,
        stranded_nodes=plan_res.stranded_areas,
        risk_score=plan_res.risk_assessment.score,
        locations_by_id=loc_by_id,
        ngo_bases=ngo_bases,
    )
    for req in dispatches:
        if req.status in ("Sent", "NEEDS AIRLIFT/BOAT"):
            notify_ngo_dispatch(req.to_dict(), risk_level=plan_res.risk_assessment.risk_level)

    return {
        "start_node": start_node,
        "start_name": plan_res.start_name,
        "snapped_distance_km": round(snapped_dist_km, 3),
        "risk_level": plan_res.risk_assessment.risk_level,
        "risk_score": plan_res.risk_assessment.score,
        "is_dangerous": plan_res.risk_assessment.is_dangerous,
        "risk_summary": plan_res.risk_assessment.summary,
        "status_message": plan_res.status_message,
        "is_stranded": plan_res.is_stranded,
        "stranded_areas": plan_res.stranded_areas,
        "reachable_set": sorted(list(bfs_res.reachable_nodes)),
        "flooded_edges": flooded_edges,
        "risky_edges": risky_edges,
        "route": route_data,
        "ngo_requests": get_all_requests(),
        "algorithm_trace": {
            "bfs_order": bfs_res.traversal_order,
            "bfs_hops": bfs_res.hop_distances,
            "dfs_stack_order": dfs_res.traversal_order,
            "dijkstra_settled_order": dijkstra_res.settled_order,
            "dijkstra_distances": {k: (round(v, 2) if v < float("inf") else "INF") for k, v in dijkstra_res.distances.items()},
            "heap_steps": dijkstra_res.heap_trace,
        },
    }


# ==========================================
# ENDPOINT: GET /api/weather
# ==========================================
@app.get("/api/weather")
def get_weather(lat: float = 18.6274, lng: float = 73.8016):
    """Return live rainfall, 24h & 6h sparkline forecast, and river discharge."""
    snapshot = get_latest_snapshot()
    if snapshot and "weather" in snapshot:
        return snapshot["weather"]
    from services.data_feed import fetch_open_meteo_forecast, fetch_open_meteo_flood_discharge
    weather = fetch_open_meteo_forecast(lat, lng)
    weather["river_discharge_m3s"] = fetch_open_meteo_flood_discharge(lat, lng)
    return weather


# ==========================================
# ENDPOINT: POST /api/assess
# ==========================================
class AssessInput(BaseModel):
    rainfall_mm_per_hr: float
    rainfall_last_24h_mm: Optional[float] = 135.0
    river_level_above_normal_m: Optional[float] = 1.8


@app.post("/api/assess")
def assess_flood(data: AssessInput):
    """Calculate flood risk score and danger level."""
    from algorithms.flood_risk.risk_calculator import calculate_flood_risk
    res = calculate_flood_risk(
        rainfall_mm_per_hr=data.rainfall_mm_per_hr,
        rainfall_last_24h_mm=data.rainfall_last_24h_mm or 0.0,
        water_levels={},
        river_level_above_normal_m=data.river_level_above_normal_m or 1.0,
    )
    return {
        "risk_level": res.risk_level,
        "risk_score": res.risk_score,
        "is_dangerous": res.is_flood_dangerous(),
        "description": res.description,
        "action_required": res.action_required,
    }


# ==========================================
# ENDPOINT 7: POST /api/simulate & /api/simulate/step
# ==========================================
@app.post("/api/simulate/step")
@app.post("/api/simulate")
def simulate(data: SimulateInput):
    """Next rainfall step and updated evacuation outcome."""
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        graph_raw = json.load(f)
    locations = graph_raw.get("locations", [])

    start_node = data.start_node
    if not start_node or start_node not in [l["id"] for l in locations]:
        if data.user_lat is not None and data.user_lng is not None:
            start_node, _ = find_nearest_node(locations, data.user_lat, data.user_lng)
        else:
            start_node = locations[0]["id"]

    with open(RAINFALL_FILE, "r", encoding="utf-8") as f:
        rainfall_data = json.load(f)

    timesteps = rainfall_data.get("simulation_timesteps", [])
    if data.step_index < 0 or data.step_index >= len(timesteps):
        raise HTTPException(status_code=400, detail="Invalid step index")

    graph = load_city_graph(GRAPH_FILE)
    reports = run_flood_simulation(graph, start_node, rainfall_data)
    target = reports[data.step_index]

    return {
        "step_index": target.step_index,
        "time_label": target.time_label,
        "rainfall_mm_per_hr": target.rainfall_mm_per_hr,
        "rainfall_last_24h_mm": target.rainfall_last_24h_mm,
        "description": target.description,
        "risk_level": target.risk_level,
        "blocked_roads_count": target.blocked_roads_count,
        "blocked_road_ids": target.blocked_road_ids,
        "is_stranded": target.is_stranded,
        "target_shelter_name": target.target_shelter_name,
        "route_distance_km": target.route_distance_km,
        "route_path": target.route_path,
        "status_summary": target.status_summary,
    }


# ==========================================
# ENDPOINT: GET /route/{request_id} & /api/route/{request_id}
# ==========================================
@app.get("/route/{request_id}", response_class=HTMLResponse)
def view_rescue_route(request_id: str):
    """
    Opens the interactive operations dashboard focused on that rescue route.
    Injected with window.FOCUSED_ROUTE_ID for auto-zoom and highlight.
    """
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_file):
        return HTMLResponse("<h3>frontend/index.html not found</h3>", status_code=404)

    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    html = html.replace("__GOOGLE_MAPS_API_KEY__", api_key)

    # Inject focused route ID so the client focuses automatically on load
    inject_script = f"<script>window.FOCUSED_ROUTE_ID = {json.dumps(request_id)};</script>"
    if "</head>" in html:
        html = html.replace("</head>", f"{inject_script}\n</head>")
    else:
        html = f"{inject_script}\n{html}"

    return HTMLResponse(content=html, status_code=200)


@app.get("/api/route/{request_id}")
def get_rescue_route_details(request_id: str):
    """Return JSON details of a specific rescue mission route."""
    requests = get_all_requests()
    for req in requests:
        if req.get("id") == request_id:
            return req
    raise HTTPException(status_code=404, detail=f"Rescue request {request_id} not found")


# ==========================================
# SERVE FRONTEND INDEX WITH API KEY INJECTION
# ==========================================
@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_file):
        return HTMLResponse("<h3>frontend/index.html not found</h3>", status_code=404)

    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    html = html.replace("__GOOGLE_MAPS_API_KEY__", api_key)

    return HTMLResponse(content=html, status_code=200)


@app.get("/style.css")
def serve_css():
    css_file = os.path.join(FRONTEND_DIR, "style.css")
    with open(css_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), media_type="text/css")


@app.get("/app.js")
def serve_js():
    js_file = os.path.join(FRONTEND_DIR, "app.js")
    with open(js_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
