"""Unit tests for Thermal Heat Exchanger Physical Model."""
from physical.icssim.plant_cooling import ThermalCoolingPlant


def test_thermal_cooling_equilibrium():
    plant = ThermalCoolingPlant(ambient_temp_c=25.0, initial_temp_c=45.0)

    # Step for 20 seconds with pump ON and valve at 35%
    for _ in range(40):
        state = plant.step(dt=0.5, pump_running=True, valve_pct=35.0)

    # Temperature should remain controlled in acceptable range
    assert 40.0 <= state["temp_c"] <= 50.0
    assert state["flow_lpm"] > 50.0
    assert state["pressure_kpa"] > 200.0


def test_thermal_cooling_loss_of_cooling_runaway():
    plant = ThermalCoolingPlant(ambient_temp_c=25.0, initial_temp_c=45.0)

    # Cut off cooling completely (pump OFF, valve 0%)
    initial_temp = plant.temp_c
    for _ in range(60): # 30 seconds
        state = plant.step(dt=0.5, pump_running=False, valve_pct=0.0)

    # Temperature MUST rise significantly
    assert state["temp_c"] > initial_temp + 5.0
    assert state["flow_lpm"] == 0.0
