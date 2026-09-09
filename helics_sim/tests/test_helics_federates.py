"""Unit tests for HELICS co-simulation federates and domino effect cascade."""
from pathlib import Path
from helics_sim.fed_power_grid import FedPowerGrid
from helics_sim.fed_plc import FedPLC
from helics_sim.fed_logger import CascadingEventLogger
from helics_sim.run_co_simulation import run_simulation

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_fed_power_grid_thermal_cascade_trip():
    grid = FedPowerGrid()
    assert grid.breaker_closed is True
    assert grid.power_available is True

    # 1. Normal temperature (45 C) -> Breaker stays closed
    state = grid.evaluate_grid_state(temp_c=45.0, plc_trip_signal=False)
    assert state["power_available"] is True
    assert state["breaker_closed"] is True

    # 2. Critical temperature excursion (96.5 C >= 95.0 C) -> Breaker TRIPS!
    state_tripped = grid.evaluate_grid_state(temp_c=96.5, plc_trip_signal=True)
    assert state_tripped["power_available"] is False
    assert state_tripped["breaker_closed"] is False
    assert state_tripped["trip_reason"] == "CRITICAL_THERMAL_CASCADE_OVERLOAD"


def test_fed_plc_attack_override():
    plc = FedPLC(setpoint_c=45.0)

    # Normal state
    out_norm = plc.execute_logic(temp_c=45.0)
    assert out_norm["pump_cmd"] is True
    assert out_norm["valve_pct"] == 35.0

    # Cyber attack override
    out_attack = plc.execute_logic(temp_c=45.0, cyber_attack_override=True, attack_valve_val=0.0)
    assert out_attack["pump_cmd"] is False, "Pump must be stopped under attack"
    assert out_attack["valve_pct"] == 0.0, "Valve must be shut under attack"
    assert out_attack["emergency_trip"] is False, "No trip at 45 C"

    # Cyber attack override with overtemperature trip (P0-04 / SEC-04)
    out_attack_crit = plc.execute_logic(temp_c=96.0, cyber_attack_override=True, attack_valve_val=0.0)
    assert out_attack_crit["emergency_trip"] is True, "Emergency trip must assert even under attack"


def test_co_simulation_end_to_end_cascade():
    # Run short 8-second simulation with attack injected at t=2s
    res = run_simulation(duration_s=8.0, attack_at_s=2.0, dt=0.5)

    assert res["attack_injected"] is True
    assert res["final_temp_c"] > 45.0

    # Check that cascading_events.csv was created and populated
    log_csv = REPO_ROOT / "logs" / "cascading_events.csv"
    assert log_csv.exists()
    content = log_csv.read_text(encoding="utf-8")
    assert "sim_time_s" in content
    assert "cooling_temp_c" in content
