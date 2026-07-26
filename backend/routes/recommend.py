"""Recommendation endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, List
from backend.db import get_db
from backend.recommendations.engine import RecommendationEngine
from backend.recommendations.rationale import RationaleGenerator

router = APIRouter()


class RecommendationRequest(BaseModel):
    event_id: int
    current_state: Dict[str, float]
    target_state: Dict[str, float]
    risk_probability: float
    risk_model_feature_importance: Optional[Dict[str, float]] = None
    stabilization_drivers: Optional[Dict[str, float]] = None


class Recommendation(BaseModel):
    variable_name: str
    current_value: float
    recommended_value: float
    expected_effect: str
    source_tag: str
    rationale: str
    confidence: float


class RecommendSetpointsResponse(BaseModel):
    event_id: int
    recommendations: List[Recommendation]
    status: str = "success"


@router.post("/recommend-setpoints", response_model=RecommendSetpointsResponse)
async def recommend_setpoints(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """Generate setpoint recommendations.
    
    Returns:
        List of recommended adjustments with source tags and rationale
    """
    try:
        engine = RecommendationEngine()
        rationale_gen = RationaleGenerator()

        # Generate raw recommendations
        raw_recommendations = engine.generate_recommendations(
            event_id=request.event_id,
            current_state=request.current_state,
            target_state=request.target_state,
            risk_probability=request.risk_probability,
            risk_model_feature_importance=request.risk_model_feature_importance or {},
            stabilization_drivers=request.stabilization_drivers or {},
        )

        # Generate rationale for each
        recommendations = []
        for rec in raw_recommendations:
            source_tag = rec["source_tag"]
            rationale = rationale_gen.generate_rationale(
                rec,
                source_tag,
                {"target_variable": "basis_weight"},
            )

            recommendations.append(Recommendation(
                variable_name=rec["variable_name"],
                current_value=rec["current_value"],
                recommended_value=rec["recommended_value"],
                expected_effect=rec["expected_effect"],
                source_tag=source_tag,
                rationale=rationale,
                confidence=rec["confidence"],
            ))

        return RecommendSetpointsResponse(
            event_id=request.event_id,
            recommendations=recommendations,
        )

    except Exception as e:
        return RecommendSetpointsResponse(
            event_id=request.event_id,
            recommendations=[],
            status="error",
        )
