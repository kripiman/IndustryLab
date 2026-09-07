#!/usr/bin/env bash
# ==============================================================================
# IndustryLab — Phase 1: Network & Segmentation (IEC 62443 / Purdue Model)
# ==============================================================================
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================================================"
echo "  IndustryLab — Fase 1: Red y Segmentación Industrial (IEC 62443 / Purdue)"
echo "================================================================================"

bash "${REPO_ROOT}/network/firewall_rules.sh" --print-rules

echo ""
echo "[*] Opciones de Despliegue de Red:"
echo "    1. Docker Compose: docker compose -f network/docker-compose.yml up -d"
echo "    2. Kathará Lab:    cd network/kathara && kathara lstart"
echo "    3. Mininet (Sudo): sudo python3 network/topology_mininet.py --test"
echo ""
echo "[+] Fase 1 verificada con éxito."
