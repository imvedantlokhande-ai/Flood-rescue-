"""
Flood Risk Assessment Engine.

Rule-based expert system that evaluates rainfall intensity, cumulative 24-hour precipitation,
and surface water levels to determine the overall flood risk threat level.
"""

from typing import Dict, List, Optional, Any, NamedTuple


# ==========================================
# CONFIGURABLE THRESHOLDS
# ==========================================
# Hourly rainfall rate thresholds in mm/hr
RAIN_HOURLY_LOW_MAX = 15.0       # < 15 mm/hr: Low
RAIN_HOURLY_MOD_MAX = 30.0       # 15 - 30 mm/hr: Moderate
RAIN_HOURLY_HIGH_MAX = 60.0      # 30 - 60 mm/hr: High; > 60 mm/hr: Severe

# 24-hour cumulative rainfall thresholds in mm
RAIN_24H_MODERATE_MIN = 75.0     # >= 75 mm in 24h triggers caution
RAIN_24H_HIGH_MIN = 120.0        # >= 120 mm triggers high risk
RAIN_24H_SEVERE_MIN = 180.0      # >= 180 mm triggers severe alert

# Surface / road water level thresholds in meters
WATER_LEVEL_ANOMALOUS_M = 0.20   # >= 0.20 m: water pooling on asphalt
WATER_LEVEL_DANGEROUS_M = 0.50   # >= 0.50 m: vehicles stalled, pedestrian danger
WATER_LEVEL_CRITICAL_M = 0.80    # >= 0.80 m: life-threatening flash flood depth

# Risk Levels
RISK_LOW = "LOW"
RISK_MODERATE = "MODERATE"
RISK_HIGH = "HIGH"
RISK_SEVERE = "SEVERE"


class RiskAssessment(NamedTuple):
    """Encapsulates the final risk calculation result."""
    risk_level: str
    is_dangerous: bool
    score: float  # 0.0 to 100.0
    summary: str
    reasons: List[str]
    evacuation_needed: bool


