"""Unit tests for Mining Slurry Conveyor Physical Model."""
from physical.icssim.plant_conveyor import SlurryConveyorPlant


def test_conveyor_speed_and_feed_ramp():
    plant = SlurryConveyorPlant()

    # Step for 10 seconds with conveyor ON at 70%
    for _ in range(20):
        state = plant.step(dt=0.5, conveyor_cmd=True, sag_mill_cmd=True, speed_pct=70.0)

    assert state["belt_speed_mps"] > 2.0
    assert state["feed_rate_tph"] > 700.0
    assert state["motor_current_a"] > 300.0
    assert state["vibration_mms"] < 6.0 # Normal vibration


def test_conveyor_bearing_vibration_escalation_on_lube_loss():
    plant = SlurryConveyorPlant()

    # Run for a few seconds normally
    for _ in range(10):
        plant.step(dt=0.5, conveyor_cmd=True, sag_mill_cmd=True, speed_pct=70.0, lube_loss=False)

    # Trigger lube loss anomaly
    for _ in range(40):
        state = plant.step(dt=0.5, conveyor_cmd=True, sag_mill_cmd=True, speed_pct=70.0, lube_loss=True)

    # Lube pressure must drop and vibration must escalate
    assert state["lube_pressure_bar"] < 2.0
    assert state["vibration_mms"] > 7.5, "Vibration must exceed ISO 10816 alarm threshold under lube loss"
