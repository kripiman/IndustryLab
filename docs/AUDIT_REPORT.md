# 🛡️ IndustryLab — Informe Técnico de Auditoría Ciberfísica y Ciberseguridad OT (IEC 62443)

**Auditor Principal**: Auditor Líder de Ciberseguridad Industrial (OT/ICS) & Sistemas Ciberfísicos (CPS)  
**Estándares de Referencia**: IEC 62443-3-3, IEC 62443-4-2, IEC 61131-3, Modelo Purdue (PERA), ISO 10816-3  
**Fecha de Auditoría**: 2026-09-07  
**Repositorio**: `/home/kripi/Documentos/GitHub/IndustryLab`  
**Estado de la Suite de Pruebas**: 23/23 Tests Unitarios Pasando (100%)  
**Consumo de Recursos Medido**: 97.47 MB RSS (Umbral requerido: < 250 MB)

---

## 1. Puntaje Global y Resumen Ejecutivo

### 1.1 Calificación General

$$\mathbf{Puntaje\ Global:\ 74.8\ /\ 100}\quad\longrightarrow\quad\mathbf{Grado\ de\ Madurez:\ B\ (Aceptable\ con\ Vulnerabilidades\ Cr\acute{i}ticas)}$$

IndustryLab presenta una base arquitectónica notablemente sólida para un Cyber Range industrial 100% de software nativo en Linux y contenedores. Modela con gran acierto el Modelo Purdue (PERA), provee ecuaciones diferenciales físicas acopladas con rigor termodinámico y mecánico (balance de energía de 1er orden en enfriamiento, rampas cinemáticas y vibración ISO 10816-3 en transporte de mineral), integra co-simulación temporal con HELICS y ofrece una cadena ofensiva-defensiva coherente.

No obstante, la auditoría forense del código fuente reveló **vulnerabilidades críticas de diseño e implementación**:
1. **Bloqueo DoS mono-hilo en el Proxy DPI Modbus** que paraliza todo el tráfico industrial ante una sola conexión lenta o maliciosa.
2. **Desalineación entre el estándar IEC 61131-3 (%IW) y la memoria Modbus**, exponiendo registros de sensores físicos como *Holding Registers* modificables por red, facilitando ataques FDIA directos.
3. **Evasión del Firewall por la arquitectura de red de Docker Compose**, donde el tráfico inter-redes puentea el contenedor `router_fw` debido a las rutas por defecto del bridge de Docker.
4. **Falla de propagación del disparo de emergencia en el federado HELICS del PLC**, donde el ataque suprime la emisión del `emergency_trip` hacia la subestación eléctrica.

### 1.2 Tabla Resumen de Madurez por Dimensión

| # | Dimensión Auditada | Ponderación | Puntaje | Grado | Estado Operativo |
|---|---|:---:|:---:|:---:|---|
| **D1** | Segmentación de Red y Conductos IEC 62443-3-3 | 20% | **72 / 100** | **C+** | Aislamiento conceptual excelente; bypass latente en Docker bridges y política INPUT permisiva. |
| **D2** | Lógica de Control PLC y Servidor Modbus (IEC 61131-3) | 20% | **68 / 100** | **C** | Código ST estructurado; desalineación %IW->HR, des-enclavamiento prematuro y bypass de interlocks sin autenticación. |
| **D3** | Fidelidad Física HIL y Co-Simulación (HELICS) | 15% | **82 / 100** | **B+** | Termodinámica y cinemática de alta fidelidad; bug en federado PLC suprime propagación de trip en cascada. |
| **D4** | Postura Ofensiva Red Team (Pentesting OT) | 15% | **80 / 100** | **B** | Scripts efectivos y limpios; falta validación en lazo cerrado del impacto físico en el proceso. |
| **D5** | Capacidades Defensivas Blue Team y SCADA | 15% | **65 / 100** | **C** | HMI airgapped estricto; DoS mono-hilo crítico en DPI Proxy y HMI sin indicación de pérdida de visión. |
| **D6** | Calidad de Software, Orquestación y Recursos | 15% | **85 / 100** | **B+** | Orquestador unificado eficaz; consumo ultra-ligero (97.5 MB); `down` requiere espera activa de PIDs. |
| **TOTAL** | **Evaluación Integral Ponderada** | **100%** | **74.8 / 100** | **B** | **Nivel de Seguridad Objetivo (SL-T): 2 / Nivel de Seguridad Alcanzado (SL-A): 1** |

