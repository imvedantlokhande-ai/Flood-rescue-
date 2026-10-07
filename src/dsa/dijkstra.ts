/**
 * Dijkstra's Shortest Path Algorithm
 *
 * Strict Compliance:
 * - Powered by our custom MinHeap priority queue.
 * - NO external libraries.
 * - Supports:
 *   1. Metric distance minimization (haversine km)
 *   2. Risk-penalized edge weights (effective distance adjusting for water depth)
 *   3. Replay animation trace tracking (step-by-step heap pop & edge relaxation for visual UI)
 */

import { Graph } from './graph';
import { MinHeap } from './minHeap';

export interface DijkstraStep {
  step: number;
  currentNode: string;
  currentDist: number;
  relaxedNeighbors: Array<{ neighbor: string; weight: number; newDist: number }>;
}

export interface DijkstraResult {
  distances: Record<string, number>;
  parents: Record<string, string | null>;
  visitedOrder: string[];
  executionTrace: DijkstraStep[];
  targetPath?: string[];
  targetDistance?: number;
}

export function dijkstraShortestPath(
  graph: Graph,
  startNode: string,
  targetNode?: string,
  useEffectiveWeights: boolean = false
): DijkstraResult {
  const minHeap = new MinHeap<string>();
  const distances: Record<string, number> = {};
  const parents: Record<string, string | null> = {};
  const visitedOrder: string[] = [];
  const executionTrace: DijkstraStep[] = [];
  const settled = new Set<string>();

  for (const nodeId of graph.getNodes()) {
    distances[nodeId] = Infinity;
    parents[nodeId] = null;
  }

  if (!graph.getNode(startNode)) {
    return { distances, parents, visitedOrder, executionTrace };
  }

  distances[startNode] = 0;
  minHeap.push(0, startNode);

  let stepCount = 0;

  while (!minHeap.isEmpty()) {
    const minElem = minHeap.pop()!;
    const currDist = minElem.key;
    const currNode = minElem.value;

    if (settled.has(currNode)) {
      continue;
    }
    settled.add(currNode);
    visitedOrder.push(currNode);

    const stepInfo: DijkstraStep = {
      step: ++stepCount,
      currentNode: currNode,
      currentDist: Math.round(currDist * 100) / 100,
      relaxedNeighbors: []
    };

    if (targetNode && currNode === targetNode) {
      executionTrace.push(stepInfo);
      break;
    }

    // Traverse unblocked incident edges
    const incidentEdges = graph.getNeighbors(currNode, false);

    for (const edge of incidentEdges) {
      const neighbor = edge.v;
      if (settled.has(neighbor)) {
        continue;
      }

      const edgeWeight = useEffectiveWeights ? edge.effectiveWeight : edge.weight;
      const altDist = currDist + edgeWeight;

      if (altDist < distances[neighbor]) {
        distances[neighbor] = altDist;
        parents[neighbor] = currNode;
        minHeap.push(altDist, neighbor);

        stepInfo.relaxedNeighbors.push({
          neighbor,
          weight: Math.round(edgeWeight * 100) / 100,
          newDist: Math.round(altDist * 100) / 100
        });
      }
    }

    executionTrace.push(stepInfo);
  }

  let targetPath: string[] | undefined = undefined;
  let targetDistance: number | undefined = undefined;

  if (targetNode && distances[targetNode] !== Infinity) {
    targetPath = reconstructDijkstraPath(parents, targetNode);
    targetDistance = Math.round(distances[targetNode] * 100) / 100;
  }

  return {
    distances,
    parents,
    visitedOrder,
    executionTrace,
    targetPath,
    targetDistance
  };
}

/**
 * Reconstructs the complete node path from start to target using parent pointers.
 */
export function reconstructDijkstraPath(
  parents: Record<string, string | null>,
  targetNode: string
): string[] {
  const path: string[] = [];
  let curr: string | null = targetNode;

  while (curr !== null) {
    path.push(curr);
    curr = parents[curr];
  }

  return path.reverse();
}
