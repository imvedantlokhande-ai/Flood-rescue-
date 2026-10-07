/**
 * Breadth-First Search (BFS) Algorithm
 *
 * Built strictly on our custom Queue data structure.
 *
 * Used for:
 * - Reachability analysis: Which municipal shelters can be reached from the evacuee's location?
 * - Unweighted shortest path: Finding paths with the fewest turns/intersections.
 * - Dynamic reachability frontier animation.
 */

import { Graph } from './graph';
import { Queue } from './queue';

export interface BfsResult {
  visitedOrder: string[];
  distances: Record<string, number>; // hop counts from startNode
  parents: Record<string, string | null>;
  reachableNodes: Set<string>;
  reachableShelters: string[];
}

export function breadthFirstSearch(
  graph: Graph,
  startNode: string,
  targetNode?: string
): BfsResult {
  const queue = new Queue<string>();
  const visitedOrder: string[] = [];
  const distances: Record<string, number> = {};
  const parents: Record<string, string | null> = {};
  const reachableNodes = new Set<string>();

  // Initialize nodes
  for (const nodeId of graph.getNodes()) {
    distances[nodeId] = Infinity;
    parents[nodeId] = null;
  }

  if (!graph.getNode(startNode)) {
    return {
      visitedOrder,
      distances,
      parents,
      reachableNodes,
      reachableShelters: []
    };
  }

  queue.enqueue(startNode);
  distances[startNode] = 0;
  reachableNodes.add(startNode);

  while (!queue.isEmpty()) {
    const current = queue.dequeue()!;
    visitedOrder.push(current);

    if (targetNode && current === targetNode) {
      break;
    }

    const neighbors = graph.getNeighbors(current, false); // Only non-blocked edges
    for (const edge of neighbors) {
      const neighbor = edge.v;
      if (distances[neighbor] === Infinity) {
        distances[neighbor] = distances[current] + 1;
        parents[neighbor] = current;
        reachableNodes.add(neighbor);
        queue.enqueue(neighbor);
      }
    }
  }

  // Filter reachable safe zones
  const reachableShelters = Array.from(reachableNodes).filter(id => {
    const node = graph.getNode(id);
    return node ? node.is_safe_zone : false;
  });

  return {
    visitedOrder,
    distances,
    parents,
    reachableNodes,
    reachableShelters
  };
}

/**
 * Reconstructs the hop-optimal path from startNode to targetNode using BFS parent pointers.
 */
export function reconstructBfsPath(
  parents: Record<string, string | null>,
  targetNode: string
): string[] {
  const path: string[] = [];
  let curr: string | null = targetNode;

  while (curr !== null) {
    path.push(curr);
    curr = parents[curr] || null;
  }

  return path.reverse();
}
