/**
 * Custom Adjacency List Graph
 *
 * Strict Compliance:
 * - NO networkx or graph packages.
 * - Stores vertices, attributes, weighted undirected/directed edges.
 * - Supports dynamic edge blocking, unblocking, and flood risk penalty weights.
 */

export interface NodeAttributes {
  id: string;
  name: string;
  lat: number;
  lng: number;
  elevation_m: number;
  population: number;
  is_safe_zone: boolean;
  type?: string;
  capacity?: number;
  [key: string]: any;
}

export interface EdgeAttributes {
  id: string;
  from: string;
  to: string;
  distance_km: number;
  effective_weight: number;
  is_blocked: boolean;
  is_risky: boolean;
  water_depth_m: number;
  name?: string;
  highway_type?: string;
  maxspeed_kmh?: number;
  low_lying?: number;
  [key: string]: any;
}

export class Edge {
  public u: string;
  public v: string;
  public weight: number; // Base distance in km
  public effectiveWeight: number; // Flood risk penalty adjusted weight
  public roadId: string;
  public isBlocked: boolean; // True if submerged / impassable
  public isRisky: boolean;   // True if shallow / cautioned
  public waterDepthM: number;
  public attributes: Record<string, any>;

  constructor(
    u: string,
    v: string,
    weight: number,
    roadId?: string,
    attributes?: Record<string, any>
  ) {
    this.u = u;
    this.v = v;
    this.weight = weight;
    this.effectiveWeight = weight;
    this.roadId = roadId || `${u}_${v}`;
    this.isBlocked = false;
    this.isRisky = false;
    this.waterDepthM = 0.0;
    this.attributes = attributes ? { ...attributes } : {};
  }
}

export class Graph {
  private nodes: Map<string, NodeAttributes> = new Map();
  private adjacency: Map<string, Edge[]> = new Map();
  private edgeLookup: Map<string, Edge> = new Map();

  constructor() {
    this.nodes = new Map();
    this.adjacency = new Map();
    this.edgeLookup = new Map();
  }

  public addNode(id: string, attributes?: Partial<NodeAttributes>): void {
    if (!this.nodes.has(id)) {
      this.nodes.set(id, {
        id,
        name: attributes?.name || id,
        lat: attributes?.lat || 0,
        lng: attributes?.lng || 0,
        elevation_m: attributes?.elevation_m ?? 560,
        population: attributes?.population ?? 0,
        is_safe_zone: attributes?.is_safe_zone ?? false,
        ...attributes
      });
      this.adjacency.set(id, []);
    } else if (attributes) {
      const existing = this.nodes.get(id)!;
      this.nodes.set(id, { ...existing, ...attributes });
    }
  }

  public addEdge(
    u: string,
    v: string,
    weight: number,
    roadId?: string,
    bidirectional: boolean = true,
    attributes?: Record<string, any>
  ): void {
    if (!this.nodes.has(u)) {
      this.addNode(u);
    }
    if (!this.nodes.has(v)) {
      this.addNode(v);
    }

    const edge = new Edge(u, v, weight, roadId, attributes);
    this.adjacency.get(u)!.push(edge);
    this.edgeLookup.set(`${u}_${v}`, edge);

    if (bidirectional) {
      const revEdge = new Edge(v, u, weight, roadId, attributes);
      this.adjacency.get(v)!.push(revEdge);
      this.edgeLookup.set(`${v}_${u}`, revEdge);
    }
  }

  public getNode(id: string): NodeAttributes | undefined {
    return this.nodes.get(id);
  }

  public getNodes(): string[] {
    return Array.from(this.nodes.keys());
  }

  public getAllNodeAttributes(): NodeAttributes[] {
    return Array.from(this.nodes.values());
  }

  public getNeighbors(id: string, includeBlocked: boolean = false): Edge[] {
    const list = this.adjacency.get(id) || [];
    if (includeBlocked) {
      return list;
    }
    return list.filter(edge => !edge.isBlocked);
  }

  public getEdge(u: string, v: string): Edge | undefined {
    return this.edgeLookup.get(`${u}_${v}`);
  }

  public getAllEdges(): Edge[] {
    const uniqueMap = new Map<string, Edge>();
    this.edgeLookup.forEach((edge) => {
      const canonicalKey = [edge.u, edge.v].sort().join("<->");
      if (!uniqueMap.has(canonicalKey)) {
        uniqueMap.set(canonicalKey, edge);
      }
    });
    return Array.from(uniqueMap.values());
  }

  public setEdgeBlocked(roadId: string, blocked: boolean, waterDepthM: number = 0.0): void {
    this.edgeLookup.forEach(edge => {
      if (edge.roadId === roadId) {
        edge.isBlocked = blocked;
        edge.waterDepthM = waterDepthM;
        if (blocked) {
          edge.isRisky = false;
        }
      }
    });
  }

  public setEdgeRisky(roadId: string, risky: boolean, effectiveWeight: number, waterDepthM: number = 0.0): void {
    this.edgeLookup.forEach(edge => {
      if (edge.roadId === roadId) {
        edge.isRisky = risky;
        edge.effectiveWeight = effectiveWeight;
        edge.waterDepthM = waterDepthM;
      }
    });
  }

  public resetAllEdges(): void {
    this.edgeLookup.forEach(edge => {
      edge.isBlocked = false;
      edge.isRisky = false;
      edge.effectiveWeight = edge.weight;
      edge.waterDepthM = 0.0;
    });
  }

  public nodeCount(): number {
    return this.nodes.size;
  }

  public edgeCount(): number {
    return this.getAllEdges().length;
  }
}
