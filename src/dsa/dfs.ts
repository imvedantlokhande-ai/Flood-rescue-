/**
 * Depth-First Search (DFS) Algorithm
 *
 * Implemented in both:
 * 1. Iterative version: using our custom Stack data structure (avoids call-stack overflow on large graphs).
 * 2. Recursive version: demonstrating standard algorithmic recurrence relations.
 *
 * Used for:
 * - Topological and connected component exploration
 * - Identifying completely isolated / cut-off subgraphs caused by floodwaters
 */

import { Graph } from './graph';
import { Stack } from './stack';

export interface DfsResult {
  visitedOrder: string[];
  parents: Record<string, string | null>;
  visitedSet: Set<string>;
}

/**
 * Iterative DFS using our custom Stack data structure.
 */
export function depthFirstSearchIterative(
  graph: Graph,
  startNode: string,
  targetNode?: string
): DfsResult {
  const stack = new Stack<string>();
  const visitedSet = new Set<string>();
  const visitedOrder: string[] = [];
  const parents: Record<string, string | null> = {};

  for (const nodeId of graph.getNodes()) {
    parents[nodeId] = null;
  }

  if (!graph.getNode(startNode)) {
    return { visitedOrder, parents, visitedSet };
  }

  stack.push(startNode);

  while (!stack.isEmpty()) {
    const current = stack.pop()!;

    if (!visitedSet.has(current)) {
      visitedSet.add(current);
      visitedOrder.push(current);

      if (targetNode && current === targetNode) {
        break;
      }

      // Traverse unblocked neighbors
      const neighbors = graph.getNeighbors(current, false);
      // Reverse neighbor iteration so first neighbor is popped first
      for (let i = neighbors.length - 1; i >= 0; i--) {
        const edge = neighbors[i];
        const neighbor = edge.v;
        if (!visitedSet.has(neighbor)) {
          if (parents[neighbor] === null && neighbor !== startNode) {
            parents[neighbor] = current;
          }
          stack.push(neighbor);
        }
      }
    }
  }

  return { visitedOrder, parents, visitedSet };
}

/**
 * Recursive DFS implementation.
 */
export function depthFirstSearchRecursive(
  graph: Graph,
  startNode: string,
  visitedSet: Set<string> = new Set(),
  visitedOrder: string[] = [],
  parents: Record<string, string | null> = {}
): DfsResult {
  if (visitedSet.size === 0) {
    for (const nodeId of graph.getNodes()) {
      parents[nodeId] = null;
    }
  }

  visitedSet.add(startNode);
  visitedOrder.push(startNode);

  const neighbors = graph.getNeighbors(startNode, false);
  for (const edge of neighbors) {
    const neighbor = edge.v;
    if (!visitedSet.has(neighbor)) {
      parents[neighbor] = startNode;
      depthFirstSearchRecursive(graph, neighbor, visitedSet, visitedOrder, parents);
    }
  }

  return { visitedOrder, parents, visitedSet };
}
