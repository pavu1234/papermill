import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "data"
DATABASE_DIR.mkdir(exist_ok=True)

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATABASE_DIR / 'papermill.db'}"
)

# Paper Mill Process Constants
BASIS_WEIGHT_TOLERANCE = 0.025  # ±2.5%
OFF_SPEC_THRESHOLD = 0.025

# Recipe Limits (defaults, can be overridden per grade)
RECIPE_LIMITS = {
    "stock_flow": {"min": 100, "max": 800},  # kg/min
    "filler_flow": {"min": 10, "max": 150},  # kg/min
    "steam_pressure": {"min": 2.0, "max": 8.0},  # bar
    "machine_speed": {"min": 200, "max": 1000},  # m/min
    "basis_weight": {"min": 50, "max": 250},  # g/m²
}

# Model Configuration
MODEL_CONFIG = {
    "risk_model": {
        "type": "xgboost",
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
    },
    "stabilization_model": {
        "type": "linear_regression",
    },
}

# Feature Engineering
FEATURE_CONFIG = {
    "lag_windows": [1, 5, 10, 30],  # seconds
    "rolling_windows": [10, 30, 60],  # seconds
    "correlation_min_threshold": 0.3,
}

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "true").lower() == "true"

# Frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
