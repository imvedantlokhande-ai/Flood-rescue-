/**
 * Spherical Haversine Distance Formula
 *
 * Computes great-circle distance between two geographic coordinates (lat, lng) in kilometers.
 *
 * Strict Compliance:
 * - NO external geo libraries (e.g. geopy, turf.js).
 * - Implemented directly using Math trigonometric functions.
 */

export interface LatLng {
  lat: number;
  lng: number;
}

const EARTH_RADIUS_KM = 6371.0;

/**
 * Calculates great-circle distance in kilometers between two lat/lng coordinates.
 *
 * Formula:
 * a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlng/2)
 * c = 2 * atan2(√a, √(1-a))
 * d = R * c
 */
export function haversineDistanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180.0;

  const phi1 = toRad(lat1);
  const phi2 = toRad(lat2);
  const deltaPhi = toRad(lat2 - lat1);
  const deltaLambda = toRad(lon2 - lon1);

  const a =
    Math.sin(deltaPhi / 2.0) * Math.sin(deltaPhi / 2.0) +
    Math.cos(phi1) *
      Math.cos(phi2) *
      Math.sin(deltaLambda / 2.0) *
      Math.sin(deltaLambda / 2.0);

  const c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0, 1.0 - a)));
  return Math.round(EARTH_RADIUS_KM * c * 1000) / 1000;
}

/**
 * Snaps a target coordinate to the closest graph node by minimizing Haversine distance.
 */
export function findNearestNode(
  targetLat: number,
  targetLng: number,
  locations: Array<{ id: string; lat: number; lng: number; [key: string]: any }>
): { nearestNodeId: string; distanceKm: number } | null {
  if (!locations || locations.length === 0) {
    return null;
  }

  let minDistance = Infinity;
  let nearestId = locations[0].id;

  for (const loc of locations) {
    const dist = haversineDistanceKm(targetLat, targetLng, loc.lat, loc.lng);
    if (dist < minDistance) {
      minDistance = dist;
      nearestId = loc.id;
    }
  }

  return {
    nearestNodeId: nearestId,
    distanceKm: Math.round(minDistance * 1000) / 1000
  };
}
