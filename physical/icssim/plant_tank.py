"""
IndustryLab — ICSSIM Buffer Storage Tank Dynamics
Simulates tank level mass balance and Torricelli gravity drainage.
"""

import math


class BufferTankPlant:
    def __init__(self, height_m=5.0, cross_area_m2=4.0, max_inflow_lps=25.0, initial_level_m=2.5):
        self.height_m = height_m
        self.cross_area = cross_area_m2
        self.max_inflow = max_inflow_lps / 1000.0 # m^3 / s
        self.level_m = 2.5 if initial_level_m is None else float(initial_level_m)
        self.outflow_coef = 0.008

    def step(self, dt: float, pump_in_cmd: bool, valve_out_cmd: bool) -> dict:
        q_in = self.max_inflow if pump_in_cmd else 0.0
        q_out = self.outflow_coef * math.sqrt(2 * 9.81 * max(0.0, self.level_m)) if valve_out_cmd else 0.0

        dh = ((q_in - q_out) / self.cross_area) * dt
        self.level_m = max(0.0, min(self.height_m, self.level_m + dh))

        level_pct = (self.level_m / self.height_m) * 100.0

        return {
            "level_m": round(self.level_m, 3),
            "level_mm": int(round(self.level_m * 1000)),
            "level_pct": round(level_pct, 1),
            "inflow_lps": round(q_in * 1000.0, 2),
            "outflow_lps": round(q_out * 1000.0, 2)
        }
