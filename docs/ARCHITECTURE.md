# PaperMill Architecture

## System Overview

The PaperMill Grade-Change Assistant is a multi-layer intelligent advisory system for paper mill operators. It sits alongside Honeywell's MPC (Multivariable Model Predictive Control) system and provides real-time risk predictions, setpoint recommendations, and correlation discovery.

## Architecture Layers

### 1. Data Ingestion Layer
- **Purpose**: Aggregate data from multiple sources
- **Sources**:
  - Honeywell QCS historian (MPC setpoints and actuator positions)
  - DCS historian (process measurements: basis weight, moisture, ash, caliper, etc.)
  - MIS reports (grade definitions, recipe limits, transition metadata)
  - Operator action logs (manual adjustments, operator ID)
  - Alarm history (scanner faults, loop failures, off-spec alerts)
- **Implementation**: SQLAlchemy ORM with SQLite for synthetic data; production uses DB2 or DMS

### 2. Feature Engineering & Correlation Engine
- **Lag Features**: Create past values (1s, 5s, 10s, 30s lag) to capture system memory
- **Rolling Statistics**: Mean, std, min, max over 10s, 30s, 60s windows
- **Rate-of-Change**: First differences to capture velocity/acceleration
- **Setpoint Tracking Error**: Deviation from MPC target (critical for control loop health)
- **Cross-Correlation Analysis**: 
  - Compute Pearson correlation and p-value for all variable pairs
  - Identify "known" loops (stock_flow → basis_weight, steam_pressure → moisture, etc.)
  - Flag "new" correlations not in the known list
  - Filter by p-value < 0.05 and |r| > 0.3 to avoid spurious findings

### 3. Prediction Engine (2 Models)

#### 3a. Deviation-Risk Model
- **Type**: XGBoost classifier
- **Input Features**: Rolling statistics, lag features, setpoint errors
- **Output**: Probability [0, 1] that Basis Weight will breach ±2.5% band
- **Training**: Binary classification (off-spec vs success) on historical events
- **Inference**: Real-time, updated as new historian data arrives
- **Time-to-Breach Estimation**: Scans future trajectory to find first breach point

#### 3b. Stabilization-Time Model
- **Type**: Linear regression or random forest
- **Input Features**: Event-level summary stats (mean, std, tracking error per variable)
- **Output**: Predicted time-to-steady-state in seconds
- **Feature Importance**: Ranked list of variables driving stabilization time
- **Use Case**: Identify which loops to adjust to speed convergence

### 4. Recommendation & Rationale Engine
- **Strategy 1 (High Risk)**: If risk probability > 0.6, identify highest-impact variable from risk model and suggest correction
- **Strategy 2 (Slow Stabilization)**: Identify top stabilization drivers and suggest setpoint adjustments to accelerate settling
- **Constraint Checking**: All recommendations clamped to recipe limits and actuator bounds
- **Source Tagging**: Every suggestion tagged with origin:
  - `risk_model` — high deviation risk detected
  - `stabilization_driver` — speeds up time-to-steady-state
  - `correlation_model` — leverages newly discovered correlation
  - `operator_pattern` — matches historical operator behavior
- **Natural Language Rationale**: Template-based generation grounded in numeric evidence (no hallucination)

### 5. Feedback & Learning Loop
- **Feedback Capture**: Operator clicks Accept/Reject; system logs:
  - recommendation_id
  - operator_id
  - timestamp
  - action (accepted / rejected)
  - outcome_status (success / failed / pending)
- **Accuracy Tracking**: Historical acceptance rate, predicted vs actual deviation, model drift over time
- **Future Enhancement**: Use feedback to retrain models monthly/quarterly

### 6. Dashboard (React Frontend)

**7 Required Panels:**

1. **Live Trajectory Panel**
   - Chart: Basis Weight actual vs setpoint vs ±2.5% band over time
   - Shows real-time progress of grade change
   - Highlights off-spec regions in red

2. **Risk Panel**
   - Risk gauge (current probability %)
   - Time-to-breach countdown
   - Color-coded status (green/yellow/red)

3. **Correlation Discovery Panel**
   - Table: Variable pairs, correlation strength, impact statement
   - Separate rows for "known" vs "newly discovered"
   - Links to future-state projections

4. **Future-State Projection Panel**
   - For each high-impact correlated variable, project forward 60s if trend continues
   - Show expected impact on Basis Weight
   - Warn if trend leads toward off-spec

5. **Stabilization Drivers Panel**
   - Ranked list of variables by contribution to settling time
   - Current value + suggested adjustment
   - Expected time reduction if applied

6. **Recommendation Feed**
   - Scrollable list of active recommendations
   - Per recommendation: setpoint, expected effect, source tag, rationale
   - Accept/Reject buttons with operator ID capture
   - Real-time update as model runs

7. **Feedback Analytics Panel**
   - Historical acceptance rate (%) over time
   - Suggestion accuracy: predicted outcome vs actual
   - Model drift detection: are recent predictions degrading?
   - Operator-specific performance (which operators follow suggestions most)

---

## Data Flow

```
Historian Data (5s resolution)
     ↓
Feature Engineer
  (lag, rolling, diff, error)
     ↓
┌────────────────────────────────────────┐
│  Risk Model          │  Stabilization   │
│  (XGBoost)           │  Model (LR)      │
│  P(off-spec)         │  Time-to-stab    │
│  Time-to-breach      │  Drivers         │
└────────────────────────────────────────┘
     ↓
Recommendation Engine
  (constraint check, source tag)
     ↓
Rationale Generator
  (natural language)
     ↓
📊 Dashboard Visualization
     ↓
👤 Operator Accept/Reject
     ↓
Feedback Logger
     ↓
📈 Feedback Analytics
```

---

## Key Design Decisions

1. **Why synthetic data?** Real mill data is proprietary; synthetic generator ensures reproducibility and allows testing corner cases (e.g., disturbances, slow loops).

2. **Why two models?** Risk model focuses on *what* (breach risk), stabilization model focuses on *how fast* (settle time). Different objectives, different features.

3. **Why source tags?** Operators need to understand *why* a suggestion was made. Tags provide transparency and build trust.

4. **Why correlation discovery?** Paper mills often have undocumented interactions (e.g., ash → basis weight measurement via scanner calibration). Surfacing these can improve control.

5. **Why feedback logging?** Machine learning models drift over time. Feedback is the ground truth for measuring model accuracy and triggering retraining.

---

## Deployment Notes

- **Backend**: FastAPI server running on port 8000
- **Frontend**: React dev server on port 3000 (CORS-enabled for development)
- **Database**: SQLite for development; production uses centralized DB (DB2, PostgreSQL, SQL Server)
- **Models**: Pickled and versioned; loaded at startup
- **Scalability**: Historian data windowed to ~300 events; real-time prediction on latest 120-point window (~10 min)

---

## Future Enhancements

1. **LSTM/Temporal Models**: Replace lag features with learned time-series embeddings
2. **Active Learning**: Prioritize which events to label next to improve model faster
3. **Transfer Learning**: Pre-train on synthetic data, fine-tune on real mill as data arrives
4. **Multi-Modal Input**: Incorporate scanner images, operator comments as text features
5. **Real-Time Model Drift Detection**: Alert when model performance degrades
6. **Causal Discovery**: Estimate directional relationships (not just correlation)
