from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.db import Base


class GradeChangeEvent(Base):
    """Historical grade change event."""
    __tablename__ = "grade_change_events"

    event_id = Column(Integer, primary_key=True, index=True)
    timestamp_start = Column(DateTime, default=datetime.utcnow, index=True)
    timestamp_end = Column(DateTime, nullable=True)
    from_grade = Column(String, index=True)
    to_grade = Column(String, index=True)
    recipe_target_basis_weight = Column(Float)
    recipe_limits = Column(JSON)  # JSON dict of min/max per variable
    outcome_label = Column(String)  # 'success' or 'off_spec'
    time_to_stabilize_sec = Column(Float, nullable=True)
    max_deviation = Column(Float, nullable=True)  # Max % deviation during event

    # Relationships
    historian_data = relationship("HistorianData", back_populates="event")
    operator_actions = relationship("OperatorAction", back_populates="event")
    alarms = relationship("AlarmLog", back_populates="event")


class HistorianData(Base):
    """Time-series process data (~1s or 5s resolution)."""
    __tablename__ = "historian_data"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("grade_change_events.event_id"), index=True)
    timestamp = Column(DateTime, index=True)
    elapsed_sec = Column(Float)  # Seconds since event start

    # Process variables
    stock_flow = Column(Float)  # kg/min
    filler_flow = Column(Float)  # kg/min
    steam_pressure = Column(Float)  # bar
    machine_speed = Column(Float)  # m/min
    basis_weight = Column(Float)  # g/m²
    moisture = Column(Float)  # %
    ash = Column(Float)  # %
    caliper = Column(Float)  # mm

    # Setpoints (target values)
    stock_flow_sp = Column(Float)
    filler_flow_sp = Column(Float)
    steam_pressure_sp = Column(Float)
    machine_speed_sp = Column(Float)
    basis_weight_sp = Column(Float)

    # Calculated fields
    basis_weight_deviation = Column(Float)  # % deviation from setpoint
    is_off_spec = Column(Boolean)  # True if deviation > 2.5%

    # Relationships
    event = relationship("GradeChangeEvent", back_populates="historian_data")


class OperatorAction(Base):
    """Operator manual adjustment log."""
    __tablename__ = "operator_actions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("grade_change_events.event_id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    variable_changed = Column(String)  # e.g., 'steam_pressure'
    old_value = Column(Float)
    new_value = Column(Float)
    operator_id = Column(String)

    # Relationships
    event = relationship("GradeChangeEvent", back_populates="operator_actions")


class AlarmLog(Base):
    """Alarm and diagnostic events."""
    __tablename__ = "alarm_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("grade_change_events.event_id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    alarm_code = Column(String)
    severity = Column(String)  # 'info', 'warning', 'critical'
    variable = Column(String)
    message = Column(String)

    # Relationships
    event = relationship("GradeChangeEvent", back_populates="alarms")


class PredictionResult(Base):
    """Stored prediction results for audit trail."""
    __tablename__ = "prediction_results"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    risk_probability = Column(Float)  # 0-1
    time_to_breach_sec = Column(Float, nullable=True)
    stabilization_time_estimate = Column(Float, nullable=True)
    model_version = Column(String)


class Recommendation(Base):
    """Generated recommendations with feedback."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, index=True)
    timestamp_created = Column(DateTime, default=datetime.utcnow)
    variable_name = Column(String)
    recommended_value = Column(Float)
    current_value = Column(Float)
    expected_effect = Column(String)  # Plain text description
    source_tag = Column(String)  # 'historical_data' | 'recipe_constraint' | 'correlation_model' | 'operator_pattern'
    rationale = Column(String)  # Natural language explanation
    confidence = Column(Float)  # 0-1


class RecommendationFeedback(Base):
    """Operator feedback on recommendations."""
    __tablename__ = "recommendation_feedback"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), index=True)
    timestamp_feedback = Column(DateTime, default=datetime.utcnow)
    operator_id = Column(String)
    action = Column(String)  # 'accepted' or 'rejected'
    outcome_status = Column(String, nullable=True)  # 'success' | 'failed' | 'pending'
    notes = Column(String, nullable=True)


class DiscoveredCorrelation(Base):
    """Discovered variable correlations."""
    __tablename__ = "discovered_correlations"

    id = Column(Integer, primary_key=True, index=True)
    variable_a = Column(String, index=True)
    variable_b = Column(String, index=True)
    correlation_strength = Column(Float)  # -1 to 1
    p_value = Column(Float)  # Statistical significance
    is_known_control_loop = Column(Boolean)  # True if documented loop
    impact_statement = Column(String)  # Plain English description
    discovered_at = Column(DateTime, default=datetime.utcnow)
    num_events_supporting = Column(Integer)  # How many events show this correlation
