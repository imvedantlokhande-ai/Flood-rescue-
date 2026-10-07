import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  ShieldAlert,
  Navigation,
  Droplets,
  RotateCcw,
  Layers,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Play,
  Pause,
  Compass,
  Footprints,
  Car,
  Activity,
  Sliders,
  Sun,
  Moon,
  Info,
  LifeBuoy,
  Phone,
  Radio,
  Crosshair,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  MapPin,
  ZoomIn,
  ZoomOut,
  Maximize2,
  HelpCircle,
  Eye,
  EyeOff,
  ShieldCheck,
  Waves,
  Table2,
  Sparkles,
  Bot,
  RefreshCw,
  Search,
  Filter,
  Download,
  AlertOctagon,
  FileSpreadsheet,
  Check,
  Flame,
  Gauge,
  Send
} from 'lucide-react';

import { Graph, NodeAttributes } from './dsa/graph';
import { calculateFloodRisk, FloodRiskResult } from './dsa/floodRisk';
import { breadthFirstSearch } from './dsa/bfs';
import { depthFirstSearchIterative } from './dsa/dfs';
import { identifyStrandedAreas } from './dsa/components';
import { dijkstraShortestPath, DijkstraStep } from './dsa/dijkstra';
import { dispatchStrandedAreas, RescueRequest, NgoBase } from './dsa/priorityDispatch';
import { findNearestNode, haversineDistanceKm } from './dsa/haversine';

interface RoadData {
  id: string;
  from: string;
  to: string;
  distance_km: number;
  name: string;
  low_lying: number;
}

interface CityGraphData {
  city_name: string;
  center_coordinates: { lat: number; lng: number };
  river_basin: string;
  locations: NodeAttributes[];
  ngo_bases: NgoBase[];
  roads: RoadData[];
}

export type RescueStatus = RescueRequest['status'] | 'Rescued';
export type ExtendedRescueRequest = Omit<RescueRequest, 'status'> & {
  status: RescueStatus;
};


