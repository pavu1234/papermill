"""Correlation discovery endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict
from backend.db import get_db
from backend.db.models import HistorianData
from backend.feature_engineering.correlation import CorrelationEngine
import pandas as pd

router = APIRouter()


class CorrelationItem(BaseModel):
    variable_a: str
    variable_b: str
    correlation_strength: float
    p_value: float
    is_known_control_loop: bool
    impact_statement: str


class CorrelationsResponse(BaseModel):
    event_id: int
    known_loops: List[CorrelationItem]
    new_correlations: List[CorrelationItem]
    status: str = "success"


@router.post("/correlations", response_model=CorrelationsResponse)
async def get_correlations(
    event_id: int,
    db: Session = Depends(get_db),
):
    """Discover correlations in process variables.
    
    Returns:
        List of known control loops and newly discovered correlations
    """
    try:
        # Fetch historian data
        historian_records = db.query(HistorianData).filter(
            HistorianData.event_id == event_id
        ).all()

        if not historian_records:
            return CorrelationsResponse(
                event_id=event_id,
                known_loops=[],
                new_correlations=[],
                status="error",
            )

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
            }
            for r in historian_records
        ])

        # Compute correlations
        corr_engine = CorrelationEngine()
        correlations = corr_engine.compute_pairwise_correlations(df_historian)

        # Separate known vs new
        known_loops = []
        new_correlations = []

        for (var_a, var_b), corr_data in correlations.items():
            item = CorrelationItem(
                variable_a=var_a,
                variable_b=var_b,
                correlation_strength=corr_data["correlation"],
                p_value=corr_data["p_value"],
                is_known_control_loop=corr_data["is_known"],
                impact_statement=corr_data.get("description") or corr_engine._interpret_correlation(
                    var_a, var_b, corr_data["correlation"]
                ),
            )

            if corr_data["is_known"]:
                known_loops.append(item)
            else:
                new_correlations.append(item)

        return CorrelationsResponse(
            event_id=event_id,
            known_loops=known_loops,
            new_correlations=new_correlations,
        )

    except Exception as e:
        return CorrelationsResponse(
            event_id=event_id,
            known_loops=[],
            new_correlations=[],
            status="error",
        )
