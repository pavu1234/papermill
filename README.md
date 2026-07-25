# PaperMill Intelligent Grade-Change Assistant

An AI-powered advisory system for paper machine operators during grade changes. Predicts Basis Weight off-spec risk, recommends corrective setpoints, discovers new correlations, and learns from operator feedback.

## Key Features

- **Risk Prediction**: Forecasts probability and time-to-breach of Basis Weight ±2.5% band
- **Smart Recommendations**: Suggests setpoint adjustments within recipe/actuator constraints
- **Correlation Discovery**: Automatically finds undocumented relationships between process variables
- **Explainability**: Every prediction includes traced source (historical data, recipe constraint, correlation model, operator pattern)
- **Human-in-the-Loop**: Capture operator Accept/Reject decisions for continuous accuracy tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA INGESTION LAYER                        │
│  (Synthetic historian + operator logs + alarm history)           │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FEATURE ENGINEERING & CORRELATION ENGINE          │
│  Rolling stats, lag features, cross-correlation, similarity      │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               PREDICTION ENGINE (2 models)                        │
│  1. Deviation-Risk Model (classification/forecasting)            │
│  2. Stabilization-Time Model (regression + feature importance)   │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 RECOMMENDATION & RATIONALE ENGINE                 │
│  Constraint-aware suggestions with source tagging                │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FEEDBACK & LEARNING LOOP                       │
│  Accept/Reject capture → Accuracy tracking                       │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        OPERATOR DASHBOARD (React)                │
│  7 required views: trajectory, risk, correlations, etc.          │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
papermill/
├── backend/
│   ├── app.py                      # FastAPI main
│   ├── config.py                   # Configuration
│   ├── data_generation/
│   │   └── synthetic_data_gen.py   # Realistic grade-change simulator
│   ├── feature_engineering/
│   │   ├── features.py             # Rolling stats, lag features
│   │   └── correlation.py          # Cross-correlation, similarity
│   ├── models/
│   │   ├── risk_predictor.py       # Deviation-risk classifier
│   │   └── stabilization.py        # Stabilization-time regressor
│   ├── recommendations/
│   │   ├── engine.py               # Constraint-aware suggestions
│   │   └── rationale.py            # Source tagging + LLM grounding
│   ├── feedback/
│   │   └── handler.py              # Accept/Reject logging
│   ├── db/
│   │   ├── models.py               # SQLAlchemy ORM
│   │   └── init.py                 # DB initialization
│   └── routes/
│       ├── predict.py              # /predict-risk endpoint
│       ├── recommend.py            # /recommend-setpoints endpoint
│       ├── correlations.py         # /correlations endpoint
│       ├── feedback.py             # /feedback endpoint
│       └── health.py               # /health endpoint
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── index.js
│   │   ├── App.js
│   │   ├── components/
│   │   │   ├── TrajectoryPanel.js
│   │   │   ├── RiskPanel.js
│   │   │   ├── CorrelationPanel.js
│   │   │   ├── FutureStatePanel.js
│   │   │   ├── StabilizationDrivers.js
│   │   │   ├── RecommendationFeed.js
│   │   │   └── FeedbackAnalytics.js
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── styles/
│   │   │   └── index.css
│   │   └── utils/
│   │       └── formatting.js
│   ├── package.json
│   └── .env.example
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── DATA_MODEL.md
│   └── PRESENTATION.md
├── requirements.txt
├── setup.py
├── docker-compose.yml
└── .gitignore
```

## Tech Stack

- **Backend**: Python (FastAPI, pandas, scikit-learn, xgboost)
- **ML**: XGBoost for risk model, regression for stabilization
- **Data**: SQLite with synthetic historian
- **Frontend**: React + Recharts for charting
- **Explainability**: SHAP for feature importance

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r ../requirements.txt
python -c "from data_generation.synthetic_data_gen import generate_synthetic_data; generate_synthetic_data(num_events=200)"
python app.py
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend runs on `http://localhost:3000`

## Dashboard Views

1. **Live Trajectory Panel** — Basis Weight actual vs. setpoint vs. ±2.5% band vs. predicted trajectory
2. **Risk Panel** — Current risk probability, predicted time-to-breach
3. **Correlation Discovery Panel** — Table of new/known correlations with impact statements
4. **Future-State Projection** — If trend continues, projected impact on Basis Weight
5. **Stabilization Drivers Panel** — Ranked loops/parameters by stabilization time contribution
6. **Recommendation Feed** — Suggested setpoints with source tag, rationale, Accept/Reject
7. **Feedback Analytics** — Historical accept/reject rates, suggestion accuracy over time

## Build Order

1. ✅ Synthetic data generator
2. Feature engineering + correlation engine
3. Deviation-risk model + stabilization-time model
4. Recommendation engine with constraint-checking
5. FastAPI endpoints
6. React dashboard
7. Feedback loop wiring
8. Documentation
9. Presentation deck

## API Endpoints

- `GET /health` — Health check
- `POST /predict-risk` — Predict Basis Weight deviation risk
- `POST /recommend-setpoints` — Generate corrective setpoint suggestions
- `GET /correlations` — Get discovered correlations
- `POST /feedback` — Log operator Accept/Reject decision
- `GET /feedback-analytics` — Historical accuracy metrics

## License

MIT
