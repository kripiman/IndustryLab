(* ============================================================================== *)
(* IndustryLab — IEC 61131-3 Structured Text                                     *)
(* Process: High-Tonnage Slurry Conveyor & Semi-Autogenous Grinding (SAG) Mill    *)
(* Target: OpenPLC v3 / v4 Runtime Engine                                         *)
(* ============================================================================== *)

PROGRAM Slurry_Conveyor_SAG_Control
  VAR
    (* Digital Inputs (%IX) *)
    PULL_CORD_ESTOP_OK   AT %IX0.0 : BOOL; (* Emergency stop cable along conveyor *)
    BELT_ALIGNMENT_OK    AT %IX0.1 : BOOL; (* Belt tracking alignment limit switch *)

    (* Digital Outputs / Coils (%QX) *)
    CONVEYOR_RUN_CMD     AT %QX0.0 : BOOL; (* Start/Stop command for conveyor motor *)
    SAG_MILL_RUN_CMD     AT %QX0.1 : BOOL; (* Start/Stop command for SAG mill drive *)
    CHUTE_SPRAY_ACT      AT %QX0.2 : BOOL; (* Dust suppression water solenoid *)
    INTERLOCK_BYPASS     AT %QX0.3 : BOOL; (* Operator bypass for vibration trips *)

    (* Analog / Scaled Input Registers (%IW) *)
    VIBRATION_RMS_X10    AT %IW0   : INT;  (* Bearing vibration RMS (0.1 mm/s) *)
    LUBE_PRESSURE_X10    AT %IW1   : INT;  (* Lube oil pressure (0.1 bar) *)

    (* Analog / Scaled Holding Registers (%QW) *)
    BELT_SPEED_PCT       AT %QW0   : INT;  (* Conveyor speed setpoint (0-100%) *)
    FEED_RATE_TPH        AT %QW1   : INT;  (* Ore feed rate in tons/hour *)
    ALARM_WORD           AT %QW2   : WORD; (* Bitmask: 1=Overload, 2=Vib, 4=Lube, 8=EStop *)
  END_VAR

  (* Safety Check 1: Emergency Pull Cord / E-Stop *)
  IF NOT PULL_CORD_ESTOP_OK OR NOT BELT_ALIGNMENT_OK THEN
    CONVEYOR_RUN_CMD := FALSE;
    SAG_MILL_RUN_CMD := FALSE;
    BELT_SPEED_PCT := 0;
    FEED_RATE_TPH := 0;
    ALARM_WORD := 16#0008; (* E-Stop tripped *)
    RETURN;
  END_IF;

  (* Safety Check 2: Severe Bearing Vibration (>11.0 mm/s) *)
  IF VIBRATION_RMS_X10 >= 110 AND NOT INTERLOCK_BYPASS THEN
    CONVEYOR_RUN_CMD := FALSE;
    SAG_MILL_RUN_CMD := FALSE;
    BELT_SPEED_PCT := 0;
    FEED_RATE_TPH := 0;
    ALARM_WORD := 16#0002; (* Vibration Trip *)
    RETURN;
  END_IF;

  (* Safety Check 3: Critical Low Lube Oil Pressure (<2.0 bar) *)
  IF LUBE_PRESSURE_X10 < 20 AND NOT INTERLOCK_BYPASS THEN
    SAG_MILL_RUN_CMD := FALSE;
    ALARM_WORD := 16#0004; (* Low Lube Trip *)
    RETURN;
  END_IF;

  (* Normal Automated Operation *)
  IF CONVEYOR_RUN_CMD THEN
    IF BELT_SPEED_PCT = 0 THEN
      BELT_SPEED_PCT := 70; (* Default 70% nominal belt velocity *)
    END_IF;
    CHUTE_SPRAY_ACT := TRUE;
    FEED_RATE_TPH := (BELT_SPEED_PCT * 1200) / 100;
  ELSE
    CHUTE_SPRAY_ACT := FALSE;
    FEED_RATE_TPH := 0;
  END_IF;

  IF INTERLOCK_BYPASS THEN
    ALARM_WORD := 16#0010; (* Warning: Interlock Bypass Active *)
  ELSE
    ALARM_WORD := 16#0000; (* All nominal *)
  END_IF;
END_PROGRAM
