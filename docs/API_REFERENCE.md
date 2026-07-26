# PaperMill API Reference

## Base URL
```
http://localhost:8000/api
```

## Endpoints

### Health Check

**GET** `/health`

Check API server status.

**Response (200)**
```json
{
  "status": "ok",
  "timestamp": "2026-07-26T05:30:00.000Z",
  "service": "papermill-api"
}
```

---

### Predict Risk

**POST** `/predict-risk`

Predict probability of Basis Weight breaching ±2.5% band and estimate time-to-breach.

**Request Body**
```json
{
  "event_id": 1,
  "current_state": {
    "stock_flow": 500,
    "filler_flow": 50,
    "steam_pressure": 5.5,
    "machine_speed": 650,
    "basis_weight": 120,
    "moisture": 8.5,
    "ash": 15.2,
    "caliper": 0.18
  },
  "basis_weight_target": 120
}
```

**Response (200)**
```json
{
  "event_id": 1,
  "risk_probability": 0.32,
  "time_to_breach_sec": 240,
  "status": "success",
  "message": null
}
```

**Fields:**
- `risk_probability` (float, 0-1): Probability of off-spec condition
- `time_to_breach_sec` (float | null): Estimated seconds until Basis Weight exits ±2.5% band; null if won't breach
- `status`: "success" or "error"

---

### Recommend Setpoints

**POST** `/recommend-setpoints`

Generate corrective setpoint suggestions with rationale and source tags.

**Request Body**
```json
{
  "event_id": 1,
  "current_state": {
    "stock_flow": 500,
    "filler_flow": 50,
    "steam_pressure": 5.5,
    "machine_speed": 650
  },
  "target_state": {
    "stock_flow": 520,
    "filler_flow": 55,
    "steam_pressure": 5.8,
    "machine_speed": 670
  },
  "risk_probability": 0.32,
  "risk_model_feature_importance": {
    "stock_flow": 0.35,
    "steam_pressure": 0.25,
    "machine_speed": 0.20
  },
  "stabilization_drivers": {
    "machine_speed_mean": 0.45,
    "stock_flow_mean": 0.30
  }
}
```

**Response (200)**
```json
{
  "event_id": 1,
  "recommendations": [
    {
      "variable_name": "stock_flow",
      "current_value": 500,
      "recommended_value": 510,
      "expected_effect": "reduce basis weight deviation",
      "source_tag": "risk_model",
      "rationale": "Based on the deviation-risk model, stock_flow is the highest-impact driver of Basis Weight stability. Adjusting it from 500.0 to 510.0 is predicted to reduce off-spec risk.",
      "confidence": 0.7
    },
    {
      "variable_name": "machine_speed",
      "current_value": 650,
      "recommended_value": 660,
      "expected_effect": "stabilize basis weight",
      "source_tag": "stabilization_driver",
      "rationale": "machine_speed is identified as a key driver of stabilization time. Suggesting adjustment from 650.0 to 660.0 to speed convergence to target.",
      "confidence": 0.6
    }
  ],
  "status": "success"
}
```

**Recommendation Object:**
- `variable_name` (string): Process variable to adjust
- `current_value` (float): Current measurement
- `recommended_value` (float): Suggested setpoint
- `expected_effect` (string): Plain-English description of impact
- `source_tag` (string): One of `risk_model`, `stabilization_driver`, `correlation_model`, `operator_pattern`
- `rationale` (string): Detailed explanation grounded in model logic
- `confidence` (float, 0-1): Model confidence in suggestion

---

### Get Correlations

**GET** `/correlations?event_id=1`

Discover known and newly discovered correlations in process variables.

**Query Parameters:**
- `event_id` (int): Grade change event ID

**Response (200)**
```json
{
  "event_id": 1,
  "known_loops": [
    {
      "variable_a": "stock_flow",
      "variable_b": "basis_weight",
      "correlation_strength": 0.85,
      "p_value": 0.0001,
      "is_known_control_loop": true,
      "impact_statement": "stock_flow strongly increases basis_weight (r=0.85)"
    },
    {
      "variable_a": "steam_pressure",
      "variable_b": "moisture",
      "correlation_strength": 0.78,
      "p_value": 0.0005,
      "is_known_control_loop": true,
      "impact_statement": "steam_pressure strongly increases moisture (r=0.78)"
    }
  ],
  "new_correlations": [
    {
      "variable_a": "ash",
      "variable_b": "caliper",
      "correlation_strength": 0.52,
      "p_value": 0.008,
      "is_known_control_loop": false,
      "impact_statement": "ash moderately increases caliper (r=0.52)"
    }
  ],
  "status": "success"
}
```

**Correlation Object:**
- `variable_a`, `variable_b` (string): Variable pair
- `correlation_strength` (float, -1 to 1): Pearson correlation coefficient
- `p_value` (float): Statistical significance (typically < 0.05)
- `is_known_control_loop` (boolean): True if documented in system
- `impact_statement` (string): Human-readable description

