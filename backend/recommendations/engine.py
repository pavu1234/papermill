import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from backend.config import RECIPE_LIMITS, BASIS_WEIGHT_TOLERANCE


class RecommendationEngine:
    """Generate setpoint recommendations within constraints."""

    def __init__(self, recipe_limits: Dict = None):
        self.recipe_limits = recipe_limits or RECIPE_LIMITS

    def generate_recommendations(
        self,
        event_id: int,
        current_state: Dict[str, float],
        target_state: Dict[str, float],
        risk_probability: float,
        risk_model_feature_importance: Dict[str, float],
        stabilization_drivers: Dict[str, float],
        recipe_limits: Dict = None,
    ) -> List[Dict]:
        """Generate recommendations to reduce risk or stabilization time.
        
        Args:
            event_id: Grade change event ID
            current_state: Current variable values
            target_state: Target/setpoint values
            risk_probability: Current risk probability (0-1)
            risk_model_feature_importance: Feature importance from risk model
            stabilization_drivers: Ranked stabilization time drivers
            recipe_limits: Recipe constraints (uses self.recipe_limits if None)
            
        Returns:
            List of recommendation dicts
        """
        recipe_limits = recipe_limits or self.recipe_limits
        recommendations = []

        # Strategy 1: If high risk, adjust high-impact variables
        if risk_probability > 0.6:
            # Find the highest-impact variable
            if risk_model_feature_importance:
                top_driver = max(risk_model_feature_importance, key=risk_model_feature_importance.get)
                # Extract base variable name (remove _sp, _lag, etc.)
                base_var = top_driver.split("_")[0]

                if base_var in current_state and base_var in target_state:
                    rec = self._recommend_adjustment(
                        variable=base_var,
                        current_value=current_state[base_var],
                        target_value=target_state[base_var],
                        direction="stabilize",
                        recipe_limits=recipe_limits,
                        source="risk_model",
                    )
                    if rec:
                        recommendations.append(rec)

        # Strategy 2: Speed up stabilization by adjusting drivers
        if stabilization_drivers:
            for driver_feature, importance in list(stabilization_drivers.items())[:2]:
                base_var = driver_feature.split("_")[0]
                if base_var in current_state and base_var in target_state:
                    rec = self._recommend_adjustment(
                        variable=base_var,
                        current_value=current_state[base_var],
                        target_value=target_state[base_var],
                        direction="accelerate",
                        recipe_limits=recipe_limits,
                        source="stabilization_driver",
                    )
                    if rec:
                        recommendations.append(rec)

        return recommendations

    def _recommend_adjustment(
        self,
        variable: str,
        current_value: float,
        target_value: float,
        direction: str,
        recipe_limits: Dict,
        source: str,
    ) -> Optional[Dict]:
        """Generate a single adjustment recommendation.
        
        Args:
            variable: Variable name
            current_value: Current measurement
            target_value: MPC setpoint
            direction: 'stabilize' or 'accelerate'
            recipe_limits: Constraint bounds
            source: Source tag
            
        Returns:
            Recommendation dict or None if invalid
        """
        if variable not in recipe_limits:
            return None

        limits = recipe_limits[variable]
        min_val = limits["min"]
        max_val = limits["max"]

        # Compute suggested adjustment
        error = current_value - target_value
        adjustment_factor = 0.5 if direction == "stabilize" else 1.2
        adjustment = error * adjustment_factor
        recommended_value = target_value - adjustment

        # Clamp to recipe limits
        recommended_value = np.clip(recommended_value, min_val, max_val)

        # Check if recommendation is meaningful
        if abs(recommended_value - current_value) < 1e-3:
            return None

        # Estimate expected effect
        if variable == "steam_pressure":
            expected_effect = "reduce moisture drift"
        elif variable == "machine_speed":
            expected_effect = "stabilize basis weight"
        elif variable == "stock_flow":
            expected_effect = "reduce basis weight deviation"
        elif variable == "filler_flow":
            expected_effect = "improve basis weight tracking"
        else:
            expected_effect = "improve process stability"

        return {
            "variable_name": variable,
            "current_value": current_value,
            "recommended_value": recommended_value,
            "expected_effect": expected_effect,
            "source_tag": source,
            "confidence": 0.7 if direction == "stabilize" else 0.6,
        }

    @staticmethod
    def validate_recommendation(
        recommendation: Dict,
        recipe_limits: Dict,
    ) -> bool:
        """Validate that recommendation respects constraints."""
        var = recommendation["variable_name"]
        value = recommendation["recommended_value"]

        if var not in recipe_limits:
            return False

        limits = recipe_limits[var]
        return limits["min"] <= value <= limits["max"]
