/**
 * Flood Risk Assessment Engine
 *
 * Evaluates municipal hydrologic threat level based on:
 * 1. Current hourly precipitation rate (mm/hr)
 * 2. 24-hour cumulative rainfall (mm)
 * 3. Maximum road water depth (m)
 *
 * Threat categories:
 * - LOW (0 - 24): Routine operations
 * - MODERATE (25 - 49): Ponding in depressions, caution advised
 * - HIGH (50 - 74): Road blockages, evacuation alerts active
 * - SEVERE / CRITICAL (75 - 100): Catastrophic inundation, immediate evacuation & airlift
 */

export interface FloodRiskResult {
  score: number;
  level: 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE';
  isDangerous: boolean;
  components: {
    rainRateScore: number;
    rain24hScore: number;
    depthScore: number;
  };
  summary: string;
}

export function calculateFloodRisk(
  rainfallRateMmHr: number,
  rainfall24hMm: number,
  maxWaterDepthM: number
): FloodRiskResult {
  let rainRateScore = 0;
  if (rainfallRateMmHr < 15.0) {
    rainRateScore = (rainfallRateMmHr / 15.0) * 10.0;
  } else if (rainfallRateMmHr <= 30.0) {
    rainRateScore = 10.0 + ((rainfallRateMmHr - 15.0) / 15.0) * 15.0;
  } else if (rainfallRateMmHr <= 60.0) {
    rainRateScore = 25.0 + ((rainfallRateMmHr - 30.0) / 30.0) * 10.0;
  } else {
    rainRateScore = 35.0 + Math.min(5.0, ((rainfallRateMmHr - 60.0) / 40.0) * 5.0);
  }

  let rain24hScore = 0;
  if (rainfall24hMm < 75.0) {
    rain24hScore = (rainfall24hMm / 75.0) * 8.0;
  } else if (rainfall24hMm < 120.0) {
    rain24hScore = 8.0 + ((rainfall24hMm - 75.0) / 45.0) * 7.0;
  } else if (rainfall24hMm < 180.0) {
    rain24hScore = 15.0 + ((rainfall24hMm - 120.0) / 60.0) * 10.0;
  } else {
    rain24hScore = 25.0;
  }

  let depthScore = 0;
  if (maxWaterDepthM < 0.20) {
    depthScore = (maxWaterDepthM / 0.20) * 8.0;
  } else if (maxWaterDepthM < 0.50) {
    depthScore = 8.0 + ((maxWaterDepthM - 0.20) / 0.30) * 10.0;
  } else if (maxWaterDepthM < 0.80) {
    depthScore = 18.0 + ((maxWaterDepthM - 0.50) / 0.30) * 12.0;
  } else {
    depthScore = 30.0 + Math.min(5.0, ((maxWaterDepthM - 0.80) / 0.50) * 5.0);
  }

  const rawScore = rainRateScore + rain24hScore + depthScore;
  const score = Math.min(100, Math.round(rawScore * 10) / 10);

  let level: 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' = 'LOW';
  if (score >= 75 || maxWaterDepthM >= 0.80) {
    level = 'SEVERE';
  } else if (score >= 50 || maxWaterDepthM >= 0.50) {
    level = 'HIGH';
  } else if (score >= 25 || maxWaterDepthM >= 0.20) {
    level = 'MODERATE';
  }

  const isDangerous = level !== 'LOW';

  let summary = '';
  switch (level) {
    case 'SEVERE':
      summary = 'Catastrophic flood crest. Low-lying riverfronts submerged; emergency evacuation mandatory.';
      break;
    case 'HIGH':
      summary = 'Severe flash flooding. Multiple transit arteries blocked; avoid lowlands.';
      break;
    case 'MODERATE':
      summary = 'Moderate waterlogging in depressions. Caution advised on riverfront roads.';
      break;
    default:
      summary = 'Normal drainage operations. All municipal evacuation corridors open.';
  }

  return {
    score,
    level,
    isDangerous,
    components: {
      rainRateScore: Math.round(rainRateScore * 10) / 10,
      rain24hScore: Math.round(rain24hScore * 10) / 10,
      depthScore: Math.round(depthScore * 10) / 10
    },
    summary
  };
}
