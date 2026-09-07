# 🏗️ IndustryLab — Guía de Arquitectura Ciberfísica (IEC 62443)

## 1. Modelo Purdue y Zonas de Seguridad IEC 62443

IndustryLab estructura su ciberespacio industrial de acuerdo al estándar internacional **IEC 62443-3-3** y el modelo **PERA (Purdue Enterprise Reference Architecture)**:

```
[NIVEL 4/5: Red Corporativa (Enterprise Zone) - 10.10.1.0/24]
        │
        ├── corp_ws  (10.10.1.50)  Estación de trabajo corporativa
        └── corp_srv (10.10.1.10)  Servidor ERP / Web
        │
      (eth0)
┌──────────────────────────────────────────────┐
│  Firewall / Router Gateway (router_fw)       │
│  - Política por defecto: FORWARD DROP        │
│  - Inspección de estado: ESTABLISHED,RELATED │
└──────────────────────────────────────────────┘
      (eth1)                    (eth2)                      (eth3)
        │                         │                           │
[NIVEL 3.5: Industrial DMZ]   [NIVEL 3: Ingeniería]    [NIVEL 0-2: Celda OT / Control]
  Subnet 10.10.2.0/24           Subnet 10.10.3.0/24      Subnet 10.10.4.0/24
  ├── dmz_jump (10.10.2.10)     └── ews_host             ├── plc_cooling (10.10.4.10)
  │    SSH Bastion                  (10.10.3.50)         │    OpenPLC Intercambiador
  ├── dmz_historian             Engineering WS           ├── plc_conveyor (10.10.4.11)
  │    (10.10.2.20) :8080                                │    OpenPLC Molienda/Correa
  ├── dmz_hmi (10.10.2.30)                               └── icssim_physics (10.10.4.20)
  │    SVG Dashboard :8085                                    Simulador HIL Proceso
  └── dmz_dpi_proxy (10.10.2.40)
       Proxy Modbus :1502
```

---

## 2. Conductos (Conduits) y Reglas de Filtrado

| ID Conducto | Origen | Destino | Protocolo / Puerto | Acción | Justificación IEC 62443 |
|---|---|---|---|---|---|
| **C-01** | Enterprise `10.10.1.0/24` | IDMZ `10.10.2.0/24` | TCP 22 (SSH), TCP 8085 (HMI) | `ACCEPT` | Monitoreo y acceso administrativo a través de salto |
| **C-02** | Enterprise `10.10.1.0/24` | OT Cell `10.10.4.0/24` | CUALQUIERA | **`DROP + LOG`** | **Aislamiento estricto**: Prohibido el salto directo IT->OT |
| **C-03** | IDMZ Historian / DPI | OT Cell `10.10.4.0/24` | TCP 502 (Modbus) | `ACCEPT` | Recolección de telemetría de controladores |
| **C-04** | EWS `10.10.3.50` | OT Cell `10.10.4.0/24` | TCP 502, TCP 8080 | `ACCEPT` | Programación y parametrización de lógica ST |
| **C-05** | Attacker `10.10.99.0/24` | OT Cell `10.10.4.0/24` | CUALQUIERA | **`DROP`** | Exige compromiso previo de TI para pivotar |

---

## 3. Dinámica Ciberfísica y Modelos Matemáticos (ICSSIM)

### 3.1 Loop de Enfriamiento Térmico (Intercambiador E-101)
El balance térmico en el intercambiador se rige por la ecuación diferencial de primer orden:

$$\frac{dT(t)}{dt} = \frac{\dot{Q}_{\text{in}}(t) - \dot{Q}_{\text{cooling}}(t) - \dot{Q}_{\text{ambient}}(t)}{M \cdot C_p}$$

Donde:
- $T(t)$: Temperatura del fluido de proceso (°C). Setpoint nominal: $45.0^\circ\text{C}$.
- $\dot{Q}_{\text{in}}(t)$: Calor residual generado por la molienda / reactor ($120.0\text{ kW}$).
- $\dot{Q}_{\text{cooling}}(t)$: Calor extraído por el circuito secundario:
  $$\dot{Q}_{\text{cooling}}(t) = C_{\text{max}} \cdot \left(\frac{\text{ValvePosition}}{100}\right) \cdot \eta_{\text{thermal}} \cdot \text{PumpRunning}$$
- $M \cdot C_p$: Inercia térmica del sistema ($500.0\text{ kJ/K}$).

**Comportamiento ante Ataque**: Si un script ofensivo fuerza $\text{PumpRunning}=0$ o $\text{ValvePosition}=0\%$, $\dot{Q}_{\text{cooling}}=0$, lo que induce una rampa de temperatura descontrolada que alcanza el umbral de disparo de emergencia ($95.0^\circ\text{C}$).

### 3.2 Molienda de Mineral y Correa Transportadora (CV-201 / ML-201)
- Dinámica de aceleración del motor de la correa:
  $$v(t+\Delta t) = v(t) + a_{\text{ramp}} \cdot \Delta t$$
- Tasa de alimentación volumétrica:
  $$F(t) = F_{\text{max}} \cdot \left(\frac{v(t)}{v_{\text{nom}}}\right)$$
- Corriente de carga del molino SAG:
  $$I_{\text{motor}}(t) = I_{\text{idle}} + k_{\text{load}} \cdot F(t)$$
- Vibración RMS de rodamientos (ISO 10816-3):
  $$\text{Vib}(t) = \text{Vib}_{\text{baseline}} + \frac{k_{\text{friction}}}{P_{\text{lube}}(t)}$$
  Si la presión de lubricación cae por debajo de $2.0\text{ bar}$, la vibración RMS escala rápidamente superando los $11.0\text{ mm/s}$, disparando los enclavamientos del controlador.

---

## 4. Orquestación de Efectos Dominó con HELICS

HELICS 3.x actúa como bus de tiempo federado:
```
┌──────────────────┐               ┌──────────────────┐
│   fed_icssim     │ ── Temp ────> │     fed_plc      │
│ (Dinámica Física)│ <── Valve ─── │(Lógica Control ST│
└──────────────────┘               └──────────────────┘
         │                                   │
       Temp                                 Trip
         │                                   │
         ▼                                   ▼
┌─────────────────────────────────────────────────────┐
│                 fed_power_grid                      │
│     (Subestación Eléctrica Industrial 13.8 kV)      │
│  - Si Temp >= 95°C o Trip = True: Disyuntor Dispara │
│  - Pérdida Total de Potencia (Blackout Industrial)  │
└─────────────────────────────────────────────────────┘
```
