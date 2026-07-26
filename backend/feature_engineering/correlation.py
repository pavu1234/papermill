import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple
from backend.config import FEATURE_CONFIG


class CorrelationEngine:
    """Discover correlations and relationships between process variables."""

    KNOWN_CONTROL_LOOPS = {
        ("stock_flow", "basis_weight"): "Stock flow directly increases basis weight",
        ("filler_flow", "basis_weight"): "Filler flow increases basis weight (slightly)",
        ("machine_speed", "basis_weight"): "Higher machine speed reduces basis weight (inverse)",
        ("steam_pressure", "moisture"): "Higher steam pressure increases moisture",
        ("moisture", "basis_weight"): "Moisture affects basis weight measurement",
    }

    def __init__(self):
        self.min_threshold = FEATURE_CONFIG.get("correlation_min_threshold", 0.3)

    def compute_pairwise_correlations(
        self,
        df_historian: pd.DataFrame,
    ) -> Dict[Tuple[str, str], Dict]:
        """Compute Pearson correlation and p-value for all variable pairs.
        
        Args:
            df_historian: DataFrame with process variables
            
        Returns:
            Dict of {(var_a, var_b): {"correlation": float, "p_value": float, ...}}
        """
        numeric_cols = df_historian.select_dtypes(include=[np.number]).columns
        correlations = {}

        for i, col_a in enumerate(numeric_cols):
            for col_b in numeric_cols[i + 1 :]:
                # Skip setpoint columns for correlation
                if "_sp" in col_a or "_sp" in col_b:
                    continue

                # Compute Pearson correlation
                valid_idx = df_historian[col_a].notna() & df_historian[col_b].notna()
                if valid_idx.sum() < 10:
                    continue

                corr, p_value = stats.pearsonr(
                    df_historian.loc[valid_idx, col_a],
                    df_historian.loc[valid_idx, col_b],
                )

                # Store if significant
                if abs(corr) >= self.min_threshold and p_value < 0.05:
                    is_known = (col_a, col_b) in self.KNOWN_CONTROL_LOOPS or (
                        col_b, col_a
                    ) in self.KNOWN_CONTROL_LOOPS
                    known_desc = None
                    if is_known:
                        known_desc = self.KNOWN_CONTROL_LOOPS.get(
                            (col_a, col_b)
                        ) or self.KNOWN_CONTROL_LOOPS.get((col_b, col_a))

                    correlations[(col_a, col_b)] = {
                        "correlation": corr,
                        "p_value": p_value,
                        "is_known": is_known,
                        "description": known_desc,
                    }

        return correlations

    def discover_new_correlations(
        self,
        correlations: Dict[Tuple[str, str], Dict],
    ) -> List[Dict]:
        """Extract newly discovered correlations (not in known loops).
        
        Returns:
            List of discovered correlation dicts
        """
        new_correlations = []

        for (var_a, var_b), corr_data in correlations.items():
            if not corr_data["is_known"]:
                impact = self._interpret_correlation(
                    var_a, var_b, corr_data["correlation"]
                )
                new_correlations.append({
                    "variable_a": var_a,
                    "variable_b": var_b,
                    "correlation": corr_data["correlation"],
                    "p_value": corr_data["p_value"],
                    "impact_statement": impact,
                })

        # Sort by absolute correlation
        new_correlations.sort(
            key=lambda x: abs(x["correlation"]), reverse=True
        )
        return new_correlations

    @staticmethod
    def _interpret_correlation(
        var_a: str,
        var_b: str,
        corr: float,
    ) -> str:
        """Generate plain-English impact statement."""
        direction = "increases" if corr > 0 else "decreases"
        strength = "strongly" if abs(corr) > 0.7 else "moderately"
        return f"{var_a} {strength} {direction} {var_b} (r={corr:.2f})"

    @staticmethod
    def project_future_state(
        historical_trajectory: np.ndarray,
        current_value: float,
        correlation: float,
        window_sec: int = 60,
    ) -> Dict:
        """Project future state if trend continues.
        
        Args:
            historical_trajectory: Historical values
            current_value: Current measurement
            correlation: Correlation strength with basis weight
            window_sec: Look-ahead window
            
        Returns:
            Dict with projected_value and impact_on_basis_weight
        """
        # Simple linear trend extrapolation
        if len(historical_trajectory) < 2:
            return {"projected_value": current_value, "impact": 0.0}

        # Fit polynomial to last values
        recent_values = historical_trajectory[-20:]
        time_points = np.arange(len(recent_values))
        coeffs = np.polyfit(time_points, recent_values, 1)
        trend = coeffs[0]  # Linear coefficient

        # Project forward
        time_steps_ahead = window_sec // 5  # Assuming 5s resolution
        projected_value = current_value + trend * time_steps_ahead
        impact_on_basis_weight = trend * time_steps_ahead * correlation

        return {
            "projected_value": projected_value,
            "trend": trend,
            "impact_on_basis_weight": impact_on_basis_weight,
        }