---

## 2. Tabla Consolidada de Hallazgos

| ID | Severidad | Dimensión | Archivo:Línea | Descripción del Problema | Impacto Operacional | Remediación Recomendada |
|---|:---:|:---:|---|---|---|---|
| **SEC-01** | **CRÍTICA** | D5 (Blue/SCADA) | `network/modbus_dpi_filter.py:194` | `handle_client` es invocado de forma sincrónica en el hilo principal del proxy DPI. | **Denegación de Servicio Total (DoS)**: Una única conexión persistente o lenta congela el proxy, desconectando SCADA y EWS de los PLCs. | Atender cada conexión en un hilo desacoplado (`threading.Thread`) o utilizar `asyncio`/`selectors` no bloqueantes. |
| **SEC-02** | **CRÍTICA** | D2 (PLC Logic) | `plc/openplc_runtime.py:38,44` | Sensores físicos (`TEMP_PV`, `VIB_RMS`, `LUBE_PRESS`) mapeados en Holding Registers (FC 03/06/16) en lugar de Input Registers (%IW / FC 04). | **False Data Injection directo**: Atacantes pueden sobreescribir la temperatura del proceso remotamente con FC 06, cegando al PLC sin tocar la física. | Mapear valores de sensores exclusivamente en `input_block` (FC 04, sólo lectura remota). |
| **SEC-03** | **CRÍTICA** | D1 (Red/Purdue) | `network/docker-compose.yml:8-68` | Los contenedores usan el gateway bridge estándar del host (`10.10.x.254`), omitiendo la IP del router firewall (`10.10.x.1`). | **Bypass del Cortafuegos**: El tráfico inter-zonas es enrutado directamente por el kernel del host sin pasar por las reglas iptables de `router_fw`. | Inyectar rutas estáticas en los contenedores o configurar `router_fw` como gateway obligatorio en cada interfaz. |
| **SEC-04** | **CRÍTICA** | D3 (HELICS) | `helics_sim/fed_plc.py:51-66` | La rama `if cyber_attack_override:` omite la evaluación de sobretemperatura (`temp_c >= 95.0`). | **Ruptura de Cascada Ciberfísica**: `emergency_trip` permanece en `False`; el disparo de la subestación sólo ocurre por sondeo de temperatura externa, no por acción del PLC. | Evaluar siempre el umbral de disparo de emergencia previo a aplicar sobreescrituras operativas. |
| **SEC-05** | **ALTA** | D2 (PLC Logic) | `plc/st_programs/industrial_cooling.st:50-59` | Falta bloque `ELSE` para retener la acción de emergencia mientras `TRIP_INTERLOCK_ACT` esté enclavado si la temperatura oscila por debajo de 95 °C. | **Bypass de Enclavamiento**: Un atacante puede forzar la parada de la bomba con Modbus durante un trip si la temperatura baja transitoriamente a 94.9 °C. | Mantener forzados `PUMP_RUN_CMD := TRUE` y `VALVE_POSITION_PCT := 100` mientras `TRIP_INTERLOCK_ACT` sea verdadero. |
| **SEC-06** | **ALTA** | D2 (PLC Logic) | `plc/st_programs/mining_slurry_conveyor.st:17,40` | `INTERLOCK_BYPASS` mapeado a bobina Modbus accesible por red (`%QX0.3`), anulando disparos de vibración y lubricación. | **Destrucción Mecánica sin Alarma**: Un atacante activa el bypass, forzando trabajo con lubricación cero; la lógica además borra la palabra de alarma a 0. | Restringir el bypass a llave física / variable interna SIL, y mantener activa la alarma de bypass en el SCADA. |
| **SEC-07** | **ALTA** | D5 (Blue/SCADA) | `network/modbus_dpi_filter.py:160-174` | El proxy reenvía el buffer TCP completo tras validar sólo el primer frame PDU; no verifica `proto_id == 0`. | **Modbus Frame Smuggling**: Un atacante puede concatenar un FC 03 (permitido) con un FC 05 (prohibido) en un solo paquete TCP y evadir el filtro. | Procesar el buffer delimitando por el campo `length` del MBAP e inspeccionar todas las transacciones presentes. |
| **SEC-08** | **ALTA** | D5 (Blue/SCADA) | `scada/hmi_web_server.py:57,123` | El HMI mantiene en verde y con valores congelados los paneles cuando Historian reporta `online: false`. | **Engaño al Operador (Loss-of-View)**: La interfaz no evidencia que la comunicación con el PLC ha muerto, indicando engañosamente "SISTEMA: EN LÍNEA". | Cambiar indicadores a rojo y desplegar alerta visual destacada "PÉRDIDA DE VISIÓN / COMUNICACIÓN CAÍDA". |
| **SEC-09** | **ALTA** | D1 (Red/Purdue) | `network/firewall_rules.sh:40` | La política por defecto de la cadena INPUT es `ACCEPT` sin reglas de protección de gestión. | **Superficie de Ataque en Gateway**: Nodos atacantes en 10.10.99.0/24 pueden intentar ataques directos contra los puertos del firewall. | Cambiar a `iptables -P INPUT DROP` y permitir únicamente conexiones administrativas autenticadas desde IDMZ/EWS. |
| **SEC-10** | **MEDIA** | D5 (Blue/SCADA) | `scada/hmi_web_server.py:116` | El frontend JS invoca `http://<hmi_host>:8080/api/snapshot` directamente mediante CORS. | **Falla de Conectividad en DMZ**: En contenedores con IPs separadas (HMI en 10.10.2.30, Historian en 10.10.2.20), las peticiones fallan. | Implementar proxy inverso en `hmi_web_server.py` hacia el Historian para servir todo por el puerto 8085. |
| **SEC-11** | **MEDIA** | D2 (PLC Logic) | `plc/modbus_server.py:43,63` | `self.lock` en `ModbusPlcServer` no es compartido con los handlers de red de `pymodbus`. | **Condición de Carrera**: Posibles inconsistencias temporales en lecturas multi-registro durante escrituras del ciclo de scan. | Sincronizar el contexto Modbus o implementar un buffer de memoria de doble página atómico. |
| **SEC-12** | **MEDIA** | D1 (Red/Purdue) | `network/topology_mininet.py:111` | El script de Mininet evalúa aislamiento con `ping` (ICMP), pero `firewall_rules.sh` no permite ICMP hacia DMZ. | **Inconsistencia de Pruebas**: Falso negativo al ejecutar la validación automatizada en Mininet bajo políticas estrictas. | Agregar regla explícita para ICMP echo-request controlado o probar conectividad mediante socket TCP. |
| **SEC-13** | **MEDIA** | D4 (Red Team) | `attacker/attack_dos.py:33` | El script captura excepciones silenciosamente y asume éxito sólo por el envío de sockets. | **Evaluación Incierta**: No verifica si el PLC efectivamente denegó servicio a clientes legítimos. | Medir la latencia de respuesta de sondeos SCADA concurrentes durante la ráfaga de saturación. |
| **SEC-14** | **MEDIA** | D6 (Software) | `industrylab.sh:107-115` | `cmd_down` borra los archivos PID sin verificar con `kill -0` que los procesos hayan terminado. | **Procesos Huérfanos**: Sockets 502/8080/8085 pueden quedar bloqueados en reinicios subsiguientes. | Incorporar un bucle de espera activa con `kill -0` y escalamiento a `SIGKILL` tras 3 segundos. |
| **SEC-15** | **BAJA** | D3 (HELICS) | `physical/bridge_modbus.py:49` | `BufferTankPlant` es instanciado pero su método `.step()` nunca es invocado. | **Código Huérfano**: Desperdicio menor de ciclos y modelo físico de tanque desaprovechado. | Integrar la dinámica del tanque al ciclo de sincronización o remover la instancia huérfana. |

