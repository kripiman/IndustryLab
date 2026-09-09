"""Unit tests for Red Team Industrial Attack Scripts."""
import time
from plc.modbus_server import ModbusPlcServer
from attacker.attack_recon import scan_target
from attacker.attack_coil_injection import execute_attack
from attacker.attack_setpoint_tamper import execute_setpoint_tamper


def test_recon_scanner_finds_registers():
    port = 15031
    server = ModbusPlcServer(host="127.0.0.1", port=port)
    server.set_holding_register(0, 450)
    server.set_coil(0, True)
    server.start(background=True)
    time.sleep(0.15)

    try:
        findings = scan_target(target_ip="127.0.0.1", port=port, unit_ids=[1])
        assert 1 in findings["coils"]
        assert findings["coils"][1][0] is True
        assert 1 in findings["holding_registers"]
        assert findings["holding_registers"][1][0] == 450
    finally:
        server.stop()


def test_attack_coil_injection_impact():
    port = 15032
    server = ModbusPlcServer(host="127.0.0.1", port=port)
    server.set_coil(0, True) # Initially running pump
    server.set_coil(2, False) # Auto mode
    server.set_holding_register(1, 35) # Valve 35%
    server.start(background=True)
    time.sleep(0.15)

    try:
        success = execute_attack(target_ip="127.0.0.1", port=port, unit_id=1)
        assert success is True

        # Check server state post-attack
        assert server.get_coil(0) is False, "Pump must be stopped post-attack"
        assert server.get_coil(2) is True, "Manual override must be locked"
        assert server.get_holding_register(1) == 0, "Valve must be shut"
    finally:
        server.stop()


def test_attack_setpoint_tamper():
    port = 15033
    server = ModbusPlcServer(host="127.0.0.1", port=port)
    server.set_holding_register(2, 450) # Setpoint 45.0 C
    server.set_holding_register(3, 20)  # Kp = 2.0
    server.start(background=True)
    time.sleep(0.15)

    try:
        success = execute_setpoint_tamper(target_ip="127.0.0.1", port=port, new_sp_c=85.0, new_kp=90)
        assert success is True

        assert server.get_holding_register(2) == 850
        assert server.get_holding_register(3) == 90
    finally:
        server.stop()


def test_attack_dos_flooding_and_latency_measurement():
    from attacker.attack_dos import execute_dos, measure_probe_latency
    port = 15034
    server = ModbusPlcServer(host="127.0.0.1", port=port)
    server.start(background=True)
    time.sleep(0.15)

    try:
        # Check probe latency before DoS
        baseline = measure_probe_latency("127.0.0.1", port)
        assert baseline >= 0.0, "Legitimate probe must succeed on running server"

        # Execute DoS attack
        success = execute_dos("127.0.0.1", port, num_packets=20, delay_s=0.001, verify_latency=True)
        assert success is True
    finally:
        server.stop()

