"""
IndustryLab — ICSSIM Thermal Heat Exchanger Dynamic Physical Model
Simulates thermodynamics of industrial cooling loop (first-order differential equation).
"""

import math
import random


class ThermalCoolingPlant:
    def __init__(self,
                 ambient_temp_c: float = 25.0,
                 initial_temp_c: float = 45.0,
                 nominal_heat_inflow_kw: float = 120.0,
                 max_cooling_capacity_kw: float = 250.0,
                 thermal_mass_kj_k: float = 500.0): # Scaled for dynamic cyber range responsiveness
        self.ambient_temp = ambient_temp_c
        self.temp_c = initial_temp_c
        self.heat_inflow_nominal = nominal_heat_inflow_kw
        self.max_cooling_capacity = max_cooling_capacity_kw
        self.thermal_mass = thermal_mass_kj_k # kJ per Kelvin
        self.heat_loss_resistance = 0.08 # K / kW ambient dissipation
        self.flow_lpm = 0.0
        self.pressure_kpa = 300.0

    def step(self, dt: float, pump_running: bool, valve_pct: float, external_heat_kw: float | None = None) -> dict:
        clamped_valve = max(0.0, min(100.0, valve_pct))

        # Effective coolant flow rate (L/min)
        if pump_running:
            self.flow_lpm = 250.0 * (clamped_valve / 100.0)
            self.pressure_kpa = 320.0 - 50.0 * (clamped_valve / 100.0)
        else:
            self.flow_lpm = 0.0
            self.pressure_kpa = 100.0

        # Heat inflow from industrial process (kW)
        q_in = external_heat_kw if external_heat_kw is not None else self.heat_inflow_nominal
        q_in += random.uniform(-1.0, 1.0)

        # Heat removed by cooling loop (kW)
        if pump_running and self.flow_lpm > 0:
            delta_t_fluid = max(0.0, self.temp_c - 18.0) # Secondary chiller water at 18 C
            efficiency = delta_t_fluid / 30.0
            q_out = self.max_cooling_capacity * (clamped_valve / 100.0) * min(1.4, efficiency)
        else:
            q_out = 0.0 # Loss of cooling!

        # Passive ambient heat dissipation
        q_ambient_loss = (self.temp_c - self.ambient_temp) / (self.heat_loss_resistance * 100.0)

        # Net thermal rate: dE/dt = q_in - q_out - q_ambient (kW)
        net_heat_flow_kw = q_in - q_out - q_ambient_loss

        # dT/dt = net_heat / thermal_mass (K/s)
        d_temp = (net_heat_flow_kw / self.thermal_mass) * dt
        self.temp_c += d_temp

        # Bound temperature to physical realistic limits
        self.temp_c = max(self.ambient_temp, min(140.0, self.temp_c))

        return {
            "temp_c": round(self.temp_c, 2),
            "temp_scaled_c10": int(round(self.temp_c * 10)),
            "flow_lpm": round(self.flow_lpm, 1),
            "pressure_kpa": round(self.pressure_kpa, 1),
            "heat_in_kw": round(q_in, 1),
            "heat_out_kw": round(q_out, 1)
        }
