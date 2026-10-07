"""
Manual Haversine Distance Implementation from Scratch.

Strict Rule Compliance:
Implemented completely using pure mathematical trigonometry from standard library `math`.
No `geopy`, `scipy`, or third-party spatial libraries. Computes the great-circle
distance between two points on the Earth's spherical surface and provides
nearest-node spatial snapping.
"""

import math
from typing import Dict, List, Tuple, Any, Optional

# Mean volumetric Earth radius in kilometers (WGS-84 spherical approximation)
EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate the great-circle distance between two geographic coordinates in kilometers.

    Formula:
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin^2(dlat / 2) + cos(radians(lat1)) * cos(radians(lat2)) * sin^2(dlon / 2)
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        d = R * c

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Great-circle distance in kilometers rounded to 3 decimal places.
    """
    # Convert decimal degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine central angle calculation
    sin_half_dphi = math.sin(delta_phi / 2.0)
    sin_half_dlambda = math.sin(delta_lambda / 2.0)

    a = (
        (sin_half_dphi * sin_half_dphi)
        + math.cos(phi1) * math.cos(phi2) * (sin_half_dlambda * sin_half_dlambda)
    )

    # Clamp 'a' between 0 and 1 to prevent domain errors with sqrt due to floating-point drift
    a = min(1.0, max(0.0, a))

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance_km = EARTH_RADIUS_KM * c

    return round(distance_km, 3)


def find_nearest_node(
    locations: List[Dict[str, Any]],
    target_lat: float,
    target_lon: float,
) -> Tuple[str, float]:
    """
    Snap arbitrary map-click coordinates to the closest graph intersection vertex.

    Uses manual linear search with O(N) comparisons over graph locations.

    Args:
        locations: List of location dictionaries with 'id', 'lat', and 'lng' (or 'lon').
        target_lat: User-selected latitude in decimal degrees.
        target_lon: User-selected longitude in decimal degrees.

    Returns:
        Tuple of (nearest_node_id, distance_km).

    Raises:
        ValueError: If locations list is empty.
    """
    if not locations:
        raise ValueError("Cannot snap to nearest node: locations list is empty")

    best_node_id = ""
    min_dist_km = float("inf")

    for loc in locations:
        node_id = loc.get("id") or loc.get("node_id", "")
        lat = float(loc.get("lat") or loc.get("latitude", 0.0))
        lon = float(loc.get("lng") or loc.get("lon") or loc.get("longitude", 0.0))

        dist = haversine_distance_km(target_lat, target_lon, lat, lon)
        if dist < min_dist_km:
            min_dist_km = dist
            best_node_id = node_id

    return best_node_id, min_dist_km


if __name__ == "__main__":
    # Self-test: Pimpri to Chinchwad distance
    # Pimpri Station: 18.6274, 73.8016
    # Chinchwad Station: 18.6348, 73.7845
    d = haversine_distance_km(18.6274, 73.8016, 18.6348, 73.7845)
    print(f"Haversine distance (Pimpri -> Chinchwad): {d:.3f} km")
    sample_nodes = [
        {"id": "LOC_01", "lat": 18.6274, "lng": 73.8016},
        {"id": "LOC_02", "lat": 18.6348, "lng": 73.7845},
    ]
    snapped, snap_d = find_nearest_node(sample_nodes, 18.6290, 73.8000)
    print(f"Nearest node to (18.6290, 73.8000): {snapped} ({snap_d:.3f} km)")
