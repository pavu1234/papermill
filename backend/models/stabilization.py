import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from typing import Dict, List, Tuple
import pickle


class StabilizationTimePredictor:
    """Predicts time-to-steady-state and identifies stabilization drivers."""

    def __init__(self, model_type: str = "linear"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_fitted = False

    def prepare_training_data(
        self,
        list_of_historian_dfs: List[pd.DataFrame],
        time_to_stabilize_values: List[float],
    ) -> Tuple[np.ndarray, np.ndarray, list]:
        """Aggregate features from multiple events for training.
        
        Args:
            list_of_historian_dfs: List of historian DataFrames (one per event)
            time_to_stabilize_values: Corresponding time-to-stabilize seconds
            
        Returns:
            (X_features, y_targets, feature_names)
        """
        X_list = []
        y_list = []

        for df_hist, time_to_stab in zip(list_of_historian_dfs, time_to_stabilize_values):
            if df_hist.empty or time_to_stab is None:
                continue

            # Extract summary statistics over the event
            features = self._extract_event_features(df_hist)
            X_list.append(features)
            y_list.append(time_to_stab)

        X = np.array(X_list)
        y = np.array(y_list)

        # Handle NaN
        X = np.nan_to_num(X, 0.0)

        return X, y, self.feature_names

    def _extract_event_features(self, df_hist: pd.DataFrame) -> np.ndarray:
        """Extract summary features from a single event."""
        features = {}
        feature_order = []

        numeric_cols = [
            "stock_flow", "filler_flow", "steam_pressure", "machine_speed",
            "basis_weight", "moisture", "ash", "caliper",
        ]

        for col in numeric_cols:
            if col in df_hist.columns:
                # Mean, std, rate of change
                features[f"{col}_mean"] = df_hist[col].mean()
                features[f"{col}_std"] = df_hist[col].std()
                features[f"{col}_rate_change"] = df_hist[col].diff().mean()
                feature_order.extend([f"{col}_mean", f"{col}_std", f"{col}_rate_change"])

        # Setpoint tracking error
        for col in numeric_cols:
            sp_col = f"{col}_sp"
            if sp_col in df_hist.columns:
                error = (df_hist[col] - df_hist[sp_col]).abs().mean()
                features[f"{col}_setpoint_error"] = error
                feature_order.append(f"{col}_setpoint_error")

        self.feature_names = feature_order
        return np.array([features.get(f, 0.0) for f in feature_order])

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ):
        """Train stabilization time predictor."""
        X_scaled = self.scaler.fit_transform(X_train)

        if self.model_type == "linear":
            self.model = LinearRegression()
        else:
            self.model = RandomForestRegressor(
                n_estimators=50,
                max_depth=8,
                random_state=42,
            )

        self.model.fit(X_scaled, y_train)
        self.is_fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict time-to-stabilize in seconds."""
        if not self.is_fitted:
            raise ValueError("Model not fitted yet")

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        return np.clip(predictions, 0, None)  # No negative times

    def get_stabilization_drivers(
        self,
        top_k: int = 5,
    ) -> Dict[str, float]:
        """Rank features by contribution to stabilization time.
        
        For linear model, uses coefficients.
        For tree model, uses feature importance.
        """
        if not self.is_fitted or self.model is None:
            return {}

        if isinstance(self.model, LinearRegression):
            importance = np.abs(self.model.coef_)
        else:
            importance = self.model.feature_importances_

        # Normalize
        importance = importance / (np.sum(importance) + 1e-6)

        # Create dict and sort
        drivers = dict(zip(self.feature_names, importance))
        drivers = dict(sorted(drivers.items(), key=lambda x: x[1], reverse=True))

        return {k: v for k, v in list(drivers.items())[:top_k]}

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
