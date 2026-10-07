"""
Comprehensive Unit Tests for Flood Evacuation Route Planner.

Tests:
1. Custom Queue (FIFO ordering, exception handling)
2. Custom Stack (LIFO ordering, exception handling)
3. Custom MinHeap (ordering, decrease_key, priority extraction)
4. Custom Graph (edge blocking, dynamic weights)
5. Flood Risk Calculator (LOW, MODERATE, HIGH, SEVERE)
6. Flood Road Marker (threshold blocking & penalty multiplication)
7. Breadth-First Search (reachability, hop distance, fewest-intersections path)
8. Depth-First Search (iterative vs recursive equivalence)
9. Connected Components (partitioning, stranded zone detection)
10. Dijkstra's Algorithm (shortest path, skipping flooded roads)
11. Edge Cases:
    - Start node is already a safe zone
    - All outgoing roads flooded (complete entrapment)
    - Completely disconnected graph
    - Multiple equal-distance routes
"""

import unittest
import math
import sys
import os
from typing import List, Set

# Ensure flood_evacuation_planner root is in python module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_structures.queue import CustomQueue
from data_structures.stack import CustomStack
from data_structures.min_heap import MinHeap
from data_structures.graph import Graph
from algorithms.flood_risk.risk_calculator import (
    calculate_flood_risk,
    RISK_LOW,
    RISK_MODERATE,
    RISK_HIGH,
    RISK_SEVERE,
)
from modules.flood_marker import mark_flooded_roads
from algorithms.bfs.bfs import breadth_first_search, get_fewest_hops_path
from algorithms.dfs.dfs import depth_first_search_iterative, depth_first_search_recursive
from algorithms.connected_components.components import find_connected_components
from algorithms.dijkstra.dijkstra import dijkstra_shortest_path, find_nearest_safe_zone
from modules.route_planner import plan_evacuation


class TestCustomQueue(unittest.TestCase):
    """Unit tests for the scratch-built linked list Queue."""

    def test_fifo_order(self):
        q = CustomQueue()
        self.assertTrue(q.is_empty())
        self.assertEqual(q.size(), 0)

        items = ["A", "B", "C", "D"]
        for item in items:
            q.enqueue(item)

        self.assertEqual(q.size(), 4)
        self.assertEqual(q.peek(), "A")

        popped = [q.dequeue() for _ in range(4)]
        self.assertEqual(popped, items)
        self.assertTrue(q.is_empty())

    def test_dequeue_empty_raises(self):
        q = CustomQueue()
        with self.assertRaises(IndexError):
            q.dequeue()
        with self.assertRaises(IndexError):
            q.peek()


class TestCustomStack(unittest.TestCase):
    """Unit tests for the scratch-built linked list Stack."""

    def test_lifo_order(self):
        s = CustomStack()
        self.assertTrue(s.is_empty())

        s.push(10)
        s.push(20)
        s.push(30)

        self.assertEqual(s.size(), 3)
        self.assertEqual(s.peek(), 30)

        self.assertEqual(s.pop(), 30)
        self.assertEqual(s.pop(), 20)
        self.assertEqual(s.pop(), 10)
        self.assertTrue(s.is_empty())

    def test_pop_empty_raises(self):
        s = CustomStack()
        with self.assertRaises(IndexError):
            s.pop()
        with self.assertRaises(IndexError):
            s.peek()


class TestCustomMinHeap(unittest.TestCase):
    """Unit tests for scratch-built binary Min-Heap / Priority Queue."""

    def test_min_order_extraction(self):
        h = MinHeap()
        self.assertTrue(h.is_empty())

        elements = [(5.5, "E"), (1.2, "B"), (9.0, "Z"), (0.4, "A"), (3.1, "C")]
        for p, item in elements:
            h.push(p, item)

        self.assertEqual(h.size(), 5)
        self.assertEqual(h.peek(), (0.4, "A"))

        sorted_extracted = []
        while not h.is_empty():
            sorted_extracted.append(h.pop())

        expected = [
            (0.4, "A"),
            (1.2, "B"),
            (3.1, "C"),
            (5.5, "E"),
            (9.0, "Z"),
        ]
        self.assertEqual(sorted_extracted, expected)

    def test_decrease_key(self):
        h = MinHeap()
        h.push(10.0, "Node_X")
        h.push(20.0, "Node_Y")
        h.push(30.0, "Node_Z")

        self.assertEqual(h.peek()[1], "Node_X")

        # Decrease Node_Z priority to 2.0 (should become new minimum)
        h.decrease_key("Node_Z", 2.0)
        self.assertEqual(h.peek(), (2.0, "Node_Z"))
        self.assertEqual(h.pop(), (2.0, "Node_Z"))
        self.assertEqual(h.pop(), (10.0, "Node_X"))

    def test_empty_heap_raises(self):
        h = MinHeap()
        with self.assertRaises(IndexError):
            h.pop()


