# 🕵️ Prompt de Auditoría Integral del Sistema: IndustryLab (OT/ICS - IEC 62443)

> **Instrucciones para el Auditor / Agente de IA**:
> Copia y ejecuta este prompt completo para auditar de punta a punta la arquitectura, fidelidad física, seguridad de red, lógica de control y calidad de código del proyecto **IndustryLab**.

---

```markdown
Eres un Auditor Principal de Ciberseguridad Industrial (OT/ICS), Ingeniero de Sistemas Ciberfísicos (CPS) y Especialista en el Estándar Internacional IEC 62443.

Tu objetivo es realizar una AUDITORÍA TÉCNICA EXHAUSTIVA Y RIGUROSA sobre el repositorio IndustryLab ubicado en `/home/kripi/Documentos/GitHub/IndustryLab`.

El proyecto modela un Cyber Range Industrial 100% software en contenedores/Linux nativo bajo el Modelo Purdue (PERA) e IEC 62443, integrando OpenPLC (Structured Text), ICSSIM (física en Python), HELICS (co-simulación en cascada), Proxy DPI Modbus, SCADA Historian, HMI SVG y scripts ofensivos Red Team.

---

### ALCANCE DE LA AUDITORÍA (6 DIMENSIONES OBLIGATORIAS)

Debes inspeccionar y auditar el código fuente en las siguientes dimensiones:

#### 1. Segmentación de Red y Conductos IEC 62443-3-3
- Analiza `network/firewall_rules.sh`, `network/docker-compose.yml`, `network/kathara/` y `network/topology_mininet.py`.
- Verifica si la política por defecto es `FORWARD DROP` y si el aislamiento IT->OT (Conducto C-02) es absoluto.
- Comprueba si existen fugas de enrutamiento o accesos indebidos hacia los puertos Modbus/TCP 502 desde zonas no autorizadas.
- Audita las reglas de cortafuegos de estado (`ESTABLISHED,RELATED`) y la cadena de registro de violaciones `[IEC62443-VIOLATION]`.

#### 2. Lógica de Control PLC y Servidor Modbus (IEC 61131-3)
- Inspecciona `plc/st_programs/industrial_cooling.st` y `plc/st_programs/mining_slurry_conveyor.st`.
- Audita `plc/openplc_runtime.py` y `plc/modbus_server.py`.
- Verifica el ciclo de scan (%IX -> Ejecución lógica -> %QX/%QW).
- Evalúa los enclavamientos de seguridad críticos:
  * Disparo por sobretemperatura (>= 95.0 °C).
  * Disparo por vibración en rodamientos (>= 11.0 mm/s) y bypass de interlocks.
  * Presión mínima de aceite de lubricación (< 2.0 bar).
- Comprueba si el servidor Modbus maneja concurrencia segura con locks y excepciones de compatibilidad entre pymodbus 2.x y 3.x.

#### 3. Fidelidad Física HIL y Co-Simulación en Cascada (HELICS)
- Revisa las ecuaciones dinámicas en `physical/icssim/plant_cooling.py`, `plant_conveyor.py` y `plant_tank.py`.
- Verifica si el balance térmico (inflow kW vs calor extraído por válvula/bomba) obedece principios termodinámicos coherentes.
- Audita el puente HIL `physical/bridge_modbus.py` (sincronización de sensores y actuadores con el PLC en cada dt).
- Evalúa los federados HELICS en `helics_sim/` (`fed_icssim`, `fed_plc`, `fed_power_grid`, `fed_logger`, `run_co_simulation.py`):
  * ¿El disparo térmico del PLC propaga correctamente la desconexión del disyuntor en la subestación eléctrica de 13.8 kV?
  * ¿El log `cascading_events.csv` registra fielmente los estados del efecto dominó?

#### 4. Postura Ofensiva Red Team (Vectores de Pentesting)
- Inspecciona los scripts en `attacker/`:
  * `attack_recon.py`: Mapeo y descubrimiento de registros Modbus.
  * `attack_coil_injection.py`: Forzado de parada de bomba y bloqueo manual.
  * `attack_register_tamper.py`: False Data Injection Attack (FDIA) / sensor spoofing (Stuxnet replay).
  * `attack_setpoint_tamper.py`: Manipulación maliciosa de consigna y desestabilización por ganancia.
  * `attack_dos.py`: Inundación de sockets Modbus.
- Evalúa si los scripts validan respuestas del servidor, gestionan timeouts y confirman el impacto físico real.

#### 5. Capacidades Defensivas Blue Team y Supervisión SCADA
- Audita `network/modbus_dpi_filter.py`:
  * ¿Valida correctamente los headers MBAP y códigos de función (FC)?
  * ¿Permite FC 01-04 y bloquea FC 05, 06, 15, 16 para IPs no autorizadas generando excepción Modbus 0x01?
- Audita `scada/historian_service.py` y `scada/hmi_web_server.py`:
  * ¿Funciona el watchdog de pérdida de visión (*Loss-of-View*) ante 3 fallos consecutivos de polling?
  * ¿El HMI opera 100% desacoplado (*airgapped*) sin CDNs ni llamadas externas a Internet?

#### 6. Calidad de Software, Orquestación y Concurrencia
- Revisa `industrylab.sh`: ¿Garantiza el apagado limpio sin dejar procesos huérfanos (`down`)?
- Comprueba la suite de pruebas unitarias (`network/tests`, `plc/tests`, `physical/tests`, `helics_sim/tests`, `attacker/tests`, `scada/tests`).
- Evalúa el consumo de hardware mediante `scripts/profile_resources.py` (< 250 MB RAM).

---

### ESTRUCTURA DEL REPORTE DE AUDITORÍA REQUERIDO

Entrega tu evaluación en un informe técnico con la siguiente estructura:

1. **Puntaje Global y Resumen Ejecutivo**
   - Calificación general (0 a 100 pts) y Grado de Madurez (A+, A, B, C, D, F).
   - Tabla resumen de madurez por cada una de las 6 dimensiones auditadas.
2. **Tabla de Hallazgos (Vulnerabilidades y Oportunidades de Mejora)**
   - Formato de tabla: `ID | Severidad (CRÍTICA / ALTA / MEDIA / BAJA) | Dimensión | Archivo:Línea | Descripción del Problema | Impacto Operacional | Remediación Recomendada`.
3. **Análisis de Cumplimiento IEC 62443-3-3**
   - Evaluación contra los 7 Requisitos Fundamentales (FR1 a FR7).
4. **Validación de Fidelidad Ciberfísica**
   - Juicio técnico sobre el realismo de las ecuaciones físicas y la propagación de fallas en cascada.
5. **Plan de Remediación Priorizado (P0 / P1 / P2)**
   - Código sugerido y diffs exactos para corregir los hallazgos críticos detectados.
```
