"""
IndustryLab — HELICS Federate: ICSSIM Physical Dynamics
Publishes process temperatures and mechanical vibrations.
Subscribes to PLC actuator outputs and electrical power availability.
"""

import sys
import time
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from physical.icssim.plant_cooling import ThermalCoolingPlant
from physical.icssim.plant_conveyor import SlurryConveyorPlant

try:
    import helics
except ImportError:
    helics = None

logger = logging.getLogger("FedICSSIM")


class FedICSSIM:
    def __init__(self, fed_name="fed_icssim", broker_address="127.0.0.1", time_step=0.5):
        self.fed_name = fed_name
        self.broker_address = broker_address
        self.time_step = time_step
        self.plant_cooling = ThermalCoolingPlant(ambient_temp_c=25.0, initial_temp_c=45.0)
        self.plant_conveyor = SlurryConveyorPlant()
        self.fed = None

    def initialize(self):
        if not helics:
            logger.warning("HELICS not available, initialized in mock mode")
            return

        fi = helics.helicsCreateFederateInfo()
        helics.helicsFederateInfoSetCoreTypeFromString(fi, "zmq")
        helics.helicsFederateInfoSetCoreInitString(fi, f"--federates=1 --broker_address={self.broker_address}")
        helics.helicsFederateInfoSetTimeProperty(fi, helics.HELICS_PROPERTY_TIME_DELTA, self.time_step)

        self.fed = helics.helicsCreateValueFederate(self.fed_name, fi)

        # Register Publications
        self.pub_temp = helics.helicsFederateRegisterGlobalPublication(self.fed, "cooling/temperature", helics.HELICS_DATA_TYPE_DOUBLE, "degC")
        self.pub_flow = helics.helicsFederateRegisterGlobalPublication(self.fed, "cooling/flow", helics.HELICS_DATA_TYPE_DOUBLE, "Lpm")
        self.pub_vib = helics.helicsFederateRegisterGlobalPublication(self.fed, "conveyor/vibration", helics.HELICS_DATA_TYPE_DOUBLE, "mm/s")

        # Register Subscriptions
        self.sub_valve = helics.helicsFederateRegisterSubscription(self.fed, "plc/valve_pos", "pct")
        self.sub_pump = helics.helicsFederateRegisterSubscription(self.fed, "plc/pump_cmd", "")
        self.sub_power = helics.helicsFederateRegisterSubscription(self.fed, "grid/power_available", "")

        helics.helicsFederateEnterExecutingMode(self.fed)
        logger.info(f"Federate {self.fed_name} entered Executing Mode")

    def step(self, current_time: float, pump_cmd: bool = True, valve_pos: float = 35.0, power_ok: bool = True) -> dict:
        # If power grid has tripped, pumps and drives lose power immediately!
        effective_pump = pump_cmd and power_ok
        effective_valve = valve_pos if power_ok else 0.0

        c_state = self.plant_cooling.step(self.time_step, effective_pump, effective_valve)
        conv_state = self.plant_conveyor.step(self.time_step, power_ok, power_ok, 70.0 if power_ok else 0.0)

        if self.fed:
            helics.helicsPublicationPublishDouble(self.pub_temp, c_state["temp_c"])
            helics.helicsPublicationPublishDouble(self.pub_flow, c_state["flow_lpm"])
            helics.helicsPublicationPublishDouble(self.pub_vib, conv_state["vibration_mms"])

        return {
            "time": current_time,
            "temp_c": c_state["temp_c"],
            "flow_lpm": c_state["flow_lpm"],
            "vibration_mms": conv_state["vibration_mms"],
            "power_ok": power_ok
        }

    def close(self):
        if self.fed:
            helics.helicsFederateFinalize(self.fed)
            helics.helicsFederateFree(self.fed)
