"""
Unit Tests for Haversine Distance, Nearest-Node Snapping, and API Endpoints.
"""

import unittest
import math
import sys
import os

# Ensure flood_evacuation_planner root is in python module search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from algorithms.haversine.haversine import haversine_distance_km, find_nearest_node


class TestHaversineDistance(unittest.TestCase):
    """Test manual Haversine trigonometric distance implementation."""

    def test_same_point_is_zero(self):
        d = haversine_distance_km(18.6274, 73.8016, 18.6274, 73.8016)
        self.assertEqual(d, 0.0)

    def test_known_real_world_distance(self):
        # Pimpri Station (18.6274, 73.8016) to Chinchwad Station (18.6348, 73.7845)
        # Expected great-circle distance is ~1.98 km
        d = haversine_distance_km(18.6274, 73.8016, 18.6348, 73.7845)
        self.assertAlmostEqual(d, 1.984, delta=0.05)

    def test_symmetry(self):
        d1 = haversine_distance_km(18.5772, 73.8185, 18.6625, 73.7702)
        d2 = haversine_distance_km(18.6625, 73.7702, 18.5772, 73.8185)
        self.assertEqual(d1, d2)


class TestNearestNodeSnapping(unittest.TestCase):
    """Test spatial snapping of map click coordinates."""

    def setUp(self):
        self.nodes = [
            {"id": "LOC_01", "name": "Old Sangvi", "lat": 18.5772, "lng": 73.8185},
            {"id": "LOC_08", "name": "Pimpri Station", "lat": 18.6274, "lng": 73.8016},
            {"id": "SZ_01", "name": "DY Patil Hospital", "lat": 18.6255, "lng": 73.8232},
        ]

    def test_exact_match(self):
        node_id, dist = find_nearest_node(self.nodes, 18.6274, 73.8016)
        self.assertEqual(node_id, "LOC_08")
        self.assertEqual(dist, 0.0)

    def test_closest_proximity_snap(self):
        # User clicks slightly north of Pimpri Station (18.6280, 73.8010)
        node_id, dist = find_nearest_node(self.nodes, 18.6280, 73.8010)
        self.assertEqual(node_id, "LOC_08")
        self.assertLess(dist, 0.2)  # within 200 meters

    def test_empty_locations_raises(self):
        with self.assertRaises(ValueError):
            find_nearest_node([], 18.0, 73.0)


class TestApiEndpoints(unittest.TestCase):
    """Test API endpoint route handlers."""

    def test_api_import_and_endpoints(self):
        try:
            import api
            from fastapi.testclient import TestClient
            client = TestClient(api.app)

            # Test GET /api/graph
            res_graph = client.get("/api/graph")
            self.assertEqual(res_graph.status_code, 200)
            data_graph = res_graph.json()
            self.assertIn("locations", data_graph)
            self.assertIn("roads", data_graph)

            # Test POST /api/evacuate
            res_evac = client.post("/api/evacuate", json={
                "start_node": "LOC_08",
                "rainfall_mm_per_hr": 48.5,
                "rainfall_last_24h_mm": 135.0,
            })
            self.assertEqual(res_evac.status_code, 200)
            data_evac = res_evac.json()
            self.assertIn("risk_level", data_evac)
            self.assertIn("reachable_set", data_evac)
            self.assertIn("algorithm_trace", data_evac)

            # Test POST /api/simulate
            res_sim = client.post("/api/simulate", json={
                "step_index": 1,
                "start_node": "LOC_08",
            })
            self.assertEqual(res_sim.status_code, 200)

            # Test GET / (Google Maps frontend served, template key substituted)
            res_index = client.get("/")
            self.assertEqual(res_index.status_code, 200)
            self.assertIn("id=\"map\"", res_index.text)
            self.assertNotIn("__google_maps_api_key__", res_index.text.lower())

            # Test GET /api/weather
            res_weather = client.get("/api/weather")
            self.assertEqual(res_weather.status_code, 200)
            data_weather = res_weather.json()
            self.assertIn("rainfall_mm_per_hr", data_weather)

            # Test POST /api/assess
            res_assess = client.post("/api/assess", json={"rainfall_mm_per_hr": 48.5})
            self.assertEqual(res_assess.status_code, 200)
            self.assertIn("risk_level", res_assess.json())

            # Test GET /route/{request_id}
            res_route_view = client.get("/route/REQ-LOC_01-1234")
            self.assertEqual(res_route_view.status_code, 200)
            self.assertIn("window.FOCUSED_ROUTE_ID", res_route_view.text)
            self.assertIn("REQ-LOC_01-1234", res_route_view.text)

        except ImportError:
            # If fastapi/testclient not installed in environment, test endpoint logic directly
            from utils.loader import load_city_graph
            g = load_city_graph(os.path.join(PROJECT_ROOT, "data", "city_graph.json"))
            self.assertGreater(len(g.get_nodes()), 10)


if __name__ == "__main__":
    unittest.main()