export default function App() {
  const [cityData, setCityData] = useState<CityGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // View Mode: 'map' | 'table'
  const [viewMode, setViewMode] = useState<'map' | 'table'>('map');

  // Weather & Hydraulic Telemetry
  const [rainfallRate, setRainfallRate] = useState<number>(45.0);
  const [rainfall24h, setRainfall24h] = useState<number>(120.0);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);
  const [isStaleData, setIsStaleData] = useState<boolean>(false);
  const [demoMode, setDemoMode] = useState<boolean>(false);
  const [lastUpdatedTime, setLastUpdatedTime] = useState<string>('Initializing...');


  // User Location & Origin Node
  const [userCoords, setUserCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [accuracyRadius, setAccuracyRadius] = useState<number>(30);
  const [userOriginNode, setUserOriginNode] = useState<string>('LOC_01');

  // Theme & Canvas Display Options
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [showAllNodes, setShowAllNodes] = useState<boolean>(true);
  const [showCriticalNodes, setShowCriticalNodes] = useState<boolean>(false);
  const [showFloodCircles, setShowFloodCircles] = useState<boolean>(true);
  const [showRiverBasin, setShowRiverBasin] = useState<boolean>(true);

  // Routing Strategy
  const [routingMode, setRoutingMode] = useState<'dijkstra' | 'risk' | 'bfs'>('dijkstra');

  // Dijkstra Step-by-Step Replay
  const [isReplaying, setIsReplaying] = useState<boolean>(false);
  const [replaySpeed, setReplaySpeed] = useState<number>(350); // ms per step
  const [replayCurrentStep, setReplayCurrentStep] = useState<number>(0);

  // Ghost route persistence (3 seconds faded history)
  const [ghostRouteNodeIds, setGhostRouteNodeIds] = useState<string[]>([]);
  const previousRouteNodeIdsRef = useRef<string[]>([]);

  // UI Panels & Selection
  const [activeTab, setActiveTab] = useState<'planner' | 'tracker' | 'dispatch' | 'dsa_docs'>('planner');
  const [focusedRescueRequestId, setFocusedRescueRequestId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredRoadId, setHoveredRoadId] = useState<string | null>(null);

  // Tabular View Filter & Search State
  const [tableSearchQuery, setTableSearchQuery] = useState<string>('');
  const [tablePriorityFilter, setTablePriorityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [tableStatusFilter, setTableStatusFilter] = useState<'ALL' | 'Dispatched' | 'Acknowledged' | 'En Route' | 'Airlift Required' | 'Rescued'>('ALL');
  const [rescueStatusOverrides, setRescueStatusOverrides] = useState<Record<string, RescueRequest['status'] | 'Rescued'>>({});

  // Canvas Pan & Zoom
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const canvasRef = useRef<SVGSVGElement | null>(null);

  // 1. Fetch city_graph.json on mount
  useEffect(() => {
    fetch('/city_graph.json')
      .then((res) => res.json())
      .then((data: CityGraphData) => {
        setCityData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load city_graph.json', err);
        setLoading(false);
      });
  }, []);

  // 2. Fetch live rainfall from Open-Meteo forecast API with fallback
  const fetchOpenMeteoRainfall = useCallback(async () => {
    try {
      const lat = cityData?.center_coordinates.lat || 18.6274;
      const lng = cityData?.center_coordinates.lng || 73.8016;
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=precipitation&hourly=precipitation&forecast_days=2`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();

      const currentPrecip = json.current?.precipitation ?? 0.0;
      const hourlyRain = json.hourly?.precipitation || [];
      const past24hSum = hourlyRain.slice(0, 24).reduce((a: number, b: number) => a + (b || 0), 0);

      const calculatedRate = currentPrecip > 0 ? currentPrecip * 12.0 : 38.5;
      const calculated24h = past24hSum > 0 ? past24hSum : 95.0;

      if (!demoMode) {
        setRainfallRate(Math.round(calculatedRate * 10) / 10);
        setRainfall24h(Math.round(calculated24h * 10) / 10);
      }
      setIsLiveApi(true);
      setIsStaleData(false);
      setLastUpdatedTime(new Date().toLocaleTimeString());
    } catch (err) {
      console.warn('Open-Meteo fetch failed, using fallback cached telemetry', err);
      setIsStaleData(true);
      setIsLiveApi(false);
      setLastUpdatedTime(`${new Date().toLocaleTimeString()} (Fallback)`);
    }
  }, [cityData, demoMode]);

  // Periodic weather polling every 2 minutes (120,000 ms)
  useEffect(() => {
    fetchOpenMeteoRainfall();
    const interval = setInterval(() => {
      fetchOpenMeteoRainfall();
    }, 120000);
    return () => clearInterval(interval);
  }, [fetchOpenMeteoRainfall]);

  // Demo mode auto-escalating rainfall cycle
  useEffect(() => {
    if (!demoMode) return;
    const interval = setInterval(() => {
      setRainfallRate((prev) => {
        if (prev >= 95.0) return 15.0;
        return Math.round((prev + 12.5) * 10) / 10;
      });
      setRainfall24h((prev) => {
        if (prev >= 240.0) return 40.0;
        return Math.round((prev + 25.0) * 10) / 10;
      });
    }, 5000);
    return () => clearInterval(interval);
  }, [demoMode]);

  // 3. User Geolocation with watchPosition
  useEffect(() => {
    if (!navigator.geolocation || !cityData) return;

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude, longitude, accuracy } = pos.coords;
        setUserCoords({ lat: latitude, lng: longitude });
        setAccuracyRadius(Math.max(15, Math.min(accuracy, 120)));

        const snap = findNearestNode(latitude, longitude, cityData.locations);
        if (snap) {
          setUserOriginNode(snap.nearestNodeId);
        }
      },
      (err) => {
        console.warn('Geolocation denied or unavailable; defaulting to LOC_01', err);
        if (cityData.locations.length > 0) {
          const defaultLoc = cityData.locations[0];
          setUserCoords({ lat: defaultLoc.lat, lng: defaultLoc.lng });
          setUserOriginNode(defaultLoc.id);
        }
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, [cityData]);

  // 4. Compute Road Water Depths
  const roadWaterDepths = useMemo(() => {
    if (!cityData) return {};
    const depths: Record<string, { depth: number; isBlocked: boolean; isRisky: boolean }> = {};

    cityData.roads.forEach((road) => {
      const base = (rainfallRate * 0.012) + (road.low_lying * 0.55);
      const depth = Math.round(base * 100) / 100;
      const isBlocked = depth >= 0.50;
      const isRisky = !isBlocked && depth >= 0.20;
      depths[road.id] = { depth, isBlocked, isRisky };
    });

    return depths;
  }, [cityData, rainfallRate]);

  // Max depth in network
  const maxWaterDepth = useMemo(() => {
    const list = Object.values(roadWaterDepths).map((d) => d.depth);
    return list.length > 0 ? Math.max(...list) : 0;
  }, [roadWaterDepths]);

  // 5. Automated Flood Risk Score
  const floodRisk = useMemo<FloodRiskResult>(() => {
    return calculateFloodRisk(rainfallRate, rainfall24h, maxWaterDepth);
  }, [rainfallRate, rainfall24h, maxWaterDepth]);

  // 6. Build Pure Adjacency List Graph
  const graph = useMemo<Graph>(() => {
    const g = new Graph();
    if (!cityData) return g;

    // Add nodes
    cityData.locations.forEach((loc) => {
      g.addNode(loc.id, loc);
    });

    // Add edges
    cityData.roads.forEach((road) => {
      g.addEdge(road.from, road.to, road.distance_km, road.id, true, {
        name: road.name,
        low_lying: road.low_lying
      });

      const state = roadWaterDepths[road.id];
      if (state) {
        if (state.isBlocked) {
          g.setEdgeBlocked(road.id, true, state.depth);
        } else if (state.isRisky) {
          const effWeight = Math.round(road.distance_km * 2.5 * 100) / 100;
          g.setEdgeRisky(road.id, true, effWeight, state.depth);
        }
      }
    });

    return g;
  }, [cityData, roadWaterDepths]);

  // 7. Graph Traversal Algorithms: BFS, DFS, Connected Components, Dijkstra
  const analysisResults = useMemo(() => {
    if (!cityData) {
      return {
        bfsResult: null,
        strandedAnalysis: null,
        dijkstraMetric: null,
        dijkstraRisk: null,
        safeShelters: [],
        bestShelterNode: null,
        activePath: [] as string[],
        activeDistanceKm: 0,
        isStranded: false
      };
    }

    const safeShelters = cityData.locations.filter((l) => l.is_safe_zone);

    // 1. BFS Reachability
    const bfsRes = breadthFirstSearch(graph, userOriginNode);

    // 2. DFS Component Check for Stranded Areas
    const strandedRes = identifyStrandedAreas(graph);

    // Check if user is stranded
    const userIsStranded = bfsRes.reachableShelters.length === 0;

    // 3. Dijkstra Shortest Path (metric haversine km)
    const dijkstraMetric = dijkstraShortestPath(graph, userOriginNode, undefined, false);

    // 4. Dijkstra Risk-Penalized Shortest Path
    const dijkstraRisk = dijkstraShortestPath(graph, userOriginNode, undefined, true);

    // Determine best reachable shelter
    let bestShelterId: string | null = null;
    let minMetricDist = Infinity;

    bfsRes.reachableShelters.forEach((shelterId) => {
      const d = dijkstraMetric.distances[shelterId];
      if (d !== undefined && d < minMetricDist) {
        minMetricDist = d;
        bestShelterId = shelterId;
      }
    });

    // Reconstruct metric path
    const metricPath: string[] = [];
    if (bestShelterId && dijkstraMetric.parents[bestShelterId] !== undefined) {
      let curr: string | null = bestShelterId;
      while (curr !== null) {
        metricPath.push(curr);
        curr = dijkstraMetric.parents[curr];
      }
      metricPath.reverse();
    }

    // Reconstruct risk path
    const riskPath: string[] = [];
    if (bestShelterId && dijkstraRisk.parents[bestShelterId] !== undefined) {
      let curr: string | null = bestShelterId;
      while (curr !== null) {
        riskPath.push(curr);
        curr = dijkstraRisk.parents[curr];
      }
      riskPath.reverse();
    }

    // BFS hop path
    const bfsPath: string[] = [];
    if (bestShelterId && bfsRes.parents[bestShelterId] !== undefined) {
      let curr: string | null = bestShelterId;
      while (curr !== null) {
        bfsPath.push(curr);
        curr = bfsRes.parents[curr];
      }
      bfsPath.reverse();
    }

    let activePath = metricPath;
    let activeDistanceKm = minMetricDist === Infinity ? 0 : Math.round(minMetricDist * 100) / 100;

    if (routingMode === 'risk') {
      activePath = riskPath;
      const rd = dijkstraRisk.distances[bestShelterId || ''];
      activeDistanceKm = rd === undefined || rd === Infinity ? 0 : Math.round(rd * 100) / 100;
    } else if (routingMode === 'bfs') {
      activePath = bfsPath;
      let distSum = 0;
      for (let i = 0; i < bfsPath.length - 1; i++) {
        const edge = cityData.roads.find(
          (r) =>
            (r.from === bfsPath[i] && r.to === bfsPath[i + 1]) ||
            (r.from === bfsPath[i + 1] && r.to === bfsPath[i])
        );
        if (edge) distSum += edge.distance_km;
      }
      activeDistanceKm = Math.round(distSum * 100) / 100;
    }

    const bestShelterNode = cityData.locations.find((l) => l.id === bestShelterId) || null;

    return {
      bfsResult: bfsRes,
      strandedAnalysis: strandedRes,
      dijkstraMetric,
      dijkstraRisk,
      safeShelters,
      bestShelterNode,
      activePath,
      activeDistanceKm,
      isStranded: userIsStranded
    };
  }, [cityData, graph, userOriginNode, routingMode]);

  // 8. Automated NGO Priority Dispatch for Stranded Areas
  const rawRescueRequests = useMemo<RescueRequest[]>(() => {
    if (!cityData || !analysisResults.strandedAnalysis) return [];
    return dispatchStrandedAreas(
      graph,
      analysisResults.strandedAnalysis.strandedNodes,
      floodRisk.score,
      cityData.ngo_bases
    );
  }, [cityData, graph, analysisResults.strandedAnalysis, floodRisk.score]);

  // Combined rescue requests with manual status overrides
  const rescueRequests = useMemo<ExtendedRescueRequest[]>(() => {
    return rawRescueRequests.map((req) => {
      if (rescueStatusOverrides[req.id]) {
        return { ...req, status: rescueStatusOverrides[req.id] };
      }
      return req;
    });
  }, [rawRescueRequests, rescueStatusOverrides]);

  // Ghost route management: keeps faded 3-second ghost when route updates
  useEffect(() => {
    if (analysisResults.activePath.length > 0) {
      const prev = previousRouteNodeIdsRef.current;
      if (prev.length > 0 && JSON.stringify(prev) !== JSON.stringify(analysisResults.activePath)) {
        setGhostRouteNodeIds(prev);
        const timer = setTimeout(() => {
          setGhostRouteNodeIds([]);
        }, 3000);
        return () => clearTimeout(timer);
      }
      previousRouteNodeIdsRef.current = analysisResults.activePath;
    }
  }, [analysisResults.activePath]);


  // Dijkstra Step-by-Step Replay Animation Runner
  useEffect(() => {
    if (!isReplaying || !analysisResults.dijkstraMetric) return;

    const traceSteps = analysisResults.dijkstraMetric.executionTrace;
    if (traceSteps.length === 0) {
      setIsReplaying(false);
      return;
    }

    const interval = setInterval(() => {
      setReplayCurrentStep((prev) => {
        if (prev >= traceSteps.length - 1) {
          setIsReplaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, replaySpeed);

    return () => clearInterval(interval);
  }, [isReplaying, analysisResults.dijkstraMetric, replaySpeed]);

  // Coordinate Projection: Convert Lat/Lng into 2D SVG Canvas coordinates
  const { nodeSvgCoords, bounds } = useMemo(() => {
    if (!cityData || cityData.locations.length === 0) {
      return { nodeSvgCoords: new Map<string, { x: number; y: number }>(), bounds: null };
    }

    const lats = cityData.locations.map((l) => l.lat);
    const lngs = cityData.locations.map((l) => l.lng);

    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    const svgWidth = 1000;
    const svgHeight = 700;
    const padding = 70;

    const mapCoords = new Map<string, { x: number; y: number }>();

    cityData.locations.forEach((loc) => {
      const normX = (loc.lng - minLng) / (maxLng - minLng || 0.001);
      const normY = (maxLat - loc.lat) / (maxLat - minLat || 0.001);

      const x = padding + normX * (svgWidth - padding * 2);
      const y = padding + normY * (svgHeight - padding * 2);

      mapCoords.set(loc.id, { x, y });
    });

    return {
      nodeSvgCoords: mapCoords,
      bounds: { minLat, maxLat, minLng, maxLng, svgWidth, svgHeight }
    };
  }, [cityData]);

  // Canvas Pan Handlers
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX - panOffset.x, y: e.clientY - panOffset.y };
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDragging) return;
    setPanOffset({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoomLevel((prev) => Math.max(0.5, Math.min(prev * zoomFactor, 4.0)));
  };

  const resetView = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Convert SVG coordinate back to closest node on canvas click
  const handleSvgBackgroundClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!canvasRef.current || !bounds || !cityData) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = (e.clientX - rect.left - panOffset.x) / zoomLevel;
    const clickY = (e.clientY - rect.top - panOffset.y) / zoomLevel;

    let closestNodeId: string | null = null;
    let minPixDist = Infinity;

    nodeSvgCoords.forEach((pos, id) => {
      const dx = pos.x - clickX;
      const dy = pos.y - clickY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < minPixDist) {
        minPixDist = dist;
        closestNodeId = id;
      }
    });

    if (closestNodeId && minPixDist < 35) {
      setUserOriginNode(closestNodeId);
      const loc = cityData.locations.find((l) => l.id === closestNodeId);
      if (loc) {
        setUserCoords({ lat: loc.lat, lng: loc.lng });
      }
    }
  };

  // Focused NGO rescue route for drawing
  const focusedRescueRouteNodes = useMemo<string[]>(() => {
    if (!focusedRescueRequestId) return [];
    const req = rescueRequests.find((r) => r.id === focusedRescueRequestId);
    return req ? req.rescueRouteNodes : [];
  }, [focusedRescueRequestId, rescueRequests]);

  // Filtered Rescue Requests for Fullscreen Tabular View
  const filteredRescueRequests = useMemo(() => {
    return rescueRequests.filter((req) => {
      // Search filter
      if (tableSearchQuery.trim()) {
        const q = tableSearchQuery.toLowerCase();
        const matchesName = req.strandedName.toLowerCase().includes(q);
        const matchesId = req.id.toLowerCase().includes(q);
        const matchesNgo = (req.ngoAssigned?.name || '').toLowerCase().includes(q);
        const matchesNode = req.strandedNode.toLowerCase().includes(q);
        if (!matchesName && !matchesId && !matchesNgo && !matchesNode) return false;
      }

      // Priority Filter
      if (tablePriorityFilter !== 'ALL') {
        const isCritical = req.needsAirlift || req.priorityScore >= 18000;
        const isHigh = !isCritical && req.priorityScore >= 9000;
        const isMedium = !isCritical && !isHigh && req.priorityScore >= 4000;
        const isLow = !isCritical && !isHigh && !isMedium;

        if (tablePriorityFilter === 'CRITICAL' && !isCritical) return false;
        if (tablePriorityFilter === 'HIGH' && !isHigh) return false;
        if (tablePriorityFilter === 'MEDIUM' && !isMedium) return false;
        if (tablePriorityFilter === 'LOW' && !isLow) return false;
      }

      // Status Filter
      if (tableStatusFilter !== 'ALL' && req.status !== tableStatusFilter) {
        return false;
      }

      return true;
    });
  }, [rescueRequests, tableSearchQuery, tablePriorityFilter, tableStatusFilter]);

  // Tabular summary stats
  const tableStats = useMemo(() => {
    const total = rescueRequests.length;
    const critical = rescueRequests.filter((r) => r.needsAirlift || r.priorityScore >= 18000).length;
    const inTransit = rescueRequests.filter((r) => r.status === 'En Route').length;
    const acknowledged = rescueRequests.filter((r) => r.status === 'Acknowledged' || r.status === 'Dispatched').length;
    const rescued = rescueRequests.filter((r) => (r.status as string) === 'Rescued').length;
    const totalPopulation = rescueRequests.reduce((sum, r) => sum + r.population, 0);

    return { total, critical, inTransit, acknowledged, rescued, totalPopulation };
  }, [rescueRequests]);

  // Cycle rescue status for interactive dispatch simulation
  const cycleRescueStatus = (requestId: string, currentStatus: RescueRequest['status'] | 'Rescued') => {
    const statuses: (RescueRequest['status'] | 'Rescued')[] = ['Dispatched', 'Acknowledged', 'En Route', 'Rescued'];
    const nextIdx = (statuses.indexOf(currentStatus) + 1) % statuses.length;
    const nextStatus = statuses[nextIdx];
    setRescueStatusOverrides((prev) => ({ ...prev, [requestId]: nextStatus }));
  };

  // Export rescue requests as CSV
  const exportRescueCsv = () => {
    if (rescueRequests.length === 0) return;
    const headers = ['Request ID', 'Stranded Node', 'Locality Name', 'Population', 'Priority Score', 'Airlift Required', 'Assigned NGO', 'Distance (km)', 'ETA (mins)', 'Status', 'Timestamp', 'OpenStreetMap URL'];
    const rows = rescueRequests.map((r) => [
      r.id,
      r.strandedNode,
      `"${r.strandedName}"`,
      r.population,
      r.priorityScore,
      r.needsAirlift ? 'YES' : 'NO',
      `"${r.ngoAssigned?.name || 'Airlift / Marine Unit'}"`,
      r.distanceKm,
      r.etaMinutes,
      r.status,
      r.timestamp,
      `"${r.osmUrl}"`
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `flood_rescue_dispatch_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading || !cityData) {
    return (
      <div className="h-screen w-screen bg-slate-950 flex flex-col items-center justify-center text-white font-sans">
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <div className="text-sm font-bold tracking-wide">Loading Topological Road Network...</div>
          <div className="text-xs text-slate-400">Pimpri-Chinchwad Flood Evacuation Planner (DSA)</div>
        </div>
      </div>
    );
  }

  const currentUserNodeData = cityData.locations.find((l) => l.id === userOriginNode);
  const selectedNodeData = selectedNodeId ? cityData.locations.find((l) => l.id === selectedNodeId) : null;
  const currentReplayStepData: DijkstraStep | undefined =
    analysisResults.dijkstraMetric?.executionTrace[replayCurrentStep];

  return (
    <div className={`h-screen w-screen flex flex-col overflow-hidden font-sans ${theme === 'dark' ? 'bg-slate-950 text-slate-100' : 'bg-slate-100 text-slate-900'}`}>
      {/* Top Telemetry & Control Navigation Bar */}
      <header className="h-16 px-4 shrink-0 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 flex items-center justify-between z-30 shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-lg flex items-center justify-center">
            <Waves className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm md:text-base font-bold tracking-tight text-white">
                Flood Evacuation Planner
              </h1>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                Pure DSA Engine
              </span>
              {isStaleData && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                  Stale data (Offline Cache)
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              Pimpri-Chinchwad, Pune • 25 Nodes • 40 Roads • MinHeap • Queue • Stack • Dijkstra • BFS • DFS
            </p>
          </div>
        </div>

        {/* 8-Step Workflow Indicator */}
        <div className="hidden xl:flex items-center gap-1 overflow-x-auto py-1 px-3 bg-slate-950/80 rounded-xl border border-slate-800">
          {[
            { num: 1, label: 'Rainfall', active: true, done: true },
            { num: 2, label: 'Flood Risk', active: true, done: true },
            { num: 3, label: 'Danger Gate', active: floodRisk.isDangerous, done: true },
            { num: 4, label: 'Road Graph', active: true, done: true },
            { num: 5, label: 'Flooded Edges', active: true, done: true },
            { num: 6, label: 'BFS/DFS', active: true, done: true },
            { num: 7, label: 'Dijkstra', active: true, done: true },
            { num: 8, label: 'Safe Route', active: !analysisResults.isStranded, done: true }
          ].map((step, idx) => (
            <React.Fragment key={step.num}>
              <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-semibold transition-all ${
                step.active ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40' : 'bg-slate-900 text-slate-500 border border-slate-800'
              }`}>
                <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] ${
                  step.active ? 'bg-blue-500 text-white' : 'bg-slate-800 text-slate-500'
                }`}>
                  {step.num}
                </span>
                <span>{step.label}</span>
              </div>
              {idx < 7 && <ChevronRight className="w-3 h-3 text-slate-600 shrink-0" />}
            </React.Fragment>
          ))}
        </div>

        {/* Navigation Controls & View Mode Toggle */}
        <div className="flex items-center gap-2 shrink-0">

          {/* Map vs Fullscreen Table Mode Toggle */}
          <button
            onClick={() => setViewMode(viewMode === 'map' ? 'table' : 'map')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border shadow ${
              viewMode === 'table'
                ? 'bg-amber-600 hover:bg-amber-500 text-white border-amber-400'
                : 'bg-slate-800 hover:bg-slate-700 text-cyan-300 border-slate-700'
            }`}
            title="Toggle between Map View and Full-Screen Tabular Rescue Dispatch View"
          >
            {viewMode === 'table' ? (
              <>
                <MapPin className="w-3.5 h-3.5" />
                <span>Show Map</span>
              </>
            ) : (
              <>
                <Table2 className="w-3.5 h-3.5" />
                <span>Rescue Table</span>
                {rescueRequests.length > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full bg-red-500 text-white text-[10px] font-mono">
                    {rescueRequests.length}
                  </span>
                )}
              </>
            )}
          </button>

          {/* Theme Toggle */}
          <button
            onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
            title="Toggle Theme"
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-blue-400" />}
          </button>

          {/* Tab switchers */}
          <div className="flex bg-slate-800/80 p-0.5 rounded-lg border border-slate-700 text-xs">
            <button
              onClick={() => {
                setActiveTab('planner');
                if (viewMode === 'table') setViewMode('map');
              }}
              className={`px-2.5 py-1.5 rounded-md font-semibold transition-all ${
                activeTab === 'planner' && viewMode === 'map' ? 'bg-blue-600 text-white shadow' : 'text-slate-300 hover:text-white'
              }`}
            >
              Planner
            </button>
            <button
              onClick={() => {
                setActiveTab('tracker');
                if (viewMode === 'table') setViewMode('map');
              }}
              className={`px-2.5 py-1.5 rounded-md font-semibold transition-all ${
                activeTab === 'tracker' ? 'bg-blue-600 text-white shadow' : 'text-slate-300 hover:text-white'
              }`}
            >
              DSA Trace
            </button>
            <button
              onClick={() => {
                setActiveTab('dispatch');
                setViewMode('table');
              }}
              className={`px-2.5 py-1.5 rounded-md font-semibold relative transition-all ${
                viewMode === 'table' || activeTab === 'dispatch' ? 'bg-blue-600 text-white shadow' : 'text-slate-300 hover:text-white'
              }`}
            >
              Rescue Table
              {rescueRequests.length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-red-500 text-white text-[10px] font-bold">
                  {rescueRequests.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('dsa_docs')}
              className={`px-2.5 py-1.5 rounded-md font-semibold transition-all ${
                activeTab === 'dsa_docs' ? 'bg-blue-600 text-white shadow' : 'text-slate-300 hover:text-white'
              }`}
            >
              Docs
            </button>
          </div>
        </div>
      </header>


      {/* Main Workspace Body */}
      <div className="relative flex-1 flex overflow-hidden">
        {/* Left Floating Control & Telemetry Sidebar */}
        <aside className="w-80 md:w-96 p-3 flex flex-col gap-3 shrink-0 z-20 overflow-y-auto bg-slate-900/90 backdrop-blur-md border-r border-slate-800 shadow-2xl">
          {/* View Mode Switcher Button in Sidebar */}
          <div className="p-2.5 rounded-xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400">
                {viewMode === 'map' ? <Table2 className="w-4 h-4" /> : <MapPin className="w-4 h-4" />}
              </div>
              <div>
                <div className="text-[11px] font-bold text-white">
                  {viewMode === 'map' ? 'Current View: Interactive Map' : 'Current View: Tabular Rescue Table'}
                </div>
                <div className="text-[10px] text-slate-400">
                  {viewMode === 'map' ? 'Switch to full rescue request grid' : 'Switch back to topology map visualizer'}
                </div>
              </div>
            </div>
            <button
              onClick={() => setViewMode(viewMode === 'map' ? 'table' : 'map')}
              className="px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow transition-all flex items-center gap-1"
            >
              {viewMode === 'map' ? 'Open Table' : 'Open Map'}
            </button>
          </div>

          {/* Map Display Options */}
          <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/70 space-y-2">
            <span className="text-xs font-bold text-white">Map Display Options</span>
            <button
              onClick={() => setShowCriticalNodes(!showCriticalNodes)}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs font-bold flex items-center gap-2 transition-all border ${
                showCriticalNodes
                  ? 'bg-red-600/20 text-red-300 border-red-500/40'
                  : 'bg-slate-700 text-slate-400 border-slate-600'
              }`}
            >
              <div className={`w-3 h-3 rounded ${showCriticalNodes ? 'bg-red-500' : 'bg-slate-600'}`} />
              {showCriticalNodes ? 'Hide Critical Nodes' : 'Show Critical Nodes'}
            </button>
          </div>


          {/* Flood Risk Alert Badge */}
          <div className={`p-3.5 rounded-xl border flex items-center justify-between ${
            floodRisk.level === 'SEVERE' ? 'bg-red-950/80 border-red-600 text-red-200' :
            floodRisk.level === 'HIGH' ? 'bg-amber-950/80 border-amber-600 text-amber-200' :
            floodRisk.level === 'MODERATE' ? 'bg-blue-950/80 border-blue-600 text-blue-200' :
            'bg-emerald-950/80 border-emerald-600 text-emerald-200'
          }`}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-black/40">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Flood Risk Status
                </div>
                <div className="text-base font-bold flex items-center gap-1.5">
                  {floodRisk.level} ({floodRisk.score}/100)
                </div>
              </div>
            </div>

            <div className="text-right">
              <span className="text-[10px] text-slate-400 block">Submerged Roads</span>
              <span className="text-sm font-bold text-red-400">
                {Object.values(roadWaterDepths).filter((s) => s.isBlocked).length} / {cityData.roads.length}
              </span>
            </div>
          </div>

          {/* Stranded Emergency Warning Banner */}
          {analysisResults.isStranded && (
            <div className="p-3 rounded-xl bg-red-950/90 border border-red-500 text-red-100 flex items-start gap-2.5 shadow-lg">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-red-200 uppercase tracking-wide">
                  NO PASSABLE ROAD ROUTE (STRANDED)
                </h4>
                <p className="text-[11px] text-red-300 mt-0.5">
                  All road links from <strong>{currentUserNodeData?.name}</strong> to municipal shelters are submerged. Automated NGO airlift/boat dispatch request activated.
                </p>
              </div>
            </div>
          )}

          {/* Recommended Route Summary */}
          {!analysisResults.isStranded && analysisResults.activePath.length > 0 && (
            <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/70 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                  <Navigation className="w-3.5 h-3.5 text-emerald-400" />
                  Target Shelter
                </span>
                <span className="text-xs font-bold text-emerald-400">
                  {analysisResults.activeDistanceKm} km
                </span>
              </div>
              <div className="text-sm font-bold text-white truncate">
                {analysisResults.bestShelterNode?.name}
              </div>
              <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-700">
                <span className="flex items-center gap-1">
                  <Footprints className="w-3.5 h-3.5 text-cyan-400" />
                  Walking: {Math.round((analysisResults.activeDistanceKm / 4.5) * 60)} mins
                </span>
                <span className="flex items-center gap-1">
                  <Car className="w-3.5 h-3.5 text-emerald-400" />
                  Vehicle: {Math.round((analysisResults.activeDistanceKm / 30.0) * 60)} mins
                </span>
              </div>
            </div>
          )}

          {/* Turn-by-Turn Instructions */}
          {!analysisResults.isStranded && analysisResults.activePath.length > 1 && (
            <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/70 space-y-2">
              <div className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5 text-indigo-400" />
                Turn-by-Turn Route
              </div>
              <div className="space-y-1">
                {analysisResults.activePath.slice(0, -1).map((nodeId, i) => {
                  const nextNodeId = analysisResults.activePath[i + 1];
                  const road = cityData?.roads.find(
                    (r) => (r.from === nodeId && r.to === nextNodeId) || (r.from === nextNodeId && r.to === nodeId)
                  );
                  return (
                    <div key={i} className="text-[11px] text-slate-400 flex items-start gap-2">
                      <span className="w-4 h-4 rounded-full bg-slate-700 flex items-center justify-center text-[9px] text-white shrink-0">
                        {i + 1}
                      </span>
                      <span>{road?.name || 'Unknown Road'}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Live Rainfall & Meteorological Controls */}
          <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/70 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Droplets className="w-3.5 h-3.5 text-blue-400" />
                Rainfall Telemetry
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={fetchOpenMeteoRainfall}
                  title="Refresh Open-Meteo Telemetry"
                  className="p-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-300"
                >
                  <RotateCcw className="w-3 h-3" />
                </button>
                <button
                  onClick={() => setDemoMode((d) => !d)}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold border transition-colors ${
                    demoMode ? 'bg-amber-500/20 text-amber-300 border-amber-500' : 'bg-slate-700 text-slate-400 border-slate-600'
                  }`}
                >
                  {demoMode ? 'Demo Auto-Rise: ON' : 'Demo Mode'}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Precipitation Rate</span>
                <span className="font-mono font-bold text-blue-300">{rainfallRate} mm/hr</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={rainfallRate}
                onChange={(e) => {
                  setDemoMode(false);
                  setRainfallRate(parseFloat(e.target.value));
                }}
                className="w-full accent-blue-500 h-1.5 bg-slate-700 rounded-lg cursor-pointer"
              />
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-900/60 p-2 rounded-lg border border-slate-800">
              <div>
                <span className="text-slate-500 block">24h Cumulative</span>
                <span className="font-semibold text-slate-200">{rainfall24h} mm</span>
              </div>
              <div>
                <span className="text-slate-500 block">Peak Water Depth</span>
                <span className="font-semibold text-amber-400">{maxWaterDepth} m</span>
              </div>
              <div className="col-span-2 text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-800">
                <span>Source: {isLiveApi ? 'Open-Meteo Real-time API' : 'Cached Fallback'}</span>
                <span>{lastUpdatedTime}</span>
              </div>
            </div>
          </div>

          {/* Routing Algorithm Selector */}
          <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/70 space-y-2">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-indigo-400" />
              Evacuation Routing Strategy
            </span>
            <div className="grid grid-cols-3 gap-1.5 text-xs">
              <button
                onClick={() => setRoutingMode('dijkstra')}
                className={`py-1.5 px-2 rounded-lg font-semibold transition-all text-center ${
                  routingMode === 'dijkstra' ? 'bg-blue-600 text-white shadow' : 'bg-slate-900/80 text-slate-400 hover:text-slate-200'
                }`}
              >
                Dijkstra (Dist)
              </button>
              <button
                onClick={() => setRoutingMode('risk')}
                className={`py-1.5 px-2 rounded-lg font-semibold transition-all text-center ${
                  routingMode === 'risk' ? 'bg-blue-600 text-white shadow' : 'bg-slate-900/80 text-slate-400 hover:text-slate-200'
                }`}
              >
                Risk Penalized
              </button>
              <button
                onClick={() => setRoutingMode('bfs')}
                className={`py-1.5 px-2 rounded-lg font-semibold transition-all text-center ${
                  routingMode === 'bfs' ? 'bg-blue-600 text-white shadow' : 'bg-slate-900/80 text-slate-400 hover:text-slate-200'
                }`}
              >
                BFS (Min Hops)
              </button>
            </div>
          </div>

          {/* Quick Node Selector */}
          <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/70 space-y-2">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-red-400" />
              Evacuee Origin Node
            </span>
            <select
              value={userOriginNode}
              onChange={(e) => {
                setUserOriginNode(e.target.value);
                const loc = cityData.locations.find((l) => l.id === e.target.value);
                if (loc) {
                  setUserCoords({ lat: loc.lat, lng: loc.lng });
                }
              }}
              className="w-full bg-slate-900 border border-slate-700 text-xs text-white rounded-lg p-2 font-sans focus:outline-none focus:border-blue-500"
            >
              {cityData.locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.id}: {loc.name} {loc.is_safe_zone ? '🛡️ (Shelter)' : ''}
                </option>
              ))}
            </select>
          </div>
        </aside>

        {/* Central Display Area: Full-screen Tabular View OR Interactive Network Canvas */}
        {viewMode === 'table' ? (
          /* FULL-SCREEN TABULAR VIEW OF CURRENT RESCUE REQUESTS */
          <div className="flex-1 h-full overflow-y-auto bg-slate-950 flex flex-col p-4 md:p-6 text-slate-100 z-10">
            {/* Table Header & Controls Bar */}
            <div className="flex flex-col gap-4 pb-4 border-b border-slate-800">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-red-600/20 border border-red-500/40 text-red-400">
                      <LifeBuoy className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        Live Emergency Rescue Dispatch Queue
                        <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                          {rescueRequests.length} Total Missions
                        </span>
                      </h2>
                      <p className="text-xs text-slate-400">
                        Automated MinHeap priority ordering (Risk Score × Population) & Dijkstra nearest NGO base routing.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={exportRescueCsv}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition-colors shadow"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export CSV</span>
                  </button>
                  <button
                    onClick={() => setViewMode('map')}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow flex items-center gap-1.5 transition-all"
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>Return to Map View</span>
                  </button>
                </div>
              </div>

              {/* Summary Stats Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                <div className="bg-slate-900/90 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Requests</span>
                  <span className="text-xl font-bold text-white">{tableStats.total}</span>
                </div>
                <div className="bg-slate-900/90 p-3 rounded-xl border border-red-900/50">
                  <span className="text-[10px] uppercase font-bold text-red-400 block">Critical / Airlift</span>
                  <span className="text-xl font-bold text-red-400">{tableStats.critical}</span>
                </div>
                <div className="bg-slate-900/90 p-3 rounded-xl border border-blue-900/50">
                  <span className="text-[10px] uppercase font-bold text-blue-400 block">En Route</span>
                  <span className="text-xl font-bold text-blue-400">{tableStats.inTransit}</span>
                </div>
                <div className="bg-slate-900/90 p-3 rounded-xl border border-amber-900/50">
                  <span className="text-[10px] uppercase font-bold text-amber-400 block">Acknowledged</span>
                  <span className="text-xl font-bold text-amber-400">{tableStats.acknowledged}</span>
                </div>
                <div className="bg-slate-900/90 p-3 rounded-xl border border-emerald-900/50">
                  <span className="text-[10px] uppercase font-bold text-emerald-400 block">Rescued / Safe</span>
                  <span className="text-xl font-bold text-emerald-400">{tableStats.rescued}</span>
                </div>
                <div className="bg-slate-900/90 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Endangered Pop.</span>
                  <span className="text-xl font-bold text-cyan-300">{tableStats.totalPopulation.toLocaleString()}</span>
                </div>
              </div>

              {/* Filters and Search Bar */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
                <div className="relative flex-1 max-w-md">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={tableSearchQuery}
                    onChange={(e) => setTableSearchQuery(e.target.value)}
                    placeholder="Search by location, node ID, or responder..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                  {tableSearchQuery && (
                    <button
                      onClick={() => setTableSearchQuery('')}
                      className="absolute right-2.5 top-2 text-slate-400 hover:text-white text-xs"
                    >
                      ✕
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2 flex-wrap text-xs">
                  <div className="flex items-center gap-1 text-slate-400">
                    <Filter className="w-3.5 h-3.5" />
                    <span>Priority:</span>
                  </div>
                  {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((p) => (
                    <button
                      key={p}
                      onClick={() => setTablePriorityFilter(p)}
                      className={`px-2 py-1 rounded-md text-[11px] font-semibold transition-all ${
                        tablePriorityFilter === p
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      {p}
                    </button>
                  ))}

                  <div className="h-4 w-px bg-slate-700 mx-1 hidden sm:block" />

                  <select
                    value={tableStatusFilter}
                    onChange={(e) => setTableStatusFilter(e.target.value as any)}
                    className="bg-slate-950 border border-slate-700 text-xs text-slate-300 rounded-md px-2 py-1 focus:outline-none"
                  >
                    <option value="ALL">All Statuses</option>
                    <option value="Created">Created</option>
                    <option value="Sent">Sent</option>
                    <option value="Acknowledged">Acknowledged</option>
                    <option value="En route">En route</option>
                    <option value="Rescued">Rescued</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Table Container */}
            <div className="flex-1 mt-4 overflow-x-auto rounded-xl border border-slate-800 shadow-xl bg-slate-900/50">
              {filteredRescueRequests.length === 0 ? (
                <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                  <div className="text-sm font-bold text-white">No Matching Rescue Requests</div>
                  <p className="text-xs text-slate-500 max-w-sm">
                    {rescueRequests.length === 0
                      ? 'No stranded areas detected. All populated sectors currently have passable road links.'
                      : 'No requests matched the current search query or filter criteria.'}
                  </p>
                </div>
              ) : (
                <table className="w-full text-left text-xs text-slate-300 border-collapse">
                  <thead className="bg-slate-900 text-slate-400 text-[11px] uppercase tracking-wider sticky top-0 border-b border-slate-800">
                    <tr>
                      <th className="p-3">Rank / ID</th>
                      <th className="p-3">Stranded Sector</th>
                      <th className="p-3">Population</th>
                      <th className="p-3">Priority Score</th>
                      <th className="p-3">Assigned NGO Unit</th>
                      <th className="p-3">ETA & Distance</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {filteredRescueRequests.map((req, idx) => {
                      const isFocused = focusedRescueRequestId === req.id;
                      const loc = cityData.locations.find((l) => l.id === req.strandedNode);

                      return (
                        <tr
                          key={req.id}
                          className={`transition-colors hover:bg-slate-800/60 ${
                            isFocused ? 'bg-blue-950/40' : ''
                          }`}
                        >
                          <td className="p-3 font-mono">
                            <div className="flex items-center gap-2">
                              <span className="w-5 h-5 rounded bg-slate-800 flex items-center justify-center text-[10px] text-slate-400 font-bold">
                                #{idx + 1}
                              </span>
                              <span className="font-bold text-slate-200">{req.id}</span>
                            </div>
                          </td>

                          <td className="p-3">
                            <div className="font-bold text-white">{req.strandedName}</div>
                            <div className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                              <span>{req.strandedNode}</span>
                              {loc && <span>({loc.lat.toFixed(4)}, {loc.lng.toFixed(4)})</span>}
                            </div>
                          </td>

                          <td className="p-3">
                            <span className="font-semibold text-slate-200">{req.population.toLocaleString()}</span>
                            <span className="text-[10px] text-slate-500 block">citizens</span>
                          </td>

                          <td className="p-3 font-mono">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-amber-400">{req.priorityScore.toLocaleString()}</span>
                              {req.needsAirlift && (
                                <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 text-[10px] font-bold border border-red-500/40">
                                  AIRLIFT
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-500">Risk × Pop Formula</span>
                          </td>

                          <td className="p-3">
                            <div className="font-semibold text-white">
                              {req.ngoAssigned?.name || 'Airlift / Marine Fleet'}
                            </div>
                            <span className="text-[10px] text-slate-400 font-mono">
                              Base: {req.ngoAssigned?.node || 'Regional Airbase'}
                            </span>
                          </td>

                          <td className="p-3 font-mono">
                            {req.needsAirlift ? (
                              <span className="text-red-400 font-bold text-xs">Direct Air Transit</span>
                            ) : (
                              <div>
                                <span className="font-bold text-emerald-400 text-xs">{req.etaMinutes} mins</span>
                                <span className="text-slate-400 text-[11px] block">{req.distanceKm} km</span>
                              </div>
                            )}
                          </td>

                          <td className="p-3">
                            <button
                              onClick={() => cycleRescueStatus(req.id, req.status)}
                              title="Click to advance emergency response status"
                              className={`px-2.5 py-1 rounded-full text-[10px] font-bold border flex items-center gap-1 transition-all ${
                                (req.status as string) === 'Rescued'
                                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                                  : req.status === 'En Route'
                                  ? 'bg-blue-500/20 text-blue-300 border-blue-500/40 animate-pulse'
                                  : req.status === 'Acknowledged'
                                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                                  : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                              }`}
                            >
                              <span>{req.status}</span>
                              <span className="text-[9px] text-slate-400">&olarr;</span>
                            </button>
                          </td>

                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <a
                                href={req.osmUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-400 hover:text-white transition-colors text-[11px] flex items-center gap-1"
                                title="Open GPS Coordinates on OpenStreetMap"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                              <button
                                onClick={() => {
                                  setFocusedRescueRequestId(req.id);
                                  setViewMode('map');
                                }}
                                className="px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-[11px] flex items-center gap-1 transition-colors shadow"
                              >
                                <MapPin className="w-3 h-3" />
                                <span>Highlight on Map</span>
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        ) : (
          /* CENTRAL INTERACTIVE NETWORK CANVAS */
          <div className="relative flex-1 h-full overflow-hidden flex flex-col bg-slate-950">
            {/* Canvas Floating Top Toolbar */}
            <div className="absolute top-3 right-3 z-10 flex items-center gap-2 bg-slate-900/90 backdrop-blur-md p-1.5 rounded-xl border border-slate-800 shadow-xl text-xs">
              {/* Fullscreen Table Toggle */}
              <button
                onClick={() => setViewMode('table')}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 font-semibold flex items-center gap-1.5 transition-all border border-slate-700"
                title="Switch to full-screen tabular rescue requests view"
              >
                <Table2 className="w-3.5 h-3.5" />
                <span>Rescue Table</span>
              </button>

              <div className="h-4 w-px bg-slate-700" />

              {/* Dijkstra Replay Button */}
              <button
                onClick={() => {
                  setReplayCurrentStep(0);
                  setIsReplaying(true);
                }}
                className="px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold flex items-center gap-1.5 transition-all shadow"
                title="Animate Dijkstra step-by-step exploration"
              >
                {isReplaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                <span>{isReplaying ? 'Pause Trace' : 'Animate Dijkstra'}</span>
              </button>

              <div className="h-4 w-px bg-slate-700" />

              {/* Zoom Controls */}
              <button
                onClick={() => setZoomLevel((z) => Math.min(3.5, z * 1.2))}
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={() => setZoomLevel((z) => Math.max(0.6, z / 1.2))}
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={resetView}
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                title="Reset View"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>

            {/* Network Canvas Legend Bar */}
            <div className="absolute bottom-3 left-3 z-10 hidden sm:flex items-center gap-4 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-800 text-[11px] text-slate-300 shadow-xl">
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-1 bg-slate-500 rounded-full inline-block" />
                <span>Passable Road</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-1 bg-amber-500 rounded-full inline-block" />
                <span>Risky (&gt;0.2m)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-1 border-t-2 border-dashed border-red-500 inline-block" />
                <span>Submerged (&ge;0.5m)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-1.5 bg-emerald-500 rounded-full inline-block" />
                <span>Safe Evacuation Route</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
                <span>Evacuee Origin</span>
              </div>
            </div>

            {/* Interactive SVG Network Graph */}
            <svg
              ref={canvasRef}
              id="network-canvas-bg"
              className="w-full h-full cursor-grab active:cursor-grabbing select-none"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onWheel={handleWheel}
              onClick={handleSvgBackgroundClick}
            >
              <defs>
                {/* Glow Filter for Evacuation Corridor */}
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3.5" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>

                {/* Blue Glow for NGO Route */}
                <filter id="blue-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="2.5" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>

                {/* River Basin Gradient */}
                <linearGradient id="riverGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#1e3a8a" stopOpacity="0.25" />
                  <stop offset="50%" stopColor="#0284c7" stopOpacity="0.18" />
                  <stop offset="100%" stopColor="#0f766e" stopOpacity="0.22" />
                </linearGradient>

                {/* Subtle Grid Pattern */}
                <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#334155" strokeWidth="0.5" strokeOpacity="0.3" />
                </pattern>
              </defs>

              {/* Background Grid */}
              <rect width="100%" height="100%" fill="url(#gridPattern)" />

              {/* Transformed Canvas Container for Pan & Zoom */}
              <g transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomLevel})`}>
                {/* River Basin Highlight Area */}
                {showRiverBasin && (
                  <path
                    d="M 120 180 Q 320 280 520 340 T 920 480 L 880 580 Q 500 450 300 380 T 90 280 Z"
                    fill="url(#riverGradient)"
                    className="pointer-events-none"
                  />
                )}

                {/* Flood Inundation Zones (semi-transparent circles that expand with rainfall) */}
                {showFloodCircles &&
                  cityData.locations
                    .filter((loc) => loc.elevation_m <= 562.0)
                    .map((loc) => {
                      const pos = nodeSvgCoords.get(loc.id);
                      if (!pos) return null;
                      const radius = Math.min(
                        75,
                        Math.max(22, (rainfallRate * 0.45) + (565.0 - loc.elevation_m) * 3.5)
                      );
                      return (
                        <g key={`flood-zone-${loc.id}`}>
                          <circle
                            cx={pos.x}
                            cy={pos.y}
                            r={radius}
                            fill="#3b82f6"
                            fillOpacity={0.16}
                            stroke="#ef4444"
                            strokeWidth="1.2"
                            strokeDasharray="4 3"
                            className="pointer-events-none"
                          />
                        </g>
                      );
                    })}

                {/* Draw Roads (Edges) */}
                {cityData.roads.map((road) => {
                  const uPos = nodeSvgCoords.get(road.from);
                  const vPos = nodeSvgCoords.get(road.to);
                  if (!uPos || !vPos) return null;

                  const state = roadWaterDepths[road.id] || { depth: 0, isBlocked: false, isRisky: false };
                  let strokeColor = theme === 'dark' ? '#475569' : '#94a3b8';
                  let strokeWidth = 3;
                  let strokeDasharray = undefined;

                  if (state.isBlocked) {
                    strokeColor = '#ef4444';
                    strokeWidth = 4;
                    strokeDasharray = '6 5';
                  } else if (state.isRisky) {
                    strokeColor = '#f59e0b';
                    strokeWidth = 3.5;
                  }

                  // Check if this road was relaxed during Dijkstra step replay
                  const isRelaxedInStep = currentReplayStepData?.relaxedNeighbors.some(
                    (n) =>
                      (currentReplayStepData.currentNode === road.from && n.neighbor === road.to) ||
                      (currentReplayStepData.currentNode === road.to && n.neighbor === road.from)
                  );

                  if (isRelaxedInStep) {
                    strokeColor = '#38bdf8';
                    strokeWidth = 5;
                  }

                  const isHovered = hoveredRoadId === road.id;

                  return (
                    <g key={road.id} className="cursor-pointer">
                      <line
                        x1={uPos.x}
                        y1={uPos.y}
                        x2={vPos.x}
                        y2={vPos.y}
                        stroke={strokeColor}
                        strokeWidth={isHovered ? strokeWidth + 2 : strokeWidth}
                        strokeDasharray={strokeDasharray}
                        strokeLinecap="round"
                        onMouseEnter={() => setHoveredRoadId(road.id)}
                        onMouseLeave={() => setHoveredRoadId(null)}
                      />
                      {/* Hover text label */}
                      {isHovered && (
                        <g
                          transform={`translate(${(uPos.x + vPos.x) / 2}, ${(uPos.y + vPos.y) / 2 - 10})`}
                          className="pointer-events-none"
                        >
                          <rect
                            x="-65"
                            y="-14"
                            width="130"
                            height="24"
                            rx="4"
                            fill="#0f172a"
                            stroke="#475569"
                            strokeWidth="1"
                          />
                          <text
                            x="0"
                            y="2"
                            textAnchor="middle"
                            fill="#f8fafc"
                            fontSize="10"
                            fontWeight="bold"
                            fontFamily="sans-serif"
                          >
                            {road.name} ({state.depth}m)
                          </text>
                        </g>
                      )}
                    </g>
                  );
                })}

                {/* Ghost Route (faded for 3 seconds when re-planned) */}
                {ghostRouteNodeIds.length > 1 && (
                  <g className="ghost-route-faded pointer-events-none">
                    {ghostRouteNodeIds.slice(0, -1).map((id, idx) => {
                      const u = nodeSvgCoords.get(id);
                      const v = nodeSvgCoords.get(ghostRouteNodeIds[idx + 1]);
                      if (!u || !v) return null;
                      return (
                        <line
                          key={`ghost-${idx}`}
                          x1={u.x}
                          y1={u.y}
                          x2={v.x}
                          y2={v.y}
                          stroke="#10b981"
                          strokeWidth="5"
                          strokeLinecap="round"
                          opacity="0.3"
                        />
                      );
                    })}
                  </g>
                )}

                {/* Active Recommended Evacuation Route (Flowing Animated Glowing Polyline) */}
                {!analysisResults.isStranded && analysisResults.activePath.length > 1 && (
                  <g className="pointer-events-none" filter="url(#glow)">
                    {analysisResults.activePath.slice(0, -1).map((id, idx) => {
                      const u = nodeSvgCoords.get(id);
                      const v = nodeSvgCoords.get(analysisResults.activePath[idx + 1]);
                      if (!u || !v) return null;
                      return (
                        <line
                          key={`route-${idx}`}
                          x1={u.x}
                          y1={u.y}
                          x2={v.x}
                          y2={v.y}
                          stroke="#10b981"
                          strokeWidth="6"
                          strokeLinecap="round"
                          className="route-flow-animation"
                        />
                      );
                    })}
                  </g>
                )}

                {/* Focused NGO Rescue Mission Route (Blue Line) */}
                {focusedRescueRouteNodes.length > 1 && (
                  <g className="pointer-events-none" filter="url(#blue-glow)">
                    {focusedRescueRouteNodes.slice(0, -1).map((id, idx) => {
                      const u = nodeSvgCoords.get(id);
                      const v = nodeSvgCoords.get(focusedRescueRouteNodes[idx + 1]);
                      if (!u || !v) return null;
                      return (
                        <line
                          key={`ngo-route-${idx}`}
                          x1={u.x}
                          y1={u.y}
                          x2={v.x}
                          y2={v.y}
                          stroke="#3b82f6"
                          strokeWidth="5"
                          strokeDasharray="8 6"
                          strokeLinecap="round"
                        />
                      );
                    })}
                  </g>
                )}

                {/* Nodes / Intersections */}
                {cityData.locations.map((loc) => {
                  const pos = nodeSvgCoords.get(loc.id);
                  if (!pos) return null;

                  const isSafeZone = loc.is_safe_zone;
                  const isStranded = analysisResults.strandedAnalysis?.strandedNodes.includes(loc.id);
                  const isNgoBase = cityData.ngo_bases.some((ngo) => ngo.node === loc.id);
                  const isUserOrigin = loc.id === userOriginNode;
                  const isSelected = loc.id === selectedNodeId;
                  const isCurrentReplay = currentReplayStepData?.currentNode === loc.id;

                  if (!showAllNodes && !isSafeZone && !isStranded && !isNgoBase && !isUserOrigin) {
                    return null;
                  }

                  return (
                    <g
                      key={loc.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      className="cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNodeId(loc.id);
                      }}
                      onDoubleClick={(e) => {
                        e.stopPropagation();
                        setUserOriginNode(loc.id);
                        setSelectedNodeId(loc.id);
                        setUserCoords({ lat: loc.lat, lng: loc.lng });
                      }}
                    >
                      {/* Pulsing ring for replay, stranded, or critical */}
                      {(isStranded || isCurrentReplay || (showCriticalNodes && loc.population > 500)) && (
                        <circle
                          r={isCurrentReplay ? '20' : '17'}
                          fill="none"
                          stroke={isCurrentReplay ? '#38bdf8' : (showCriticalNodes && loc.population > 500 ? '#f59e0b' : '#ef4444')}
                          strokeWidth="2.5"
                          opacity="0.8"
                          className={isStranded || (showCriticalNodes && loc.population > 500) ? 'animate-ping' : ''}
                        />
                      )}

                      {/* Safe Zone Marker */}
                      {isSafeZone ? (
                        <g>
                          <rect
                            x="-14"
                            y="-14"
                            width="28"
                            height="28"
                            rx="7"
                            fill="#10b981"
                            stroke="#ffffff"
                            strokeWidth="2"
                          />
                          <path
                            d="M -4 2 L -1 6 L 5 -3"
                            fill="none"
                            stroke="#ffffff"
                            strokeWidth="2.2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                          {/* Label Badge */}
                          <text
                            x="0"
                            y="24"
                            textAnchor="middle"
                            fill="#10b981"
                            fontSize="9"
                            fontWeight="bold"
                          >
                            Shelter
                          </text>
                        </g>
                      ) : isNgoBase ? (
                        /* NGO Base Marker */
                        <g>
                          <rect
                            x="-13"
                            y="-13"
                            width="26"
                            height="26"
                            rx="6"
                            fill="#3b82f6"
                            stroke="#ffffff"
                            strokeWidth="2"
                          />
                          <circle cx="0" cy="0" r="4" fill="#ffffff" />
                          <text
                            x="0"
                            y="23"
                            textAnchor="middle"
                            fill="#60a5fa"
                            fontSize="9"
                            fontWeight="bold"
                          >
                            NGO
                          </text>
                        </g>
                      ) : isStranded ? (
                        /* Stranded Warning Node Marker */
                        <g>
                          <circle
                            r="12"
                            fill="#ef4444"
                            stroke="#ffffff"
                            strokeWidth="2.2"
                          />
                          <text
                            x="0"
                            y="4"
                            textAnchor="middle"
                            fill="#ffffff"
                            fontSize="11"
                            fontWeight="bold"
                          >
                            !
                          </text>
                        </g>
                      ) : (
                        /* Standard Intersection Node */
                        <g>
                          <circle
                            r={isSelected ? '11' : '8.5'}
                            fill={isSelected ? '#3b82f6' : '#1e293b'}
                            stroke={isSelected ? '#ffffff' : '#64748b'}
                            strokeWidth={isSelected ? '2' : '1.5'}
                          />
                          <text
                            x="0"
                            y="3"
                            textAnchor="middle"
                            fill="#f8fafc"
                            fontSize="7.5"
                            fontWeight="bold"
                          >
                            {loc.id.replace('LOC_', '')}
                          </text>
                        </g>
                      )}

                      {/* Evacuee Origin Marker Halo */}
                      {isUserOrigin && (
                        <g>
                          <circle
                            r="18"
                            fill="none"
                            stroke="#3b82f6"
                            strokeWidth="2.5"
                            strokeDasharray="3 3"
                            className="animate-spin"
                            style={{ animationDuration: '8s' }}
                          />
                          <circle r="4.5" fill="#3b82f6" stroke="#ffffff" strokeWidth="1.5" />
                        </g>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>

            {/* Node Inspector Floating Modal */}
            {selectedNodeData && (
              <div className="absolute top-16 right-4 z-20 w-72 bg-slate-900/95 backdrop-blur-md p-3.5 rounded-2xl border border-slate-700 shadow-2xl space-y-2.5">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                      {selectedNodeData.id}
                    </span>
                    <h3 className="font-bold text-sm text-white mt-1">{selectedNodeData.name}</h3>
                  </div>
                  <button
                    onClick={() => setSelectedNodeId(null)}
                    className="text-slate-400 hover:text-white text-xs px-1.5 py-0.5 rounded bg-slate-800"
                  >
                    ✕
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-1.5 text-[11px] bg-slate-800/60 p-2 rounded-xl border border-slate-700">
                  <div>
                    Elevation: <span className="font-semibold text-white">{selectedNodeData.elevation_m}m</span>
                  </div>
                  <div>
                    Population: <span className="font-semibold text-white">{selectedNodeData.population.toLocaleString()}</span>
                  </div>
                  {selectedNodeData.capacity && (
                    <div className="col-span-2">
                      Shelter Capacity: <span className="font-semibold text-emerald-400">{selectedNodeData.capacity} evacuees</span>
                    </div>
                  )}
                  <div className="col-span-2">
                    Terrain: <span className="font-semibold text-cyan-300">{selectedNodeData.type}</span>
                  </div>
                </div>

                {analysisResults.strandedAnalysis?.strandedNodes.includes(selectedNodeData.id) && (
                  <div className="p-2 rounded-lg bg-red-950/80 border border-red-600 text-red-200 text-[11px] font-bold">
                    ⚠️ CUT OFF / STRANDED: Road access to municipal shelters submerged!
                  </div>
                )}

                {selectedNodeData.is_safe_zone && (
                  <div className="p-2 rounded-lg bg-emerald-950/80 border border-emerald-600 text-emerald-200 text-[11px]">
                    🛡️ Designated Safe Municipal Shelter
                  </div>
                )}

                <button
                  onClick={() => {
                    setUserOriginNode(selectedNodeData.id);
                    setUserCoords({ lat: selectedNodeData.lat, lng: selectedNodeData.lng });
                  }}
                  className="w-full py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors shadow"
                >
                  <Crosshair className="w-3.5 h-3.5" /> Set As Evacuee Origin
                </button>
              </div>
            )}
          </div>
        )}
      </div>



      {/* Floating Bottom Tab Drawers / Modals */}
      {activeTab === 'tracker' && (
        <div className="absolute bottom-4 right-4 left-4 lg:left-96 max-h-80 z-30 bg-slate-900/95 backdrop-blur-md border border-slate-800 rounded-2xl p-4 shadow-2xl flex flex-col gap-3 overflow-y-auto">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-bold text-white">
                Dijkstra Execution Trace (Custom MinHeap Operations)
              </h3>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  setReplayCurrentStep(0);
                  setIsReplaying(true);
                }}
                className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1"
              >
                {isReplaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                {isReplaying ? 'Pause Trace' : 'Animate Replay'}
              </button>
              <button
                onClick={() => setActiveTab('planner')}
                className="text-xs text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-800/60 text-slate-400 text-[11px] uppercase">
                <tr>
                  <th className="p-2">Step</th>
                  <th className="p-2">Popped Vertex (MinHeap)</th>
                  <th className="p-2">Distance (km)</th>
                  <th className="p-2">Relaxed Neighbors</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                {analysisResults.dijkstraMetric?.executionTrace.map((step) => {
                  const isCurrent = isReplaying && step.step === replayCurrentStep;
                  return (
                    <tr
                      key={step.step}
                      className={isCurrent ? 'bg-blue-600/30 text-white font-bold' : 'hover:bg-slate-800/40'}
                    >
                      <td className="p-2 text-slate-500">#{step.step}</td>
                      <td className="p-2 text-cyan-300">{step.currentNode}</td>
                      <td className="p-2 text-slate-200">{step.currentDist.toFixed(2)}</td>
                      <td className="p-2 text-slate-400">
                        {step.relaxedNeighbors.length > 0
                          ? step.relaxedNeighbors.map((n) => `${n.neighbor} (${n.newDist}km)`).join(', ')
                          : 'No relaxations'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'dsa_docs' && (
        <div className="absolute bottom-4 right-4 left-4 lg:left-96 max-h-96 z-30 bg-slate-900/95 backdrop-blur-md border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col gap-4 overflow-y-auto">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white">
                Data Structures & Algorithms Implementation Architecture
              </h3>
            </div>
            <button onClick={() => setActiveTab('planner')} className="text-xs text-slate-400 hover:text-white">
              Close
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="font-bold text-white">1. Adjacency List Graph (`graph.ts`)</div>
              <p className="text-slate-400 text-[11px]">
                Maintains vertices and incident edge arrays. Supports dynamic edge blocking (`isBlocked`) and penalty weights (`isRisky`, multiplier 2.5x).
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="font-bold text-white">2. Binary Min-Heap (`minHeap.ts`)</div>
              <p className="text-slate-400 text-[11px]">
                0-indexed array with `siftUp` and `siftDown`. Used in Dijkstra for O(log V) priority vertex extraction and priority NGO dispatch.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="font-bold text-white">3. Linked Queue (`queue.ts`) & BFS (`bfs.ts`)</div>
              <p className="text-slate-400 text-[11px]">
                True O(1) doubly-linked queue used to explore reachability frontiers and find paths with the minimum number of intersections.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="font-bold text-white">4. Linked Stack (`stack.ts`) & DFS (`dfs.ts`)</div>
              <p className="text-slate-400 text-[11px]">
                Iterative stack-based DFS and recursive DFS to compute connected components (`components.ts`) and isolate stranded flood zones.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="font-bold text-white">5. Spherical Haversine (`haversine.ts`)</div>
              <p className="text-slate-400 text-[11px]">
                Great-circle formula (R = 6371km) for exact geodesic edge distances and GPS user position snapping without external libraries.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
              <div className="font-bold text-white">6. Priority Rescue Dispatcher (`priorityDispatch.ts`)</div>
              <p className="text-slate-400 text-[11px]">
                Pushes stranded zones into MinHeap with priority = -(risk_score * population). Runs Dijkstra from each NGO base to assign the nearest responder unit.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