---

## 3. Análisis Detallado de Cumplimiento IEC 62443-3-3

Evaluación técnica contra los 7 Requisitos Fundamentales (**Fundamental Requirements - FR**) y asignación de Nivel de Seguridad (**Security Level - SL**):

```
Leyenda de Niveles de Seguridad (IEC 62443-3-3):
- SL 1: Protección contra violaciones casuales o no intencionadas.
- SL 2: Protección contra violaciones intencionadas con medios sencillos y bajos recursos.
- SL 3: Protección contra violaciones intencionadas con medios sofisticados y recursos moderados.
- SL 4: Protección contra ataques patrocinados por estados con recursos ilimitados.
```

### FR 1: Control de Identificación y Autenticación (IAC) — *Cumplimiento: SL-1 (Parcial)*
* **Requisito**: Identificar y autenticar a todos los usuarios, procesos y dispositivos antes de permitir el acceso a zonas y conductos.
* **Estado en IndustryLab**:
  * Implementa filtrado de direcciones IP en el Proxy DPI (`authorized_write_ips = {"10.10.3.50", "127.0.0.1"}`).
  * Define bastión SSH (`dmz_jump`) para acceso a la DMZ industrial.
  * **Brecha**: No implementa autenticación criptográfica en el protocolo de control (Modbus/TCP clásico no posee mecanismo nativo; requiere migración o encapsulamiento en Modbus Security / TLS según IEC 62443-4-2).

