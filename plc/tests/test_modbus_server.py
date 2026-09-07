"""Unit tests for Modbus/TCP Slave Server."""
import time
from plc.modbus_server import ModbusPlcServer

try:
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    from pymodbus.client import ModbusTcpClient


def test_modbus_plc_server_datastore_in_memory():
    server = ModbusPlcServer(host="127.0.0.1", port=15021)

    # Test Coils
    assert server.get_coil(0) is False
    server.set_coil(0, True)
    assert server.get_coil(0) is True

    # Test Holding Registers
    assert server.get_holding_register(0) == 0
    server.set_holding_register(0, 450)
    assert server.get_holding_register(0) == 450

    # Test Discrete Inputs
    server.set_discrete_input(1, True)
    assert server.get_discrete_input(1) is True

    # Test Input Registers
    server.set_input_register(2, 1024)
    assert server.get_input_register(2) == 1024


def test_modbus_plc_server_network_client():
    test_port = 15022
    server = ModbusPlcServer(host="127.0.0.1", port=test_port)
    server.set_holding_register(0, 520)
    server.set_coil(1, True)

    server.start(background=True)
    time.sleep(0.2)

    try:
        client = ModbusTcpClient("127.0.0.1", port=test_port)
        connected = client.connect()
        assert connected is True, "Modbus client must connect successfully"

        # Read Holding Register 0
        rr = client.read_holding_registers(0, 1, unit=1)
        assert not rr.isError()
        assert rr.registers[0] == 520

        # Read Coil 1
        rc = client.read_coils(1, 1, unit=1)
        assert not rc.isError()
        assert rc.bits[0] is True

        # Write Holding Register 0
        client.write_register(0, 750, unit=1)
        assert server.get_holding_register(0) == 750

        client.close()
    finally:
        server.stop()
