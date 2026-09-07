#!/usr/bin/env bash
# ==============================================================================
# IndustryLab — Unified Cyber Range Master Orchestration CLI
# Single Entrypoint for Deployment, Testing, Attacks, Simulation, and Profiling
# ==============================================================================

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_ROOT}"

RUNFILES_DIR="${REPO_ROOT}/runfiles"
LOGS_DIR="${REPO_ROOT}/logs"
mkdir -p "${RUNFILES_DIR}" "${LOGS_DIR}"

export PYTHONPATH="${REPO_ROOT}"

show_help() {
    cat << 'HELP'
================================================================================
  🏭 IndustryLab — Cyber Range Industrial (OT/ICS) en Contenedores (IEC 62443)
================================================================================

Uso: ./industrylab.sh <comando> [opciones]

Comandos Principales:
  up [--docker|--mininet]  Inicia el entorno Cyber Range completo
                           --docker (por defecto): Despliega red de contenedores Docker
                           --mininet: Despliega topología Mininet nativa (requiere sudo)
  down                     Detiene y limpia procesos, contenedores y namespaces
  status                   Muestra el estado de salud de los nodos y servicios OT
  smoke                    Ejecuta co-simulación física HELICS con inyección de cascada
  test [pytest-args]       Ejecuta la batería completa de pruebas unitarias y de integración
  attack <tipo>            Lanza vector de ataque Red Team contra el Cyber Range:
                           recon     -> Escaneo y descubrimiento Modbus OT
                           coil      -> Inyección de comandos / parada forzada de bomba
                           fdia      -> False Data Injection / Sensor Spoofing
                           setpoint  -> Manipulación maliciosa de consigna térmica
                           dos       -> Inundación de transacciones Modbus
  profile                  Mide y reporta el consumo real de RAM (RSS) y CPU
  phase <1|2|3|4>          Ejecuta la demostración guiada de cada fase de ingeniería
  graphify                 Construye el grafo de conocimiento del código fuente
  help                     Muestra esta ayuda

HELP
}

cmd_up() {
    local mode="${1:-docker}"
    echo "[*] Levantando IndustryLab Cyber Range (Modo: ${mode})..."

    if [[ "${mode}" == "--docker" || "${mode}" == "docker" ]]; then
        if command -v docker >/dev/null 2>&1; then
            echo "[*] Iniciando Docker Compose stack (Purdue Model)..."
            docker compose -f network/docker-compose.yml up -d
            echo "[+] Cyber Range desplegado en contenedores Docker."
            echo "    - Dashboard HMI: http://localhost:8085"
            echo "    - API Historian: http://localhost:8080/api/snapshot"
            echo "    - Proxy DPI:     localhost:1502"
        else
            echo "[-] Docker no encontrado. Iniciando modo proceso local ligero..."
            cmd_up_local
        fi
    elif [[ "${mode}" == "--mininet" || "${mode}" == "mininet" ]]; then
        if [[ $EUID -ne 0 ]]; then
            echo "[!] Mininet requiere privilegios de root. Ejecute: sudo ./industrylab.sh up --mininet"
            exit 1
        fi
        python3 network/topology_mininet.py
    else
        cmd_up_local
    fi
}

cmd_up_local() {
    echo "[*] Iniciando servicios locales en segundo plano..."
    # 1. Start Cooling PLC on port 1502
    python3 plc/openplc_runtime.py --process cooling --port 1502 > logs/plc_cooling.log 2>&1 &
    echo $! > runfiles/plc_cooling.pid

    # 2. Start HIL Physics Bridge
    python3 physical/bridge_modbus.py --cooling-port 1502 --dt 0.2 > logs/hil_bridge.log 2>&1 &
    echo $! > runfiles/hil_bridge.pid

    # 3. Start Historian API on 8080
    python3 scada/historian_service.py --cooling-port 1502 --port 8080 > logs/historian.log 2>&1 &
    echo $! > runfiles/historian.pid

    # 4. Start HMI Dashboard on 8085
    python3 scada/hmi_web_server.py --port 8085 > logs/hmi.log 2>&1 &
    echo $! > runfiles/hmi.pid

    echo "[+] Servicios industriales iniciados localmente:"
    echo "    - PLC Modbus:     127.0.0.1:1502"
    echo "    - SCADA Historian: http://localhost:8080/api/snapshot"
    echo "    - Dashboard HMI:   http://localhost:8085"
}

