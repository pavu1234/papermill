import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
from typing import Dict, Tuple
import pickle
from pathlib import Path


class DeviationRiskPredictor:
    """Predicts probability of Basis Weight breaching ±2.5% band."""

    def __init__(self, model_type: str = "xgboost"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_fitted = False

    def prepare_training_data(
        self,
        df_historian: pd.DataFrame,
        basis_weight_target: float,
        tolerance: float = 0.025,
    ) -> Tuple[np.ndarray, np.ndarray, list]:
        """Prepare features and labels for training.
        
        Args:
            df_historian: Historian DataFrame
            basis_weight_target: Target basis weight
            tolerance: Off-spec threshold (default ±2.5%)
            
        Returns:
            (X_features, y_labels, feature_names)
        """
        # Select feature columns
        feature_cols = [
            "stock_flow", "filler_flow", "steam_pressure", "machine_speed",
            "moisture", "ash", "caliper",
            "stock_flow_error", "filler_flow_error", "machine_speed_error",
            "basis_weight_rolling_mean_30", "basis_weight_rolling_std_30",
            "stock_flow_rate_change", "filler_flow_rate_change",
        ]

        # Keep only columns that exist
        available_cols = [c for c in feature_cols if c in df_historian.columns]
        X = df_historian[available_cols].values

        # Create label: 1 if deviation > tolerance
        if "basis_weight" in df_historian.columns:
            deviation = (
                np.abs(df_historian["basis_weight"] - basis_weight_target) /
                basis_weight_target
            )
            y = (deviation > tolerance).astype(int).values
        else:
            y = np.zeros(len(X), dtype=int)

        # Handle NaN
        X = np.nan_to_num(X, 0.0)

        self.feature_names = available_cols
        return X, y, available_cols

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ):
        """Train the risk prediction model."""
        # Scale features
        X_scaled = self.scaler.fit_transform(X_train)

        if self.model_type == "xgboost":
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric="logloss",
            )
        else:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
            )

        self.model.fit(X_scaled, y_train)
        self.is_fitted = True

    def predict(
        self,
        X: np.ndarray,
    ) -> np.ndarray:
        """Predict risk probability (0-1)."""
        if not self.is_fitted:
            raise ValueError("Model not fitted yet")

        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)[:, 1]

    def predict_time_to_breach(
        self,
        df_historian: pd.DataFrame,
        basis_weight_target: float,
        tolerance: float = 0.025,
    ) -> float:
        """Estimate seconds until basis weight breaches tolerance band.
        
        Returns:
            Seconds to breach, or None if won't breach
        """
        if "elapsed_sec" not in df_historian.columns:
            return None

        deviation = (
            np.abs(df_historian["basis_weight"] - basis_weight_target) /
            basis_weight_target
        )
        breaches = df_historian[deviation > tolerance]

        if len(breaches) > 0:
            time_to_breach = breaches.iloc[0]["elapsed_sec"]
            return time_to_breach

        return None

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        if not self.is_fitted or self.model is None:
            return {}

        if hasattr(self.model, "feature_importances_"):
            importance = self.model.feature_importances_
            return dict(zip(self.feature_names, importance))

        return {}

    def save(self, path: str):
        """Save model to disk."""
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
            }, f)

    def load(self, path: str):
        """Load model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.feature_names = data["feature_names"]
            self.is_fitted = True
