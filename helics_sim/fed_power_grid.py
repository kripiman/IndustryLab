"""
IndustryLab — HELICS Federate: Electrical Substation (Cascading Power Grid)
Models 13.8 kV industrial electrical feed and thermal/overcurrent protective trip relays.
Demonstrates cascading cyber-physical domino effects:
Attack -> Thermal runaway -> Substation breaker trip -> Plant Blackout.
"""

import sys
import logging

try:
    import helics
except ImportError:
    helics = None

logger = logging.getLogger("FedPowerGrid")


class FedPowerGrid:
    def __init__(self, fed_name="fed_power_grid", nominal_voltage_kv=13.8):
        self.fed_name = fed_name
        self.nominal_voltage = nominal_voltage_kv
        self.breaker_closed = True
        self.power_available = True
        self.substation_load_kw = 850.0
        self.trip_reason = "NONE"
        self.fed = None

    def initialize(self, broker_address="127.0.0.1"):
        if not helics:
            return

        fi = helics.helicsCreateFederateInfo()
        helics.helicsFederateInfoSetCoreTypeFromString(fi, "zmq")
        helics.helicsFederateInfoSetCoreInitString(fi, f"--federates=1 --broker_address={broker_address}")
        helics.helicsFederateInfoSetTimeProperty(fi, helics.HELICS_PROPERTY_TIME_DELTA, 0.5)

        self.fed = helics.helicsCreateValueFederate(self.fed_name, fi)
        self.pub_power = helics.helicsFederateRegisterGlobalPublication(self.fed, "grid/power_available", helics.HELICS_DATA_TYPE_BOOLEAN, "")
        self.pub_load = helics.helicsFederateRegisterGlobalPublication(self.fed, "grid/substation_load_kw", helics.HELICS_DATA_TYPE_DOUBLE, "kW")
        self.pub_breaker = helics.helicsFederateRegisterGlobalPublication(self.fed, "grid/breaker_status", helics.HELICS_DATA_TYPE_STRING, "")

        self.sub_trip = helics.helicsFederateRegisterSubscription(self.fed, "plc/emergency_trip", "")
        self.sub_temp = helics.helicsFederateRegisterSubscription(self.fed, "cooling/temperature", "degC")
        helics.helicsFederateEnterExecutingMode(self.fed)

    def evaluate_grid_state(self, temp_c: float, plc_trip_signal: bool) -> dict:
        """
        Evaluates electrical protection relays.
        If reactor/mill temperature reaches critical thermal trip (>= 95.0 C)
        or emergency trip is asserted, the high-voltage breaker trips to protect transformers.
        """
        if (temp_c >= 95.0 or plc_trip_signal) and self.breaker_closed:
            self.breaker_closed = False
            self.power_available = False
            self.substation_load_kw = 0.0
            self.trip_reason = "CRITICAL_THERMAL_CASCADE_OVERLOAD"
            logger.critical(
                f"[DOMINO-EFFECT] Electrical Substation Breaker TRIPPED! Temp={temp_c} C. "
                "Main 13.8kV feeder open. Complete plant power lost!"
            )

        if self.fed:
            helics.helicsPublicationPublishBoolean(self.pub_power, self.power_available)
            helics.helicsPublicationPublishDouble(self.pub_load, self.substation_load_kw)
            helics.helicsPublicationPublishString(self.pub_breaker, "CLOSED" if self.breaker_closed else self.trip_reason)

        return {
            "power_available": self.power_available,
            "breaker_closed": self.breaker_closed,
            "load_kw": self.substation_load_kw,
            "trip_reason": self.trip_reason
        }

    def close(self):
        if self.fed:
            helics.helicsFederateFinalize(self.fed)
            helics.helicsFederateFree(self.fed)
