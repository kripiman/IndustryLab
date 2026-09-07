"""Tests for Modbus Deep Packet Inspection (DPI) Proxy."""
from network.modbus_dpi_filter import (
    parse_modbus_pdu,
    make_modbus_exception,
    ModbusDpiProxy
)


def test_parse_modbus_pdu():
    # Construct Modbus frame: TxID=1, Proto=0, Len=6, Unit=1, FC=3 (Read Holding Registers), Addr=0, Count=2
    # Bytes: 00 01 | 00 00 | 00 06 | 01 | 03 00 00 00 02
    frame = bytes([0x00, 0x01, 0x00, 0x00, 0x00, 0x06, 0x01, 0x03, 0x00, 0x00, 0x00, 0x02])
    pdu = parse_modbus_pdu(frame)
    assert pdu is not None
    assert pdu["tx_id"] == 1
    assert pdu["proto_id"] == 0
    assert pdu["unit_id"] == 1
    assert pdu["function_code"] == 3
    assert pdu["fc_name"] == "Read Holding Registers"


def test_modbus_exception_generation():
    # For TxID=12, Unit=1, FC=5 (Write Coil), Exception=0x01
    resp = make_modbus_exception(tx_id=12, unit_id=1, fc=5, exception_code=0x01)
    assert len(resp) == 9
    assert resp[0:2] == (12).to_bytes(2, 'big')
    assert resp[6] == 1  # Unit ID
    assert resp[7] == (5 | 0x80)  # Error code: 0x85
    assert resp[8] == 1  # Exception Code: 0x01 (Illegal Function)


def test_dpi_proxy_authorization_logic():
    proxy = ModbusDpiProxy(authorized_write_ips=["10.10.3.50", "127.0.0.1"])

    # 1. Read Holding Registers (FC 03) from unauthorized IP should be allowed
    read_req = bytes([0x00, 0x02, 0x00, 0x00, 0x00, 0x06, 0x01, 0x03, 0x00, 0x00, 0x00, 0x05])
    allow_read, _ = proxy.inspect_request("10.10.99.10", read_req)
    assert allow_read is True, "Read requests must pass inspection"

    # 2. Write Single Coil (FC 05) from unauthorized IP should be BLOCKED
    # Payload: TxID=3, Proto=0, Len=6, Unit=1, FC=5, Coil=0, Val=0xFF00
    write_req = bytes([0x00, 0x03, 0x00, 0x00, 0x00, 0x06, 0x01, 0x05, 0x00, 0x00, 0xFF, 0x00])
    allow_write_unauth, exc_resp = proxy.inspect_request("10.10.99.10", write_req)
    assert allow_write_unauth is False, "Unauthorized write must be rejected by DPI"
    assert exc_resp is not None
    assert exc_resp[7] == (5 | 0x80), "Response must be Modbus exception"
    assert exc_resp[8] == 0x01

    # 3. Write Single Coil (FC 05) from authorized EWS IP (10.10.3.50) should be PERMITTED
    allow_write_auth, exc_auth = proxy.inspect_request("10.10.3.50", write_req)
    assert allow_write_auth is True, "Authorized write from EWS must pass inspection"
    assert exc_auth is None