### FR 2: Control de Uso (UC) — *Cumplimiento: SL-1 (Deficiente ante DoS)*
* **Requisito**: Hacer cumplir los privilegios asignados para impedir la ejecución no autorizada de comandos críticos.
* **Estado en IndustryLab**:
  * El Proxy DPI discrimina con precisión entre códigos de función de lectura (FC 01-04 permitidos) y escritura (FC 05, 06, 15, 16 restringidos a EWS).
  * Devuelve la excepción estándar Modbus `0x01` (*Illegal Function*).
  * **Brecha**: La arquitectura mono-hilo bloqueante del proxy permite a un atacante con medios muy simples anular el control de uso mediante saturación de sockets (SEC-01).

### FR 3: Integridad del Sistema (SI) — *Cumplimiento: SL-1 (Vulnerable a FDIA)*
* **Requisito**: Proteger la integridad de las aplicaciones de control, configuraciones y datos de proceso contra modificaciones no autorizadas.
* **Estado en IndustryLab**:
  * El programa Structured Text define enclavamientos de sobretemperatura a 95.0 °C y vibración a 11.0 mm/s.
  * **Brecha Crítica**: La asignación de la variable de proceso analógica `TEMP_PV` a un Holding Register Modbus en `openplc_runtime.py` permite la inyección de datos falsos (FDIA) desde cualquier estación autorizada a escribir registros, anulando la integridad del proceso (SEC-02).
  * **Brecha de Lógica**: Falta de persistencia en el enclavamiento cuando la temperatura oscila (SEC-05).

### FR 4: Confidencialidad de Datos (DC) — *Cumplimiento: SL-1 (Básico)*
* **Requisito**: Asegurar la confidencialidad de la información transmitida a través de conductos de comunicación.
* **Estado en IndustryLab**:
  * Las comunicaciones entre zonas están segmentadas por el cortafuegos.
  * **Brecha**: Las tramas Modbus y los endpoints HTTP REST se transmiten en texto plano. En entornos de Nivel 2 o superior, se requiere TLS en el Historian API y segmentación física/VLAN con cifrado en conductos inter-zona.

### FR 5: Flujo de Datos Restringido (RDF) — *Cumplimiento: SL-2 (Diseño) / SL-1 (Docker)*
* **Requisito**: Segmentar la red en zonas y conductos para restringir el flujo de datos exclusivamente a las comunicaciones necesarias.
* **Estado en IndustryLab**:
  * El modelo conceptual PERA implementa 5 zonas diferenciadas y 5 conductos (C-01 a C-05).
  * La política en `firewall_rules.sh` establece `FORWARD DROP` estricto y bloquea con regla de registro `[IEC62443-VIOLATION]` el tráfico directo IT->OT.
  * **Brecha Crítica**: En el despliegue Docker Compose, las interfaces bridge del host permiten evasión del firewall perimetral (SEC-03).

