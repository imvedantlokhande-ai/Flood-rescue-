# Haversine Distance & Spatial Snapping Algorithm

This module implements the Haversine formula and nearest-node spatial snapping from scratch in pure Python without `geopy`, `scipy`, or external GIS libraries.

---

## 1. What This Algorithm Does

1. Computes the great-circle surface distance in kilometers between two latitude/longitude coordinates on a spherical Earth ($R = 6371.009\text{ km}$).
2. Dynamically calculates road edge lengths in the city graph using GPS coordinates.
3. Snaps user clicks or device GPS coordinates to the closest road intersection in the network.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

When evacuees open a map during a flood emergency, they do not know internal graph IDs like `LOC_07`. They tap their current physical location or GPS location on the map. Haversine distance allows snapping that tap to the nearest safe street intersection. Furthermore, computing edge weights from true coordinates ensures accurate evacuation distances and walking/driving travel times.

---

## 3. How It Works, Step by Step

1. Convert latitudes and longitudes from decimal degrees to radians.
2. Calculate coordinate differences: $\Delta\phi = \text{rad}(\text{lat}_2 - \text{lat}_1)$, $\Delta\lambda = \text{rad}(\text{lon}_2 - \text{lon}_1)$.
3. Compute the square of half the chord length:
   $$a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)$$
4. Compute angular distance in radians:
   $$c = 2 \cdot \text{atan2}(\sqrt{a}, \sqrt{1 - a})$$
5. Multiply by Earth's radius: $d = R \cdot c$.
6. For nearest-node snapping, perform a linear scan across all graph vertices and select the node with minimum Haversine distance.

---

## 4. Small Worked Example

```text
Point 1: Pimpri Station (18.6274° N, 73.8016° E)
Point 2: Chinchwad Station (18.6348° N, 73.7845° E)

Calculated Haversine Distance = 1.984 km.
User clicks (18.6280, 73.8010) -> Snapped to Pimpri Station (0.091 km away).
```

---

## 5. Pseudocode

```text
FUNCTION haversine_distance(lat1, lon1, lat2, lon2):
    phi1 = RADIANS(lat1), phi2 = RADIANS(lat2)
    dphi = RADIANS(lat2 - lat1), dlambda = RADIANS(lon2 - lon1)
    a = SIN(dphi / 2)^2 + COS(phi1) * COS(phi2) * SIN(dlambda / 2)^2
    a = CLAMP(a, 0.0, 1.0)
    c = 2 * ATAN2(SQRT(a), SQRT(1 - a))
    RETURN 6371.009 * c

FUNCTION find_nearest_node(locations, target_lat, target_lon):
    best_node = NULL, min_dist = INFINITY
    FOR EACH loc IN locations:
        dist = haversine_distance(target_lat, target_lon, loc.lat, loc.lon)
        IF dist < min_dist:
            min_dist = dist
            best_node = loc.id
    RETURN (best_node, min_dist)
```

---

## 6. Time and Space Complexity

- **Haversine Distance**:
  - Time Complexity: $O(1)$ constant trigonometric operations.
  - Space Complexity: $O(1)$.
- **Nearest Node Snapping**:
  - Time Complexity: $O(V)$ where $V$ is number of locations.
  - Space Complexity: $O(1)$ auxiliary memory.

---

## 7. Input and Output Format

- **Input**: `lat1, lon1, lat2, lon2: float` in decimal degrees.
- **Output**: `distance_km: float` rounded to 3 decimal places.

---

## 8. How to Run / Test Individually

```bash
python3 algorithms/haversine/haversine.py
```

---

## 9. Limitations and Possible Improvements

1. **Spherical Earth Assumption**: Assumes a spherical Earth with $R = 6371\text{ km}$. For sub-meter precision, Vincenty's ellipsoidal formula can be used.
2. **Spatial Indexing**: For metropolitan networks with $> 50,000$ nodes, a spatial k-d tree or R-tree can reduce nearest-neighbor lookup from $O(V)$ to $O(\log V)$.
