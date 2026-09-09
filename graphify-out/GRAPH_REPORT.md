# Graph Report - .  (2026-09-08)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 281 nodes · 396 edges · 28 communities (15 shown, 13 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `62f4455b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ModbusPlcServer
- run_co_simulation.py
- FedICSSIM
- IEC 62443 Conduits Configuration
- test_attack_scripts.py
- ModbusDpiProxy
- HistorianStore
- HilModbusBridge
- LinuxRouter
- industrylab.sh
- HmiRequestHandler
- Control and Field Zone Level 0-2
- test_firewall_rules.py
- attack_register_tamper.py
- Audit Executive Summary and Score
- Consolidated Security Findings Table
- IndustryLab Overview
- conftest.py
- firewall_rules.sh
- run_phase1_network.sh
- run_phase2_plc.sh
- run_phase3_simulation.sh
- run_phase4_offensive.sh
- Git Commits and SemVer Tagging Rule
- Buffer Tank TK-301 Process Map
- 4-Phase Engineering Methodology
- BaseHTTPRequestHandler

## God Nodes (most connected - your core abstractions)
1. `ModbusPlcServer` - 32 edges
2. `IEC 62443 Conduits Configuration` - 11 edges
3. `industrylab.sh script` - 10 edges
4. `FedICSSIM` - 9 edges
5. `SlurryConveyorPlant` - 9 edges
6. `ThermalCoolingPlant` - 9 edges
7. `FedPLC` - 9 edges
8. `ModbusDpiProxy` - 9 edges
9. `CoolingControlLogic` - 9 edges
10. `HilModbusBridge` - 8 edges

## Surprising Connections (you probably didn't know these)
- `IEC 62443 Conduits Configuration` --semantically_similar_to--> `Purdue Architecture and Security Zones Specification`  [INFERRED] [semantically similar]
  config/purdue_model.yaml → docs/ARCHITECTURE.md
- `Hardware Resource Footprint Benchmark` --semantically_similar_to--> `Audit Executive Summary and Score`  [INFERRED] [semantically similar]
  logs/resource_profile_summary.txt → docs/AUDIT_REPORT.md
- `Purdue Multi-Zone Docker Networks` --implements--> `IEC 62443 Conduits Configuration`  [INFERRED]
  network/docker-compose.yml → config/purdue_model.yaml
- `indlab_router_fw Container Service` --implements--> `IEC 62443 Conduits Configuration`  [INFERRED]
  network/docker-compose.yml → config/purdue_model.yaml
- `test_recon_scanner_finds_registers()` --calls--> `ModbusPlcServer`  [EXTRACTED]
  attacker/tests/test_attack_scripts.py → plc/modbus_server.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Purdue Security Zones and Conduits** — config_purdue_model_enterprise_zone, config_purdue_model_dmz_zone, config_purdue_model_engineering_zone, config_purdue_model_ot_cell_zone, config_purdue_model_attacker_zone [EXTRACTED 1.00]
- **Industrial Cyber-Physical Process Loops** — config_industrial_process_cooling_loop, config_industrial_process_slurry_conveyor, config_industrial_process_buffer_tank [EXTRACTED 1.00]
- **IEC 62443 Cyber Range Verification Pipeline** — docs_iec62443_compliance_matrix, docs_audit_prompt_scope, docs_audit_report_iec62443_compliance [EXTRACTED 1.00]

## Communities (28 total, 13 thin omitted)

### Community 0 - "ModbusPlcServer"
Cohesion: 0.09
Nodes (17): ModbusSequentialDataBlock, ModbusPlcServer, Thread-safe ModbusSequentialDataBlock sharing server lock to prevent race condit, ThreadSafeDataBlock, ConveyorControlLogic, CoolingControlLogic, main(), OpenPLCRuntime (+9 more)

### Community 1 - "run_co_simulation.py"
Cohesion: 0.09
Nodes (12): CascadingEventLogger, IndustryLab — HELICS Federate: Cascading Event & Domino Effect Logger Records sy, FedPLC, IndustryLab — HELICS Federate: PLC Control Loop Executes proportional control an, FedPowerGrid, IndustryLab — HELICS Federate: Electrical Substation (Cascading Power Grid) Mode, Evaluates electrical protection relays.         If reactor/mill temperature reac, main() (+4 more)

### Community 2 - "FedICSSIM"
Cohesion: 0.12
Nodes (12): FedICSSIM, IndustryLab — HELICS Federate: ICSSIM Physical Dynamics Publishes process temper, IndustryLab — ICSSIM Mining Slurry Conveyor & SAG Mill Physical Model Simulates, SlurryConveyorPlant, IndustryLab — ICSSIM Thermal Heat Exchanger Dynamic Physical Model Simulates the, ThermalCoolingPlant, Unit tests for Mining Slurry Conveyor Physical Model., test_conveyor_bearing_vibration_escalation_on_lube_loss() (+4 more)

