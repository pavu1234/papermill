"""Feedback logging endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.db import get_db
from backend.db.models import RecommendationFeedback, Recommendation
from datetime import datetime

router = APIRouter()


class FeedbackRequest(BaseModel):
    recommendation_id: int
    operator_id: str
    action: str  # 'accepted' or 'rejected'
    outcome_status: Optional[str] = None  # 'success' | 'failed' | 'pending'
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    feedback_id: int
    recommendation_id: int
    status: str = "success"


class FeedbackAnalyticsResponse(BaseModel):
    total_recommendations: int
    accepted_count: int
    rejected_count: int
    acceptance_rate: float
    avg_confidence_accepted: float
    avg_confidence_rejected: float


@router.post("/feedback", response_model=FeedbackResponse)
async def log_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
):
    """Log operator feedback on a recommendation."""
    try:
        # Verify recommendation exists
        recommendation = db.query(Recommendation).filter(
            Recommendation.id == request.recommendation_id
        ).first()

        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        # Create feedback record
        feedback = RecommendationFeedback(
            recommendation_id=request.recommendation_id,
            timestamp_feedback=datetime.utcnow(),
            operator_id=request.operator_id,
            action=request.action,
            outcome_status=request.outcome_status,
            notes=request.notes,
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return FeedbackResponse(
            feedback_id=feedback.id,
            recommendation_id=request.recommendation_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback-analytics", response_model=FeedbackAnalyticsResponse)
async def get_feedback_analytics(
    db: Session = Depends(get_db),
):
    """Get historical feedback analytics."""
    try:
        # Get all feedback
        all_feedback = db.query(RecommendationFeedback).all()
        if not all_feedback:
            return FeedbackAnalyticsResponse(
                total_recommendations=0,
                accepted_count=0,
                rejected_count=0,
                acceptance_rate=0.0,
                avg_confidence_accepted=0.0,
                avg_confidence_rejected=0.0,
            )

        # Count by action
        accepted = [f for f in all_feedback if f.action == "accepted"]
        rejected = [f for f in all_feedback if f.action == "rejected"]

        acceptance_rate = len(accepted) / len(all_feedback) if all_feedback else 0.0

        # Get average confidence
        accepted_recommendations = db.query(Recommendation).filter(
            Recommendation.id.in_([f.recommendation_id for f in accepted])
        ).all()
        rejected_recommendations = db.query(Recommendation).filter(
            Recommendation.id.in_([f.recommendation_id for f in rejected])
        ).all()

        avg_conf_accepted = (
            sum(r.confidence for r in accepted_recommendations) / len(accepted_recommendations)
            if accepted_recommendations else 0.0
        )
        avg_conf_rejected = (
            sum(r.confidence for r in rejected_recommendations) / len(rejected_recommendations)
            if rejected_recommendations else 0.0
        )

        return FeedbackAnalyticsResponse(
            total_recommendations=len(all_feedback),
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            acceptance_rate=acceptance_rate,
            avg_confidence_accepted=avg_conf_accepted,
            avg_confidence_rejected=avg_conf_rejected,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
