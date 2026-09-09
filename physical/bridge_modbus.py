#!/usr/bin/env python3
"""
IndustryLab — Hardware-in-the-Loop (HIL) Physical Process Bridge
Connects dynamic differential equations (ICSSIM) with OpenPLC Modbus controllers.
Steps physics models forward and synchronizes process sensors and actuators.
"""

import sys
import time
import signal
import logging
import argparse
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from physical.icssim.plant_cooling import ThermalCoolingPlant
from physical.icssim.plant_conveyor import SlurryConveyorPlant
from physical.icssim.plant_tank import BufferTankPlant

try:
    from pymodbus.client.sync import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        ModbusTcpClient = None

logger = logging.getLogger("HILBridge")


class HilModbusBridge:
    def __init__(self, cooling_plc_host="127.0.0.1", cooling_plc_port=502,
                 conveyor_plc_host="127.0.0.1", conveyor_plc_port=502,
                 dt: float = 0.2):
        self.cooling_plc_host = cooling_plc_host
        self.cooling_plc_port = cooling_plc_port
        self.conveyor_plc_host = conveyor_plc_host
        self.conveyor_plc_port = conveyor_plc_port
        self.dt = dt
        self.running = False

        # Physics engines
        self.cooling_plant = ThermalCoolingPlant(ambient_temp_c=25.0, initial_temp_c=45.0)
        self.conveyor_plant = SlurryConveyorPlant()
        self.tank_plant = BufferTankPlant()

        self.cooling_client = None
        self.conveyor_client = None

    def connect(self) -> bool:
        if ModbusTcpClient is None:
            logger.warning("pymodbus not available; running in offline simulation mode")
            return False

        try:
            self.cooling_client = ModbusTcpClient(self.cooling_plc_host, port=self.cooling_plc_port, timeout=2.0)
            self.cooling_client.connect()
            logger.info(f"Connected to Cooling PLC at {self.cooling_plc_host}:{self.cooling_plc_port}")
        except Exception as e:
            logger.warning(f"Could not connect to Cooling PLC: {e}")

        try:
            self.conveyor_client = ModbusTcpClient(self.conveyor_plc_host, port=self.conveyor_plc_port, timeout=2.0)
            self.conveyor_client.connect()
            logger.info(f"Connected to Conveyor PLC at {self.conveyor_plc_host}:{self.conveyor_plc_port}")
        except Exception as e:
            logger.warning(f"Could not connect to Conveyor PLC: {e}")

        return True

    def step_cycle(self) -> dict:
        """Executes one HIL synchronization cycle."""
        # --- 1. Cooling Loop Synchronization ---
        pump_run = True
        valve_pct = 35.0

        if self.cooling_client:
            try:
                # Read actuator commands from PLC
                rc = self.cooling_client.read_coils(0, 1, unit=1)
                if not rc.isError():
                    pump_run = bool(rc.bits[0])

                rr = self.cooling_client.read_holding_registers(1, 1, unit=1)
                if not rr.isError():
                    valve_pct = float(rr.registers[0])
            except Exception as e:
                logger.debug(f"Modbus read cooling error: {e}")

        # Advance physics
        cooling_state = self.cooling_plant.step(self.dt, pump_run, valve_pct)

        if self.cooling_client:
            try:
                # Write back sensor PV to PLC holding register 0 (Temp * 10)
                self.cooling_client.write_register(0, cooling_state["temp_scaled_c10"], unit=1)
                # Write flow rate to register 4
                self.cooling_client.write_register(4, int(cooling_state["flow_lpm"]), unit=1)
            except Exception as e:
                logger.debug(f"Modbus write cooling error: {e}")

        # --- 2. Conveyor & Mill Synchronization ---
        conv_run = True
        mill_run = True
        speed_pct = 70.0

        if self.conveyor_client and self.conveyor_client != self.cooling_client:
            try:
                rc = self.conveyor_client.read_coils(0, 2, unit=1)
                if not rc.isError():
                    conv_run = bool(rc.bits[0])
                    mill_run = bool(rc.bits[1])

                rr = self.conveyor_client.read_holding_registers(0, 1, unit=1)
                if not rr.isError():
                    speed_pct = float(rr.registers[0])
            except Exception as e:
                logger.debug(f"Modbus read conveyor error: {e}")

        conveyor_state = self.conveyor_plant.step(self.dt, conv_run, mill_run, speed_pct)

        if self.conveyor_client and self.conveyor_client != self.cooling_client:
            try:
                self.conveyor_client.write_register(2, conveyor_state["vibration_rms_x10"], unit=1)
                self.conveyor_client.write_register(3, conveyor_state["lube_pressure_x10"], unit=1)
                self.conveyor_client.write_register(4, int(conveyor_state["motor_current_a"]), unit=1)
            except Exception as e:
                logger.debug(f"Modbus write conveyor error: {e}")

        # --- 3. Buffer Tank Dynamics (SEC-15) ---
        tank_state = self.tank_plant.step(self.dt, pump_in_cmd=pump_run, valve_out_cmd=(valve_pct > 0.0))

        return {
            "cooling": cooling_state,
            "conveyor": conveyor_state,
            "tank": tank_state,
            "timestamp": time.time()
        }

    def run(self):
        self.running = True
        self.connect()
        logger.info(f"HIL Physical Process Bridge running (dt={self.dt}s)...")

        try:
            while self.running:
                t0 = time.time()
                state = self.step_cycle()
                elapsed = time.time() - t0
                time.sleep(max(0.001, self.dt - elapsed))
        except KeyboardInterrupt:
            logger.info("Stopping HIL Bridge...")
        finally:
            if self.cooling_client:
                self.cooling_client.close()
            if self.conveyor_client:
                self.conveyor_client.close()


def main():
    parser = argparse.ArgumentParser(description="ICSSIM HIL Modbus Physical Bridge")
    parser.add_argument("--cooling-host", default="127.0.0.1", help="Cooling PLC host")
    parser.add_argument("--cooling-port", type=int, default=502, help="Cooling PLC port")
    parser.add_argument("--conveyor-host", default="127.0.0.1", help="Conveyor PLC host")
    parser.add_argument("--conveyor-port", type=int, default=502, help="Conveyor PLC port")
    parser.add_argument("--dt", type=float, default=0.2, help="Time step dt in seconds")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [HILBridge] %(message)s")
    bridge = HilModbusBridge(
        cooling_plc_host=args.cooling_host,
        cooling_plc_port=args.cooling_port,
        conveyor_plc_host=args.conveyor_host,
        conveyor_plc_port=args.conveyor_port,
        dt=args.dt
    )

    def sig_handler(sig, frame):
        bridge.running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    bridge.run()


if __name__ == "__main__":
    main()
