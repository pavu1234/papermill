import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.db import init_db, SessionLocal
from backend.db.models import GradeChangeEvent, HistorianData, AlarmLog, OperatorAction
from backend.config import RECIPE_LIMITS, BASIS_WEIGHT_TOLERANCE
import random

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)


class SyntheticGradeChangeSimulator:
    """Simulates realistic paper mill grade changes with physics-based dynamics."""

    def __init__(self):
        self.grades = {
            "grade_A": {"basis_weight": 80, "filler_ratio": 0.25, "stock_consistency": 1.0},
            "grade_B": {"basis_weight": 120, "filler_ratio": 0.30, "stock_consistency": 1.1},
            "grade_C": {"basis_weight": 180, "filler_ratio": 0.20, "stock_consistency": 0.9},
            "grade_D": {"basis_weight": 100, "filler_ratio": 0.35, "stock_consistency": 1.2},
        }
        self.known_control_loops = {
            ("stock_flow", "basis_weight"): 0.85,
            ("filler_flow", "basis_weight"): 0.72,
            ("machine_speed", "basis_weight"): -0.60,
            ("steam_pressure", "moisture"): 0.78,
        }

    def generate_event(
        self,
        event_id: int,
        from_grade: str,
        to_grade: str,
        success: bool = True,
        duration_sec: int = 600,
        resolution_sec: int = 5,
    ) -> tuple:
        """Generate a single grade change event with realistic dynamics.
        
        Returns:
            (event_record, historian_records)
        """
        from_spec = self.grades[from_grade]
        to_spec = self.grades[to_grade]

        timestamp_start = datetime.utcnow() - timedelta(days=random.randint(1, 30))
        timestamp_end = timestamp_start + timedelta(seconds=duration_sec)
        times = np.arange(0, duration_sec, resolution_sec)

        # Recipe limits for this grade
        recipe_limits = {
            "stock_flow": {"min": 300, "max": 750},
            "filler_flow": {"min": 30, "max": 120},
            "steam_pressure": {"min": 3.0, "max": 7.0},
            "machine_speed": {"min": 400, "max": 900},
            "basis_weight": {"min": to_spec["basis_weight"] * 0.97, "max": to_spec["basis_weight"] * 1.03},
        }

        # Setpoint ramps (smooth transitions)
        t_ramp = times / times[-1]  # 0 to 1 over duration
        t_ramp_smooth = 0.5 * (1 - np.cos(np.pi * t_ramp))  # Smoother S-curve

        # Starting conditions
        stock_flow_0 = from_spec["basis_weight"] * 6  # kg/min, heuristic
        filler_flow_0 = stock_flow_0 * from_spec["filler_ratio"]
        machine_speed_0 = 600  # m/min baseline
        steam_pressure_0 = 5.0  # bar baseline

        # Target conditions
        stock_flow_target = to_spec["basis_weight"] * 6
        filler_flow_target = stock_flow_target * to_spec["filler_ratio"]
        machine_speed_target = 650 + random.uniform(-50, 100)  # m/min
        steam_pressure_target = 5.5 + random.uniform(-0.5, 0.5)  # bar
        basis_weight_target = to_spec["basis_weight"]

        # Setpoints (what MPC is targeting)
        stock_flow_sp = stock_flow_0 + t_ramp_smooth * (stock_flow_target - stock_flow_0)
        filler_flow_sp = filler_flow_0 + t_ramp_smooth * (filler_flow_target - filler_flow_0)
        machine_speed_sp = machine_speed_0 + t_ramp_smooth * (machine_speed_target - machine_speed_0)
        steam_pressure_sp = steam_pressure_0 + t_ramp_smooth * (steam_pressure_target - steam_pressure_0)
        basis_weight_sp = np.full_like(times, basis_weight_target, dtype=float)

        # Process variables with realistic lag and noise
        # Stock flow follows setpoint with 1st-order lag (time constant ~30s)
        stock_flow = self._apply_lag(stock_flow_sp, tau=30)
        stock_flow += np.random.normal(0, stock_flow * 0.02, len(times))  # ±2% noise

        # Filler flow, more direct response but coupled to stock flow
        filler_flow = self._apply_lag(filler_flow_sp, tau=25)
        filler_flow += stock_flow * 0.001 + np.random.normal(0, filler_flow * 0.03, len(times))

        # Machine speed with slower lag (time constant ~40s)
        machine_speed = self._apply_lag(machine_speed_sp, tau=40)
        machine_speed += np.random.normal(0, machine_speed * 0.01, len(times))  # ±1% noise

        # Steam pressure follows setpoint quickly (tau ~15s)
        steam_pressure = self._apply_lag(steam_pressure_sp, tau=15)
        steam_pressure += np.random.normal(0, 0.1, len(times))

        # Basis weight: complex function of stock flow, filler flow, and machine speed
        # BW ≈ (stock_flow + 0.8*filler_flow) / machine_speed * 100
        # Plus lag (time constant ~60s) and noise
        basis_weight_ideal = (
            (stock_flow + 0.8 * filler_flow) / (machine_speed / 100)
        )
        basis_weight = self._apply_lag(basis_weight_ideal, tau=60)

        # Add measurement drift due to scanner calibration
        measurement_drift = np.sin(times / 150) * (basis_weight_target * 0.01)
        basis_weight += measurement_drift
        basis_weight += np.random.normal(0, basis_weight_target * 0.015, len(times))  # ±1.5% noise

        # Moisture: coupled to steam pressure with lag
        moisture = 8.0 + (steam_pressure - 5.0) * 2.0  # g/m² basis
        moisture = self._apply_lag(moisture, tau=50)
        moisture += np.random.normal(0, 0.3, len(times))

        # Ash: mostly constant, slight coupling to filler
        ash = 15.0 + (filler_flow / filler_flow_0 - 1) * 2.0
        ash += np.random.normal(0, 0.5, len(times))

        # Caliper: follows basis weight and filler ratio
        caliper = (basis_weight / 100) * (1 + ash / 100) * 0.15
        caliper += np.random.normal(0, 0.01, len(times))

        # Calculate basis weight deviation
        basis_weight_deviation = (basis_weight - basis_weight_target) / basis_weight_target
        is_off_spec = np.abs(basis_weight_deviation) > BASIS_WEIGHT_TOLERANCE

        # Determine outcome
        max_deviation = np.max(np.abs(basis_weight_deviation))
        if not success:
            # Force off-spec by adding step disturbance
            disturbance_start = int(len(times) * random.uniform(0.3, 0.6))
            basis_weight[disturbance_start:] += basis_weight_target * random.choice([-0.04, 0.04])
            basis_weight_deviation = (basis_weight - basis_weight_target) / basis_weight_target
            is_off_spec = np.abs(basis_weight_deviation) > BASIS_WEIGHT_TOLERANCE
            max_deviation = np.max(np.abs(basis_weight_deviation))

        # Time to stabilize: when basis weight stays within ±1.5% for 60s
        stable_window = 60 // resolution_sec
        time_to_stabilize = None
        for i in range(len(times) - stable_window):
            if np.all(np.abs(basis_weight_deviation[i : i + stable_window]) < 0.015):
                time_to_stabilize = times[i]
                break

        outcome_label = "off_spec" if np.any(is_off_spec) else "success"

        # Create event record
        event = GradeChangeEvent(
            event_id=event_id,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            from_grade=from_grade,
            to_grade=to_grade,
            recipe_target_basis_weight=basis_weight_target,
            recipe_limits=recipe_limits,
            outcome_label=outcome_label,
            time_to_stabilize_sec=time_to_stabilize,
            max_deviation=max_deviation,
        )

        # Create historian records
        historian_records = []
        for i, t in enumerate(times):
            record = HistorianData(
                event_id=event_id,
                timestamp=timestamp_start + timedelta(seconds=float(t)),
                elapsed_sec=float(t),
                stock_flow=float(stock_flow[i]),
                filler_flow=float(filler_flow[i]),
                steam_pressure=float(steam_pressure[i]),
                machine_speed=float(machine_speed[i]),
                basis_weight=float(basis_weight[i]),
                moisture=float(moisture[i]),
                ash=float(ash[i]),
                caliper=float(caliper[i]),
                stock_flow_sp=float(stock_flow_sp[i]),
                filler_flow_sp=float(filler_flow_sp[i]),
                steam_pressure_sp=float(steam_pressure_sp[i]),
                machine_speed_sp=float(machine_speed_sp[i]),
                basis_weight_sp=float(basis_weight_target),
                basis_weight_deviation=float(basis_weight_deviation[i]),
                is_off_spec=bool(is_off_spec[i]),
            )
            historian_records.append(record)

        return event, historian_records

    def _apply_lag(self, setpoint: np.ndarray, tau: float, resolution: float = 5.0) -> np.ndarray:
        """Apply 1st-order lag to a setpoint trajectory.
        
        dx/dt = (u - x) / tau
        Discrete: x[i+1] = x[i] + (u[i] - x[i]) * (dt/tau)
        """
        dt = resolution
        x = np.zeros_like(setpoint)
        x[0] = setpoint[0]
        for i in range(len(setpoint) - 1):
            x[i + 1] = x[i] + (setpoint[i] - x[i]) * (dt / tau)
        return x


