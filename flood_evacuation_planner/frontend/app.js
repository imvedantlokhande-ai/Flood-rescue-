/**
 * Flood Evacuation Ops - Real-Time Emergency Operations Controller
 * Full-Screen Google Maps JavaScript API Visualizer with Pure Python DSA Engine
 *
 * Strict Compliance:
 * - All routing, reachability, and prioritization run on custom Python DSA backend.
 * - Google Maps JavaScript API is used strictly for client-side rendering.
 * - Live Server-Sent Events (SSE /api/stream) continuous telemetry stream.
 * - Autonomous re-planning on road inundation and user movement (watchPosition).
 * - Full audio/visual emergency dispatch alerts, sparklines, and Dijkstra replays.
 */

// Global Application State
let map = null;
let googleMapsLoaded = false;
let trafficLayer = null;
let infoWindow = null;
let graphData = null;
let currentResult = null;
let sseConnection = null;

// Map Overlays
let roadPolylines = []; // Array of { road, polyline }
let floodCircles = []; // Array of google.maps.Circle
let routePolyline = null; // Current evacuation route
let routeArrowAnimationInterval = null;
let ghostRoutePolyline = null;
let ngoRoutePolylines = {}; // req_id -> google.maps.Polyline
let shelterMarkers = {}; // id -> google.maps.Marker
let ngoMarkers = {}; // id -> google.maps.Marker
let strandedMarkers = {}; // id -> google.maps.Marker
let allNodeMarkers = []; // Array of google.maps.Marker
let bfsReachMarkers = []; // Array of google.maps.Circle / Marker
let dijkstraReplayMarkers = []; // Array of google.maps.Marker

// User Position
let userMarker = null;
let userAccuracyCircle = null;
let currentUserNode = "NODE_001";
let currentUserName = "Old Sangvi Riverfront Bridge";
let currentUserCoords = { lat: 18.5772, lng: 73.8185 };
let geolocationWatchId = null;

// Telemetry & UI State
let currentTheme = 'dark';
let soundEnabled = true;
let isReplayingDijkstra = false;
let replaySpeedMs = 180;
let lastRiskLevel = null;
let lastTelemetryTimestamp = Date.now();
let secondsSinceLastUpdate = 0;
let isSimulatingSurge = false;
let simInterval = null;
let currentActiveStepIdx = 0;

