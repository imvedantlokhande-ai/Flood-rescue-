"""
Automated Rescue Dispatcher Service for Stranded Flood Zones.

Strict DSA Compliance:
- Priority Queue: Custom Min-Heap (`data_structures.min_heap.MinHeap`)
  Priority = -(risk_score * population) so the highest-need zone pops first.
- Resource Assignment: Custom Dijkstra (`algorithms.dijkstra.dijkstra.dijkstra_shortest_path`)
  Evaluates shortest passable route from every NGO emergency base to the stranded area.
- Unreachable Escalation: If no ground NGO can reach the stranded area due to flooded roads,
  marks the request as "NEEDS AIRLIFT/BOAT".
- Deduplication & Auto-Resolution: Prevents duplicate requests for already active zones;
  auto-resolves requests once access is restored or rescue is executed.
"""

import datetime
from typing import Dict, List, Optional, Any, Set
from data_structures.graph import Graph
from data_structures.min_heap import MinHeap
from algorithms.dijkstra.dijkstra import dijkstra_shortest_path


class RescueRequest:
    """Encapsulates an emergency NGO rescue dispatch mission."""

    def __init__(
        self,
        request_id: str,
        stranded_node: str,
        stranded_name: str,
        population: int,
        risk_score: float,
        priority_score: float,
        priority_rank: int = 1,
        ngo_assigned: Optional[Dict[str, Any]] = None,
        rescue_route_nodes: Optional[List[str]] = None,
        rescue_route_coords: Optional[List[Dict[str, Any]]] = None,
        distance_km: float = 0.0,
        eta_minutes: float = 0.0,
        status: str = "Created",
        needs_airlift: bool = False,
        google_maps_url: str = "",
    ) -> None:
        self.id = request_id
        self.stranded_node = stranded_node
        self.stranded_name = stranded_name
        self.population = population
        self.risk_score = risk_score
        self.priority_score = priority_score
        self.priority_rank = priority_rank
        self.ngo_assigned = ngo_assigned
        self.rescue_route_nodes = rescue_route_nodes if rescue_route_nodes else []
        self.rescue_route_coords = rescue_route_coords if rescue_route_coords else []
        self.distance_km = round(distance_km, 2)
        self.eta_minutes = round(eta_minutes, 1)
        self.status = status  # Created -> Sent -> Acknowledged -> En route -> Resolved
        self.needs_airlift = needs_airlift
        self.google_maps_url = google_maps_url
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "stranded_node": self.stranded_node,
            "stranded_name": self.stranded_name,
            "population": self.population,
            "risk_score": self.risk_score,
            "priority_score": self.priority_score,
            "priority_rank": self.priority_rank,
            "ngo_assigned": self.ngo_assigned,
            "rescue_route_nodes": self.rescue_route_nodes,
            "rescue_route_coords": self.rescue_route_coords,
            "distance_km": self.distance_km,
            "eta_minutes": self.eta_minutes,
            "status": self.status,
            "needs_airlift": self.needs_airlift,
            "google_maps_url": self.google_maps_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# In-memory store for active and historical rescue requests
# Key: stranded_node ID -> RescueRequest
ACTIVE_REQUESTS: Dict[str, RescueRequest] = {}
REQUEST_COUNTER = 0


def generate_google_maps_url(coords: List[Dict[str, Any]]) -> str:
    """Generate a shareable Google Maps directions URL for NGO responders."""
    if not coords or len(coords) < 2:
        return ""
    origin = f"{coords[0]['lat']},{coords[0]['lng']}"
    dest = f"{coords[-1]['lat']},{coords[-1]['lng']}"
    if len(coords) > 2:
        waypoints = "|".join([f"{c['lat']},{c['lng']}" for c in coords[1:-1]])
        return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={dest}&waypoints={waypoints}"
    return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={dest}"


