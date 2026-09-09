"""Unit tests for Buffer Tank Physical Model."""
from physical.icssim.plant_tank import BufferTankPlant


def test_tank_fill_and_drain():
    tank = BufferTankPlant(height_m=5.0, initial_level_m=2.0)
    initial_level = tank.level_m
    assert initial_level == 2.0

    # Fill tank (pump ON, discharge valve closed)
    for _ in range(20):
        state = tank.step(dt=0.5, pump_in_cmd=True, valve_out_cmd=False)

    assert state["level_m"] > initial_level
    assert state["inflow_lps"] > 0.0
    assert state["outflow_lps"] == 0.0

    # Drain tank (pump OFF, valve open)
    filled_level = state["level_m"]
    for _ in range(20):
        state = tank.step(dt=0.5, pump_in_cmd=False, valve_out_cmd=True)

    assert state["level_m"] < filled_level
    assert state["outflow_lps"] > 0.0


def test_hil_modbus_bridge_tank_integration():
    from physical.bridge_modbus import HilModbusBridge
    bridge = HilModbusBridge(dt=0.5)
    # Step cycle without network connections (offline mode)
    cycle_res = bridge.step_cycle()
    assert "cooling" in cycle_res
    assert "conveyor" in cycle_res
    assert "tank" in cycle_res
    assert "level_m" in cycle_res["tank"]
    assert cycle_res["tank"]["level_m"] > 0.0

