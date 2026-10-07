"""
Unit Tests for Automated Rescue Dispatcher Service.

Tests:
1. Min-Heap Priority Ordering (triage based on population * risk score)
2. Nearest NGO Assignment via custom Dijkstra on passable edges
3. Unreachable Area Escalation to "NEEDS AIRLIFT/BOAT"
4. Deduplication (no duplicate requests for active stranded zones)
5. Request Lifecycle & Acknowledgement Flow
"""

import os
import sys
import unittest

# Ensure flood_evacuation_planner root is in sys.path
PLANNER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PLANNER_ROOT not in sys.path:
    sys.path.insert(0, PLANNER_ROOT)

from data_structures.graph import Graph
from data_structures.min_heap import MinHeap
from services.rescue_dispatcher import (
    dispatch_stranded_areas,
    get_all_requests,
    acknowledge_request,
    reset_requests,
    RescueRequest,
)


class TestRescueDispatcher(unittest.TestCase):

    def setUp(self):
        reset_requests()

        # Build small test road network
        #
        # [NGO_1] --- (2km) --- [A] --- (1km) --- [B] (Stranded high pop)
        #                          |
        #                        (3km)
        #                          |
        # [NGO_2] --- (1km) --- [C] --- (2km) --- [D] (Stranded low pop)
        #
        # Isolated Zone:
        # [X] (Stranded Island, all incident edges flooded)
        self.graph = Graph()
        self.graph.add_node("NGO_1", {"name": "Red Cross Post", "population": 500, "is_safe_zone": False})
        self.graph.add_node("NGO_2", {"name": "Civil Defense Post", "population": 500, "is_safe_zone": False})
        self.graph.add_node("A", {"name": "Alpha Sector", "population": 3000, "is_safe_zone": False})
        self.graph.add_node("B", {"name": "Bravo Lowland", "population": 12000, "is_safe_zone": False})
        self.graph.add_node("C", {"name": "Charlie Sector", "population": 2500, "is_safe_zone": False})
        self.graph.add_node("D", {"name": "Delta Hamlet", "population": 1500, "is_safe_zone": False})
        self.graph.add_node("X", {"name": "X-Ray Island", "population": 4000, "is_safe_zone": False})

        self.graph.add_edge("NGO_1", "A", 2.0, road_id="RD_N1_A", bidirectional=True)
        self.graph.add_edge("A", "B", 1.0, road_id="RD_A_B", bidirectional=True)
        self.graph.add_edge("A", "C", 3.0, road_id="RD_A_C", bidirectional=True)
        self.graph.add_edge("NGO_2", "C", 1.0, road_id="RD_N2_C", bidirectional=True)
        self.graph.add_edge("C", "D", 2.0, road_id="RD_C_D", bidirectional=True)
        self.graph.add_edge("D", "X", 5.0, road_id="RD_D_X", bidirectional=True)

        self.locations_by_id = {
            "NGO_1": {"name": "Red Cross Post", "population": 500, "lat": 18.60, "lng": 73.80},
            "NGO_2": {"name": "Civil Defense Post", "population": 500, "lat": 18.62, "lng": 73.82},
            "A": {"name": "Alpha Sector", "population": 3000, "lat": 18.61, "lng": 73.81},
            "B": {"name": "Bravo Lowland", "population": 12000, "lat": 18.61, "lng": 73.82},
            "C": {"name": "Charlie Sector", "population": 2500, "lat": 18.62, "lng": 73.81},
            "D": {"name": "Delta Hamlet", "population": 1500, "lat": 18.63, "lng": 73.81},
            "X": {"name": "X-Ray Island", "population": 4000, "lat": 18.65, "lng": 73.85},
        }

        self.ngo_bases = [
            {"id": "NGO_01", "name": "Red Cross Post", "node": "NGO_1", "contact": "555-0101", "vehicle_capacity": 6},
            {"id": "NGO_02", "name": "Civil Defense Post", "node": "NGO_2", "contact": "555-0202", "vehicle_capacity": 8},
        ]

    def test_min_heap_priority_order(self):
        """Verify MinHeap pops the zone with highest (risk_score * population) first."""
        stranded_nodes = ["D", "B"]  # D: 1,500 pop, B: 12,000 pop
        risk_score = 80.0

        dispatches = dispatch_stranded_areas(
            graph=self.graph,
            stranded_nodes=stranded_nodes,
            risk_score=risk_score,
            locations_by_id=self.locations_by_id,
            ngo_bases=self.ngo_bases,
        )

        self.assertEqual(len(dispatches), 2)
        # B has 12,000 pop -> highest priority -> must be Rank #1
        self.assertEqual(dispatches[0].stranded_node, "B")
        self.assertEqual(dispatches[0].priority_rank, 1)
        # D has 1,500 pop -> Rank #2
        self.assertEqual(dispatches[1].stranded_node, "D")
        self.assertEqual(dispatches[1].priority_rank, 2)

    def test_nearest_ngo_assigned_via_dijkstra(self):
        """Verify Dijkstra evaluates passable edges from all NGOs to find the nearest base."""
        # For zone B:
        # From NGO_1: NGO_1 -> A (2km) + A -> B (1km) = 3.0 km
        # From NGO_2: NGO_2 -> C (1km) + C -> A (3km) + A -> B (1km) = 5.0 km
        # Therefore, NGO_1 must be assigned!
        stranded_nodes = ["B"]
        risk_score = 75.0

        dispatches = dispatch_stranded_areas(
            graph=self.graph,
            stranded_nodes=stranded_nodes,
            risk_score=risk_score,
            locations_by_id=self.locations_by_id,
            ngo_bases=self.ngo_bases,
        )

        self.assertEqual(len(dispatches), 1)
        req = dispatches[0]
        self.assertIsNotNone(req.ngo_assigned)
        self.assertEqual(req.ngo_assigned["id"], "NGO_01")
        self.assertAlmostEqual(req.distance_km, 3.0, places=2)
        self.assertEqual(req.rescue_route_nodes, ["NGO_1", "A", "B"])
        self.assertFalse(req.needs_airlift)

    def test_unreachable_area_escalates_to_airlift(self):
        """Verify that when all incoming roads are flooded, request escalates to 'NEEDS AIRLIFT/BOAT'."""
        # Submerge all roads to X
        self.graph.block_edge("D", "X")

        stranded_nodes = ["X"]
        risk_score = 90.0

        dispatches = dispatch_stranded_areas(
            graph=self.graph,
            stranded_nodes=stranded_nodes,
            risk_score=risk_score,
            locations_by_id=self.locations_by_id,
            ngo_bases=self.ngo_bases,
        )

        self.assertEqual(len(dispatches), 1)
        req = dispatches[0]
        self.assertTrue(req.needs_airlift)
        self.assertEqual(req.status, "NEEDS AIRLIFT/BOAT")
        self.assertIsNone(req.ngo_assigned)

    def test_deduplication_of_active_requests(self):
        """Verify repeated pipeline cycles do not duplicate active requests for the same zone."""
        stranded_nodes = ["B", "D"]
        risk_score = 80.0

        # Cycle 1
        dispatch_stranded_areas(
            graph=self.graph,
            stranded_nodes=stranded_nodes,
            risk_score=risk_score,
            locations_by_id=self.locations_by_id,
            ngo_bases=self.ngo_bases,
        )
        self.assertEqual(len(get_all_requests()), 2)

        # Cycle 2 with identical stranded nodes
        dispatch_stranded_areas(
            graph=self.graph,
            stranded_nodes=stranded_nodes,
            risk_score=risk_score,
            locations_by_id=self.locations_by_id,
            ngo_bases=self.ngo_bases,
        )
        # Count must remain 2 (no duplicates!)
        all_reqs = get_all_requests()
        self.assertEqual(len(all_reqs), 2)

    def test_acknowledgement_flow(self):
        """Verify NGO field responder can acknowledge request and advance status."""
        stranded_nodes = ["B"]
        dispatches = dispatch_stranded_areas(
            graph=self.graph,
            stranded_nodes=stranded_nodes,
            risk_score=85.0,
            locations_by_id=self.locations_by_id,
            ngo_bases=self.ngo_bases,
        )
        req_id = dispatches[0].id
        self.assertEqual(dispatches[0].status, "Sent")

        # 1st Acknowledgment -> 'Acknowledged'
        ack1 = acknowledge_request(req_id)
        self.assertIsNotNone(ack1)
        self.assertEqual(ack1["status"], "Acknowledged")

        # 2nd Acknowledgment -> 'En route'
        ack2 = acknowledge_request(req_id)
        self.assertEqual(ack2["status"], "En route")


if __name__ == "__main__":
    unittest.main()
