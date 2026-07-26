# Data Model

## Overview

The PaperMill system uses a relational data model to store:
- Historical grade change events
- Time-series historian data (process measurements)
- Operator actions and alarms
- Model predictions and recommendations
- Operator feedback for continuous learning
- Discovered correlations

## Database Schema

### grade_change_events

Stores metadata about each grade transition.

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | INTEGER PK | Unique event identifier |
| `timestamp_start` | DATETIME | Grade change start time |
| `timestamp_end` | DATETIME | Grade change end time (nullable) |
| `from_grade` | VARCHAR | Starting grade (e.g., "grade_A") |
| `to_grade` | VARCHAR | Target grade (e.g., "grade_B") |
| `recipe_target_basis_weight` | FLOAT | Target basis weight (g/m²) |
| `recipe_limits` | JSON | Dict of min/max for each variable |
| `outcome_label` | VARCHAR | "success" or "off_spec" |
| `time_to_stabilize_sec` | FLOAT | Seconds to reach steady state (nullable) |
| `max_deviation` | FLOAT | Maximum % deviation from target during event |

**Example:**
```json
{
  "event_id": 42,
  "from_grade": "grade_A",
  "to_grade": "grade_B",
  "recipe_target_basis_weight": 120,
  "outcome_label": "success",
  "time_to_stabilize_sec": 320,
  "max_deviation": 0.018
}
```

---

### historian_data

Time-series measurements at ~5-second resolution per event.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Historian record ID |
| `event_id` | INTEGER FK | Reference to grade_change_events |
| `timestamp` | DATETIME | Absolute timestamp of measurement |
| `elapsed_sec` | FLOAT | Seconds since event start |
| **Process Variables** | | |
| `stock_flow` | FLOAT | kg/min |
| `filler_flow` | FLOAT | kg/min |
| `steam_pressure` | FLOAT | bar |
| `machine_speed` | FLOAT | m/min |
| `basis_weight` | FLOAT | g/m² |
| `moisture` | FLOAT | % |
| `ash` | FLOAT | % |
| `caliper` | FLOAT | mm |
| **Setpoints (MPC Targets)** | | |
| `stock_flow_sp` | FLOAT | kg/min |
| `filler_flow_sp` | FLOAT | kg/min |
| `steam_pressure_sp` | FLOAT | bar |
| `machine_speed_sp` | FLOAT | m/min |
| `basis_weight_sp` | FLOAT | g/m² |
| **Calculated Fields** | | |
| `basis_weight_deviation` | FLOAT | (basis_weight - target) / target |
| `is_off_spec` | BOOLEAN | True if \|deviation\| > 2.5% |

**Example:**
```json
{
  "id": 1001,
  "event_id": 42,
  "elapsed_sec": 125.0,
  "stock_flow": 480.5,
  "filler_flow": 48.2,
  "steam_pressure": 5.2,
  "machine_speed": 620.3,
  "basis_weight": 119.8,
  "moisture": 8.4,
  "ash": 14.9,
  "caliper": 0.18,
  "basis_weight_sp": 120.0,
  "basis_weight_deviation": -0.00167,
  "is_off_spec": false
}
```

---

### operator_actions

Manual adjustments made by operators during grade changes.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Operator action ID |
| `event_id` | INTEGER FK | Reference to grade_change_events |
| `timestamp` | DATETIME | When action was taken |
| `variable_changed` | VARCHAR | Variable adjusted (e.g., "steam_pressure") |
| `old_value` | FLOAT | Previous value |
| `new_value` | FLOAT | New value |
| `operator_id` | VARCHAR | Operator identifier (e.g., "OP_1001") |

**Example:**
```json
{
  "id": 1,
  "event_id": 42,
  "timestamp": "2026-07-26T10:30:45Z",
  "variable_changed": "steam_pressure",
  "old_value": 5.0,
  "new_value": 5.3,
  "operator_id": "OP_1001"
}
```

---

