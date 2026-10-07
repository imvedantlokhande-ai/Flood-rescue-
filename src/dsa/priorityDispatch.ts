/**
 * Priority Rescue Dispatcher Engine
 *
 * Strict Compliance:
 * 1. Priority Ordering: Uses our custom MinHeap
 *    priority = -(risk_score * population)
 *    The most vulnerable / populous stranded area pops first.
 * 2. Resource Assignment: Runs custom Dijkstra's algorithm from each NGO base to find the nearest
 *    reachable NGO response unit with passable road access.
 * 3. Fallback / Escalation: If all roads between NGOs and the stranded area are submerged,
 *    marks the request as "NEEDS AIRLIFT / BOAT RESCUE".
 */

import { Graph } from './graph';
import { MinHeap } from './minHeap';
import { dijkstraShortestPath, reconstructDijkstraPath } from './dijkstra';

export interface NgoBase {
  id: string;
  name: string;
  node: string;
  contact: string;
  vehicle_capacity: number;
  base_location?: string;
}

export interface RescueRequest {
  id: string;
  strandedNode: string;
  strandedName: string;
  population: number;
  riskScore: number;
  priorityScore: number;
  priorityRank: number;
  ngoAssigned: NgoBase | null;
  rescueRouteNodes: string[];
  distanceKm: number;
  etaMinutes: number;
  status: 'Dispatched' | 'Acknowledged' | 'En Route' | 'Airlift Required';
  needsAirlift: boolean;
  appRouteUrl: string;
  osmUrl: string;
  timestamp: string;
}

export function dispatchStrandedAreas(
  graph: Graph,
  strandedNodes: string[],
  riskScore: number,
  ngoBases: NgoBase[]
): RescueRequest[] {
  if (!strandedNodes || strandedNodes.length === 0) {
    return [];
  }

  // 1. MinHeap: insert with negative priority so highest urgency pops first
  const priorityHeap = new MinHeap<string>();

  for (const nodeId of strandedNodes) {
    const node = graph.getNode(nodeId);
    const pop = node ? node.population : 5000;
    const urgency = riskScore * pop;
    priorityHeap.push(-urgency, nodeId);
  }

  const requests: RescueRequest[] = [];
  let rank = 1;

  // 2. Pop in descending urgency order
  while (!priorityHeap.isEmpty()) {
    const minElem = priorityHeap.pop()!;
    const nodeId = minElem.value;
    const priorityScore = -minElem.key;
    const node = graph.getNode(nodeId);
    const nodeName = node ? node.name : nodeId;
    const population = node ? node.population : 5000;

    // 3. Multi-NGO Dijkstra search: find closest reachable NGO base
    let bestNgo: NgoBase | null = null;
    let bestDist = Infinity;
    let bestPath: string[] = [];

    for (const ngo of ngoBases) {
      if (!graph.getNode(ngo.node)) {
        continue;
      }

      // Run Dijkstra from this NGO base to the stranded node
      const dijkstraRes = dijkstraShortestPath(graph, ngo.node, nodeId, true);
      const dist = dijkstraRes.distances[nodeId];

      if (dist !== undefined && dist < bestDist && dist !== Infinity) {
        bestDist = dist;
        bestNgo = ngo;
        bestPath = reconstructDijkstraPath(dijkstraRes.parents, nodeId);
      }
    }

    const needsAirlift = bestNgo === null || bestDist === Infinity;
    const distanceKm = needsAirlift ? 0 : Math.round(bestDist * 100) / 100;
    const etaMinutes = needsAirlift ? 0 : Math.round((distanceKm / 35.0) * 60.0);

    const targetCoords = node ? `${node.lat},${node.lng}` : '';
    const osmUrl = node
      ? `https://www.openstreetmap.org/?mlat=${node.lat}&mlon=${node.lng}#map=15/${node.lat}/${node.lng}`
      : '';

    const reqId = `REQ_${String(rank).padStart(3, '0')}`;
    requests.push({
      id: reqId,
      strandedNode: nodeId,
      strandedName: nodeName,
      population,
      riskScore,
      priorityScore: Math.round(priorityScore),
      priorityRank: rank,
      ngoAssigned: bestNgo,
      rescueRouteNodes: bestPath,
      distanceKm,
      etaMinutes,
      status: needsAirlift ? 'Airlift Required' : 'Dispatched',
      needsAirlift,
      appRouteUrl: `/#route=${reqId}`,
      osmUrl,
      timestamp: new Date().toLocaleTimeString()
    });

    rank++;
  }

  return requests;
}
