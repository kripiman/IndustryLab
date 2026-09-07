#!/usr/bin/env python3
"""
IndustryLab — Industrial SCADA Historian & Telemetry Service
Continuously polls OT PLCs via Modbus/TCP, stores time-series telemetry,
implements Loss-of-View watchdog monitoring, and exposes an airgapped JSON REST API.
"""

import sys
import json
import time
import socket
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        ModbusTcpClient = None

logger = logging.getLogger("SCADAHistorian")


class HistorianStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.latest_telemetry = {
            "cooling": {
                "temp_c": 45.0,
                "flow_lpm": 120.0,
                "valve_pct": 35,
                "pump_run": True,
                "online": True,
                "last_seen": time.time()
            },
            "conveyor": {
                "belt_speed_pct": 70,
                "feed_rate_tph": 840,
                "vibration_mms": 3.2,
                "lube_pressure_bar": 3.5,
                "motor_current_a": 380,
                "online": True,
                "last_seen": time.time()
            }
        }
        self.alarms = []
        self.poll_failures = {"cooling": 0, "conveyor": 0}

    def update_cooling(self, temp_c, flow_lpm, valve_pct, pump_run):
        with self.lock:
            self.latest_telemetry["cooling"] = {
                "temp_c": temp_c,
                "flow_lpm": flow_lpm,
                "valve_pct": valve_pct,
                "pump_run": pump_run,
                "online": True,
                "last_seen": time.time()
            }
            self.poll_failures["cooling"] = 0

            # Alarms evaluation
            if temp_c >= 95.0:
                self._add_alarm("CRITICAL", "COOLING_EMERGENCY_TRIP", f"Temperature exceeded 95.0 C ({temp_c:.1f} C)")
            elif temp_c >= 85.0:
                self._add_alarm("WARNING", "COOLING_HIGH_TEMP", f"Temperature high ({temp_c:.1f} C)")

    def update_conveyor(self, speed_pct, feed_tph, vib_mms, lube_bar, current_a):
        with self.lock:
            self.latest_telemetry["conveyor"] = {
                "belt_speed_pct": speed_pct,
                "feed_rate_tph": feed_tph,
                "vibration_mms": vib_mms,
                "lube_pressure_bar": lube_bar,
                "motor_current_a": current_a,
                "online": True,
                "last_seen": time.time()
            }
            self.poll_failures["conveyor"] = 0

            if vib_mms >= 11.0:
                self._add_alarm("CRITICAL", "CONVEYOR_VIBRATION_TRIP", f"Severe bearing vibration ({vib_mms:.1f} mm/s)")
            elif vib_mms >= 7.5:
                self._add_alarm("WARNING", "CONVEYOR_HIGH_VIBRATION", f"Vibration above ISO 10816 threshold ({vib_mms:.1f} mm/s)")

    def record_failure(self, plc_name: str):
        with self.lock:
            self.poll_failures[plc_name] = self.poll_failures.get(plc_name, 0) + 1
            if self.poll_failures[plc_name] >= 3:
                self.latest_telemetry[plc_name]["online"] = False
                self._add_alarm("CRITICAL", "LOSS_OF_VIEW", f"PLC {plc_name.upper()} stopped responding to Modbus polls!")

    def _add_alarm(self, severity: str, code: str, msg: str):
        alarm_entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "severity": severity,
            "code": code,
            "message": msg
        }
        # Avoid duplicate consecutive alarms
        if not self.alarms or self.alarms[-1]["code"] != code:
            self.alarms.append(alarm_entry)
            logger.warning(f"[ALARM] [{severity}] {code}: {msg}")
        if len(self.alarms) > 100:
            self.alarms.pop(0)

    def get_snapshot(self) -> dict:
        with self.lock:
            return {
                "telemetry": dict(self.latest_telemetry),
                "alarms": list(self.alarms),
                "server_time": time.time()
            }


STORE = HistorianStore()


class HistorianRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress noisy stdout access logs

    def do_GET(self):
        if self.path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = STORE.get_snapshot()["telemetry"]
            self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

        elif self.path == "/api/alarms":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = STORE.get_snapshot()["alarms"]
            self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

        elif self.path == "/api/snapshot" or self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = STORE.get_snapshot()
            self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()


class ScadaHistorian:
    def __init__(self, cooling_host="127.0.0.1", cooling_port=502,
                 conveyor_host="127.0.0.1", conveyor_port=502,
                 api_host="0.0.0.0", api_port=8080):
        self.cooling_host = cooling_host
        self.cooling_port = cooling_port
        self.conveyor_host = conveyor_host
        self.conveyor_port = conveyor_port
        self.api_host = api_host
        self.api_port = api_port
        self.running = False
        self.httpd = None
        self.poll_thread = None

    def poll_cycle(self):
        if ModbusTcpClient is None:
            return

        # Poll Cooling PLC
        try:
            c_client = ModbusTcpClient(self.cooling_host, port=self.cooling_port, timeout=1.0)
            if c_client.connect():
                rr = c_client.read_holding_registers(0, 5, unit=1)
                rc = c_client.read_coils(0, 1, unit=1)
                if not rr.isError() and not rc.isError():
                    temp = rr.registers[0] / 10.0
                    valve = rr.registers[1]
                    flow = rr.registers[4] if len(rr.registers) > 4 else 100.0
                    pump = bool(rc.bits[0])
                    STORE.update_cooling(temp, flow, valve, pump)
                else:
                    STORE.record_failure("cooling")
                c_client.close()
            else:
                STORE.record_failure("cooling")
        except Exception:
            STORE.record_failure("cooling")

        # Poll Conveyor PLC
        try:
            conv_client = ModbusTcpClient(self.conveyor_host, port=self.conveyor_port, timeout=1.0)
            if conv_client.connect():
                rr = conv_client.read_holding_registers(0, 5, unit=1)
                if not rr.isError():
                    speed = rr.registers[0]
                    feed = rr.registers[1]
                    vib = rr.registers[2] / 10.0
                    lube = rr.registers[3] / 10.0
                    current_a = rr.registers[4]
                    STORE.update_conveyor(speed, feed, vib, lube, current_a)
                else:
                    STORE.record_failure("conveyor")
                conv_client.close()
            else:
                STORE.record_failure("conveyor")
        except Exception:
            STORE.record_failure("conveyor")

    def _polling_worker(self):
        logger.info(f"SCADA Modbus Polling worker started (Cooling: {self.cooling_host}:{self.cooling_port}, Conveyor: {self.conveyor_host}:{self.conveyor_port})")
        while self.running:
            self.poll_cycle()
            time.sleep(1.0)

    def start(self, background: bool = False):
        self.running = True
        self.poll_thread = threading.Thread(target=self._polling_worker, daemon=True)
        self.poll_thread.start()

        self.httpd = HTTPServer((self.api_host, self.api_port), HistorianRequestHandler)
        logger.info(f"SCADA Historian REST API listening on http://{self.api_host}:{self.api_port}/api/snapshot")

        if background:
            server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            server_thread.start()
        else:
            try:
                self.httpd.serve_forever()
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        self.running = False
        if self.httpd:
            self.httpd.shutdown()
        logger.info("SCADA Historian stopped.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SCADA Historian Service")
    parser.add_argument("--cooling-host", default="127.0.0.1")
    parser.add_argument("--cooling-port", type=int, default=502)
    parser.add_argument("--conveyor-host", default="127.0.0.1")
    parser.add_argument("--conveyor-port", type=int, default=502)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    historian = ScadaHistorian(
        cooling_host=args.cooling_host,
        cooling_port=args.cooling_port,
        conveyor_host=args.conveyor_host,
        conveyor_port=args.conveyor_port,
        api_host=args.host,
        api_port=args.port
    )
    historian.start(background=False)


if __name__ == "__main__":
    main()
