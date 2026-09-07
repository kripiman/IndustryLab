#!/usr/bin/env bash
# ==============================================================================
# IndustryLab — Phase 2: Control Logic & OpenPLC IEC 61131-3
# ==============================================================================
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================================================"
echo "  IndustryLab — Fase 2: Lógica de Control (OpenPLC & Structured Text)"
echo "================================================================================"

echo "[*] Programas IEC 61131-3 Structured Text compilables:"
ls -lh "${REPO_ROOT}/plc/st_programs/"

echo ""
echo "[*] Iniciando OpenPLC Runtime (Heat Exchanger Cooling) en puerto 1502..."
PYTHONPATH="${REPO_ROOT}" python3 -c "
from plc.openplc_runtime import OpenPLCRuntime
import time

rt = OpenPLCRuntime(process='cooling', host='127.0.0.1', port=1502, scan_period_s=0.05)
rt.modbus.start(background=True)
print('[+] OpenPLC Modbus Server escuchando en 127.0.0.1:1502')
for cycle in range(5):
    rt.logic.scan_cycle()
    time.sleep(0.05)
print('[+] 5 ciclos de scan PLC ejecutados exitosamente.')
rt.modbus.stop()
"
echo "[+] Fase 2 completada con éxito."
