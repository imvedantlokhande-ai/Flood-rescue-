# Flood Risk Calculator Module

This module provides rule-based hydrologic risk scoring to determine whether weather and water level conditions represent an active flood emergency.

---

## 1. What This Module Does

Evaluates four environmental telemetry inputs:
- Current rainfall intensity ($\text{mm/hr}$)
- 24-hour cumulative precipitation ($\text{mm}$)
- Peak observed roadway surface water level ($\text{meters}$)
- River swell datum offset ($\text{meters}$)

Outputs a composite risk classification:
- **`LOW`** (Score $< 25$): Normal weather, no evacuation required.
- **`MODERATE`** (Score $25 - 49$): Localized pooling, cautious evacuation.
- **`HIGH`** (Score $50 - 74$): Arterials compromised, urgent evacuation.
- **`SEVERE`** (Score $\ge 75$): Life-threatening flash flood, mandatory immediate evacuation.

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

Evacuating an entire municipality creates immense traffic congestion, economic disruption, and risk of panic. The planner must first verify if dangerous conditions exist before executing graph partitioning and pathfinding. If conditions are `LOW`, the planner immediately reports `"No evacuation needed"`, saving emergency municipal resources.

---

## 3. How It Works, Step by Step

1. **Parameter Weighting**:
   - Hourly Rainfall contributes up to **40 points**.
   - 24-Hour Cumulative Rainfall contributes up to **25 points**.
   - Surface Water Level contributes up to **25 points**.
   - River Swell contributes up to **10 points**.
2. **Threshold Overrides**:
   - If water level exceeds critical safety depth ($0.8$ m), the system immediately forces a `SEVERE` classification regardless of rainfall.
   - If water level exceeds $0.5$ m, the system guarantees at least `HIGH` alert.
3. **Reason Compilation**:
   - Generates human-readable bullet points explaining the meteorological factors driving the assessment.

---

## 4. Small Worked Example

```text
Input:
  Hourly Rain: 48.5 mm/hr  -> Score: 25 + ((48.5 - 30)/(60 - 30)) * 10 = 31.2 pts
  24h Rain:   135.0 mm     -> Score: 15 + ((135 - 120)/(180 - 120)) * 10 = 17.5 pts
  Max Water:  0.75 m       -> Score: 18 + ((0.75 - 0.50)/(0.80 - 0.50)) * 7 = 23.8 pts
  River:      2.6 m        -> Score: 10.0 pts

Total Composite Score = 31.2 + 17.5 + 23.8 + 10.0 = 82.5 / 100
Result = SEVERE (Dangerous: True -> Continue to Graph Modeling)
```

---

## 5. Pseudocode

```text
FUNCTION calculate_flood_risk(rain_hr, rain_24h, water_m, river_m):
    score = 0.0
    score += evaluate_hourly_rain(rain_hr)      // max 40
    score += evaluate_24h_rain(rain_24h)        // max 25
    score += evaluate_water_level(water_m)      // max 25
    score += evaluate_river_swell(river_m)      // max 10
    score = CLAMP(score, 0.0, 100.0)

    IF score >= 75 OR water_m >= 0.8:
        RETURN RiskAssessment(SEVERE, dangerous=TRUE, evacuation=TRUE)
    ELSE IF score >= 50 OR water_m >= 0.5:
        RETURN RiskAssessment(HIGH, dangerous=TRUE, evacuation=TRUE)
    ELSE IF score >= 25:
        RETURN RiskAssessment(MODERATE, dangerous=TRUE, evacuation=TRUE)
    ELSE:
        RETURN RiskAssessment(LOW, dangerous=FALSE, evacuation=FALSE)
```

---

## 6. Time and Space Complexity

- **Time Complexity**: $O(1)$ constant time arithmetic comparisons.
- **Space Complexity**: $O(1)$ auxiliary storage for the result tuple.

---

## 7. Input and Output Format

- **Input**:
  - `rainfall_mm_per_hr` (`float`): Rate in mm/hr
  - `rainfall_last_24h_mm` (`float`): Past 24h total
  - `max_water_level_m` (`float`): Deepest water depth recorded
  - `river_level_above_normal_m` (`float`): River swell
- **Output**:
  - `RiskAssessment` named tuple: `(risk_level, is_dangerous, score, summary, reasons, evacuation_needed)`

---

## 8. How to Run / Test Individually

```bash
python3 algorithms/flood_risk/risk_calculator.py
```

---

## 9. Limitations and Possible Improvements

1. **Topographic Elevation Awareness**: Future versions can ingest Digital Elevation Model (DEM) slope angles to predict flash flood velocity.
2. **Dynamic Machine Learning**: Neural hydrological precipitation run-off models could replace static thresholds.