// Google Maps Custom Vector Styles
const darkMapStyle = [
  { elementType: 'geometry', stylers: [{ color: '#090d16' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#090d16' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#94a3b8' }] },
  { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#cbd5e1' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#172033' }] },
  { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#0f172a' }] },
  { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#64748b' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#25334d' }] },
  { featureType: 'road.highway', elementType: 'geometry.stroke', stylers: [{ color: '#172033' }] },
  { featureType: 'transit', stylers: [{ visibility: 'simplified' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0a192f' }] },
  { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#38bdf8' }] }
];

const lightMapStyle = [
  { elementType: 'geometry', stylers: [{ color: '#f8fafc' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#334155' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#cbd5e1' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#94a3b8' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#bae6fd' }] }
];

// Bootstrap on DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  setupUIEventListeners();
  initLiveTicker();
  await loadGraphData();
  initGoogleMapsLoader();
  initGeolocationTracking();
  initSSEStream();
  initSheetTouchDrag();
});

// ==========================================
// 1. THEME & LIVE TICKER
// ==========================================
function initTheme() {
  const saved = localStorage.getItem('flood_ops_theme');
  if (saved) {
    setTheme(saved);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    setTheme('light');
  } else {
    setTheme('dark');
  }
}

function setTheme(theme) {
  currentTheme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('flood_ops_theme', theme);

  const sun = document.getElementById('theme-icon-sun');
  const moon = document.getElementById('theme-icon-moon');
  if (sun && moon) {
    if (theme === 'dark') {
      sun.classList.remove('hidden');
      moon.classList.add('hidden');
    } else {
      sun.classList.add('hidden');
      moon.classList.remove('hidden');
    }
  }

  if (map && map.setOptions) {
    map.setOptions({ styles: theme === 'dark' ? darkMapStyle : lightMapStyle });
  }
}

function initLiveTicker() {
  setInterval(() => {
    secondsSinceLastUpdate = Math.max(1, Math.floor((Date.now() - lastTelemetryTimestamp) / 1000));
    const timerEl = document.getElementById('live-timer-counter');
    if (timerEl) {
      timerEl.textContent = `Updated ${secondsSinceLastUpdate}s ago`;
    }
  }, 1000);
}

// ==========================================
// 2. AUDIO CHIMES & BROWSER NOTIFICATIONS
// ==========================================
function playEmergencyChime(severity = 'warning') {
  if (!soundEnabled) return;
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);
    const now = ctx.currentTime;

    if (severity === 'critical') {
      // 3-tone urgent alert chime
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(440, now); // A4
      osc.frequency.setValueAtTime(659, now + 0.12); // E5
      osc.frequency.setValueAtTime(880, now + 0.24); // A5
      gain.gain.setValueAtTime(0.28, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.55);
      osc.start(now);
      osc.stop(now + 0.55);
    } else {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(523.25, now);
      osc.frequency.setValueAtTime(659.25, now + 0.1);
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.start(now);
      osc.stop(now + 0.35);
    }
  } catch (e) {
    console.debug('Audio chime notice:', e);
  }
}

function fireNotification(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    try {
      new Notification(title, { body: body, icon: '/favicon.ico' });
    } catch (e) {
      console.debug('Notification err:', e);
    }
  }
}

// ==========================================
// 3. GRAPH NETWORK INGESTION
// ==========================================
async function loadGraphData() {
  try {
    const res = await fetch('/api/graph');
    if (!res.ok) throw new Error('Municipal network graph not found');
    graphData = await res.json();
  } catch (e) {
    showToast('Failed to load municipal graph: ' + e.message, 'error');
  }
}

// ==========================================
// 4. GOOGLE MAPS LOADER & VECTOR RENDERING
// ==========================================
function initGoogleMapsLoader() {
  const envKey = (window.GOOGLE_MAPS_API_KEY || '').trim();
  const savedKey = localStorage.getItem('google_maps_key') || '';
  const keyToUse = envKey && !envKey.includes('__GOOGLE') ? envKey : savedKey;

  if (!keyToUse) {
    // Show Missing Key Modal
    const modal = document.getElementById('api-key-modal');
    if (modal) modal.classList.remove('hidden');
    renderLocalCanvasFallback();
    return;
  }

  loadGoogleMapsScript(keyToUse);
}

function loadGoogleMapsScript(apiKey) {
  if (window.google && window.google.maps) {
    onGoogleMapsReady();
    return;
  }

  const script = document.createElement('script');
  script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=onGoogleMapsReady&libraries=geometry`;
  script.async = true;
  script.defer = true;
  script.onerror = () => {
    document.getElementById('api-key-modal')?.classList.remove('hidden');
    renderLocalCanvasFallback();
  };
  window.onGoogleMapsReady = onGoogleMapsReady;
  document.head.appendChild(script);
}

function onGoogleMapsReady() {
  googleMapsLoaded = true;
  const center = graphData?.center_coordinates || { lat: 18.6274, lng: 73.8016 };

  map = new google.maps.Map(document.getElementById('map'), {
    center: center,
    zoom: 13,
    styles: currentTheme === 'dark' ? darkMapStyle : lightMapStyle,
    disableDefaultUI: false,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
    tilt: 0,
    gestureHandling: 'greedy',
  });

  infoWindow = new google.maps.InfoWindow();

  // Traffic Layer instance
  trafficLayer = new google.maps.TrafficLayer();

  // Click on map snaps user location and re-runs pure-DSA evacuation pipeline
  map.addListener('click', async (e) => {
    const lat = e.latLng.lat();
    const lng = e.latLng.lng();
    await snapUserCoordinate(lat, lng);
  });

  renderGraphRoads();
  renderCandidateShelters();
  renderNGOResponseBases();

  // Check URL focused route parameter
  checkUrlRouteFocus();
}

function renderLocalCanvasFallback() {
  const mapEl = document.getElementById('map');
  if (mapEl && !googleMapsLoaded) {
    mapEl.innerHTML = `
      <div style="height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#080c14; color:#94a3b8; text-align:center; padding:32px;">
        <div style="width:60px; height:60px; border-radius:50%; background:rgba(59,130,246,0.15); display:flex; align-items:center; justify-content:center; margin-bottom:16px;">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="12 8 8 12 12 16 12 8"/><polygon points="12 8 16 12 12 16 12 8"/></svg>
        </div>
        <h3 style="color:#f8fafc; font-size:18px; font-weight:800; margin-bottom:8px;">Live Telemetry Visualizer Active</h3>
        <p style="font-size:13px; max-width:480px; line-height:1.5; color:#94a3b8;">
          All pure Python DSA modules (MinHeap priority queue, Dijkstra shortest safe path, BFS/DFS reachability)
          and real-time Open-Meteo weather streams are actively calculating routes in the background.
        </p>
        <button id="btn-reopen-modal" style="margin-top:16px;" class="btn btn-primary btn-sm" onclick="document.getElementById('api-key-modal').classList.remove('hidden')">
          Enter Google Maps Key
        </button>
      </div>
    `;
  }
}

// ==========================================
// 5. VECTOR DRAWING: ROADS, FLOOD OVERLAYS, ROUTES
// ==========================================
function renderGraphRoads() {
  if (!map || !graphData || !graphData.roads) return;

  const locById = {};
  graphData.locations.forEach(l => { locById[l.id] = l; });

  // Clear existing
  roadPolylines.forEach(r => r.polyline.setMap(null));
  roadPolylines = [];

  graphData.roads.forEach(road => {
    const u = locById[road.from];
    const v = locById[road.to];
    if (!u || !v) return;

    const path = [
      { lat: u.lat, lng: u.lng },
      { lat: v.lat, lng: v.lng }
    ];

    const polyline = new google.maps.Polyline({
      path: path,
      geodesic: true,
      strokeColor: '#94a3b8',
      strokeOpacity: 0.75,
      strokeWeight: 3.5,
      map: map,
    });

    polyline.addListener('click', (e) => {
      const water = currentResult?.water_levels?.[road.id] || 0.0;
      const isBlocked = water >= 0.5;
      const isRisky = water >= 0.2 && !isBlocked;

      infoWindow.setContent(`
        <div class="info-window-card">
          <h4>${road.name}</h4>
          <p><strong>Code:</strong> ${road.id} (${road.from} ➔ ${road.to})</p>
          <p><strong>Distance:</strong> ${road.distance_km} km</p>
          <p><strong>Water Inundation:</strong> ${(water * 100).toFixed(0)} cm</p>
          <p><strong>Status:</strong> <span style="font-weight:700; color:${isBlocked ? '#ef4444' : isRisky ? '#f97316' : '#10b981'};">${isBlocked ? 'SUBMERGED (BLOCKED)' : isRisky ? 'RISKY / CAUTION' : 'PASSABLE'}</span></p>
        </div>
      `);
      infoWindow.setPosition(e.latLng);
      infoWindow.open(map);
    });

    roadPolylines.push({ road: road, polyline: polyline });
  });
}

function updateRoadColors(waterLevels = {}, blockedRoads = []) {
  if (!roadPolylines.length) return;

  const lineSymbol = {
    path: 'M 0,-1 0,1',
    strokeOpacity: 1,
    scale: 3,
  };

  roadPolylines.forEach(({ road, polyline }) => {
    const isBlocked = blockedRoads.includes(road.id);
    const depth = waterLevels[road.id] || 0.0;
    const isRisky = depth >= 0.2 && !isBlocked;

    if (isBlocked) {
      polyline.setOptions({
        strokeColor: '#ef4444',
        strokeOpacity: 0.0,
        strokeWeight: 4.5,
        icons: [{
          icon: lineSymbol,
          offset: '0',
          repeat: '16px',
        }],
      });
    } else if (isRisky) {
      polyline.setOptions({
        strokeColor: '#f97316',
        strokeOpacity: 0.88,
        strokeWeight: 4.2,
        icons: [],
      });
    } else {
      polyline.setOptions({
        strokeColor: '#94a3b8',
        strokeOpacity: 0.72,
        strokeWeight: 3.2,
        icons: [],
      });
    }
  });
}

function updateFloodOverlays(rainfallRate, riverDischarge) {
  if (!map || !graphData) return;

  floodCircles.forEach(c => c.setMap(null));
  floodCircles = [];

  if (rainfallRate < 15.0) return;

  const lowlands = graphData.locations.filter(l => l.elevation_m < 558.0 || l.type === 'riverfront_lowland');
  const baseRadius = 240;
  const growth = Math.min(3.2, 1.0 + (rainfallRate / 35.0) + (riverDischarge / 70.0));
  const radius = baseRadius * growth;
  const opacity = Math.min(0.38, 0.12 + (rainfallRate / 260.0));

  lowlands.forEach(loc => {
    const circle = new google.maps.Circle({
      strokeColor: '#ef4444',
      strokeOpacity: 0.8,
      strokeWeight: 1.5,
      fillColor: '#ef4444',
      fillOpacity: opacity,
      map: map,
      center: { lat: loc.lat, lng: loc.lng },
      radius: radius,
      clickable: false,
    });
    floodCircles.push(circle);
  });
}

function renderEvacuationRoute(routeData) {
  if (!map) return;

  // Handle ghost of previous route for 3 seconds
  if (routePolyline) {
    const oldPath = routePolyline.getPath();
    if (oldPath && oldPath.getLength() > 1) {
      if (ghostRoutePolyline) ghostRoutePolyline.setMap(null);
      ghostRoutePolyline = new google.maps.Polyline({
        path: oldPath,
        geodesic: true,
        strokeColor: '#10b981',
        strokeOpacity: 0.22,
        strokeWeight: 7,
        map: map,
      });

      setTimeout(() => {
        if (ghostRoutePolyline) {
          ghostRoutePolyline.setMap(null);
          ghostRoutePolyline = null;
        }
      }, 3000);
    }
    routePolyline.setMap(null);
    routePolyline = null;
    clearInterval(routeArrowAnimationInterval);
  }

  if (!routeData || !routeData.route_found || routeData.is_stranded) {
    document.getElementById('card-route-section')?.classList.add('hidden');
    document.getElementById('banner-emergency-alert')?.classList.remove('hidden');
    return;
  }

  document.getElementById('card-route-section')?.classList.remove('hidden');
  document.getElementById('banner-emergency-alert')?.classList.add('hidden');

  const coords = (routeData.route_coords || []).map(c => ({ lat: c.lat, lng: c.lng }));
  if (coords.length < 2) return;

  // Polyline with animated flowing directional chevron arrows
  const arrowSymbol = {
    path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
    scale: 3,
    strokeColor: '#ffffff',
    fillColor: '#10b981',
    fillOpacity: 1,
  };

  routePolyline = new google.maps.Polyline({
    path: coords,
    geodesic: true,
    strokeColor: '#10b981',
    strokeOpacity: 0.95,
    strokeWeight: 7.5,
    icons: [{
      icon: arrowSymbol,
      offset: '0%',
      repeat: '60px',
    }],
    map: map,
  });

  // Animated flowing arrows loop
  let arrowOffset = 0;
  routeArrowAnimationInterval = setInterval(() => {
    arrowOffset = (arrowOffset + 2) % 100;
    const icons = routePolyline.get('icons');
    if (icons && icons[0]) {
      icons[0].offset = `${arrowOffset}%`;
      routePolyline.set('icons', icons);
    }
  }, 75);

  // Auto-fit bounds with padding
  const bounds = new google.maps.LatLngBounds();
  coords.forEach(pt => bounds.extend(pt));
  map.fitBounds(bounds, 70);
}

// Safe Shelters (Green Shield)
function renderCandidateShelters() {
  if (!map || !graphData) return;

  graphData.locations.filter(l => l.is_safe_zone).forEach(shelter => {
    const marker = new google.maps.Marker({
      position: { lat: shelter.lat, lng: shelter.lng },
      map: map,
      title: shelter.name,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 12,
        fillColor: '#10b981',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2.5,
      },
    });

    marker.addListener('click', () => {
      infoWindow.setContent(`
        <div class="info-window-card">
          <h4 style="color:#10b981;">🛡️ Safe Shelter: ${shelter.name}</h4>
          <p>Elevated Ground: ${shelter.elevation_m}m</p>
          <p>Capacity: ${(shelter.capacity || 3500).toLocaleString()} Evacuees</p>
          <p>Status: <span style="color:#10b981; font-weight:700;">OPEN / SECURE</span></p>
        </div>
      `);
      infoWindow.open(map, marker);
    });

    shelterMarkers[shelter.id] = marker;
  });
}

// NGO Response Bases (Blue Cross/Truck)
function renderNGOResponseBases() {
  if (!map || !graphData || !graphData.ngo_bases) return;

  const locById = {};
  graphData.locations.forEach(l => { locById[l.id] = l; });

  graphData.ngo_bases.forEach(ngo => {
    const loc = locById[ngo.node];
    if (!loc) return;

    const marker = new google.maps.Marker({
      position: { lat: loc.lat, lng: loc.lng },
      map: map,
      title: ngo.name,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 11,
        fillColor: '#2563eb',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2.5,
      },
    });

    marker.addListener('click', () => {
      infoWindow.setContent(`
        <div class="info-window-card">
          <h4 style="color:#3b82f6;">🚑 ${ngo.name}</h4>
          <p><strong>Base Sector:</strong> ${loc.name}</p>
          <p><strong>Hotline:</strong> ${ngo.contact}</p>
          <p><strong>Zodiac / Fleet Capacity:</strong> ${ngo.vehicle_capacity} units</p>
        </div>
      `);
      infoWindow.open(map, marker);
    });

    ngoMarkers[ngo.id] = marker;
  });
}

// ==========================================
// 6. LIVE GEOLOCATION & AUTO-SNAPPING (watchPosition)
// ==========================================
function initGeolocationTracking() {
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        await handlePositionChange(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy);
      },
      (err) => {
        console.warn('Geolocation permission not granted; using municipal hub:', err.message);
        snapUserCoordinate(currentUserCoords.lat, currentUserCoords.lng);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );

    geolocationWatchId = navigator.geolocation.watchPosition(
      async (pos) => {
        const dLat = Math.abs(pos.coords.latitude - currentUserCoords.lat);
        const dLng = Math.abs(pos.coords.longitude - currentUserCoords.lng);
        // Only re-snap if user moves > 20 meters
        if (dLat > 0.0002 || dLng > 0.0002) {
          await handlePositionChange(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy);
        }
      },
      (err) => console.debug('WatchPosition notice:', err),
      { enableHighAccuracy: true, maximumAge: 10000 }
    );
  } else {
    snapUserCoordinate(currentUserCoords.lat, currentUserCoords.lng);
  }
}

async function handlePositionChange(lat, lng, accuracy = 40) {
  currentUserCoords = { lat, lng };
  updateUserDotOnMap(lat, lng, accuracy);
  await snapUserCoordinate(lat, lng);
}

function updateUserDotOnMap(lat, lng, accuracy = 40) {
  if (!map) return;

  const pos = { lat, lng };

  if (!userMarker) {
    userMarker = new google.maps.Marker({
      position: pos,
      map: map,
      title: 'Your Location (GPS)',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 9,
        fillColor: '#3b82f6',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 3,
      },
      zIndex: 9999,
    });
  } else {
    userMarker.setPosition(pos);
  }

  if (!userAccuracyCircle) {
    userAccuracyCircle = new google.maps.Circle({
      strokeColor: '#3b82f6',
      strokeOpacity: 0.6,
      strokeWeight: 1,
      fillColor: '#3b82f6',
      fillOpacity: 0.12,
      map: map,
      center: pos,
      radius: Math.max(accuracy, 40),
    });
  } else {
    userAccuracyCircle.setCenter(pos);
    userAccuracyCircle.setRadius(Math.max(accuracy, 40));
  }
}

async function snapUserCoordinate(lat, lng) {
  try {
    const res = await fetch('/api/snap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng }),
    });
    if (!res.ok) throw new Error('Snap API error');
    const data = await res.json();

    currentUserNode = data.nearest_node;
    currentUserName = data.nearest_name;
    currentUserCoords = { lat, lng };

    document.getElementById('val-user-pos').textContent = `${data.nearest_name} (${data.nearest_node})`;
    showToast(`Snapped to road intersection: ${data.nearest_name}`, 'info');

    // Trigger instant evaluation
    await triggerEvacuateCalculation();
  } catch (e) {
    console.error('Snap coordinate error:', e);
  }
}

// ==========================================
// 7. REAL-TIME SSE TELEMETRY STREAM (/api/stream)
// ==========================================
function initSSEStream() {
  if (sseConnection) sseConnection.close();

  sseConnection = new EventSource('/api/stream');

  sseConnection.onopen = () => {
    document.getElementById('live-dot')?.classList.remove('offline');
  };

  sseConnection.onmessage = (event) => {
    try {
      const state = JSON.parse(event.data);
      applyTelemetryUpdate(state);
    } catch (e) {
      console.error('SSE JSON error:', e);
    }
  };

  sseConnection.onerror = () => {
    document.getElementById('live-dot')?.classList.add('offline');
  };
}

function applyTelemetryUpdate(state) {
  lastTelemetryTimestamp = Date.now();
  secondsSinceLastUpdate = 0;

  // 1. Update Hero Status Card
  const risk = state.risk_level || 'LOW';
  const score = state.risk_score || 20;
  const rain = state.weather?.rainfall_mm_per_hr || 0;
  const discharge = state.weather?.river_discharge_m3s || 35.0;

  document.getElementById('val-rainfall-rate').textContent = rain.toFixed(1);
  document.getElementById('text-river-discharge').textContent = `River: ${discharge.toFixed(1)} m³/s`;
  document.getElementById('text-threat-desc').textContent = state.risk_description || '';

  const badgeWrapper = document.getElementById('card-hero-status');
  badgeWrapper.className = `card card-hero threat-${risk.toLowerCase()}`;

  const threatText = document.getElementById('text-threat-level');
  threatText.textContent = `${risk} RISK (${score}/100)`;

  const pulseRing = document.getElementById('risk-pulsing-ring');
  if (risk === 'SEVERE') {
    pulseRing.classList.remove('hidden');
  } else {
    pulseRing.classList.add('hidden');
  }

  // Audio & Notification check on threat elevation
  if (lastRiskLevel && risk !== lastRiskLevel) {
    if (risk === 'SEVERE' || risk === 'HIGH') {
      playEmergencyChime('critical');
      fireNotification('🚨 Flood Threat Escalation', `Municipal threat upgraded to ${risk}. Check evacuation paths.`);
    } else {
      playEmergencyChime('warning');
    }
  }
  lastRiskLevel = risk;

  // 2. Render Sparklines (Past 24h & Next 6h)
  renderSparkline(state.weather?.sparkline_past_24h || [], state.weather?.sparkline_next_6h || []);

  // 3. Stale Data Badge
  const staleBadge = document.getElementById('badge-stale-data');
  if (state.is_stale_data) {
    staleBadge?.classList.remove('hidden');
  } else {
    staleBadge?.classList.add('hidden');
  }

  // 4. Animate 8-Step Pipeline Tracker
  animatePipelineStepper(state.pipeline_timings || {});

  // 5. Update Road Colors & Flood Inundation Zones
  updateRoadColors(state.water_levels, state.blocked_roads);
  updateFloodOverlays(rain, discharge);

  // 6. Update Evacuation Route & Route Guidance
  if (state.evacuation_route) {
    renderEvacuationRoute(state.evacuation_route);
    updateRouteCardDetails(state.evacuation_route);
  }

  // 7. Update Reachability Donut & Counts
  updateReachabilityDonut(state.stats || {});

  // 8. Update NGO Rescue Dispatch List
  updateRescueMissionsList(state.dispatch_missions || []);

  // 9. Update Explain Traces
  updateExplainModeTraces(state.algorithm_trace || {});
}

// Sparkline SVG Path Generation
function renderSparkline(past24, next6) {
  const allPoints = [...past24, ...next6];
  if (!allPoints.length) return;

  const maxVal = Math.max(...allPoints, 60.0);
  const width = 360;
  const height = 48;
  const stepX = width / (allPoints.length - 1);

  const coords = allPoints.map((val, idx) => {
    const x = idx * stepX;
    const y = height - (val / maxVal) * (height - 8);
    return [x, y];
  });

  const pathD = coords.reduce((acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${pt[0].toFixed(1)},${pt[1].toFixed(1)}`, '');
  const areaD = `${pathD} L ${width},${height} L 0,${height} Z`;

  document.getElementById('sparkline-path')?.setAttribute('d', pathD);
  document.getElementById('sparkline-area')?.setAttribute('d', areaD);

  // Position now-divider line exactly at junction between past and next
  const dividerX = (past24.length - 1) * stepX;
  document.getElementById('sparkline-now-divider')?.setAttribute('x1', dividerX);
  document.getElementById('sparkline-now-divider')?.setAttribute('x2', dividerX);
}

// 8-Step Stepper Progress Animation
function animatePipelineStepper(timings) {
  const steps = document.querySelectorAll('.step-row');
  steps.forEach((step, idx) => {
    setTimeout(() => {
      step.classList.add('completed');
    }, idx * 100);
  });

  if (timings.step_2_risk_calc_ms) document.getElementById('time-step-2').textContent = `${timings.step_2_risk_calc_ms}ms`;
  if (timings.step_4_graph_build_ms) document.getElementById('time-step-4').textContent = `${timings.step_4_graph_build_ms}ms`;
  if (timings.step_5_road_flood_ms) document.getElementById('time-step-5').textContent = `${timings.step_5_road_flood_ms}ms`;
  if (timings.step_6_reachability_ms) document.getElementById('time-step-6').textContent = `${timings.step_6_reachability_ms}ms`;
  if (timings.step_7_safe_route_ms) document.getElementById('time-step-7').textContent = `${timings.step_7_safe_route_ms}ms`;
  if (timings.step_8_ngo_dispatch_ms) document.getElementById('time-step-8').textContent = `${timings.step_8_ngo_dispatch_ms}ms`;
}

// Reachability Donut Chart Animation
function updateReachabilityDonut(stats) {
  const reachable = stats.reachable_count || 94;
  const total = stats.total_nodes || 100;
  const stranded = stats.stranded_count || (total - reachable);

  const pct = Math.round((reachable / total) * 100);
  document.getElementById('donut-reachable-pct').textContent = `${pct}%`;

  const circumference = 201.06;
  const strokeOffset = circumference - (pct / 100) * circumference;
  document.getElementById('donut-fill-reachable').style.strokeDashoffset = strokeOffset;

  document.getElementById('val-reachable-count').textContent = reachable;
  document.getElementById('val-stranded-count').textContent = stranded;
  document.getElementById('val-flooded-roads-count').textContent = stats.flooded_roads_count || 0;
  document.getElementById('val-risky-roads-count').textContent = stats.risky_roads_count || 0;
}

// Evacuation Route Card & Waypoint Guidance List
function updateRouteCardDetails(evac) {
  document.getElementById('route-destination-name').textContent = evac.destination_name || 'Designated Safe Shelter';
  document.getElementById('val-route-distance').textContent = `${evac.total_distance_km.toFixed(2)} km`;
  document.getElementById('val-eta-drive').textContent = `${evac.driving_eta_mins.toFixed(1)} mins`;
  document.getElementById('val-eta-walk').textContent = `${evac.walking_eta_mins.toFixed(1)} mins`;

  const listEl = document.getElementById('route-steps-list');
  listEl.innerHTML = '';

  const nodes = evac.route_coords || [];
  nodes.forEach((node, i) => {
    const li = document.createElement('li');
    li.className = 'step-guide-item';
    li.innerHTML = `
      <span class="step-num-badge">${i + 1}</span>
      <span style="flex:1;">${node.name}</span>
      <span style="font-size:10px; color:#64748b;">${node.elevation_m}m</span>
    `;

    // Hover highlights segment on map
    li.addEventListener('mouseenter', () => {
      if (map) map.panTo({ lat: node.lat, lng: node.lng });
    });

    listEl.appendChild(li);
  });
}

// Rescue Missions List & NGO Blue Route
function updateRescueMissionsList(missions) {
  const listEl = document.getElementById('dispatch-queue-list');
  const countBadge = document.getElementById('badge-active-dispatches');

  if (!missions.length) {
    listEl.innerHTML = `
      <div class="empty-state">
        <svg class="icon-empty" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
        <p>No cut-off neighborhoods detected. All sectors retain accessible shelter ingress routes.</p>
      </div>
    `;
    countBadge.textContent = '0 Active';
    countBadge.className = 'badge badge-blue badge-sm';
    return;
  }

  countBadge.textContent = `${missions.length} Active`;
  countBadge.className = 'badge badge-danger badge-sm';

  listEl.innerHTML = '';
  missions.forEach(m => {
    const isAirlift = m.needs_airlift;
    const card = document.createElement('div');
    card.className = `dispatch-item ${isAirlift ? 'airlift' : ''}`;
    card.innerHTML = `
      <div class="dispatch-item-top">
        <span class="dispatch-priority-badge">#${m.priority_rank} Priority</span>
        <span class="dispatch-status-badge ${m.status === 'Acknowledged' ? 'status-ack' : 'status-sent'}">${m.status}</span>
      </div>
      <div class="dispatch-location-name">${m.stranded_name} (${m.stranded_node})</div>
      <div class="dispatch-subtext">
        <span>${(m.population || 0).toLocaleString()} residents</span> • 
        <span>Threat: ${m.risk_score}/100</span> • 
        <strong>${m.ngo_assigned?.name || 'NDRF Tactical Airlift'}</strong>
      </div>
    `;

    // Clicking draws the NGO route in blue
    card.addEventListener('click', () => {
      highlightNGORoute(m);
    });

    listEl.appendChild(card);
  });
}

function highlightNGORoute(mission) {
  if (!map) return;

  // Clear existing
  Object.values(ngoRoutePolylines).forEach(p => p.setMap(null));
  ngoRoutePolylines = {};

  if (!mission.rescue_route_coords || mission.rescue_route_coords.length < 2) {
    showToast(`Stranded: ${mission.stranded_name} (Requires Helicopter / Boat Airlift)`, 'error');
    return;
  }

  const coords = mission.rescue_route_coords.map(c => ({ lat: c.lat, lng: c.lng }));
  const poly = new google.maps.Polyline({
    path: coords,
    geodesic: true,
    strokeColor: '#3b82f6',
    strokeOpacity: 0.95,
    strokeWeight: 6,
    map: map,
  });

  ngoRoutePolylines[mission.id] = poly;

  const bounds = new google.maps.LatLngBounds();
  coords.forEach(pt => bounds.extend(pt));
  map.fitBounds(bounds, 80);

  showToast(`Drawing NGO Response Route for ${mission.stranded_name}`, 'info');
}

// Explain Mode Traces
function updateExplainModeTraces(trace) {
  window._lastTraces = trace;
  const activeTab = document.querySelector('.explain-tab.active')?.dataset?.tab || 'dijkstra';
  renderExplainTab(activeTab);
}

function renderExplainTab(tab) {
  const trace = window._lastTraces || {};
  const box = document.getElementById('explain-trace-log');
  if (!box) return;

  if (tab === 'dijkstra') {
    box.textContent = `// Custom MinHeap Dijkstra Safe Path Exploration:\nSettled Order: ${JSON.stringify(trace.dijkstra_settled_order, null, 2)}\n\nMinHeap Trace Steps:\n${JSON.stringify(trace.heap_steps, null, 2)}`;
  } else if (tab === 'heap') {
    box.textContent = `// Custom MinHeap Stranded Triage Priority Queue:\n// Formula: -(Risk_Score * Population)\n${JSON.stringify(trace.ngo_dispatch_heap, null, 2)}`;
  } else if (tab === 'bfs') {
    box.textContent = `// CustomQueue BFS Reachability Traversal:\n${JSON.stringify(trace.bfs_order, null, 2)}`;
  } else if (tab === 'dfs') {
    box.textContent = `// CustomStack DFS Cut-Off Island Discovery:\n${JSON.stringify(trace.dfs_stack_order, null, 2)}`;
  }
}

// ==========================================
// 8. DIJKSTRA REPLAY STEP-BY-STEP ANIMATION
// ==========================================
async function replayDijkstraStepByStep() {
  if (isReplayingDijkstra || !map) return;
  isReplayingDijkstra = true;

  const btn = document.getElementById('btn-replay-dijkstra');
  btn.disabled = true;
  btn.textContent = '⏳ Animating...';

  // Clear previous replay markers
  dijkstraReplayMarkers.forEach(m => m.setMap(null));
  dijkstraReplayMarkers = [];

  const visited = window._lastTraces?.dijkstra_settled_order || [];
  const locById = {};
  graphData.locations.forEach(l => { locById[l.id] = l; });

  for (let i = 0; i < visited.length; i++) {
    const nid = visited[i];
    const loc = locById[nid];
    if (loc) {
      const marker = new google.maps.Marker({
        position: { lat: loc.lat, lng: loc.lng },
        map: map,
        title: `Explored: ${loc.name}`,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 9,
          fillColor: '#f59e0b',
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2,
        },
      });
      dijkstraReplayMarkers.push(marker);
    }
    await new Promise(r => setTimeout(r, replaySpeedMs));
  }

  showToast(`Dijkstra animated ${visited.length} node expansions!`, 'success');
  isReplayingDijkstra = false;
  btn.disabled = false;
  btn.textContent = 'Animate Dijkstra';
}

// ==========================================
// 9. UI EVENT LISTENERS
// ==========================================
function setupUIEventListeners() {
  // Theme Toggle
  document.getElementById('btn-theme-toggle')?.addEventListener('click', () => {
    setTheme(currentTheme === 'dark' ? 'light' : 'dark');
  });

  // Sound Toggle
  document.getElementById('btn-sound-toggle')?.addEventListener('click', () => {
    soundEnabled = !soundEnabled;
    document.getElementById('sound-icon-on')?.classList.toggle('hidden', !soundEnabled);
    document.getElementById('sound-icon-off')?.classList.toggle('hidden', soundEnabled);
    showToast(`Emergency alert sounds ${soundEnabled ? 'unmuted' : 'muted'}`, 'info');
  });

  // Data Sources Tooltip Click Toggle
  document.getElementById('btn-data-sources')?.addEventListener('click', () => {
    document.getElementById('tooltip-popover')?.classList.toggle('active');
  });

  // Use My Location GPS button
  document.getElementById('btn-use-my-location')?.addEventListener('click', () => {
    initGeolocationTracking();
  });

  // Google Maps API Key Modal Save
  document.getElementById('btn-save-key')?.addEventListener('click', () => {
    const inputKey = document.getElementById('input-api-key')?.value.trim();
    if (inputKey) {
      localStorage.setItem('google_maps_key', inputKey);
      document.getElementById('api-key-modal')?.classList.add('hidden');
      loadGoogleMapsScript(inputKey);
    }
  });

  // Continue Simulation Mode without Key
  document.getElementById('btn-continue-simulation')?.addEventListener('click', () => {
    document.getElementById('api-key-modal')?.classList.add('hidden');
  });

  // Google Traffic Layer Toggle
  document.getElementById('toggle-traffic-layer')?.addEventListener('change', (e) => {
    if (trafficLayer && map) {
      trafficLayer.setMap(e.target.checked ? map : null);
    }
  });

  // Replay speed slider & button
  document.getElementById('slider-replay-speed')?.addEventListener('input', (e) => {
    replaySpeedMs = parseInt(e.target.value, 10);
    document.getElementById('val-replay-speed').textContent = `${replaySpeedMs}ms`;
  });

  document.getElementById('btn-replay-dijkstra')?.addEventListener('click', () => {
    replayDijkstraStepByStep();
  });

  // Simulation Play / Pause / Step
  document.getElementById('btn-sim-play')?.addEventListener('click', toggleSimSurge);
  document.getElementById('btn-sim-step')?.addEventListener('click', stepSimulation);
  document.getElementById('btn-sim-reset')?.addEventListener('click', () => setSimulationStep(0));

  document.querySelectorAll('.btn-sim-tab').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const step = parseInt(e.target.dataset.step, 10);
      setSimulationStep(step);
    });
  });

  document.getElementById('slider-sim-timeline')?.addEventListener('input', (e) => {
    setSimulationStep(parseInt(e.target.value, 10));
  });

  // Explain tabs
  document.querySelectorAll('.explain-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      document.querySelectorAll('.explain-tab').forEach(t => t.classList.remove('active'));
      e.target.classList.add('active');
      renderExplainTab(e.target.dataset.tab);
    });
  });

  // Start Navigation Button
  document.getElementById('btn-start-navigation')?.addEventListener('click', () => {
    startNavigationStepGuidance();
  });

  // Legend minimize
  document.getElementById('btn-legend-toggle')?.addEventListener('click', () => {
    const body = document.getElementById('legend-body');
    const isHidden = body.classList.toggle('hidden');
    document.getElementById('btn-legend-toggle').textContent = isHidden ? '▴' : '▾';
  });
}

