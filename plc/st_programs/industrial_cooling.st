(* ============================================================================== *)
(* IndustryLab — IEC 61131-3 Structured Text                                     *)
(* Process: Heavy Industrial Heat Exchanger & Reactor/Mill Cooling Loop           *)
(* Target: OpenPLC v3 / v4 Runtime Engine                                         *)
(* ============================================================================== *)

PROGRAM Cooling_Exchanger_Control
  VAR
    (* Digital Inputs (%IX) *)
    FLOW_SWITCH_OK       AT %IX0.0 : BOOL; (* Coolant flow sensor contact *)
    PUMP_FEEDBACK_RUN    AT %IX0.1 : BOOL; (* Auxiliary contact from pump contactor *)

    (* Digital Outputs / Coils (%QX) *)
    PUMP_RUN_CMD         AT %QX0.0 : BOOL; (* Command to start/stop coolant pump *)
    EMERGENCY_TRIP_RST   AT %QX0.1 : BOOL; (* Operator reset pulse for trip latch *)
    MANUAL_OVERRIDE      AT %QX0.2 : BOOL; (* 1=Manual valve control, 0=Auto PID *)
    TRIP_INTERLOCK_ACT   AT %QX0.3 : BOOL; (* Safety interlock active status *)

    (* Analog / Scaled Input Registers (%IW) *)
    TEMP_PV_SCALED_C10   AT %IW0   : INT;  (* Temperature PV in 0.1 C (e.g. 450 = 45.0 C) *)
    INLET_PRESSURE_KPA   AT %IW1   : INT;  (* Coolant inlet pressure *)

    (* Analog / Scaled Holding Registers (%QW) *)
    VALVE_POSITION_PCT   AT %QW0   : INT;  (* Cooling valve position 0 - 100% *)
    TEMP_SP_SCALED_C10   AT %QW1   : INT;  (* Temperature Setpoint (Default: 450) *)
    KP_GAIN_X10          AT %QW2   : INT;  (* Proportional control gain (Default: 20) *)
    ALARM_STATUS_WORD    AT %QW3   : WORD; (* Bit 0=HighTemp, Bit 1=CritTrip, Bit 2=NoFlow *)

    (* Internal State Variables *)
    Temp_Error           : INT := 0;
    Valve_Calc           : INT := 0;
  END_VAR

  (* Initial default setpoint safety check *)
  IF TEMP_SP_SCALED_C10 <= 0 OR TEMP_SP_SCALED_C10 > 900 THEN
    TEMP_SP_SCALED_C10 := 450; (* 45.0 C default *)
  END_IF;

  IF KP_GAIN_X10 <= 0 THEN
    KP_GAIN_X10 := 20; (* 2.0 proportional gain *)
  END_IF;

  (* Reset trip interlock if operator pulsed reset and temp is back under 70 C *)
  IF EMERGENCY_TRIP_RST AND TEMP_PV_SCALED_C10 < 700 THEN
    TRIP_INTERLOCK_ACT := FALSE;
    EMERGENCY_TRIP_RST := FALSE;
  END_IF;

  (* Safety Interlock: Over-temperature Trip at 95.0 C *)
  IF TEMP_PV_SCALED_C10 >= 950 THEN
    TRIP_INTERLOCK_ACT := TRUE;
    PUMP_RUN_CMD := TRUE;       (* Force max flow *)
    VALVE_POSITION_PCT := 100;  (* 100% full open emergency cooling *)
    ALARM_STATUS_WORD := 16#0003; (* HighTemp + CritTrip *)
    RETURN;
  ELSIF TRIP_INTERLOCK_ACT THEN
    PUMP_RUN_CMD := TRUE;       (* Keep emergency cooling locked *)
    VALVE_POSITION_PCT := 100;
    ALARM_STATUS_WORD := 16#0003;
    RETURN;
  END_IF;

  (* Normal Automatic Control Logic *)
  IF NOT TRIP_INTERLOCK_ACT THEN
    (* Temperature Alarm Thresholds *)
    IF TEMP_PV_SCALED_C10 >= 850 THEN
      ALARM_STATUS_WORD := 16#0001; (* Warning: High Temperature *)
    ELSE
      ALARM_STATUS_WORD := 16#0000; (* Normal *)
    END_IF;

    (* If not in manual override mode, compute proportional valve positioning *)
    IF NOT MANUAL_OVERRIDE THEN
      PUMP_RUN_CMD := TRUE;
      Temp_Error := TEMP_PV_SCALED_C10 - TEMP_SP_SCALED_C10;

      (* Proportional valve positioning: Valve% = Baseline(35%) + Error * Gain *)
      Valve_Calc := 35 + (Temp_Error * KP_GAIN_X10) / 100;

      (* Clamp between 0% and 100% *)
      IF Valve_Calc > 100 THEN
        VALVE_POSITION_PCT := 100;
      ELSIF Valve_Calc < 5 THEN
        VALVE_POSITION_PCT := 5;
      ELSE
        VALVE_POSITION_PCT := Valve_Calc;
      END_IF;
    END_IF;
  END_IF;

END_PROGRAM
