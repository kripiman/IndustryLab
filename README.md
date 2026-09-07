# 🏭 IndustryLab — Cyber Range Industrial (OT/ICS) en Contenedores (IEC 62443)

[![Standard](https://img.shields.io/badge/Standard-IEC%2062443-blue.svg)](https://www.isa.org/standards-and-publications/isa-standards/isa-standards-committees/isa62443)
[![Purdue Model](https://img.shields.io/badge/Architecture-Purdue%20PERA%20(L0--L5)-orange.svg)](#1-arquitectura-y-fundamentos-bajo-el-est%C3%A1ndar-iec-62443)
[![Tests](https://img.shields.io/badge/Tests-23%20PASS%20(100%25)-brightgreen.svg)](#4-bater%C3%ADa-de-pruebas)
[![Stack](https://img.shields.io/badge/Stack-Docker%20%7C%20Kathar%C3%A1%20%7C%20Mininet-purple.svg)](#2-stack-tecnol%C3%B3gico-ligero-y-optimizado-100-software)
[![Co-Simulation](https://img.shields.io/badge/Co--Simulation-HELICS%203.x-red.svg)](https://helics.org/)
[![Memory](https://img.shields.io/badge/RAM%20Footprint-%3C250%20MB-success.svg)](#medici%C3%B3n-de-recursos)

**IndustryLab** es un entorno de entrenamiento y simulación de ciberseguridad industrial (*Cyber Range*) 100% basado en software y contenedores ligeros. Diseñado bajo los lineamientos del estándar internacional **IEC 62443** y el **Modelo Purdue (PERA)**, permite emular redes de control operacional, autómatas programables (PLCs), modelos físicos continuos de plantas industriales y faenas mineras, y el impacto de ciberataques ciberfísicos que desencadenan fallas en cascada (*domino effects*).

---

## 🌟 Características Destacadas

- **0% Sobrecarga de Máquinas Virtuales**: Ejecución nativa en Linux mediante contenedores Docker, Kathará o espacios de nombres de red en Mininet, con un consumo global inferior a **250 MB de RAM**.
- **Segmentación Estricta IEC 62443**: Zonas Corporativa (L4/5), DMZ Industrial (L3.5), Ingeniería (L3) y Celda OT (L0-2) con conductos (*conduits*) estrictamente filtrados (`FORWARD DROP`).
- **Lógica de Control Real (IEC 61131-3)**: Programas en **Structured Text (.st)** para OpenPLC que gobiernan sistemas de enfriamiento térmico por intercambiador de calor y circuitos de molienda y transporte minero.
- **Hardware-in-the-Loop (HIL) con ICSSIM**: Modelos dinámicos en Python basados en ecuaciones diferenciales (balances térmicos de primer orden, masa y dinámica mecánica de correas) acoplados en tiempo real mediante **Modbus/TCP**.
- **Orquestación de Efectos Dominó con HELICS**: Bus de co-simulación temporal sincronizada que vincula la inyección de ataques lógicos con sobrecalentamiento físico y el posterior disparo de protecciones en subestaciones eléctricas (Blackout industrial).
- **Inspección Profunda de Paquetes (DPI)**: Proxy de capa de aplicación que valida códigos de función Modbus (`FC 01-04` permitidos; `FC 05/06/15/16` restringidos a IPs de ingeniería autorizadas).
- **Visualizador HMI Airgapped**: Dashboard interactivo SVG/HTML5/CSS en tiempo real (puerto `:8085`), 100% offline y sin dependencias externas.

---

## 📐 1. Arquitectura y Fundamentos bajo el Estándar IEC 62443

El laboratorio modela la estricta separación física y lógica entre el mundo de las tecnologías de la información (IT) y los procesos operacionales (OT):

```
[Nivel 4-5: Zona Corporativa / IT - 10.10.1.0/24]
        │
        ├── corp_ws  (10.10.1.50)  Estación de trabajo corporativa
        └── corp_srv (10.10.1.10)  Servidor ERP empresarial
        │
      (eth0)
┌─────────────────────────────────────────────────────────────┐
│  Firewall / Router Perimetral Industrial (router_fw)        │
│  - Política por defecto: FORWARD DROP                       │
│  - Conducto C-02: Bloqueo estricto IT -> OT (Salto directo) │
│  - Registro de auditoría: [IEC62443-VIOLATION]              │
└─────────────────────────────────────────────────────────────┘
      (eth1)                      (eth2)                      (eth3)
        │                           │                           │
[Nivel 3.5: Industrial DMZ]     [Nivel 3: Ingeniería]       [Nivel 0-2: Celda OT / Campo]
  Subnet 10.10.2.0/24             Subnet 10.10.3.0/24         Subnet 10.10.4.0/24
  ├── dmz_jump (10.10.2.10)       └── ews_host                ├── plc_cooling (10.10.4.10)
  │    SSH Bastion                     (10.10.3.50)           │    OpenPLC Intercambiador
  ├── dmz_historian                   Estación EWS            ├── plc_conveyor (10.10.4.11)
  │    (10.10.2.20) :8080                                     │    OpenPLC Molienda/Correa
  ├── dmz_hmi (10.10.2.30)                                    └── icssim_physics (10.10.4.20)
  │    HMI SVG :8085                                               Simulador Físico HIL
  └── dmz_dpi_proxy (10.10.2.40)
       Proxy DPI Modbus :1502
```

### Tabla de Conductos y Políticas de Tráfico

| ID Conducto | Origen | Destino | Protocolos / Puertos | Acción | Propósito Operacional |
|---|---|---|---|---|---|
| **C-01** | Red IT `10.10.1.0/24` | IDMZ `10.10.2.0/24` | TCP 22 (SSH), TCP 8085 (HMI) | `ACCEPT` | Monitoreo supervisado y acceso administrativo |
| **C-02** | Red IT `10.10.1.0/24` | Celda OT `10.10.4.0/24` | CUALQUIERA | **`DROP + LOG`** | **Aislamiento IEC 62443**: Prohibido acceso directo a PLCs |
| **C-03** | IDMZ Historian / DPI | Celda OT `10.10.4.0/24` | TCP 502, TCP 5020 | `ACCEPT` | Lectura de registros y polling de telemetría |
| **C-04** | EWS `10.10.3.50` | Celda OT `10.10.4.0/24` | TCP 502, TCP 8080 | `ACCEPT` | Carga de lógica IEC 61131-3 y calibración |
| **C-05** | Amenaza `10.10.99.0/24`| Celda OT `10.10.4.0/24` | CUALQUIERA | **`DROP`** | Obliga al atacante a pivotar a través de IT/DMZ |

---

## 🧰 2. Stack Tecnológico Ligero y Optimizado (100% Software)

| Capa / Subsistema | Tecnología Utilizada | Rol en la Arquitectura |
|---|---|---|
| **Red y Segmentación** | **Docker Compose**, **Kathará** y **Mininet** | Emulación multi-zona con routers Linux, tablas de enrutamiento y reglas `iptables`. |
| **Lógica de Control (PLC)** | **OpenPLC** + IEC 61131-3 Structured Text | Motor de ejecución del ciclo de scan (%IX, %QX, %IW, %QW) con servidor Modbus/TCP. |
| **Capa Física y HIL** | **ICSSIM** (Python nativo) | Modelos físicos continuos acoplados en lazo cerrado con los registros del PLC. |
| **Efectos en Cascada** | **HELICS 3.x** | Co-simulación federada que propaga el ataque cibernético a la red eléctrica. |
| **Defensa y Supervisión** | **Proxy DPI** + **SCADA Historian** + **HMI SVG** | Filtrado de comandos no autorizados, detección de pérdida de visión y telemetría. |
| **Red Team Pentesting** | **Python + `pymodbus`** | Scripts modulares de inyección de comandos, FDIA, manipulación de consignas y DoS. |

---

## 🚀 3. Metodología de Implementación: Nodo Mínimo Viable (PoC)

El proyecto se estructura y valida en 4 fases progresivas:

### Fase 1: Red y Segmentación
Se configuran los conductos y reglas de cortafuegos en el router de borde:
```bash
./industrylab.sh phase 1
```

### Fase 2: Lógica de Control (PLC)
Se compila y ejecuta la lógica de control en Structured Text ([`industrial_cooling.st`](file:///home/kripi/Documentos/GitHub/IndustryLab/plc/st_programs/industrial_cooling.st) y [`mining_slurry_conveyor.st`](file:///home/kripi/Documentos/GitHub/IndustryLab/plc/st_programs/mining_slurry_conveyor.st)):
```bash
./industrylab.sh phase 2
```

### Fase 3: Simulación Física y Efecto Cascada (HELICS)
Se acopla la física termodinámica y mecánica en tiempo real; ante un ataque, la planta entra en rampa térmica y dispara la subestación eléctrica:
```bash
./industrylab.sh phase 3
# o para una ejecución interactiva completa:
./industrylab.sh smoke
```

### Fase 4: Pentesting Ofensivo y Validación de Seguridad
Desde la estación de ataque se ejecutan ataques de reconocimiento, inyección de bobinas (Coil 0 OFF), spoofing de sensores (FDIA) y manipulación de setpoints:
```bash
./industrylab.sh phase 4
```

---

## ⚡ 4. Guía Rápida de Comandos

`./industrylab.sh` es el **punto de entrada único** del laboratorio:

```bash
# 1. Iniciar el laboratorio completo en contenedores Docker
./industrylab.sh up

# 2. Abrir la consola HMI Industrial en el navegador
# http://localhost:8085

# 3. Consultar la API REST del Historian SCADA
curl http://localhost:8080/api/snapshot

# 4. Lanzar un ataque de inyección de bobina Modbus
./industrylab.sh attack coil

# 5. Ejecutar la batería completa de pruebas automatizadas
./industrylab.sh test

# 6. Medir el consumo real de RAM y CPU
./industrylab.sh profile

# 7. Detener y limpiar todo (Garantía de 0 procesos huérfanos)
./industrylab.sh down
```

---

## 🎯 5. ¿Cómo presentar esto en tu Portafolio o CV?

Incorporar este proyecto en tu perfil profesional demuestra ante consultoras de ciberseguridad, empresas de energía, minería y manufactura crítica habilidades altamente cotizadas y escasas en el mercado:

### Viñetas listas para tu Currículum Vitae (CV)
- **Ingeniero de Ciberseguridad OT / Desarrollador Cyber Range**:
  - *Diseñó e implementó un Cyber Range Ciberfísico Industrial (OT/ICS) ligero (<250 MB RAM) en contenedores Docker y Python bajo el estándar internacional **IEC 62443** y el **Modelo Purdue (Niveles 0 a 5)**.*
  - *Programó autómatas en **Structured Text (IEC 61131-3)** sobre OpenPLC integrando lazo cerrado de control con simulación física continua (**ICSSIM**) de intercambiadores de calor y molinos SAG.*
  - *Orquestó escenarios de fallas en cascada (*domino effects*) con **HELICS 3.x**, conectando la manipulación de registros Modbus con disparos por sobrecarga térmica en la subestación eléctrica.*
  - *Desarrolló un proxy de inspección profunda de paquetes (**Modbus DPI**) para mitigar ataques de inyección de comandos no autorizados (`FC 05/06`), y una suite de pruebas con **23 tests automatizados en Pytest**.*

### Puntos clave para entrevistas técnicas (Método STAR)
1. **Prioridades OT vs IT**: Explica que en OT prima la **seguridad física de las personas, los equipos y la continuidad operacional (SRI: Safety, Reliability, Integrity)** por sobre la confidencialidad.
2. **Segmentación Efectiva**: Describe cómo implementaste la regla `FORWARD DROP` para evitar que un ransomware en la red corporativa alcance la celda de control.
3. **Consecuencias Ciberfísicas**: Enfatiza que tus scripts ofensivos no solo envían paquetes a un puerto, sino que alteran variables de estado físico (temperatura, presión, vibración) provocando disparos reales de protecciones eléctricas.

Consulta la guía completa en [docs/PORTFOLIO_CV_GUIDE.md](docs/PORTFOLIO_CV_GUIDE.md).

---

## 📚 Documentación Técnica Detallada

- 🏗️ **[Arquitectura y Modelo Matemático Ciberfísico](docs/ARCHITECTURE.md)**: Diagramas, modelos de ecuaciones diferenciales y mapas de memoria Modbus.
- 🛠️ **[Manual de Operaciones y Despliegue](docs/OPERATIONS.md)**: Instrucciones detalladas para Docker, Kathará y Mininet.
- 📋 **[Matriz de Cumplimiento IEC 62443](docs/IEC62443_COMPLIANCE.md)**: Mapeo de Requisitos Fundamentales (FR1 a FR7).
- 💼 **[Guía de Portafolio y Empleabilidad OT/ICS](docs/PORTFOLIO_CV_GUIDE.md)**: Guía estratégica para destacar en procesos de selección.
