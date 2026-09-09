#!/usr/bin/env python3
"""
IndustryLab — OpenPLC IEC 61131-3 Simulation Runtime Engine
Executes deterministic scan cycles for industrial control programs:
- Cooling Heat Exchanger (%IX, %QX, %IW, %QW)
- Mining Slurry Conveyor & SAG Mill
Serves variables via integrated Modbus/TCP server.
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

from plc.modbus_server import ModbusPlcServer

logger = logging.getLogger("OpenPLCRuntime")


class CoolingControlLogic:
    """
    Implements IEC 61131-3 logic defined in plc/st_programs/industrial_cooling.st
    """
    def __init__(self, modbus: ModbusPlcServer):
        self.modbus = modbus
        # Default initialization
        self.modbus.set_coil(0, True)            # PUMP_RUN_CMD = 1
        self.modbus.set_holding_register(1, 35)  # VALVE_POSITION_PCT = 35%
        self.modbus.set_holding_register(2, 450) # TEMP_SP_SCALED_C10 = 45.0 C (addr 2)
        self.modbus.set_holding_register(3, 20)  # KP_GAIN_X10 = 20 (addr 3)
        self.modbus.set_input_register(0, 450)   # TEMP_PV_SCALED_C10 (%IW0 - Read-Only)
        self.modbus.set_holding_register(0, 450) # Mirror to HR0 for legacy telemetry/bus
        self.modbus.set_discrete_input(0, True)  # FLOW_SWITCH_OK = 1
        self.modbus.set_discrete_input(1, True)  # PUMP_FEEDBACK_RUN = 1
        self._last_hr_temp = 450

    def scan_cycle(self):
        # 1. Read Inputs from Input Register (%IW0) with sync from virtual field bus
        ir_pv = self.modbus.get_input_register(0)
        hr_pv = self.modbus.get_holding_register(0)
        if hr_pv != self._last_hr_temp:
            temp_pv = hr_pv
            self.modbus.set_input_register(0, hr_pv)
            self._last_hr_temp = hr_pv
        else:
            temp_pv = ir_pv

        manual_override = self.modbus.get_coil(2)      # MANUAL_OVERRIDE
        emergency_rst = self.modbus.get_coil(1)        # EMERGENCY_TRIP_RST
        trip_active = self.modbus.get_coil(3)          # TRIP_INTERLOCK_ACT
        temp_sp = self.modbus.get_holding_register(2)  # Setpoint * 10
        kp_gain = self.modbus.get_holding_register(3)  # Gain * 10

        if temp_sp <= 0 or temp_sp > 900:
            temp_sp = 450
            self.modbus.set_holding_register(2, 450)

        if kp_gain <= 0:
            kp_gain = 20
            self.modbus.set_holding_register(3, 20)

        # Handle emergency reset pulse
        if emergency_rst and temp_pv < 700:
            trip_active = False
            self.modbus.set_coil(3, False)
            self.modbus.set_coil(1, False)

        # 2. Safety Interlock: Emergency Over-Temperature Trip (>= 95.0 C) or Latched Trip
        if temp_pv >= 950:
            trip_active = True
            self.modbus.set_coil(3, True)            # TRIP_INTERLOCK_ACT := TRUE

        if trip_active:
            self.modbus.set_coil(0, True)            # PUMP_RUN_CMD := TRUE (Emergency lock)
            self.modbus.set_holding_register(1, 100) # VALVE_POSITION_PCT := 100%
            self.modbus.set_holding_register(5, 0x0003) # HighTemp + CritTrip Alarm
            return

        # 3. Normal Control Logic
        if not trip_active:
            if temp_pv >= 850:
                self.modbus.set_holding_register(5, 0x0001) # HighTemp warning
            else:
                self.modbus.set_holding_register(5, 0x0000) # Normal

            if not manual_override:
                self.modbus.set_coil(0, True) # Keep pump running
                temp_error = temp_pv - temp_sp
                # Proportional calculation: Valve = 35% + Error * Kp
                valve_calc = 35 + int((temp_error * kp_gain) / 100)
                valve_clamped = max(5, min(100, valve_calc))
                self.modbus.set_holding_register(1, valve_clamped)


class ConveyorControlLogic:
    """
    Implements IEC 61131-3 logic defined in plc/st_programs/mining_slurry_conveyor.st
    """
    def __init__(self, modbus: ModbusPlcServer):
        self.modbus = modbus
        # Default initialization
        self.modbus.set_discrete_input(0, True)  # PULL_CORD_ESTOP_OK
        self.modbus.set_discrete_input(1, True)  # BELT_ALIGNMENT_OK
        self.modbus.set_coil(0, True)            # CONVEYOR_RUN_CMD
        self.modbus.set_coil(1, True)            # SAG_MILL_RUN_CMD
        self.modbus.set_holding_register(0, 70)  # BELT_SPEED_PCT = 70%
        self.modbus.set_holding_register(1, 840) # FEED_RATE_TPH = 840 TPH
        self.modbus.set_input_register(0, 32)    # VIBRATION_RMS_X10 (%IW0 - Read-Only)
        self.modbus.set_input_register(1, 35)    # LUBE_PRESSURE_X10 (%IW1 - Read-Only)
        self.modbus.set_holding_register(2, 32)  # VIBRATION_RMS_X10 = 3.2 mm/s (legacy HR2)
        self.modbus.set_holding_register(3, 35)  # LUBE_PRESSURE_X10 = 3.5 bar (legacy HR3)
        self.modbus.set_holding_register(4, 380) # MOTOR_CURRENT_AMPS = 380 A
        self._last_hr_vib = 32
        self._last_hr_lube = 35

    def scan_cycle(self):
        estop_ok = self.modbus.get_discrete_input(0)
        align_ok = self.modbus.get_discrete_input(1)
        conv_run = self.modbus.get_coil(0)
        interlock_bypass = self.modbus.get_coil(3)

        # Read sensor inputs from Input Registers (%IW) with fallback sync
        ir_vib = self.modbus.get_input_register(0)
        hr_vib = self.modbus.get_holding_register(2)
        if hr_vib != self._last_hr_vib:
            vib_rms = hr_vib
            self.modbus.set_input_register(0, hr_vib)
            self._last_hr_vib = hr_vib
        else:
            vib_rms = ir_vib

        ir_lube = self.modbus.get_input_register(1)
        hr_lube = self.modbus.get_holding_register(3)
        if hr_lube != self._last_hr_lube:
            lube_press = hr_lube
            self.modbus.set_input_register(1, hr_lube)
            self._last_hr_lube = hr_lube
        else:
            lube_press = ir_lube

        # Interlock 1: E-Stop & Alignment
        if not estop_ok or not align_ok:
            self.modbus.set_coil(0, False)
            self.modbus.set_coil(1, False)
            self.modbus.set_holding_register(0, 0)
            self.modbus.set_holding_register(1, 0)
            self.modbus.set_holding_register(5, 0x0008) # E-Stop alarm
            return

        # Interlock 2: High Vibration (>11.0 mm/s)
        if vib_rms >= 110 and not interlock_bypass:
            self.modbus.set_coil(0, False)
            self.modbus.set_coil(1, False)
            self.modbus.set_holding_register(0, 0)
            self.modbus.set_holding_register(1, 0)
            self.modbus.set_holding_register(5, 0x0002) # Vibration Trip
            return

        # Interlock 3: Low Lube Oil (<2.0 bar)
        if lube_press < 20 and not interlock_bypass:
            self.modbus.set_coil(1, False) # Trip mill motor
            self.modbus.set_holding_register(5, 0x0004) # Low lube trip
            return

        # Normal Operation
        if conv_run:
            speed_pct = self.modbus.get_holding_register(0)
            if speed_pct == 0:
                speed_pct = 70
                self.modbus.set_holding_register(0, 70)
            self.modbus.set_coil(2, True) # Chute spray ON
            feed_rate = int((speed_pct * 1200) / 100)
            self.modbus.set_holding_register(1, feed_rate)
        else:
            self.modbus.set_coil(2, False)
            self.modbus.set_holding_register(1, 0)

        if interlock_bypass:
            self.modbus.set_holding_register(5, 0x0010) # Warning: Interlock Bypass Active
        else:
            self.modbus.set_holding_register(5, 0x0000)


class OpenPLCRuntime:
    def __init__(self, process="cooling", host="0.0.0.0", port=502, scan_period_s=0.1):
        self.process = process
        self.host = host
        self.port = port
        self.scan_period_s = scan_period_s
        self.running = False
        self.modbus = ModbusPlcServer(host=self.host, port=self.port)

        if self.process == "cooling":
            self.logic = CoolingControlLogic(self.modbus)
        elif self.process == "conveyor":
            self.logic = ConveyorControlLogic(self.modbus)
        else:
            raise ValueError(f"Unknown process: {process}")

    def run(self):
        self.running = True
        self.modbus.start(background=True)
        logger.info(f"OpenPLC Runtime started for process '{self.process}' on port {self.port} (Scan: {self.scan_period_s*1000}ms)")

        try:
            while self.running:
                start_t = time.time()
                self.logic.scan_cycle()
                elapsed = time.time() - start_t
                sleep_t = max(0.001, self.scan_period_s - elapsed)
                time.sleep(sleep_t)
        except KeyboardInterrupt:
            logger.info("Stopping OpenPLC Runtime...")
        finally:
            self.modbus.stop()


def main():
    parser = argparse.ArgumentParser(description="OpenPLC IEC 61131-3 Runtime Engine")
    parser.add_argument("--process", choices=["cooling", "conveyor"], default="cooling", help="Industrial process model")
    parser.add_argument("--host", default="0.0.0.0", help="Modbus bind host")
    parser.add_argument("--port", type=int, default=502, help="Modbus bind port (default: 502)")
    parser.add_argument("--scan-ms", type=int, default=100, help="Scan cycle period in ms (default: 100)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [OpenPLC] %(message)s")

    runtime = OpenPLCRuntime(
        process=args.process,
        host=args.host,
        port=args.port,
        scan_period_s=args.scan_ms / 1000.0
    )

    def sig_handler(sig, frame):
        runtime.running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    runtime.run()


if __name__ == "__main__":
    main()
