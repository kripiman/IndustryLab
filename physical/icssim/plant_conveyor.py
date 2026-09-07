"""
IndustryLab — ICSSIM Mining Slurry Conveyor & SAG Mill Physical Model
Simulates belt speed, ore feed dynamics, motor current, and trunnion bearing vibration.
"""

import random


class SlurryConveyorPlant:
    def __init__(self, nominal_speed_mps=3.5, max_tonnage_tph=1200.0):
        self.nominal_speed_mps = nominal_speed_mps
        self.max_tonnage = max_tonnage_tph
        self.belt_speed_mps = 0.0
        self.feed_rate_tph = 0.0
        self.motor_current_a = 0.0
        self.vibration_mms = 1.8 # Normal ISO 10816 baseline mm/s RMS
        self.lube_pressure_bar = 3.5 # Normal lube pressure

    def step(self, dt: float, conveyor_cmd: bool, sag_mill_cmd: bool, speed_pct: float, lube_loss: bool = False) -> dict:
        clamped_speed_pct = max(0.0, min(100.0, speed_pct))

        # Target belt speed
        if conveyor_cmd:
            target_speed = self.nominal_speed_mps * (clamped_speed_pct / 100.0)
            # Motor acceleration ramp (0.8 m/s^2)
            if self.belt_speed_mps < target_speed:
                self.belt_speed_mps = min(target_speed, self.belt_speed_mps + 0.8 * dt)
            elif self.belt_speed_mps > target_speed:
                self.belt_speed_mps = max(target_speed, self.belt_speed_mps - 1.2 * dt)
            self.feed_rate_tph = self.max_tonnage * (self.belt_speed_mps / self.nominal_speed_mps)
        else:
            # Coast down
            self.belt_speed_mps = max(0.0, self.belt_speed_mps - 1.5 * dt)
            self.feed_rate_tph = 0.0

        # SAG Mill motor current and vibration
        if sag_mill_cmd:
            # Base current (idle 180A) + load dependent current up to 450A
            load_ratio = self.feed_rate_tph / self.max_tonnage
            self.motor_current_a = 180.0 + 260.0 * load_ratio + random.uniform(-5.0, 5.0)

            # Lube oil dynamics
            if lube_loss:
                self.lube_pressure_bar = max(0.5, self.lube_pressure_bar - 0.4 * dt)
            else:
                self.lube_pressure_bar = min(3.8, self.lube_pressure_bar + 0.2 * dt)

            # Vibration dynamics: healthy is ~2.0-3.5 mm/s. If lube drops or mechanical anomaly occurs, vibration climbs
            if self.lube_pressure_bar < 2.0:
                # Critical friction runaway!
                self.vibration_mms += (2.5 / self.lube_pressure_bar) * dt
            else:
                baseline = 2.0 + 1.5 * load_ratio
                self.vibration_mms = baseline + random.uniform(-0.2, 0.2)
        else:
            self.motor_current_a = 0.0
            self.vibration_mms = max(0.1, self.vibration_mms - 2.0 * dt)
            self.lube_pressure_bar = max(0.0, self.lube_pressure_bar - 0.1 * dt)

        return {
            "belt_speed_mps": round(self.belt_speed_mps, 2),
            "feed_rate_tph": round(self.feed_rate_tph, 1),
            "motor_current_a": round(self.motor_current_a, 1),
            "vibration_mms": round(self.vibration_mms, 2),
            "vibration_rms_x10": int(round(self.vibration_mms * 10)),
            "lube_pressure_bar": round(self.lube_pressure_bar, 2),
            "lube_pressure_x10": int(round(self.lube_pressure_bar * 10))
        }
