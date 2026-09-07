"""Unit tests for OpenPLC IEC 61131-3 logic scan cycle."""
from plc.openplc_runtime import CoolingControlLogic, ConveyorControlLogic
from plc.modbus_server import ModbusPlcServer


def test_cooling_control_scan_proportional_and_trip():
    modbus = ModbusPlcServer(host="127.0.0.1", port=15023)
    logic = CoolingControlLogic(modbus)

    # 1. Test setpoint at 45.0 C (450), Process Temp at 45.0 C (450) -> Error = 0
    modbus.set_holding_register(0, 450)
    modbus.set_holding_register(2, 450)
    modbus.set_holding_register(3, 20) # Kp = 2.0
    logic.scan_cycle()

    # Valve should remain at baseline (35%)
    assert modbus.get_holding_register(1) == 35
    assert modbus.get_coil(3) is False # Trip inactive

    # 2. Process Temp rises to 60.0 C (600) -> Error = 150 -> 150 * 20 / 100 = 30 -> Valve = 35 + 30 = 65%
    modbus.set_holding_register(0, 600)
    logic.scan_cycle()
    assert modbus.get_holding_register(1) == 65
    assert modbus.get_coil(3) is False

    # 3. Emergency Over-temperature condition: Temp reaches 96.0 C (960 >= 950)
    modbus.set_holding_register(0, 960)
    logic.scan_cycle()
    assert modbus.get_coil(3) is True, "TRIP_INTERLOCK_ACT must be True"
    assert modbus.get_holding_register(1) == 100, "Valve must be forced to 100% full open"
    assert modbus.get_holding_register(5) == 0x0003, "HighTemp + CritTrip alarm set"

    # 4. Operator Reset test: pulse reset while still too hot (>70 C) -> should NOT reset
    modbus.set_coil(1, True)
    modbus.set_holding_register(0, 800)
    logic.scan_cycle()
    assert modbus.get_coil(3) is True, "Trip must remain latched if temp > 70 C"

    # 5. Temperature safely cools to 50.0 C (500) and reset pulsed -> Trip cleared
    modbus.set_holding_register(0, 500)
    modbus.set_coil(1, True)
    logic.scan_cycle()
    assert modbus.get_coil(3) is False, "Trip should clear upon reset below 70 C"


def test_conveyor_control_scan_and_interlocks():
    modbus = ModbusPlcServer(host="127.0.0.1", port=15024)
    logic = ConveyorControlLogic(modbus)

    # 1. Normal operation: Belt running at 80% speed
    modbus.set_holding_register(0, 80)
    modbus.set_coil(0, True) # Conveyor ON
    logic.scan_cycle()

    # Feed rate = (80 * 1200) / 100 = 960 TPH
    assert modbus.get_holding_register(1) == 960
    assert modbus.get_coil(2) is True # Chute spray active

    # 2. Severe Vibration Trip: Vibration jumps to 12.0 mm/s (120 >= 110)
    modbus.set_holding_register(2, 120)
    logic.scan_cycle()
    assert modbus.get_coil(0) is False, "Conveyor must trip on high vibration"
    assert modbus.get_coil(1) is False, "SAG mill must trip on high vibration"
    assert modbus.get_holding_register(1) == 0, "Feed rate must drop to 0"
    assert modbus.get_holding_register(5) == 0x0002, "Vibration trip alarm"

    # 3. Interlock bypass engaged: Conveyor can run despite vibration
    modbus.set_coil(3, True) # Interlock bypass = 1
    modbus.set_coil(0, True)
    logic.scan_cycle()
    assert modbus.get_coil(0) is True, "Bypass permits running despite high vibration"
