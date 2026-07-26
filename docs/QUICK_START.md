# Quick Start Guide

## Prerequisites

- **Python 3.9+**
- **Node.js 16+** and npm
- **Git**
- 2 GB disk space for synthetic data

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/pavu1234/papermill.git
cd papermill
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
cd backend
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

#### Install Dependencies

```bash
pip install -r ../requirements.txt
```

#### Generate Synthetic Data

```bash
python -c "from data_generation.synthetic_data_gen import generate_synthetic_data; generate_synthetic_data(num_events=200)"
```

This generates 200 realistic grade-change events with ~100,000 historian records and stores them in `data/papermill.db`.

**Output:**
```
Generating 200 synthetic grade-change events...
  Generated 50/200 events...
  Generated 100/200 events...
  Generated 150/200 events...
  Generated 200/200 events...

✓ Generated 200 events

Summary:
outcome
success     161
off_spec     39
Name: count, dtype: int64

Average time to stabilize: 312.5s
Average max deviation: 0.0287 (2.87%)
```

#### Start API Server

```bash
python app.py
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✓ Database initialized
INFO:     Application startup complete
```

Server is ready at `http://localhost:8000`

### 3. Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Create Environment File

Create `.env.local` in the `frontend` directory:

```bash
echo "REACT_APP_API_URL=http://localhost:8000/api" > .env.local
```

#### Start Dev Server

```bash
npm start
```

**Expected Output:**
```
Compiled successfully!

You can now view papermill-dashboard in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.1.100:3000
```

## Verification

### 1. Check API Health

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{"status":"ok","timestamp":"2026-07-26T05:30:00Z","service":"papermill-api"}
```

### 2. Test Prediction Endpoint

```bash
curl -X POST http://localhost:8000/api/predict-risk \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": 1,
    "current_state": {"stock_flow": 500, "filler_flow": 50, "steam_pressure": 5.5, "machine_speed": 650},
    "basis_weight_target": 120
  }'
```

**Response:**
```json
{"event_id":1,"risk_probability":0.32,"time_to_breach_sec":240,"status":"success","message":null}
```

### 3. Open Dashboard

Navigate to `http://localhost:3000` in your browser. You should see:

- Header with "PaperMill Grade-Change Assistant" title
- Control panel with Event ID selector and action buttons
- Three dashboard panels: Risk, Recommendations, Correlations

---

## Quick API Usage

### Generate Predictions

```python
import requests

resp = requests.post(
    'http://localhost:8000/api/predict-risk',
    json={
        'event_id': 5,
        'current_state': {
            'stock_flow': 480,
            'filler_flow': 48,
            'steam_pressure': 5.2,
            'machine_speed': 620,
        },
        'basis_weight_target': 100,
    }
)
print(resp.json())
```

### Get Recommendations

```python
resp = requests.post(
    'http://localhost:8000/api/recommend-setpoints',
    json={
        'event_id': 5,
        'current_state': {'stock_flow': 480, 'filler_flow': 48},
        'target_state': {'stock_flow': 500, 'filler_flow': 50},
        'risk_probability': 0.45,
    }
)
for rec in resp.json()['recommendations']:
    print(f"{rec['variable_name']}: {rec['current_value']} → {rec['recommended_value']}")
```

### Discover Correlations

```python
resp = requests.get('http://localhost:8000/api/correlations?event_id=5')
data = resp.json()
print("Known loops:")
for loop in data['known_loops']:
    print(f"  {loop['variable_a']} ↔ {loop['variable_b']}: {loop['impact_statement']}")
print("\nNew correlations:")
for corr in data['new_correlations']:
    print(f"  {corr['variable_a']} ↔ {corr['variable_b']}: {corr['impact_statement']}")
```

---

## Data Exploration

### View Generated Events

```python
from backend.db import SessionLocal
from backend.db.models import GradeChangeEvent

session = SessionLocal()
events = session.query(GradeChangeEvent).limit(10).all()

for event in events:
    print(f"Event {event.event_id}: {event.from_grade} → {event.to_grade}")
    print(f"  Outcome: {event.outcome_label}")
    print(f"  Time to stabilize: {event.time_to_stabilize_sec:.0f}s")
    print(f"  Max deviation: {event.max_deviation*100:.2f}%")
```

### Export Historian Data to CSV

```python
import pandas as pd
from backend.db import SessionLocal
from backend.db.models import HistorianData

session = SessionLocal()
records = session.query(HistorianData).filter(
    HistorianData.event_id == 1
).all()

df = pd.DataFrame([
    {
        'elapsed_sec': r.elapsed_sec,
        'stock_flow': r.stock_flow,
        'filler_flow': r.filler_flow,
        'basis_weight': r.basis_weight,
        'basis_weight_sp': r.basis_weight_sp,
        'deviation': r.basis_weight_deviation,
    }
    for r in records
])

df.to_csv('event_1.csv', index=False)
print(f"Exported {len(df)} records to event_1.csv")
```

---

## Development Workflow

### Adding a New Feature

1. **Backend**: Add model/feature to `backend/feature_engineering/` or `backend/models/`
2. **API**: Create endpoint in `backend/routes/`
3. **Frontend**: Add React component to `frontend/src/components/`
4. **Test**: Use curl or Python requests to test endpoint
5. **Dashboard**: Wire component to API in `App.js`

### Running Tests

```bash
# Backend tests (add to backend/tests/)
pytest backend/tests/ -v

# Frontend tests
cd frontend
npm test
```

### Checking Code Quality

```bash
# Python linting
flake8 backend/ --max-line-length=100

# JavaScript linting
cd frontend
npm run lint
```

---

## Troubleshooting

### Backend won't start: "Address already in use"

```bash
# Kill process on port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or change port in config.py
export API_PORT=8001
python app.py
```

### Frontend shows "Connection refused"

- Ensure backend is running on `http://localhost:8000`
- Check `.env.local` has correct `REACT_APP_API_URL`
- Check CORS headers: backend should allow `http://localhost:3000`

### Database locked error

```bash
# SQLite gets locked with many concurrent writes
# Solution: use PostgreSQL for production
# For dev, just restart backend:
kill -9 $(lsof -t -i:8000)
python app.py
```

### Models not trained

Predictions will return mock values (risk ≈ 0.3) if models haven't been trained. To train:

```python
from backend.models.risk_predictor import DeviationRiskPredictor
from backend.db import SessionLocal
from backend.db.models import HistorianData, GradeChangeEvent

session = SessionLocal()
events = session.query(GradeChangeEvent).limit(50).all()

model = DeviationRiskPredictor()
X_list, y_list = [], []

for event in events:
    records = session.query(HistorianData).filter(
        HistorianData.event_id == event.event_id
    ).all()
    if records:
        # Engineer features...
        X, y, _ = model.prepare_training_data(df, event.recipe_target_basis_weight)
        X_list.append(X)
        y_list.append(y)

# Train
model.fit(np.vstack(X_list), np.hstack(y_list))
model.save('backend/models/risk_model.pkl')
```

---

## Next Steps

1. **Generate More Events**: Adjust `num_events` in `generate_synthetic_data()` to 500+ for better model training
2. **Train Models**: Load historical data and train risk/stabilization models
3. **Customize**: Modify recipe limits and known control loops in `backend/config.py` for your mill
4. **Deploy**: Use Docker and production-grade database (PostgreSQL, DB2)
5. **Monitor**: Set up logging/alerting on model predictions

---

## Support & Resources

- **API Docs**: http://localhost:8000/docs (auto-generated Swagger UI)
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Data Model**: See `docs/DATA_MODEL.md`
