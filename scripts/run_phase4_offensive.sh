#!/usr/bin/env bash
# ==============================================================================
# IndustryLab — Phase 4: Industrial Pentesting & Defensive Response
# ==============================================================================
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================================================"
echo "  IndustryLab — Fase 4: Pentesting Ofensivo y Validación de Seguridad OT"
echo "================================================================================"

TEST_PORT=15020

echo "[*] Levantando PLC emulado temporal en puerto ${TEST_PORT}..."
PYTHONPATH="${REPO_ROOT}" python3 -c "
from plc.openplc_runtime import OpenPLCRuntime
import time

rt = OpenPLCRuntime(process='cooling', host='127.0.0.1', port=${TEST_PORT}, scan_period_s=0.05)
rt.modbus.start(background=True)

print('\n--- 1. Reconocimiento OT (Modbus Discovery) ---')
from attacker.attack_recon import scan_target
scan_target('127.0.0.1', port=${TEST_PORT}, unit_ids=[1])

print('\n--- 2. Inyección Ofensiva de Comandos (Rogue Coil Injection) ---')
from attacker.attack_coil_injection import execute_attack
execute_attack('127.0.0.1', port=${TEST_PORT}, unit_id=1)

print('\n--- 3. Manipulación Maliciosa de Setpoint ---')
from attacker.attack_setpoint_tamper import execute_setpoint_tamper
execute_setpoint_tamper('127.0.0.1', port=${TEST_PORT}, new_sp_c=88.0, new_kp=95)

rt.modbus.stop()
"

echo ""
echo "[+] Fase 4 completada con éxito."
