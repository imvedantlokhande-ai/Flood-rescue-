/**
 * Connected Components Algorithm
 *
 * Built on DFS to partition the road graph into connected subgraphs after road closures.
 * Identifies stranded areas (components with no passable path to any municipal safe shelter).
 */

import { Graph } from './graph';
import { depthFirstSearchIterative } from './dfs';

export interface StrandedAnalysis {
  components: string[][];
  strandedComponents: string[][];
  strandedNodes: string[];
  shelterComponentMap: Record<string, number>;
}

export function findConnectedComponents(graph: Graph): string[][] {
  const visitedGlobal = new Set<string>();
  const components: string[][] = [];

  for (const nodeId of graph.getNodes()) {
    if (!visitedGlobal.has(nodeId)) {
      const dfsRes = depthFirstSearchIterative(graph, nodeId);
      const componentNodes: string[] = [];
      dfsRes.visitedSet.forEach(id => {
        visitedGlobal.add(id);
        componentNodes.push(id);
      });
      components.push(componentNodes);
    }
  }

  return components;
}

/**
 * Identifies which graph components contain municipal shelters vs which are cut off (stranded).
 */
export function identifyStrandedAreas(graph: Graph): StrandedAnalysis {
  const components = findConnectedComponents(graph);
  const strandedComponents: string[][] = [];
  const strandedNodes: string[] = [];
  const shelterComponentMap: Record<string, number> = {};

  components.forEach((component, idx) => {
    let hasShelter = false;
    for (const nodeId of component) {
      const node = graph.getNode(nodeId);
      if (node && node.is_safe_zone) {
        hasShelter = true;
        shelterComponentMap[nodeId] = idx;
      }
    }

    if (!hasShelter) {
      strandedComponents.push(component);
      strandedNodes.push(...component);
    }
  });

  return {
    components,
    strandedComponents,
    strandedNodes,
    shelterComponentMap
  };
}