def dispatch_stranded_areas(
    graph: Graph,
    stranded_nodes: List[str],
    risk_score: float,
    locations_by_id: Dict[str, Dict[str, Any]],
    ngo_bases: List[Dict[str, Any]],
) -> List[RescueRequest]:
    """
    Core Automated Rescue Dispatcher Engine.

    DSA Workflow:
    1. Filter and compute priority for each stranded node:
       priority = -(risk_score * population)
    2. Insert all stranded zones into our custom `MinHeap`.
    3. Extract nodes from `MinHeap` in order of maximum priority.
    4. For each extracted node:
       - Run custom `dijkstra_shortest_path` from each NGO base.
       - Select the reachable NGO with the shortest passable distance.
       - If no ground NGO can reach the node due to submerged roads,
         flag as `needs_airlift = True` ("NEEDS AIRLIFT/BOAT").
    5. Deduplicate against existing active requests; auto-close resolved areas.
    """
    global ACTIVE_REQUESTS, REQUEST_COUNTER

    current_stranded_set: Set[str] = set(stranded_nodes)

    # 1. Auto-resolve requests for areas that are no longer stranded (water receded)
    for node_id, req in list(ACTIVE_REQUESTS.items()):
        if node_id not in current_stranded_set and req.status not in ("Resolved", "Closed"):
            req.status = "Resolved"
            req.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if not stranded_nodes:
        return [r for r in ACTIVE_REQUESTS.values() if r.status != "Resolved"]

    # 2. Priority Min-Heap: custom implementation from scratch
    # Priority = -(risk_score * population), so largest product has lowest (most negative) key
    priority_heap: MinHeap[str] = MinHeap()

    for node_id in stranded_nodes:
        loc_data = locations_by_id.get(node_id, {})
        pop = loc_data.get("population", 5000)
        # Numerical priority score (higher is more urgent)
        metric = float(risk_score * pop)
        # Push negative value into MinHeap
        priority_heap.push(-metric, node_id)

    rank = 1
    updated_requests: List[RescueRequest] = []

    # 3. Process each stranded zone in descending order of urgency
    while not priority_heap.is_empty():
        neg_priority, node_id = priority_heap.pop()
        priority_metric = -neg_priority
        loc_data = locations_by_id.get(node_id, {})
        node_name = loc_data.get("name", node_id)
        pop = loc_data.get("population", 5000)

        # Check for existing open request to prevent duplication
        existing = ACTIVE_REQUESTS.get(node_id)
        if existing and existing.status in ("Sent", "Acknowledged", "En route"):
            existing.priority_rank = rank
            existing.priority_score = priority_metric
            existing.risk_score = risk_score
            updated_requests.append(existing)
            rank += 1
            continue

        # 4. Multi-NGO assignment via custom Dijkstra
        best_ngo: Optional[Dict[str, Any]] = None
        best_distance = float("inf")
        best_path: Optional[List[str]] = None

        for ngo in ngo_bases:
            ngo_node = ngo.get("node")
            if not ngo_node or ngo_node not in graph.get_nodes():
                continue

            # Run Dijkstra from this NGO's base over non-flooded edges
            dijkstra_res = dijkstra_shortest_path(graph, start_node=ngo_node, risk_adjusted=True)
            if dijkstra_res.is_reachable(node_id):
                dist = dijkstra_res.get_distance(node_id)
                if dist < best_distance:
                    best_distance = dist
                    best_ngo = ngo
                    best_path = dijkstra_res.reconstruct_path(node_id)

        # 5. Format route coordinates & handle airlift escalation
        route_coords: List[Dict[str, Any]] = []
        if best_path:
            for nid in best_path:
                info = locations_by_id.get(nid, {})
                route_coords.append({
                    "id": nid,
                    "name": info.get("name", nid),
                    "lat": info.get("lat", 0.0),
                    "lng": info.get("lng", 0.0),
                })

        gmaps_url = generate_google_maps_url(route_coords)

        if best_ngo is not None and best_path is not None:
            # Passable road route exists for this NGO
            eta = (best_distance / 30.0) * 60.0  # Assumes 30 km/h emergency speed in severe weather
            req_id = existing.id if existing else f"REQ-{node_id}-{int(datetime.datetime.now().timestamp()) % 10000:04d}"
            req = RescueRequest(
                request_id=req_id,
                stranded_node=node_id,
                stranded_name=node_name,
                population=pop,
                risk_score=risk_score,
                priority_score=priority_metric,
                priority_rank=rank,
                ngo_assigned={
                    "id": best_ngo["id"],
                    "name": best_ngo["name"],
                    "contact": best_ngo["contact"],
                    "vehicle_capacity": best_ngo.get("vehicle_capacity", 6),
                    "base_location": best_ngo.get("base_location", best_ngo.get("node")),
                    "node": best_ngo.get("node"),
                },
                rescue_route_nodes=best_path,
                rescue_route_coords=route_coords,
                distance_km=best_distance,
                eta_minutes=eta,
                status="Sent",
                needs_airlift=False,
                google_maps_url=gmaps_url,
            )
        else:
            # Cut off from all ground NGOs: escalate to air/boat evacuation
            req_id = existing.id if existing else f"REQ-{node_id}-{int(datetime.datetime.now().timestamp()) % 10000:04d}"
            req = RescueRequest(
                request_id=req_id,
                stranded_node=node_id,
                stranded_name=node_name,
                population=pop,
                risk_score=risk_score,
                priority_score=priority_metric,
                priority_rank=rank,
                ngo_assigned=None,
                rescue_route_nodes=[node_id],
                rescue_route_coords=[{
                    "id": node_id,
                    "name": node_name,
                    "lat": loc_data.get("lat", 0.0),
                    "lng": loc_data.get("lng", 0.0),
                }],
                distance_km=0.0,
                eta_minutes=15.0,  # Estimated helicopter transit time
                status="NEEDS AIRLIFT/BOAT",
                needs_airlift=True,
                google_maps_url="",
            )

        ACTIVE_REQUESTS[node_id] = req
        updated_requests.append(req)
        rank += 1

    return updated_requests


def get_all_requests() -> List[Dict[str, Any]]:
    """Return all active and resolved rescue requests sorted by priority rank."""
    reqs = list(ACTIVE_REQUESTS.values())
    reqs.sort(key=lambda r: (0 if r.status != "Resolved" else 1, r.priority_rank))
    return [r.to_dict() for r in reqs]


def acknowledge_request(request_id: str) -> Optional[Dict[str, Any]]:
    """Acknowledge a dispatch request and transition status."""
    for req in ACTIVE_REQUESTS.values():
        if req.id == request_id:
            if req.status == "Sent":
                req.status = "Acknowledged"
            elif req.status == "Acknowledged":
                req.status = "En route"
            req.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return req.to_dict()
    return None


def reset_requests() -> None:
    """Clear in-memory rescue requests (useful for testing and simulation resets)."""
    global ACTIVE_REQUESTS
    ACTIVE_REQUESTS.clear()