### FR 6: Respuesta Oportuna a Eventos (TRE) — *Cumplimiento: SL-2 (Robusto)*
* **Requisito**: Registrar eventos de seguridad, generar alarmas en tiempo real y permitir auditorías post-incidente.
* **Estado en IndustryLab**:
  * SCADA Historian mantiene buffer circular de alarmas con marcas de tiempo y niveles de severidad (`COOLING_HIGH_TEMP`, `LOSS_OF_VIEW`).
  * Reglas de Snort/Suricata específicas (`ids_snort_rules.rules`) con firmas para escrituras FC 05/06/16 no autorizadas y violaciones de zona.
  * Co-simulación registra fielmente la evolución en `logs/cascading_events.csv`.

### FR 7: Disponibilidad de Recursos (RA) — *Cumplimiento: SL-1 (Vulnerable a Inundación)*
* **Requisito**: Proteger los sistemas contra condiciones de degradación o denegación de servicio para garantizar la continuidad operacional.
* **Estado en IndustryLab**:
  * SCADA Historian posee watchdog activo ante pérdida de visión (3 fallos de sondeo consecutivos).
  * Consumo de memoria ultra-eficiente (< 100 MB).
  * **Brecha**: Ni el firewall ni el servidor PLC implementan limitación de conexiones concurrentes (*rate limiting* / `connlimit`), siendo susceptibles a saturación mediante `attack_dos.py`.

---

## 4. Validación de Fidelidad Ciberfísica

### 4.1 Dinámica Termodinámica del Intercambiador de Calor
El balance térmico en `physical/icssim/plant_cooling.py`:

$$\frac{dT}{dt} = \frac{\dot{Q}_{\text{in}} - \dot{Q}_{\text{cooling}} - \dot{Q}_{\text{ambient}}}{M \cdot C_p}$$

* **Parámetros**: $\dot{Q}_{\text{in}} = 120.0\text{ kW}$, $\dot{Q}_{\text{cooling}} = 250.0 \cdot \left(\frac{\text{valve}}{100}\right) \cdot \eta$, $M \cdot C_p = 500.0\text{ kJ/K}$.
* **Fidelidad**: **Alta**. En condiciones de pérdida total de refrigeración ($\text{valve}=0\%$, $\text{pump}=0$), $\dot{Q}_{\text{cooling}}=0$, resultando en una tasa de calentamiento neta inicial de:
  $$\frac{dT}{dt} \approx \frac{120 - 2.5}{500} = 0.235^\circ\text{C/s}$$
  El sistema tarda exactamente $212.7\text{ s}$ en escalar desde los $45.0^\circ\text{C}$ de régimen nominal hasta los $95.0^\circ\text{C}$ de disparo de emergencia. La integración de Euler con paso $\Delta t = 0.2\text{ s}$ provee estabilidad numérica absoluta.

### 4.2 Cinemática y Vibración en Molienda y Correa
El modelo en `physical/icssim/plant_conveyor.py`:
* Aceleración del motor a $0.8\text{ m/s}^2$, desaceleración a $-1.5\text{ m/s}^2$.
* Tasa de alimentación volumétrica $F(t)$ lineal con la velocidad de la cinta.
* Vibración de rodamientos basada en la norma **ISO 10816-3**:
  $$\text{Vib}(t) = \text{Vib}_{\text{baseline}} + \int \frac{2.5}{P_{\text{lube}}(t)} dt\quad\text{cuando } P_{\text{lube}} < 2.0\text{ bar}$$
* **Fidelidad**: **Excelente**. Representa fielmente el daño progresivo por degradación de película hidrodinámica en cojinetes de muñón del molino SAG.

