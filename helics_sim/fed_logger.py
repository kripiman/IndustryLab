"""
IndustryLab — HELICS Federate: Cascading Event & Domino Effect Logger
Records synchronized physical, control, and electrical metrics into logs/cascading_events.csv.
"""

import sys
import csv
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_ROOT / "logs" / "cascading_events.csv"

logger = logging.getLogger("FedLogger")


class CascadingEventLogger:
    def __init__(self, output_csv: Path = LOG_FILE):
        self.output_csv = Path(output_csv)
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)
        self.writer = None
        self.file_handle = None
        self._init_csv()

    def _init_csv(self):
        self.file_handle = open(self.output_csv, mode="w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file_handle)
        self.writer.writerow([
            "sim_time_s",
            "cooling_temp_c",
            "cooling_flow_lpm",
            "valve_position_pct",
            "pump_running",
            "vibration_rms_mms",
            "grid_power_ok",
            "grid_load_kw",
            "cascading_state"
        ])
        self.file_handle.flush()

    def log_step(self, t: float, temp_c: float, flow_lpm: float, valve_pct: float,
                 pump_ok: bool, vib_mms: float, grid_power: bool, grid_kw: float, status: str):
        if self.writer:
            self.writer.writerow([
                f"{t:.2f}",
                f"{temp_c:.2f}",
                f"{flow_lpm:.1f}",
                f"{valve_pct:.1f}",
                int(pump_ok),
                f"{vib_mms:.2f}",
                int(grid_power),
                f"{grid_kw:.1f}",
                status
            ])
            self.file_handle.flush()

    def close(self):
        if self.file_handle:
            self.file_handle.close()
