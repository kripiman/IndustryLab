"""
IndustryLab — HELICS Federate: PLC Control Loop
Executes proportional control and trips safety interlocks.
Publishes valve positions and emergency trip signals.
"""

import sys
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import helics
except ImportError:
    helics = None

logger = logging.getLogger("FedPLC")


class FedPLC:
    def __init__(self, fed_name="fed_plc", setpoint_c: float = 45.0):
        self.fed_name = fed_name
        self.setpoint = setpoint_c
        self.valve_pct = 35.0
        self.pump_cmd = True
        self.emergency_trip = False
        self.fed = None

    def initialize(self, broker_address="127.0.0.1"):
        if not helics:
            return

        fi = helics.helicsCreateFederateInfo()
        helics.helicsFederateInfoSetCoreTypeFromString(fi, "zmq")
        helics.helicsFederateInfoSetCoreInitString(fi, f"--federates=1 --broker_address={broker_address}")
        helics.helicsFederateInfoSetTimeProperty(fi, helics.HELICS_PROPERTY_TIME_DELTA, 0.5)

        self.fed = helics.helicsCreateValueFederate(self.fed_name, fi)
        self.pub_valve = helics.helicsFederateRegisterGlobalPublication(self.fed, "plc/valve_pos", helics.HELICS_DATA_TYPE_DOUBLE, "pct")
        self.pub_pump = helics.helicsFederateRegisterGlobalPublication(self.fed, "plc/pump_cmd", helics.HELICS_DATA_TYPE_BOOLEAN, "")
        self.pub_trip = helics.helicsFederateRegisterGlobalPublication(self.fed, "plc/emergency_trip", helics.HELICS_DATA_TYPE_BOOLEAN, "")

        self.sub_temp = helics.helicsFederateRegisterSubscription(self.fed, "cooling/temperature", "degC")
        helics.helicsFederateEnterExecutingMode(self.fed)

    def execute_logic(self, temp_c: float, cyber_attack_override: bool = False, attack_valve_val: float = 0.0) -> dict:
        # Safety interlock always monitors process limit regardless of override
        if temp_c >= 95.0:
            self.emergency_trip = True
        else:
            self.emergency_trip = False

        # Evaluate actuator outputs
        if cyber_attack_override:
            self.valve_pct = attack_valve_val
            self.pump_cmd = False # Attack shuts off coolant pump!
        else:
            if self.emergency_trip:
                self.valve_pct = 100.0
                self.pump_cmd = True
            else:
                error = temp_c - self.setpoint
                calc = 35.0 + error * 2.0
                self.valve_pct = max(5.0, min(100.0, calc))
                self.pump_cmd = True

        if self.fed:
            helics.helicsPublicationPublishDouble(self.pub_valve, self.valve_pct)
            helics.helicsPublicationPublishBoolean(self.pub_pump, self.pump_cmd)
            helics.helicsPublicationPublishBoolean(self.pub_trip, self.emergency_trip)

        return {
            "valve_pct": round(self.valve_pct, 1),
            "pump_cmd": self.pump_cmd,
            "emergency_trip": self.emergency_trip
        }

    def close(self):
        if self.fed:
            helics.helicsFederateFinalize(self.fed)
            helics.helicsFederateFree(self.fed)