### alarm_logs

Alarms and diagnostic events (e.g., off-spec alerts, loop failures).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Alarm log ID |
| `event_id` | INTEGER FK | Reference to grade_change_events |
| `timestamp` | DATETIME | When alarm occurred |
| `alarm_code` | VARCHAR | Alarm code (e.g., "ALM_001") |
| `severity` | VARCHAR | "info", "warning", or "critical" |
| `variable` | VARCHAR | Affected variable |
| `message` | TEXT | Alarm message |

**Example:**
```json
{
  "id": 1,
  "event_id": 42,
  "timestamp": "2026-07-26T10:35:00Z",
  "alarm_code": "ALM_001",
  "severity": "warning",
  "variable": "basis_weight",
  "message": "Basis weight deviation exceeded 2.5% threshold"
}
```

---

### prediction_results

Audit trail of model predictions for each event.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Prediction record ID |
| `event_id` | INTEGER FK | Reference to grade_change_events |
| `timestamp` | DATETIME | When prediction was made |
| `risk_probability` | FLOAT | Probability of off-spec [0, 1] |
| `time_to_breach_sec` | FLOAT | Estimated seconds to breach (nullable) |
| `stabilization_time_estimate` | FLOAT | Expected time to steady state (nullable) |
| `model_version` | VARCHAR | Model version identifier |

**Example:**
```json
{
  "id": 42,
  "event_id": 42,
  "timestamp": "2026-07-26T10:32:15Z",
  "risk_probability": 0.32,
  "time_to_breach_sec": 240.0,
  "stabilization_time_estimate": 350.0,
  "model_version": "v0.1.0"
}
```

---

### recommendations

Generated setpoint suggestions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Recommendation ID |
| `event_id` | INTEGER FK | Reference to grade_change_events |
| `timestamp_created` | DATETIME | When recommendation was generated |
| `variable_name` | VARCHAR | Variable to adjust |
| `recommended_value` | FLOAT | Suggested setpoint |
| `current_value` | FLOAT | Current measurement |
| `expected_effect` | TEXT | Plain English description |
| `source_tag` | VARCHAR | "risk_model", "stabilization_driver", "correlation_model", "operator_pattern" |
| `rationale` | TEXT | Detailed explanation |
| `confidence` | FLOAT | Model confidence [0, 1] |

**Example:**
```json
{
  "id": 1,
  "event_id": 42,
  "timestamp_created": "2026-07-26T10:32:20Z",
  "variable_name": "stock_flow",
  "current_value": 480.5,
  "recommended_value": 490.0,
  "expected_effect": "reduce basis weight deviation",
  "source_tag": "risk_model",
  "rationale": "Based on the deviation-risk model, stock_flow is the highest-impact driver of Basis Weight stability...",
  "confidence": 0.7
}
```

---

### recommendation_feedback

Operator feedback on recommendations (Accept/Reject + outcome).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Feedback record ID |
| `recommendation_id` | INTEGER FK | Reference to recommendations |
| `timestamp_feedback` | DATETIME | When feedback was logged |
| `operator_id` | VARCHAR | Operator ID |
| `action` | VARCHAR | "accepted" or "rejected" |
| `outcome_status` | VARCHAR | "success", "failed", "pending" (nullable) |
| `notes` | TEXT | Operator comment (nullable) |

**Example:**
```json
{
  "id": 1,
  "recommendation_id": 1,
  "timestamp_feedback": "2026-07-26T10:33:00Z",
  "operator_id": "OP_1001",
  "action": "accepted",
  "outcome_status": "success",
  "notes": "Applied suggestion; Basis Weight stabilized within 2 minutes"
}
```

---

### discovered_correlations