---

### Log Feedback

**POST** `/feedback`

Capture operator acceptance/rejection of a recommendation.

**Request Body**
```json
{
  "recommendation_id": 42,
  "operator_id": "OP_1001",
  "action": "accepted",
  "outcome_status": "success",
  "notes": "Applied suggestion; Basis Weight stabilized within 2 minutes"
}
```

**Response (200)**
```json
{
  "feedback_id": 15,
  "recommendation_id": 42,
  "status": "success"
}
```

**Fields:**
- `operator_id` (string): Operator identifier
- `action` (string): "accepted" or "rejected"
- `outcome_status` (string, optional): "success", "failed", or "pending"
- `notes` (string, optional): Free-text comment

---

### Get Feedback Analytics

**GET** `/feedback-analytics`

Retrieve historical feedback statistics and model accuracy metrics.

**Response (200)**
```json
{
  "total_recommendations": 127,
  "accepted_count": 98,
  "rejected_count": 29,
  "acceptance_rate": 0.771,
  "avg_confidence_accepted": 0.74,
  "avg_confidence_rejected": 0.58
}
```

**Fields:**
- `total_recommendations` (int): Total feedback records
- `accepted_count` (int): Number accepted by operators
- `rejected_count` (int): Number rejected
- `acceptance_rate` (float, 0-1): Fraction accepted
- `avg_confidence_accepted` (float): Mean model confidence for accepted suggestions
- `avg_confidence_rejected` (float): Mean model confidence for rejected suggestions

---

## Error Handling

**400 Bad Request**: Missing or invalid request parameters
```json
{
  "detail": "Invalid event_id: must be positive integer"
}
```

**404 Not Found**: Event or resource not found
```json
{
  "detail": "Event 9999 not found"
}
```

**500 Internal Server Error**: Server-side error
```json
{
  "detail": "Database connection failed"
}
```

---

## Example Usage

### Python (requests library)

```python
import requests

BASE_URL = "http://localhost:8000/api"

# 1. Health check
resp = requests.get(f"{BASE_URL}/health")
print(resp.json())  # {"status": "ok", ...}

# 2. Predict risk
resp = requests.post(
    f"{BASE_URL}/predict-risk",
    json={
        "event_id": 1,
        "current_state": {
            "stock_flow": 500,
            "filler_flow": 50,
            "steam_pressure": 5.5,
            "machine_speed": 650,
        },
        "basis_weight_target": 120,
    }
)
data = resp.json()
print(f"Risk: {data['risk_probability']:.1%}")
if data['time_to_breach_sec']:
    print(f"Time to breach: {data['time_to_breach_sec']:.0f}s")

# 3. Get recommendations
resp = requests.post(
    f"{BASE_URL}/recommend-setpoints",
    json={
        "event_id": 1,
        "current_state": {"stock_flow": 500, "filler_flow": 50},
        "target_state": {"stock_flow": 520, "filler_flow": 55},
        "risk_probability": 0.32,
    }
)
for rec in resp.json()["recommendations"]:
    print(f"- Adjust {rec['variable_name']} from {rec['current_value']} to {rec['recommended_value']}")
    print(f"  Source: {rec['source_tag']}")
    print(f"  Rationale: {rec['rationale']}")

# 4. Log feedback
resp = requests.post(
    f"{BASE_URL}/feedback",
    json={
        "recommendation_id": 42,
        "operator_id": "OP_1001",
        "action": "accepted",
        "outcome_status": "success",
    }
)
print(f"Feedback logged: {resp.json()['feedback_id']}")
```

### JavaScript (fetch API)

```javascript
const BASE_URL = 'http://localhost:8000/api';

// 1. Predict risk
const riskResp = await fetch(`${BASE_URL}/predict-risk`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    event_id: 1,
    current_state: { stock_flow: 500, filler_flow: 50 },
    basis_weight_target: 120,
  }),
});
const riskData = await riskResp.json();
console.log(`Risk: ${(riskData.risk_probability * 100).toFixed(1)}%`);

// 2. Get recommendations
const recResp = await fetch(`${BASE_URL}/recommend-setpoints`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    event_id: 1,
    current_state: { stock_flow: 500 },
    target_state: { stock_flow: 520 },
    risk_probability: 0.32,
  }),
});
const recData = await recResp.json();
recData.recommendations.forEach(rec => {
  console.log(`${rec.variable_name}: ${rec.current_value} → ${rec.recommended_value}`);
});
```

---

## Rate Limiting

Currently unlimited. Production deployment should implement:
- 100 requests per minute per client IP
- 1000 requests per hour per API key

---

## Version History

- **0.1.0** (2026-07-26): Initial release with 5 core endpoints