### Community 3 - "IEC 62443 Conduits Configuration"
Cohesion: 0.11
Nodes (22): 4-Layer Cyber Range Architecture, Simulated Threat and Pentesting Zone, IEC 62443 Conduits Configuration, Industrial DMZ Level 3.5, Operations and Engineering Zone Level 3, Enterprise Zone Level 4-5, Purdue Architecture and Security Zones Specification, IEC 62443-3-3 FR1-FR7 Compliance Analysis (+14 more)

### Community 4 - "test_attack_scripts.py"
Cohesion: 0.15
Nodes (15): execute_attack(), main(), execute_dos(), main(), measure_probe_latency(), Measures round-trip response latency (ms) for a legitimate Modbus query (SEC-13), main(), scan_target() (+7 more)

### Community 5 - "ModbusDpiProxy"
Cohesion: 0.19
Nodes (13): main(), make_modbus_exception(), ModbusDpiProxy, parse_modbus_pdu(), Inspects incoming client Modbus request.         Returns: (allow_forward, option, Parses MBAP Header (7 bytes) and Modbus PDU:     Bytes 0-1: Transaction ID     B, Creates a standard Modbus TCP Exception response (Error FC = FC + 0x80)., Tests for Modbus Deep Packet Inspection (DPI) Proxy. (+5 more)

### Community 6 - "HistorianStore"
Cohesion: 0.15
Nodes (5): HistorianRequestHandler, HistorianStore, main(), BaseHTTPRequestHandler, ScadaHistorian

### Community 7 - "HilModbusBridge"
Cohesion: 0.16
Nodes (7): HilModbusBridge, main(), Executes one HIL synchronization cycle., BufferTankPlant, IndustryLab — ICSSIM Buffer Storage Tank Dynamics Simulates tank level mass bala, Unit tests for Buffer Tank Physical Model., test_hil_modbus_bridge_tank_integration()

### Community 8 - "LinuxRouter"
Cohesion: 0.17
Nodes (11): apply_firewall_rules(), LinuxRouter, main(), PurdueTopo, Automated test validating IEC 62443 isolation policies., A Node with IP forwarding and iptables capability acting as an IEC 62443 Firewal, Purdue Reference Architecture Topo:     Zone 1: Enterprise (10.10.1.0/24)     Zo, Configures iptables on the fw node to implement IEC 62443 conduits. (+3 more)

### Community 9 - "industrylab.sh"
Cohesion: 0.28
Nodes (12): cmd_attack(), cmd_down(), cmd_phase(), cmd_profile(), cmd_smoke(), cmd_status(), cmd_test(), cmd_up() (+4 more)

### Community 10 - "HmiRequestHandler"
Cohesion: 0.21
Nodes (6): BaseHTTPRequestHandler, HmiRequestHandler, main(), run_hmi(), Unit tests for SCADA Historian and Alarm Monitoring., test_hmi_server_and_reverse_proxy()

### Community 11 - "Control and Field Zone Level 0-2"
Cohesion: 0.22
Nodes (11): Cooling Loop E-101 Process Map, Slurry Conveyor CV-201 and SAG Mill ML-201 Process Map, Control and Field Zone Level 0-2, Ore Conveyor CV-201 and SAG Mill Kinematic Model, HELICS 3.x Cascading Domino Effects Bus, Exchanger E-101 First-Order Thermodynamic Model, Physical and HELICS Cascade Fidelity Evaluation, indlab_icssim_physics Container Service (+3 more)

### Community 14 - "Audit Executive Summary and Score"
Cohesion: 0.67
Nodes (3): Audit Report Structure Guidelines, Audit Executive Summary and Score, Hardware Resource Footprint Benchmark

### Community 15 - "Consolidated Security Findings Table"
Cohesion: 0.67
Nodes (3): Audit Scope 6 Mandatory Dimensions, Consolidated Security Findings Table, Prioritized Remediation Plan P0, P1, P2

## Knowledge Gaps
- **18 isolated node(s):** `run_phase1_network.sh script`, `run_phase2_plc.sh script`, `run_phase3_simulation.sh script`, `run_phase4_offensive.sh script`, `IndustryLab Overview` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ModbusPlcServer` connect `ModbusPlcServer` to `test_attack_scripts.py`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Why does `apply_firewall_rules()` connect `LinuxRouter` to `run_co_simulation.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ModbusPlcServer` (e.g. with `ConveyorControlLogic` and `CoolingControlLogic`) actually correct?**
  _`ModbusPlcServer` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `IEC 62443 Conduits Configuration` (e.g. with `Purdue Architecture and Security Zones Specification` and `Purdue Multi-Zone Docker Networks`) actually correct?**
  _`IEC 62443 Conduits Configuration` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `FedICSSIM` (e.g. with `SlurryConveyorPlant` and `ThermalCoolingPlant`) actually correct?**
  _`FedICSSIM` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `run_phase1_network.sh script`, `run_phase2_plc.sh script`, `run_phase3_simulation.sh script` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ModbusPlcServer` be split into smaller, more focused modules?**
  _Cohesion score 0.08637873754152824 - nodes in this community are weakly interconnected._