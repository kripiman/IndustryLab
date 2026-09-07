# CLAUDE.md

This file provides guidance to Claude Code and AI agents when working with code in this repository.

## What this is

IndustryLab is a 100% software-based **Industrial Cyber-Physical Cyber Range (OT/ICS)** in containers and native Linux, designed under the international standard **IEC 62443** and the **Purdue Enterprise Reference Architecture (PERA)**. It models critical industrial plants (heat exchangers, mining slurry conveyors, and SAG mills), connects OpenPLC control logic in Structured Text (IEC 61131-3) with real dynamic physical models (ICSSIM), and demonstrates cascading domino effects orchestrated by HELICS 3.x.

## Core Commands

**`./industrylab.sh` is the single entrypoint** for all operations:

```bash
./industrylab.sh up [--docker|--mininet]  # Start the cyber range (Docker by default)
./industrylab.sh down                     # Stop all processes/containers (0 orphan guarantee)
./industrylab.sh smoke                    # Run HELICS co-simulation with cyber-physical cascade demo
./industrylab.sh test [pytest args]       # Run complete test suite (23 deterministic tests PASS)
./industrylab.sh attack <vector>          # Run offensive Red Team script (recon, coil, fdia, setpoint, dos)
./industrylab.sh profile                  # Measure real RSS memory and CPU usage
./industrylab.sh phase <1|2|3|4>          # Step-by-step engineering phase demonstration
./industrylab.sh status                   # Check health of background services and containers
./industrylab.sh help                     # Display command menu
```

- **Run unit tests directly:**
  ```bash
  PYTHONPATH=. pytest network/tests plc/tests physical/tests helics_sim/tests attacker/tests scada/tests -v
  ```
  `PYTHONPATH=.` is mandatory when invoking pytest directly.

## Architecture — The 4 Layers

1. **Network & Segmentation (IEC 62443 / Purdue Model)**:
   - Enterprise Zone (`10.10.1.0/24`): Workstations, ERP.
   - Industrial DMZ (`10.10.2.0/24`): Jump Host, SCADA Historian (:8080), Airgapped HMI (:8085), Modbus DPI Proxy (:1502).
   - Engineering Zone (`10.10.3.0/24`): EWS Workstation (`10.10.3.50`).
   - OT Cell / Field Zone (`10.10.4.0/24`): PLCs (`10.10.4.10`, `10.10.4.11`), ICSSIM Physics (`10.10.4.20`).
   - Threat / Attacker Zone (`10.10.99.0/24`): Pentesting station (`10.10.99.10`).
   - Enforced by multi-homed Linux router `router_fw` with `FORWARD DROP` default policy and strict conduits.

2. **Control Logic (OpenPLC & IEC 61131-3)**:
   - `plc/st_programs/industrial_cooling.st`: Heat exchanger proportional control and 95°C emergency trip interlock.
   - `plc/st_programs/mining_slurry_conveyor.st`: SAG mill & conveyor interlocks for E-stop, vibration (>11.0 mm/s), and lube pressure (<2.0 bar).
   - `plc/openplc_runtime.py`: Python-based scan cycle engine executing identical ST semantics over Modbus/TCP.

3. **Physical Dynamics & HIL (ICSSIM & HELICS)**:
   - `physical/icssim/plant_cooling.py`: Differential thermodynamic energy balance equation.
   - `physical/icssim/plant_conveyor.py`: Mechanical conveyor velocity and bearing vibration dynamics.
   - `physical/bridge_modbus.py`: Hardware-in-the-Loop bridge synchronizing physical sensors with PLC holding registers.
   - `helics_sim/`: Co-simulation bus coordinating physical plant, PLC logic, and electrical substation feeder.

4. **Defensive & Offensive Stack**:
   - `attacker/attack_*.py`: Modular Red Team tools (discovery, rogue coil write, FDIA sensor spoofing, setpoint tampering, DoS).
   - `network/modbus_dpi_filter.py`: DMZ application proxy restricting write function codes (`FC 05/06/15/16`) to authorized IPs.
   - `scada/historian_service.py`: SCADA polling service with Loss-of-View watchdog and REST API.
   - `scada/hmi_web_server.py`: 100% offline, airgapped SVG/HTML5 interactive dashboard.

## Git Commits and SemVer Tagging Rule (MANDATORY)

- **Always tag every commit**: Whenever generating a git commit, **always** generate its respective annotated git tag on that exact commit.
- **Format**: `vX.Y.Z` adhering to Semantic Versioning (SemVerTag):
  - **X (Major)**: Breaking / incompatible changes or major architecture shifts.
  - **Y (Minor)**: New backward-compatible features, scenarios, federates, or enhancements.
  - **Z (Patch)**: Bug fixes, test stabilization, documentation fixes.
- **Command pattern**:
  ```bash
  git commit -m "<type>(<scope>): <clear description>"
  git tag -a vX.Y.Z -m "vX.Y.Z: <summary of changes>"
  ```