def calculate_flood_risk(
    rainfall_mm_per_hr: float,
    rainfall_last_24h_mm: float = 0.0,
    max_water_level_m: float = 0.0,
    river_level_above_normal_m: float = 0.0,
) -> RiskAssessment:
    """
    Compute rule-based flood risk score based on multi-parameter hydrologic conditions.

    Scoring Logic (0 - 100 points):
    - Hourly rainfall: up to 40 points
    - Cumulative 24h rainfall: up to 25 points
    - Max observed water level: up to 25 points
    - River swell / basin level: up to 10 points

    Risk Classification:
    - Score < 25: LOW (Normal conditions, no evacuation required)
    - 25 <= Score < 50: MODERATE (Localized puddling, watch status)
    - 50 <= Score < 75: HIGH (Flooding widespread, evacuation strongly advised)
    - Score >= 75: SEVERE (Flash flood crisis, mandatory immediate evacuation)

    Returns:
        RiskAssessment tuple with status, boolean flag, score, and explanation reasons.
    """
    reasons: List[str] = []
    score = 0.0

    # 1. Evaluate Hourly Rainfall Rate (Weight: 40)
    if rainfall_mm_per_hr < RAIN_HOURLY_LOW_MAX:
        hourly_score = (rainfall_mm_per_hr / RAIN_HOURLY_LOW_MAX) * 10.0
        reasons.append(f"Hourly rainfall is light to steady ({rainfall_mm_per_hr:.1f} mm/hr).")
    elif rainfall_mm_per_hr <= RAIN_HOURLY_MOD_MAX:
        hourly_score = 10.0 + ((rainfall_mm_per_hr - RAIN_HOURLY_LOW_MAX) / (RAIN_HOURLY_MOD_MAX - RAIN_HOURLY_LOW_MAX)) * 15.0
        reasons.append(f"Moderate rainfall intensity detected ({rainfall_mm_per_hr:.1f} mm/hr).")
    elif rainfall_mm_per_hr <= RAIN_HOURLY_HIGH_MAX:
        hourly_score = 25.0 + ((rainfall_mm_per_hr - RAIN_HOURLY_MOD_MAX) / (RAIN_HOURLY_HIGH_MAX - RAIN_HOURLY_MOD_MAX)) * 10.0
        reasons.append(f"Heavy downpour ({rainfall_mm_per_hr:.1f} mm/hr) exceeding urban storm drain capacity.")
    else:
        hourly_score = 40.0
        reasons.append(f"Torrential cloudburst ({rainfall_mm_per_hr:.1f} mm/hr) causing rapid runoff accumulation.")
    score += hourly_score

    # 2. Evaluate 24-Hour Cumulative Rainfall (Weight: 25)
    if rainfall_last_24h_mm >= RAIN_24H_SEVERE_MIN:
        score += 25.0
        reasons.append(f"Severe 24h rain ({rainfall_last_24h_mm:.1f} mm): Ground is 100% saturated, full surface runoff.")
    elif rainfall_last_24h_mm >= RAIN_24H_HIGH_MIN:
        ratio = (rainfall_last_24h_mm - RAIN_24H_HIGH_MIN) / (RAIN_24H_SEVERE_MIN - RAIN_24H_HIGH_MIN)
        score += 15.0 + (ratio * 10.0)
        reasons.append(f"Substantial 24h rain ({rainfall_last_24h_mm:.1f} mm) heightening soil saturation.")
    elif rainfall_last_24h_mm >= RAIN_24H_MODERATE_MIN:
        ratio = (rainfall_last_24h_mm - RAIN_24H_MODERATE_MIN) / (RAIN_24H_HIGH_MIN - RAIN_24H_MODERATE_MIN)
        score += 7.0 + (ratio * 8.0)
        reasons.append(f"Elevated 24h rain ({rainfall_last_24h_mm:.1f} mm).")
    else:
        score += min(7.0, (rainfall_last_24h_mm / RAIN_24H_MODERATE_MIN) * 7.0)

    # 3. Evaluate Surface Water Level (Weight: 25)
    if max_water_level_m >= WATER_LEVEL_CRITICAL_M:
        score += 25.0
        reasons.append(f"Critical standing water detected ({max_water_level_m:.2f} m): Roadway completely submerged.")
    elif max_water_level_m >= WATER_LEVEL_DANGEROUS_M:
        ratio = (max_water_level_m - WATER_LEVEL_DANGEROUS_M) / (WATER_LEVEL_CRITICAL_M - WATER_LEVEL_DANGEROUS_M)
        score += 18.0 + (ratio * 7.0)
        reasons.append(f"Dangerous water level ({max_water_level_m:.2f} m): Inundation impedes standard vehicular evacuation.")
    elif max_water_level_m >= WATER_LEVEL_ANOMALOUS_M:
        ratio = (max_water_level_m - WATER_LEVEL_ANOMALOUS_M) / (WATER_LEVEL_DANGEROUS_M - WATER_LEVEL_ANOMALOUS_M)
        score += 8.0 + (ratio * 10.0)
        reasons.append(f"Puddle accumulation on low-elevation roads ({max_water_level_m:.2f} m).")
    else:
        score += (max_water_level_m / WATER_LEVEL_ANOMALOUS_M) * 8.0

    # 4. Evaluate River Swell (Weight: 10)
    if river_level_above_normal_m > 2.0:
        score += 10.0
        reasons.append(f"River basin is {river_level_above_normal_m:.1f}m above datum (estuary breach risk).")
    elif river_level_above_normal_m > 1.0:
        score += 5.0 + (river_level_above_normal_m - 1.0) * 5.0
        reasons.append(f"River swell elevated ({river_level_above_normal_m:.1f}m above normal).")

    score = min(100.0, max(0.0, score))

    # Determine Risk Classification
    if score >= 75.0 or max_water_level_m >= WATER_LEVEL_CRITICAL_M:
        risk_level = RISK_SEVERE
        is_dangerous = True
        evacuation_needed = True
        summary = "SEVERE FLOOD EMERGENCY: Life-threatening water depths present. Immediate evacuation required!"
    elif score >= 50.0 or max_water_level_m >= WATER_LEVEL_DANGEROUS_M:
        risk_level = RISK_HIGH
        is_dangerous = True
        evacuation_needed = True
        summary = "HIGH FLOOD THREAT: Critical arterial routes compromised. Evacuate to high ground immediately."
    elif score >= 25.0:
        risk_level = RISK_MODERATE
        is_dangerous = True
        evacuation_needed = True
        summary = "MODERATE FLOOD RISK: Low-lying roads impassable. Precautionary evacuation activated."
    else:
        risk_level = RISK_LOW
        is_dangerous = False
        evacuation_needed = False
        summary = "LOW RISK: Rainfall within standard drainage capacity. No evacuation needed at this time."

    return RiskAssessment(
        risk_level=risk_level,
        is_dangerous=is_dangerous,
        score=round(score, 1),
        summary=summary,
        reasons=reasons,
        evacuation_needed=evacuation_needed,
    )


if __name__ == "__main__":
    print("Testing Risk Calculator across test scenarios:")
    scenarios = [
        ("Dry / Light Rain", 5.0, 10.0, 0.05, 0.2),
        ("Moderate Afternoon Shower", 22.0, 45.0, 0.25, 0.8),
        ("Heavy Tropical Storm", 48.5, 135.0, 0.75, 2.4),
        ("Catastrophic Cloudburst", 90.0, 220.0, 1.40, 3.2),
    ]
    for label, rain_hr, rain_24, water_m, river_m in scenarios:
        res = calculate_flood_risk(rain_hr, rain_24, water_m, river_m)
        print(f"\n--- Scenario: {label} ---")
        print(f"Risk Level: {res.risk_level} (Score: {res.score}/100, Evacuate: {res.evacuation_needed})")
        print(f"Summary: {res.summary}")
        for r in res.reasons:
            print(f"  * {r}")