// Step-by-Step Navigation Simulator
function startNavigationStepGuidance() {
  const steps = document.querySelectorAll('.step-guide-item');
  if (!steps.length) return;

  currentActiveStepIdx = 0;
  showToast('Starting turn-by-turn evacuation guidance', 'success');

  const navInterval = setInterval(() => {
    steps.forEach(s => s.style.background = '');
    if (currentActiveStepIdx < steps.length) {
      steps[currentActiveStepIdx].style.background = 'rgba(16, 185, 129, 0.25)';
      steps[currentActiveStepIdx].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      currentActiveStepIdx++;
    } else {
      clearInterval(navInterval);
      showToast('Arrived safely at Designated Emergency Shelter!', 'success');
    }
  }, 1200);
}

// Multi-timestep Simulation Control
async function setSimulationStep(step) {
  document.querySelectorAll('.btn-sim-tab').forEach(b => b.classList.remove('active'));
  document.querySelector(`.btn-sim-tab[data-step="${step}"]`)?.classList.add('active');
  const slider = document.getElementById('slider-sim-timeline');
  if (slider) slider.value = step;

  try {
    const res = await fetch('/api/simulate/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        step_index: step,
        start_node: currentUserNode,
        user_lat: currentUserCoords.lat,
        user_lng: currentUserCoords.lng,
      }),
    });
    if (!res.ok) throw new Error('Simulation step failed');
    const report = await res.json();
    showToast(`Simulation T+${step}h: ${report.description}`, 'info');
  } catch (e) {
    console.debug('Sim notice:', e);
  }
}