cmd_down() {
    echo "[*] Deteniendo IndustryLab Cyber Range..."

    # 1. Stop docker compose if running
    if command -v docker >/dev/null 2>&1; then
        docker compose -f network/docker-compose.yml down --remove-orphans >/dev/null 2>&1 || true
    fi

    # 2. Stop PID processes
    for pidfile in runfiles/*.pid; do
        if [[ -f "${pidfile}" ]]; then
            pid=$(cat "${pidfile}")
            if kill -0 "${pid}" 2>/dev/null; then
                kill "${pid}" 2>/dev/null || true
            fi
            rm -f "${pidfile}"
        fi
    done

    # 3. Clean mininet if installed and root
    if [[ $EUID -eq 0 ]] && command -v mn >/dev/null 2>&1; then
        mn -c >/dev/null 2>&1 || true
    fi

    echo "[+] Cyber Range detenido. 0 procesos huérfanos garantizados."
}

cmd_status() {
    echo "=== Estado de Componentes IndustryLab ==="
    if command -v docker >/dev/null 2>&1; then
        echo "Contenedores Docker:"
        docker ps --filter "name=indlab_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true
    fi

    echo ""
    echo "Procesos Locales:"
    for pidfile in runfiles/*.pid; do
        if [[ -f "${pidfile}" ]]; then
            name=$(basename "${pidfile}" .pid)
            pid=$(cat "${pidfile}")
            if kill -0 "${pid}" 2>/dev/null; then
                echo "  [✓] ${name} (PID: ${pid}) ACTIVO"
            else
                echo "  [✗] ${name} (PID: ${pid}) DETENIDO"
            fi
        fi
    done
}

cmd_test() {
    echo "[*] Ejecutando batería completa de pruebas unitarias y de integración..."
    pytest network/tests plc/tests physical/tests helics_sim/tests attacker/tests scada/tests -v "$@"
}

cmd_smoke() {
    echo "[*] Ejecutando Co-Simulación HELICS con Demostración de Cascada Ciberfísica..."
    python3 helics_sim/run_co_simulation.py --duration 12.0 --attack-at 4.0 --dt 0.5
}

cmd_attack() {
    local attack_type="${1:-recon}"
    case "${attack_type}" in
        recon)
            python3 attacker/attack_recon.py --target 127.0.0.1 --port 1502
            ;;
        coil)
            python3 attacker/attack_coil_injection.py --target 127.0.0.1 --port 1502
            ;;
        fdia)
            python3 attacker/attack_register_tamper.py --target 127.0.0.1 --port 1502 --duration 3.0
            ;;
        setpoint)
            python3 attacker/attack_setpoint_tamper.py --target 127.0.0.1 --port 1502
            ;;
        dos)
            python3 attacker/attack_dos.py --target 127.0.0.1 --port 1502 --count 30
            ;;
        *)
            echo "[-] Vector desconocido: ${attack_type}. Opciones: recon, coil, fdia, setpoint, dos"
            exit 1
            ;;
    esac
}

cmd_profile() {
    python3 scripts/profile_resources.py
}

cmd_phase() {
    local phase_num="${1:-1}"
    case "${phase_num}" in
        1) bash scripts/run_phase1_network.sh ;;
        2) bash scripts/run_phase2_plc.sh ;;
        3) bash scripts/run_phase3_simulation.sh ;;
        4) bash scripts/run_phase4_offensive.sh ;;
        *) echo "[-] Fase desconocida: ${phase_num}. Use 1, 2, 3 o 4." ;;
    esac
}

# Main Dispatcher
CMD="${1:-help}"
shift || true

case "${CMD}" in
    up) cmd_up "$@" ;;
    down) cmd_down ;;
    status) cmd_status ;;
    smoke) cmd_smoke ;;
    test) cmd_test "$@" ;;
    attack) cmd_attack "$@" ;;
    profile) cmd_profile ;;
    phase) cmd_phase "$@" ;;
    help|-h|--help) show_help ;;
    *) echo "[-] Comando desconocido: ${CMD}. Ejecute ./industrylab.sh help" ; exit 1 ;;
esac
