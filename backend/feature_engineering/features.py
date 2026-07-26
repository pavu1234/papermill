import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from backend.config import FEATURE_CONFIG


class FeatureEngineer:
    """Feature engineering for grade change events."""

    def __init__(self, config: Dict = None):
        self.config = config or FEATURE_CONFIG
        self.lag_windows = self.config.get("lag_windows", [1, 5, 10, 30])
        self.rolling_windows = self.config.get("rolling_windows", [10, 30, 60])

    def engineer_features(self, df_historian: pd.DataFrame) -> pd.DataFrame:
        """Create lag and rolling statistics features from historian data.
        
        Args:
            df_historian: DataFrame with columns like basis_weight, stock_flow, etc.
            
        Returns:
            Enhanced DataFrame with lag/rolling features
        """
        df = df_historian.copy()

        # Numeric columns to process
        numeric_cols = [
            "stock_flow", "filler_flow", "steam_pressure", "machine_speed",
            "basis_weight", "moisture", "ash", "caliper",
        ]

        # Create lag features
        for col in numeric_cols:
            for lag in self.lag_windows:
                df[f"{col}_lag_{lag}"] = df[col].shift(lag)

        # Create rate-of-change features
        for col in numeric_cols:
            df[f"{col}_rate_change"] = df[col].diff()

        # Create rolling statistics
        for col in numeric_cols:
            for window in self.rolling_windows:
                df[f"{col}_rolling_mean_{window}"] = df[col].rolling(window=window).mean()
                df[f"{col}_rolling_std_{window}"] = df[col].rolling(window=window).std()
                df[f"{col}_rolling_min_{window}"] = df[col].rolling(window=window).min()
                df[f"{col}_rolling_max_{window}"] = df[col].rolling(window=window).max()

        # Setpoint tracking error
        for col in numeric_cols:
            sp_col = f"{col}_sp"
            if sp_col in df.columns:
                df[f"{col}_error"] = df[col] - df[sp_col]
                df[f"{col}_error_abs"] = np.abs(df[f"{col}_error"])

        # Fill NaN from lag/rolling
        df = df.fillna(method="bfill").fillna(method="ffill")

        return df


class SimilaritySearcher:
    """Find similar historical grade changes."""

    @staticmethod
    def compute_trajectory_similarity(
        trajectory_a: np.ndarray,
        trajectory_b: np.ndarray,
    ) -> float:
        """Compute DTW or Euclidean similarity between two trajectories.
        
        For speed, uses Euclidean distance on normalized trajectories.
        """
        # Normalize to [0, 1]
        a_norm = (trajectory_a - np.min(trajectory_a)) / (np.max(trajectory_a) - np.min(trajectory_a) + 1e-6)
        b_norm = (trajectory_b - np.min(trajectory_b)) / (np.max(trajectory_b) - np.min(trajectory_b) + 1e-6)

        # Resample to same length if needed
        if len(a_norm) != len(b_norm):
            min_len = min(len(a_norm), len(b_norm))
            a_norm = a_norm[:min_len]
            b_norm = b_norm[:min_len]

        # Euclidean distance
        distance = np.sqrt(np.mean((a_norm - b_norm) ** 2))
        similarity = 1.0 / (1.0 + distance)  # Convert to similarity [0, 1]

        return similarity

    @staticmethod
    def find_similar_events(
        query_event_id: int,
        all_historian_data: Dict[int, pd.DataFrame],
        variable: str = "basis_weight",
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        """Find top-k historical events most similar to query event.
        
        Args:
            query_event_id: Event ID to find matches for
            all_historian_data: Dict mapping event_id -> historian DataFrame
            variable: Which variable to compare on
            top_k: Number of results
            
        Returns:
            List of (event_id, similarity) tuples, sorted by similarity desc
        """
        if query_event_id not in all_historian_data:
            return []

        query_traj = all_historian_data[query_event_id][variable].values
        similarities = []

        for event_id, df_hist in all_historian_data.items():
            if event_id == query_event_id:
                continue
            if variable not in df_hist.columns:
                continue

            traj = df_hist[variable].values
            sim = SimilaritySearcher.compute_trajectory_similarity(query_traj, traj)
            similarities.append((event_id, sim))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