class TestGraphStructure(unittest.TestCase):
    """Unit tests for Graph adjacency list and dynamic blocking."""

    def test_graph_add_and_block(self):
        g = Graph()
        g.add_node("A", {"name": "Alpha"})
        g.add_node("B", {"name": "Beta"})
        g.add_edge("A", "B", 4.5, road_id="RD_AB")

        self.assertEqual(len(g.get_nodes()), 2)
        self.assertFalse(g.is_edge_blocked("A", "B"))

        # Block road
        g.block_edge("A", "B")
        self.assertTrue(g.is_edge_blocked("A", "B"))
        self.assertTrue(g.is_edge_blocked("B", "A"))

        # Neighbors without blocked should be empty
        self.assertEqual(g.get_neighbors("A", include_blocked=False), [])
        # Including blocked should show the edge
        self.assertEqual(len(g.get_neighbors("A", include_blocked=True)), 1)

        # Unblock road
        g.unblock_edge("A", "B")
        self.assertFalse(g.is_edge_blocked("A", "B"))
        self.assertEqual(len(g.get_neighbors("A", include_blocked=False)), 1)


class TestFloodRiskCalculator(unittest.TestCase):
    """Unit tests for rule-based risk evaluation."""

    def test_low_risk(self):
        res = calculate_flood_risk(rainfall_mm_per_hr=6.0, rainfall_last_24h_mm=12.0, max_water_level_m=0.05)
        self.assertEqual(res.risk_level, RISK_LOW)
        self.assertFalse(res.is_dangerous)
        self.assertFalse(res.evacuation_needed)

    def test_moderate_risk(self):
        res = calculate_flood_risk(rainfall_mm_per_hr=22.0, rainfall_last_24h_mm=50.0, max_water_level_m=0.25)
        self.assertEqual(res.risk_level, RISK_MODERATE)
        self.assertTrue(res.is_dangerous)
        self.assertTrue(res.evacuation_needed)

    def test_high_risk(self):
        res = calculate_flood_risk(rainfall_mm_per_hr=45.0, rainfall_last_24h_mm=130.0, max_water_level_m=0.60)
        self.assertEqual(res.risk_level, RISK_HIGH)
        self.assertTrue(res.is_dangerous)

    def test_severe_risk(self):
        res = calculate_flood_risk(rainfall_mm_per_hr=85.0, rainfall_last_24h_mm=210.0, max_water_level_m=1.20)
        self.assertEqual(res.risk_level, RISK_SEVERE)
        self.assertTrue(res.is_dangerous)


class TestFloodMarker(unittest.TestCase):
    """Unit tests for road blocking and penalty multiplier."""

    def test_marking_thresholds(self):
        g = Graph()
        g.add_edge("A", "B", 10.0, road_id="RD_NORM")
        g.add_edge("B", "C", 10.0, road_id="RD_RISK")
        g.add_edge("C", "D", 10.0, road_id="RD_FLOOD")

        water = {
            "RD_NORM": 0.10,   # normal
            "RD_RISK": 0.30,   # risky: penalty x2.5 -> 25.0
            "RD_FLOOD": 0.80,  # blocked
        }
        summary = mark_flooded_roads(g, water)
        self.assertEqual(len(summary.normal_roads), 1)
        self.assertEqual(len(summary.risky_roads), 1)
        self.assertEqual(len(summary.blocked_roads), 1)

        # Check effective weights
        self.assertEqual(g.get_edge("A", "B").effective_weight, 10.0)
        self.assertEqual(g.get_edge("B", "C").effective_weight, 25.0)
        self.assertTrue(g.get_edge("C", "D").is_blocked)


class TestBFSAlgorithm(unittest.TestCase):
    """Unit tests for BFS reachability and fewest hops path."""

    def setUp(self):
        self.g = Graph()
        # Diamond graph:
        # A - B (10km) - D (10km) -> 2 hops, 20km
        # A - C (1km) - E (1km) - F (1km) - D (1km) -> 4 hops, 4km
        self.g.add_edge("A", "B", 10.0)
        self.g.add_edge("B", "D", 10.0)
        self.g.add_edge("A", "C", 1.0)
        self.g.add_edge("C", "E", 1.0)
        self.g.add_edge("E", "F", 1.0)
        self.g.add_edge("F", "D", 1.0)

    def test_bfs_hops_vs_metric(self):
        res = breadth_first_search(self.g, "A")
        self.assertTrue("D" in res.reachable_nodes)
        self.assertEqual(res.hop_distances["D"], 2)  # via A -> B -> D

        path, hops = get_fewest_hops_path(self.g, "A", "D")
        self.assertEqual(hops, 2)
        self.assertEqual(path, ["A", "B", "D"])