Statistically significant variable relationships found during analysis.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Correlation ID |
| `variable_a` | VARCHAR | First variable in pair |
| `variable_b` | VARCHAR | Second variable in pair |
| `correlation_strength` | FLOAT | Pearson r [-1, 1] |
| `p_value` | FLOAT | Statistical significance |
| `is_known_control_loop` | BOOLEAN | True if documented loop |
| `impact_statement` | TEXT | Plain English description |
| `discovered_at` | DATETIME | When correlation was found |
| `num_events_supporting` | INTEGER | How many events show this correlation |

**Example:**
```json
{
  "id": 1,
  "variable_a": "stock_flow",
  "variable_b": "basis_weight",
  "correlation_strength": 0.85,
  "p_value": 0.0001,
  "is_known_control_loop": true,
  "impact_statement": "stock_flow strongly increases basis_weight (r=0.85)",
  "num_events_supporting": 45
}
```

---

## Relationships

```
grade_change_events
├── historian_data (1:N)
├── operator_actions (1:N)
├── alarm_logs (1:N)
├── prediction_results (1:N)
└── recommendations (1:N)
    └── recommendation_feedback (1:N)

discovered_correlations (standalone)
```

---

## Indices

For query performance:

```sql
CREATE INDEX idx_event_id ON historian_data(event_id);
CREATE INDEX idx_timestamp ON historian_data(timestamp);
CREATE INDEX idx_event_outcome ON grade_change_events(outcome_label);
CREATE INDEX idx_recommendation_event ON recommendations(event_id);
CREATE INDEX idx_feedback_recommendation ON recommendation_feedback(recommendation_id);
```

---

## Synthetic Data Generation

The `SyntheticGradeChangeSimulator` creates realistic data with:

1. **Grades**: 4 predefined paper grades (A, B, C, D) with basis weight targets (80–180 g/m²)
2. **Physics-Based Dynamics**:
   - Stock flow: 1st-order lag (τ = 30s)
   - Filler flow: Coupled to stock flow with lag (τ = 25s)
   - Machine speed: Slower lag (τ = 40s)
   - Steam pressure: Quick response (τ = 15s)
   - **Basis weight**: Complex function of stock flow, filler flow, machine speed with 60s lag
   - Moisture: Coupled to steam pressure
   - Ash: Slight coupling to filler flow
   - Caliper: Follows basis weight and ash

3. **Noise & Measurement**:
   - ±2% noise on stock flow
   - ±3% noise on filler flow
   - ±1.5% noise on basis weight
   - Measurement drift: sinusoidal scanner calibration error

4. **Success/Failure**:
   - 80% events complete successfully
   - 20% events go off-spec via step disturbance

5. **Operators**:
   - 20% of events include operator manual adjustment
   - 15% of events trigger alarms

---

## Query Examples

### Get all off-spec events

```sql
SELECT * FROM grade_change_events WHERE outcome_label = 'off_spec';
```

### Get events with longest stabilization time

```sql
SELECT event_id, from_grade, to_grade, time_to_stabilize_sec
FROM grade_change_events
WHERE time_to_stabilize_sec IS NOT NULL
ORDER BY time_to_stabilize_sec DESC
LIMIT 10;
```

### Get recommendations most often accepted

```sql
SELECT r.variable_name, COUNT(*) as count,
       SUM(CASE WHEN rf.action = 'accepted' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as acceptance_rate
FROM recommendations r
JOIN recommendation_feedback rf ON r.id = rf.recommendation_id
GROUP BY r.variable_name
ORDER BY acceptance_rate DESC;
```

### Get basis weight deviations for event 42

```sql
SELECT elapsed_sec, basis_weight, basis_weight_sp, basis_weight_deviation, is_off_spec
FROM historian_data
WHERE event_id = 42
ORDER BY elapsed_sec;
```

---

## Scaling Considerations

- **Single Event**: ~120–200 historian records (10–15 min at 5s resolution)
- **Monthly Data**: 1000–2000 events → 120M–400M historian records
- **Annual Data**: 12,000–24,000 events → 1.4B–4.8B records
- **Recommendation**: Move to PostgreSQL or DB2 after 6 months; partition historian_data by month