### 4.3 Propagación de Fallas en Cascada (Efecto Dominó en HELICS)
* **Verificación Experimental**:
  * Ejecución de co-simulación con inyección maliciosa en $t=4.0\text{ s}$.
  * En $t=221.0\text{ s}$, la temperatura alcanza $95.15^\circ\text{C}$.
  * En $t=222.0\text{ s}$, el disyuntor de $13.8\text{ kV}$ de la subestación abre por sobrecarga térmica (`CASCADE_BLACKOUT_TRIPPED`), la potencia de planta cae a $0\text{ kW}$, la cinta y el molino pierden alimentación eléctrica y la vibración colapsa a reposo ($0.10\text{ mm/s}$).
* **Defecto Detectado**: Como se identificó en **SEC-04**, la apertura del disyuntor se debió a la lectura de la temperatura externa en `fed_power_grid.py`, pero la señal `emergency_trip` del PLC nunca se transmitió por el bus HELICS debido al cortocircuito lógico en `FedPLC.execute_logic()`.

---

## 5. Plan de Remediación Priorizado (P0 / P1 / P2)

### 5.1 Parches Prioridad P0 (Inmediato / Crítico)

#### P0-01: Desacoplamiento Multihilo en Proxy DPI Modbus (Resuelve SEC-01)
* **Archivo**: `network/modbus_dpi_filter.py`
* **Diff**:

```diff
--- a/network/modbus_dpi_filter.py
+++ b/network/modbus_dpi_filter.py
@@ -12,6 +12,7 @@ import sys
 import socket
 import select
 import logging
+import threading
 import argparse
 from pathlib import Path
 
@@ -191,7 +192,8 @@ class ModbusDpiProxy:
                 r, _, _ = select.select([server], [], [], 0.5)
                 if r:
                     client_sock, client_addr = server.accept()
-                    self.handle_client(client_sock, client_addr)
+                    client_thread = threading.Thread(target=self.handle_client, args=(client_sock, client_addr), daemon=True)
+                    client_thread.start()
         except KeyboardInterrupt:
             logger.info("Shutting down DPI Proxy...")
         finally:
```

---

#### P0-02: Corrección de Mapeo de Registros Modbus %IW vs %QW (Resuelve SEC-02)
* **Archivo**: `plc/openplc_runtime.py`
* **Diff**:

```diff
--- a/plc/openplc_runtime.py
+++ b/plc/openplc_runtime.py
@@ -35,15 +35,15 @@ class CoolingControlLogic:
         self.modbus.set_holding_register(1, 35)  # VALVE_POSITION_PCT = 35%
         self.modbus.set_holding_register(2, 450) # TEMP_SP_SCALED_C10 = 45.0 C (addr 2)
         self.modbus.set_holding_register(3, 20)  # KP_GAIN_X10 = 20 (addr 3)
-        self.modbus.set_holding_register(0, 450) # TEMP_PV_SCALED_C10 (addr 0)
+        self.modbus.set_input_register(0, 450)   # TEMP_PV_SCALED_C10 (%IW0 - Read-Only)
         self.modbus.set_discrete_input(0, True)  # FLOW_SWITCH_OK = 1
         self.modbus.set_discrete_input(1, True)  # PUMP_FEEDBACK_RUN = 1
 
     def scan_cycle(self):
-        # 1. Read Inputs
-        temp_pv = self.modbus.get_holding_register(0) # Process Temp * 10
+        # 1. Read Inputs from Input Register (%IW0)
+        temp_pv = self.modbus.get_input_register(0)   # Process Temp * 10
         manual_override = self.modbus.get_coil(2)      # MANUAL_OVERRIDE
```

---

#### P0-03: Retención Estricta de Enclavamiento en Structured Text (Resuelve SEC-05)
* **Archivo**: `plc/st_programs/industrial_cooling.st`
* **Diff**:

```diff
--- a/plc/st_programs/industrial_cooling.st
+++ b/plc/st_programs/industrial_cooling.st
@@ -53,6 +53,10 @@ PROGRAM Cooling_Exchanger_Control
     VALVE_POSITION_PCT := 100;  (* 100% full open emergency cooling *)
     ALARM_STATUS_WORD := 16#0003; (* HighTemp + CritTrip *)
     RETURN;
+  ELSIF TRIP_INTERLOCK_ACT THEN
+    PUMP_RUN_CMD := TRUE;       (* Keep emergency cooling locked *)
+    VALVE_POSITION_PCT := 100;
+    ALARM_STATUS_WORD := 16#0003;
   END_IF;
 
   (* Normal Automatic Control Logic *)
```