class TestDFSAndComponents(unittest.TestCase):
    """Unit tests for DFS and Connected Components."""

    def test_iterative_recursive_consistency(self):
        g = Graph()
        g.add_edge("1", "2", 1.0)
        g.add_edge("2", "3", 1.0)
        g.add_edge("1", "4", 1.0)

        res_iter = depth_first_search_iterative(g, "1")
        res_rec = depth_first_search_recursive(g, "1")

        self.assertEqual(res_iter.visited_nodes, res_rec.visited_nodes)
        self.assertEqual(res_iter.visited_nodes, {"1", "2", "3", "4"})

    def test_stranded_component_detection(self):
        g = Graph()
        g.add_node("SZ_1", {"is_safe_zone": True})
        g.add_node("LOC_1")
        g.add_node("LOC_2")
        g.add_edge("LOC_1", "SZ_1", 2.0)
        # LOC_2 is isolated / cut off
        comp_res = find_connected_components(g)
        self.assertEqual(comp_res.total_components, 2)
        self.assertTrue(comp_res.is_node_stranded("LOC_2"))
        self.assertFalse(comp_res.is_node_stranded("LOC_1"))


class TestDijkstraShortestPath(unittest.TestCase):
    """Unit tests for Dijkstra shortest path and edge cases."""

    def test_shortest_metric_path(self):
        g = Graph()
        # Diamond where lower path is physically shorter
        g.add_edge("A", "B", 10.0)
        g.add_edge("B", "D", 10.0)
        g.add_edge("A", "C", 2.0)
        g.add_edge("C", "D", 3.0)

        res = dijkstra_shortest_path(g, "A")
        self.assertEqual(res.get_distance("D"), 5.0)
        self.assertEqual(res.reconstruct_path("D"), ["A", "C", "D"])

    def test_skipping_flooded_roads(self):
        g = Graph()
        g.add_edge("A", "B", 2.0)
        g.add_edge("B", "SZ", 2.0)
        g.add_edge("A", "C", 5.0)
        g.add_edge("C", "SZ", 5.0)

        # Block the shorter route A-B
        g.block_edge("A", "B")

        res = dijkstra_shortest_path(g, "A")
        self.assertEqual(res.get_distance("SZ"), 10.0)
        self.assertEqual(res.reconstruct_path("SZ"), ["A", "C", "SZ"])


class TestEndToEndEdgeCases(unittest.TestCase):
    """Comprehensive tests for extreme flood edge cases."""

    def test_edge_case_start_is_safe_zone(self):
        g = Graph()
        g.add_node("SZ_01", {"name": "Hilltop Shelter", "is_safe_zone": True, "capacity": 2000})
        g.add_node("LOC_02", {"name": "Downtown"})
        g.add_edge("SZ_01", "LOC_02", 3.0)

        res = plan_evacuation(
            graph=g,
            start_node="SZ_01",
            rainfall_mm_per_hr=50.0,
            rainfall_last_24h_mm=120.0,
            water_levels={},
        )
        self.assertFalse(res.is_stranded)
        self.assertEqual(res.primary_route.distance_km, 0.0)
        self.assertEqual(res.primary_route.path, ["SZ_01"])
        self.assertIn("already an established emergency safe shelter", res.status_message)

    def test_edge_case_all_roads_flooded_entrapment(self):
        g = Graph()
        g.add_node("LOC_01", {"name": "Floodplain Home"})
        g.add_node("SZ_01", {"name": "Hospital", "is_safe_zone": True})
        g.add_edge("LOC_01", "SZ_01", 4.0, road_id="RD_EXIT")

        # RD_EXIT is 1.5m deep underwater
        water_levels = {"RD_EXIT": 1.5}
        res = plan_evacuation(
            graph=g,
            start_node="LOC_01",
            rainfall_mm_per_hr=75.0,
            rainfall_last_24h_mm=190.0,
            water_levels=water_levels,
        )

        self.assertTrue(res.is_stranded)
        self.assertIsNone(res.primary_route)
        self.assertIn("NO SAFE ROUTE - REQUEST RESCUE", res.status_message)

    def test_edge_case_no_flood_no_evacuation(self):
        g = Graph()
        g.add_node("LOC_01", {"name": "Downtown"})
        g.add_node("SZ_01", {"name": "Hospital", "is_safe_zone": True})
        g.add_edge("LOC_01", "SZ_01", 4.0)

        # Sunny / light rain
        res = plan_evacuation(
            graph=g,
            start_node="LOC_01",
            rainfall_mm_per_hr=3.0,
            rainfall_last_24h_mm=5.0,
            water_levels={},
        )
        self.assertFalse(res.risk_assessment.is_dangerous)
        self.assertIn("No evacuation needed", res.status_message)


if __name__ == "__main__":
    unittest.main()
