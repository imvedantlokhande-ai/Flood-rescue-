# Utils Module: Data Loader and Visualizer

This module provides data deserialization and visual mapping utilities for the Flood Evacuation Route Planner.

---

## 1. What This Module Does

1. **`loader.py`**:
   - Ingests structured JSON data (`city_graph.json`, `rainfall_data.json`) and constructs the custom `Graph` instance with node attributes (elevation, coordinates, shelter capacity) and road edges.
   - Provides programmatic fallback generators in case data files are accessed from alternate directories.
2. **`visualizer.py`**:
   - Generates high-resolution cartographic network maps using `matplotlib`.
   - Renders color-coded road conditions:
     - Flooded / blocked roads in red dashed lines with "X" markers.
     - Risky roads in amber dash-dot lines.
     - Open roads in slate gray.
     - The recommended evacuation route in thick glowing green.
     - Shelters in blue squares and start position in gold.
   - Provides a clean ASCII terminal fallback for headless environments without matplotlib.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

- In an emergency evacuation, text tables alone are difficult to interpret quickly. Visual cartographic maps allow both evacuees and emergency response incident commanders to immediately see where floodwaters have cut across roads and how the recommended route navigates around hazardous inundation zones to high ground.

---

## 3. How It Works, Step by Step

### Loader:
1. Opens JSON file with UTF-8 encoding.
2. Iterates over `locations` list, invoking `graph.add_node(loc["id"], loc)`.
3. Iterates over `roads` list, invoking `graph.add_edge(road["from"], road["to"], road["distance_km"])`.

### Visualizer:
1. Sets up matplotlib figure with dark slate background `#0f172a`.
2. Gathers $(x, y)$ planar coordinates from node metadata.
3. Renders edges by status layer (unblocked roads at base, flooded roads above, highlighted route on top).
4. Plots node markers according to type (shelters as squares, starting location as diamonds, cut-off nodes in red).
5. Adds customized legend and exports PNG or returns Figure to Streamlit.

---

## 4. Small Worked Example

```text
Loading city_graph.json:
  -> Parsed 18 locations: LOC_01 through LOC_15, SZ_01, SZ_02, SZ_03
  -> Parsed 30 road segments
Visualizing:
  -> Identified evacuation path: LOC_01 -> LOC_10 -> SZ_01
  -> Exported high-resolution map to: flood_evacuation_map.png
```

---

## 5. Pseudocode

```text
FUNCTION load_city_graph(filepath):
    data = PARSE_JSON(filepath)
    g = Graph()
    FOR loc IN data.locations:
        g.add_node(loc.id, loc)
    FOR road IN data.roads:
        g.add_edge(road.from, road.to, road.distance_km, road.id, road)
    RETURN g

FUNCTION render_graph(graph, path, start_node):
    fig, ax = CREATE_PLOT()
    FOR edge IN graph.edges:
        DRAW_LINE(edge.u.coords, edge.v.coords, COLOR_BY_STATUS(edge))
    IF path:
        DRAW_THICK_GREEN_LINE(path)
    FOR node IN graph.nodes:
        DRAW_MARKER(node.coords, COLOR_BY_TYPE(node))
    SAVE_PNG("flood_evacuation_map.png")
    RETURN fig
```

---

## 6. Time and Space Complexity

- **Loader**:
  - Time Complexity: $O(V + E)$ to parse JSON elements and build adjacency entries.
  - Space Complexity: $O(V + E)$ memory for the graph.
- **Visualizer**:
  - Time Complexity: $O(V + E)$ plot calls.
  - Space Complexity: $O(V + E)$ coordinates and figure canvas buffer.

---

## 7. Input and Output Format

- **Loader Input**: Paths to JSON files.
- **Loader Output**: Populated `Graph` instance and dictionary of telemetry data.
- **Visualizer Input**: `graph: Graph`, `evacuation_path: List[str]`, `start_node: str`.
- **Visualizer Output**: PNG file saved to disk and/or matplotlib `Figure` instance.

---

## 8. How to Run / Test Individually

```bash
# Test Loader
python3 utils/loader.py

# Test Visualizer
python3 -c "from utils.loader import create_sample_city_graph; from utils.visualizer import print_ascii_graph; g=create_sample_city_graph(); print_ascii_graph(g, ['LOC_01', 'SZ_01'], 'LOC_01')"
```

---

## 9. Limitations and Possible Improvements

1. **GeoTIFF / GIS Coordinates**: Can be upgraded to ingest real-world WGS84 GPS latitude/longitude and GIS shapefiles for live OpenStreetMap overlay.
2. **Interactive WebGL**: In web browsers, Leaflet or Three.js can render dynamic 3D water surface animations over elevation contours.
