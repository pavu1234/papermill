from typing import Dict, List


class RationaleGenerator:
    """Generate natural-language explanations for recommendations."""

    TEMPLATES = {
        "risk_model": (
            "Based on the deviation-risk model, {variable} is the highest-impact driver "
            "of Basis Weight stability. Adjusting it from {current:.1f} to {recommended:.1f} "
            "is predicted to reduce off-spec risk."
        ),
        "stabilization_driver": (
            "{variable} is identified as a key driver of stabilization time. "
            "Suggesting adjustment from {current:.1f} to {recommended:.1f} "
            "to speed convergence to target."
        ),
        "correlation_model": (
            "A discovered correlation shows {variable} impacts {target_variable}. "
            "Adjusting {variable} from {current:.1f} to {recommended:.1f} "
            "should improve {target_variable} tracking."
        ),
        "recipe_constraint": (
            "Recommendation respects recipe limits for {variable}. "
            "Current value {current:.1f} suggests adjustment to {recommended:.1f} "
            "within bounds [{min:.1f}, {max:.1f}]."
        ),
        "operator_pattern": (
            "Historical operator adjustments for similar transitions typically "
            "move {variable} from {current:.1f} to ~{recommended:.1f}. "
            "This suggestion follows that pattern."
        ),
    }

    @staticmethod
    def generate_rationale(
        recommendation: Dict,
        source_tag: str,
        additional_context: Dict = None,
    ) -> str:
        """Generate plain-English rationale for a recommendation.
        
        Args:
            recommendation: Recommendation dict
            source_tag: Source identifier
            additional_context: Optional extra info for templates
            
        Returns:
            Rationale string
        """
        additional_context = additional_context or {}

        template = RationaleGenerator.TEMPLATES.get(
            source_tag,
            "Recommended adjustment to {variable} from {current:.1f} to {recommended:.1f}."
        )

        # Build context dict
        context = {
            "variable": recommendation["variable_name"],
            "current": recommendation["current_value"],
            "recommended": recommendation["recommended_value"],
            "target_variable": additional_context.get("target_variable", "basis weight"),
        }

        # Add limits if available
        if "limits" in additional_context:
            context["min"] = additional_context["limits"]["min"]
            context["max"] = additional_context["limits"]["max"]

        try:
            rationale = template.format(**context)
        except KeyError:
            # Fallback
            rationale = (
                f"Recommend adjusting {recommendation['variable_name']} "
                f"from {recommendation['current_value']:.1f} "
                f"to {recommendation['recommended_value']:.1f}."
            )

        return rationale

    @staticmethod
    def tag_recommendation_source(
        recommendation: Dict,
        risk_probability: float,
        has_discovered_correlation: bool = False,
    ) -> str:
        """Assign source tag based on recommendation origin."""
        if risk_probability > 0.7:
            return "risk_model"
        elif has_discovered_correlation:
            return "correlation_model"
        else:
            return "stabilization_driver"
