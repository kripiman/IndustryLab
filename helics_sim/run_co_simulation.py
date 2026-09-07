#!/usr/bin/env python3
"""
IndustryLab — Master Co-Simulation Orchestrator
Synchronizes HELICS federates: ICSSIM, OpenPLC, Power Grid, and Cascading Event Logger.
Demonstrates cascading domino effect under cyber-attack injection.
"""

import sys
import time
import logging
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from helics_sim.fed_icssim import FedICSSIM
from helics_sim.fed_plc import FedPLC
from helics_sim.fed_power_grid import FedPowerGrid
from helics_sim.fed_logger import CascadingEventLogger

logger = logging.getLogger("CoSimulationMaster")


def run_simulation(duration_s=30.0, attack_at_s=10.0, dt=0.5):
    logger.info(f"Starting IndustryLab Co-Simulation (Duration: {duration_s}s, Attack inject at: {attack_at_s}s)")

    icssim = FedICSSIM(time_step=dt)
    plc = FedPLC(setpoint_c=45.0)
    grid = FedPowerGrid()
    event_logger = CascadingEventLogger()

    sim_time = 0.0
    attack_injected = False
    cascade_triggered = False

    while sim_time <= duration_s:
        # Check if cyber-attack should be injected (e.g. at t=10s)
        if sim_time >= attack_at_s and not attack_injected:
            logger.warning(
                f"[CYBER-ATTACK INJECTED @ t={sim_time:.1f}s] Malicious Modbus coil injection: "
                "Cooling pump forced OFF (Coil 0=0) and Valve forced closed (0%)!"
            )
            attack_injected = True

        # Current temperature
        current_temp = icssim.plant_cooling.temp_c

        # 1. Execute PLC control logic
        if attack_injected:
            plc_out = plc.execute_logic(current_temp, cyber_attack_override=True, attack_valve_val=0.0)
        else:
            plc_out = plc.execute_logic(current_temp)

        # 2. Evaluate Electrical Substation Grid Protection
        grid_out = grid.evaluate_grid_state(current_temp, plc_out["emergency_trip"])

        if not grid_out["power_available"] and not cascade_triggered:
            cascade_triggered = True
            logger.critical(
                f"[DOMINO CASCADE CONFIRMED @ t={sim_time:.1f}s] Plant blackout initiated! "
                "Conveyor, mill, and cooling loop stopped due to grid breaker trip."
            )

        # 3. Advance ICSSIM physical model
        phys_out = icssim.step(
            current_time=sim_time,
            pump_cmd=plc_out["pump_cmd"],
            valve_pos=plc_out["valve_pct"],
            power_ok=grid_out["power_available"]
        )

        status = "NORMAL"
        if cascade_triggered:
            status = "CASCADE_BLACKOUT_TRIPPED"
        elif attack_injected:
            status = "UNDER_ATTACK_OVERHEATING"

        event_logger.log_step(
            t=sim_time,
            temp_c=phys_out["temp_c"],
            flow_lpm=phys_out["flow_lpm"],
            valve_pct=plc_out["valve_pct"],
            pump_ok=plc_out["pump_cmd"],
            vib_mms=phys_out["vibration_mms"],
            grid_power=grid_out["power_available"],
            grid_kw=grid_out["load_kw"],
            status=status
        )

        sim_time += dt

    event_logger.close()
    logger.info("Co-Simulation completed successfully. Event log written to logs/cascading_events.csv")
    return {
        "final_temp_c": phys_out["temp_c"],
        "cascade_triggered": cascade_triggered,
        "attack_injected": attack_injected
    }


def main():
    parser = argparse.ArgumentParser(description="IndustryLab Co-Simulation Master")
    parser.add_argument("--duration", type=float, default=30.0, help="Simulation duration (s)")
    parser.add_argument("--attack-at", type=float, default=10.0, help="Time in seconds to inject cyber-attack")
    parser.add_argument("--dt", type=float, default=0.5, help="Simulation time-step (s)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_simulation(duration_s=args.duration, attack_at_s=args.attack_at, dt=args.dt)


if __name__ == "__main__":
    main()