def generate_synthetic_data(num_events: int = 200, db_session: Session = None) -> pd.DataFrame:
    """Generate synthetic dataset and store in database.
    
    Args:
        num_events: Number of grade change events to generate
        db_session: SQLAlchemy session; if None, creates local session
        
    Returns:
        DataFrame summary of generated events
    """
    init_db()

    if db_session is None:
        db_session = SessionLocal()

    simulator = SyntheticGradeChangeSimulator()
    grade_list = list(simulator.grades.keys())
    event_summaries = []

    print(f"Generating {num_events} synthetic grade-change events...")

    for event_id in range(1, num_events + 1):
        # Random grade transition
        from_grade = random.choice(grade_list)
        to_grade = random.choice([g for g in grade_list if g != from_grade])

        # 80% success, 20% off-spec
        success = random.random() > 0.2

        # Duration varies: 300-900 seconds
        duration_sec = random.randint(300, 900)

        # Generate event
        event, historian_records = simulator.generate_event(
            event_id=event_id,
            from_grade=from_grade,
            to_grade=to_grade,
            success=success,
            duration_sec=duration_sec,
        )

        # Store event
        db_session.add(event)
        db_session.flush()  # Get event_id

        # Store historian data
        for record in historian_records:
            db_session.add(record)

        # Occasionally add operator actions (20% of events)
        if random.random() < 0.2:
            action = OperatorAction(
                event_id=event_id,
                timestamp=event.timestamp_start + timedelta(seconds=random.randint(100, 300)),
                variable_changed=random.choice(["steam_pressure", "machine_speed"]),
                old_value=random.uniform(4.0, 6.0),
                new_value=random.uniform(4.0, 6.0),
                operator_id=f"OP_{random.randint(1001, 1005)}",
            )
            db_session.add(action)

        # Occasionally add alarms (15% of events)
        if random.random() < 0.15:
            alarm = AlarmLog(
                event_id=event_id,
                timestamp=event.timestamp_start + timedelta(seconds=random.randint(50, 200)),
                alarm_code=random.choice(["ALM_001", "ALM_002", "ALM_003"]),
                severity=random.choice(["warning", "critical"]),
                variable=random.choice(["basis_weight", "moisture", "stock_flow"]),
                message="Process variable deviation detected",
            )
            db_session.add(alarm)

        event_summaries.append({
            "event_id": event_id,
            "from_grade": from_grade,
            "to_grade": to_grade,
            "outcome": event.outcome_label,
            "max_deviation": event.max_deviation,
            "time_to_stabilize": event.time_to_stabilize_sec,
            "duration_sec": duration_sec,
        })

        if event_id % 50 == 0:
            print(f"  Generated {event_id}/{num_events} events...")
            db_session.commit()

    db_session.commit()
    db_session.close()

    print(f"\n✓ Generated {num_events} events")
    df_summary = pd.DataFrame(event_summaries)
    print(f"\nSummary:")
    print(df_summary["outcome"].value_counts())
    print(f"\nAverage time to stabilize: {df_summary['time_to_stabilize'].mean():.1f}s")
    print(f"Average max deviation: {df_summary['max_deviation'].mean():.4f} ({df_summary['max_deviation'].mean()*100:.2f}%)")

    return df_summary


if __name__ == "__main__":
    generate_synthetic_data(num_events=200)