function stepSimulation() {
  const slider = document.getElementById('slider-sim-timeline');
  const next = (parseInt(slider.value, 10) + 1) % 6;
  setSimulationStep(next);
}

function toggleSimSurge() {
  const btn = document.getElementById('btn-sim-play');
  const text = document.getElementById('text-sim-play');

  if (isSimulatingSurge) {
    clearInterval(simInterval);
    isSimulatingSurge = false;
    text.textContent = 'Play Surge Cycle';
  } else {
    isSimulatingSurge = true;
    text.textContent = 'Pause Cycle';
    simInterval = setInterval(stepSimulation, 3000);
  }
}

async function triggerEvacuateCalculation() {
  try {
    const res = await fetch('/api/evacuate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_node: currentUserNode,
        rainfall_mm_per_hr: parseFloat(document.getElementById('val-rainfall-rate')?.textContent || 48.5),
        user_lat: currentUserCoords.lat,
        user_lng: currentUserCoords.lng,
      }),
    });
    if (!res.ok) throw new Error('Evacuate calculate failed');
    const result = await res.json();
    currentResult = result;
  } catch (e) {
    console.debug('Evacuate err:', e);
  }
}

function checkUrlRouteFocus() {
  const params = new URLSearchParams(window.location.search);
  const routeId = window.FOCUSED_ROUTE_ID || params.get('route') || (window.location.hash.startsWith('#route=') ? window.location.hash.replace('#route=', '') : null);

  if (routeId) {
    setTimeout(async () => {
      try {
        const res = await fetch(`/api/route/${routeId}`);
        if (res.ok) {
          const mission = await res.json();
          highlightNGORoute(mission);
        }
      } catch (e) {
        console.debug('Route focus error:', e);
      }
    }, 1500);
  }
}

// Mobile Bottom Sheet Drag Interaction
function initSheetTouchDrag() {
  const handle = document.getElementById('sheet-drag-handle');
  const sidebar = document.getElementById('sidebar');
  if (!handle || !sidebar) return;

  let startY = 0;
  let currentHeight = 50;

  handle.addEventListener('touchstart', (e) => {
    startY = e.touches[0].clientY;
  });

  handle.addEventListener('touchend', (e) => {
    const endY = e.changedTouches[0].clientY;
    const diff = startY - endY;

    if (diff > 50) {
      sidebar.className = 'sidebar-sheet snap-full';
    } else if (diff < -50) {
      sidebar.className = 'sidebar-sheet snap-peek';
    } else {
      sidebar.className = 'sidebar-sheet snap-half';
    }
  });
}

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="dot-indicator dot-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'warning'}"></span>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}