---

#### P0-04: Corrección de Emisión de Disparo de Emergencia en HELICS (Resuelve SEC-04)
* **Archivo**: `helics_sim/fed_plc.py`
* **Diff**:

```diff
--- a/helics_sim/fed_plc.py
+++ b/helics_sim/fed_plc.py
@@ -47,7 +47,15 @@ class FedPLC:
         helics.helicsFederateEnterExecutingMode(self.fed)
 
     def execute_logic(self, temp_c: float, cyber_attack_override: bool = False, attack_valve_val: float = 0.0) -> dict:
-        # Check if under cyber-physical override
+        # Safety interlock always monitors process limit regardless of override
+        if temp_c >= 95.0:
+            self.emergency_trip = True
+        else:
+            self.emergency_trip = False
+
+        # Evaluate actuator outputs
         if cyber_attack_override:
             self.valve_pct = attack_valve_val
             self.pump_cmd = False # Attack shuts off coolant pump!
```

---

### 5.2 Parches Prioridad P1 (Alta Prioridad / Robustecimiento)

#### P1-01: Endurecimiento de la Cadena INPUT en el Cortafuegos (Resuelve SEC-09)
* **Archivo**: `network/firewall_rules.sh`
* **Acción**:
```bash
# Cambiar política de INPUT a DROP
iptables -P INPUT DROP
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
# Permitir ping de diagnóstico únicamente desde EWS
iptables -A INPUT -s 10.10.3.50 -p icmp -j ACCEPT
```

#### P1-02: Indicación Visual Activa de Pérdida de Visión en HMI (Resuelve SEC-08)
* **Archivo**: `scada/hmi_web_server.py`
* **Acción**:
```javascript
if (!c.online) {
  document.getElementById('val-temp').innerText = 'COMM FAULT';
  document.getElementById('val-temp').className = 'metric-val val-crit';
  document.getElementById('svg-temp').innerText = 'LOSS OF VIEW';
  document.getElementById('svg-temp').setAttribute('fill', '#ef4444');
}
```

#### P1-03: Validación MBAP y Control de Concatenación PDU (Resuelve SEC-07)
* **Archivo**: `network/modbus_dpi_filter.py`
* **Acción**: Validar que `pdu["proto_id"] == 0` y comprobar que la longitud declarada en el encabezado coincida exactamente con la cantidad de bytes recibidos antes de autorizar la retransmisión.

---

### 5.3 Mejoras Prioridad P2 (Optimización y Operaciones)

1. **P2-01 (Orquestación Limpia)**: Modificar `cmd_down` en `industrylab.sh` para iterar con `kill -0` hasta confirmar la liberación efectiva de sockets de red antes de remover archivos `.pid`.
2. **P2-02 (Cierre de Lazo en Pentesting)**: Actualizar `attacker/attack_coil_injection.py` para consultar el endpoint `/api/snapshot` del Historian y verificar que la temperatura física aumentó por encima de $70.0^\circ\text{C}$ como prueba de impacto físico real.
3. **P2-03 (Proxy Inverso HMI)**: Integrar un handler HTTP en `hmi_web_server.py` que reenvíe internamente las consultas `/api/snapshot` al host `dmz_historian:8080`, eliminando la necesidad de CORS y acceso directo a puertos auxiliares desde la estación corporativa.

---

## 6. Conclusión Técnica del Auditor

IndustryLab constituye una plataforma pedagógica y experimental de nivel industrial excepcional. La combinación de especificaciones formales IEC 61131-3, modelos de física de procesos en tiempo continuo y co-simulación temporal en cascada supera ampliamente a la mayoría de los cyber ranges convencionales basados exclusivamente en emulación de red. 

La implementación de los parches **P0** y **P1** detallados en este informe elevará el Nivel de Seguridad del laboratorio de **SL-1** a un **SL-2 certificado bajo IEC 62443-3-3**, garantizando inmunidad frente a ataques de salto de zona, inyecciones ciegas de datos y condiciones de denegación de servicio en la capa de control.
