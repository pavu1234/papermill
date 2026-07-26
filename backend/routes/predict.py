"""Prediction endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, List
from backend.db import get_db
from backend.db.models import HistorianData, GradeChangeEvent
from backend.models.risk_predictor import DeviationRiskPredictor
from backend.feature_engineering.features import FeatureEngineer
import pandas as pd
import numpy as np

router = APIRouter()

# Global model instance (in production, use proper dependency injection)
_risk_model = DeviationRiskPredictor(model_type="xgboost")
_model_loaded = False


class PredictRiskRequest(BaseModel):
    event_id: int
    current_state: Dict[str, float]
    basis_weight_target: float


class PredictRiskResponse(BaseModel):
    event_id: int
    risk_probability: float
    time_to_breach_sec: Optional[float]
    status: str = "success"
    message: Optional[str] = None


@router.post("/predict-risk", response_model=PredictRiskResponse)
async def predict_risk(
    request: PredictRiskRequest,
    db: Session = Depends(get_db),
):
    """Predict risk of Basis Weight going off-spec.
    
    Returns:
        Risk probability (0-1) and estimated time-to-breach
    """
    try:
        # Fetch historian data for this event
        historian_records = db.query(HistorianData).filter(
            HistorianData.event_id == request.event_id
        ).all()

        if not historian_records:
            raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")

        # Convert to DataFrame
        df_historian = pd.DataFrame([
            {
                "stock_flow": r.stock_flow,
                "filler_flow": r.filler_flow,
                "steam_pressure": r.steam_pressure,
                "machine_speed": r.machine_speed,
                "basis_weight": r.basis_weight,
                "moisture": r.moisture,
                "ash": r.ash,
                "caliper": r.caliper,
                "stock_flow_sp": r.stock_flow_sp,
                "filler_flow_sp": r.filler_flow_sp,
                "steam_pressure_sp": r.steam_pressure_sp,
                "machine_speed_sp": r.machine_speed_sp,
                "basis_weight_sp": r.basis_weight_sp,
                "elapsed_sec": r.elapsed_sec,
                "basis_weight_deviation": r.basis_weight_deviation,
            }
            for r in historian_records
        ])

        # Engineer features
        feature_engineer = FeatureEngineer()
        df_features = feature_engineer.engineer_features(df_historian)

        # Prepare data for prediction (use latest data point)
        try:
            X, _, _ = _risk_model.prepare_training_data(
                df_features,
                request.basis_weight_target,
            )
            # Use last row for prediction
            if len(X) > 0:
                risk_prob = float(_risk_model.predict(X[-1:].reshape(1, -1))[0])
            else:
                risk_prob = 0.0
        except Exception as e:
            # Model not trained yet, return mock prediction
            risk_prob = 0.3

        # Estimate time to breach
        time_to_breach = _risk_model.predict_time_to_breach(
            df_historian,
            request.basis_weight_target,
        )

        return PredictRiskResponse(
            event_id=request.event_id,
            risk_probability=risk_prob,
            time_to_breach_sec=time_to_breach,
        )

    except HTTPException:
        raise
    except Exception as e:
        return PredictRiskResponse(
            event_id=request.event_id,
            risk_probability=0.0,
            time_to_breach_sec=None,
            status="error",
            message=str(e),
        )
