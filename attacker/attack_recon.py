#!/usr/bin/env python3
"""
IndustryLab — OT/ICS Reconnaissance & Modbus/TCP Discovery
Scans target PLC for active Unit IDs, supported Function Codes, and maps memory registers.
"""

import sys
import socket
import argparse
import logging
from pathlib import Path

try:
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        ModbusTcpClient = None

logger = logging.getLogger("ModbusRecon")


def scan_target(target_ip="127.0.0.1", port=502, unit_ids=range(1, 4)):
    print(f"\n[*] Commencing Industrial Modbus/TCP Reconnaissance on {target_ip}:{port}...")

    if ModbusTcpClient is None:
        print("[!] pymodbus is required for live network scanning.")
        return {"status": "ERROR_NO_PYMODBUS"}

    client = ModbusTcpClient(target_ip, port=port, timeout=1.5)
    if not client.connect():
        print(f"[-] Connection refused to {target_ip}:{port}. Host unreachable or port blocked by firewall.")
        return {"status": "CONNECTION_FAILED"}

    print(f"[+] TCP Connection Established to Modbus Endpoint {target_ip}:{port}")
    findings = {"coils": {}, "holding_registers": {}, "discrete_inputs": {}, "input_registers": {}}

    for uid in unit_ids:
        print(f"\n--- Probing Unit ID: {uid} ---")

        # 1. Probe Coils (0..7)
        rc = client.read_coils(0, 8, unit=uid)
        if not rc.isError():
            findings["coils"][uid] = rc.bits[:8]
            print(f"  [+] FC 01 (Read Coils): Coils 0-7 = {rc.bits[:8]}")
        else:
            print(f"  [-] FC 01 (Read Coils): No response or Exception")

        # 2. Probe Holding Registers (0..7)
        rr = client.read_holding_registers(0, 8, unit=uid)
        if not rr.isError():
            findings["holding_registers"][uid] = rr.registers
            print(f"  [+] FC 03 (Read Holding Registers): Regs 0-7 = {rr.registers}")
        else:
            print(f"  [-] FC 03 (Read Holding Registers): No response or Exception")

        # 3. Probe Discrete Inputs (0..7)
        rdi = client.read_discrete_inputs(0, 8, unit=uid)
        if not rdi.isError():
            findings["discrete_inputs"][uid] = rdi.bits[:8]
            print(f"  [+] FC 02 (Read Discrete Inputs): Inputs 0-7 = {rdi.bits[:8]}")

        # 4. Probe Input Registers (0..7)
        rir = client.read_input_registers(0, 8, unit=uid)
        if not rir.isError():
            findings["input_registers"][uid] = rir.registers
            print(f"  [+] FC 04 (Read Input Registers): Regs 0-7 = {rir.registers}")

    client.close()
    print("\n[+] Modbus Reconnaissance Completed.")
    return findings


def main():
    parser = argparse.ArgumentParser(description="Modbus OT Reconnaissance")
    parser.add_argument("--target", default="127.0.0.1", help="Target PLC IP")
    parser.add_argument("--port", type=int, default=502, help="Target PLC Modbus Port")
    args = parser.parse_args()

    scan_target(target_ip=args.target, port=args.port)


if __name__ == "__main__":
    main()
