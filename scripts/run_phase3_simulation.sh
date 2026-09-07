#!/usr/bin/env bash
# ==============================================================================
# IndustryLab — Phase 3: Physical Simulation & HELICS Domino Effects
# ==============================================================================
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================================================"
echo "  IndustryLab — Fase 3: Simulación Física ICSSIM y Co-Simulación HELICS"
echo "================================================================================"

echo "[*] Ejecutando co-simulación con inyección de ataque ciberfísico a t=5s..."
PYTHONPATH="${REPO_ROOT}" python3 "${REPO_ROOT}/helics_sim/run_co_simulation.py" --duration 12.0 --attack-at 5.0 --dt 0.5

echo ""
echo "[+] Telemetría de efecto dominó registrada en logs/cascading_events.csv:"
tail -n 8 "${REPO_ROOT}/logs/cascading_events.csv"
echo "[+] Fase 3 completada con éxito."
