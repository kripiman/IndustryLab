# 🛠️ IndustryLab — Guía de Operaciones y Manual de Despliegue

## 1. Requisitos Previos del Sistema

- **Sistema Operativo**: Linux nativo (Ubuntu 22.04+, Debian 12+, Arch Linux o similar).
- **Python**: Versión 3.10 o superior con `pip`.
- **Contenedores**: Docker Engine y Docker Compose (opcional para modo contenedor).
- **Herramientas de red**: `iptables`, `iproute2` (opcional: `mininet`, `kathara`).
- **Memoria RAM**: $< 500\text{ MB}$ para toda la infraestructura en ejecución.

---

## 2. Despliegue Rápido con `industrylab.sh`

El script `./industrylab.sh` es el punto de entrada unificado:

```bash
# Ver menú de ayuda
./industrylab.sh help

# Desplegar el Cyber Range en contenedores Docker
./industrylab.sh up --docker

# Desplegar localmente sin Docker (máxima ligereza)
./industrylab.sh up local

# Ejecutar co-simulación física con HELICS
./industrylab.sh smoke

# Ejecutar la suite completa de 23 tests de validación
./industrylab.sh test

# Medir el consumo real de hardware (RAM / CPU)
./industrylab.sh profile

# Detener el laboratorio y limpiar procesos (0 procesos huérfanos)
./industrylab.sh down
```

---

## 3. Pruebas Ofensivas (Red Team Pentesting)

Con el laboratorio en ejecución (vía Docker o local), ejecuta los vectores ofensivos:

```bash
# 1. Reconocimiento OT (Mapeo de registros y UIDs Modbus)
./industrylab.sh attack recon

# 2. Inyección de Comandos (Parada forzada de bomba y bloqueo manual)
./industrylab.sh attack coil

# 3. Spoofing de Sensores (False Data Injection Attack - FDIA)
./industrylab.sh attack fdia

# 4. Modificación de Consigna Térmica y Ganancia Proporcional
./industrylab.sh attack setpoint

# 5. Ataque de Denegación de Servicio (DoS Modbus Flooding)
./industrylab.sh attack dos
```

---

## 4. Acceso a Interfaces de Monitoreo (Blue Team)

- **HMI Web Central (Airgapped SVG)**: `http://localhost:8085`
- **SCADA Historian REST API**: `http://localhost:8080/api/snapshot`
- **Telemetría en Vivo (JSON)**: `http://localhost:8080/api/telemetry`
- **Alarmas Activas (JSON)**: `http://localhost:8080/api/alarms`
- **Proxy Modbus con Inspección DPI**: `localhost:1502`
- **Log de Eventos en Cascada CSV**: `logs/cascading_events.csv`
