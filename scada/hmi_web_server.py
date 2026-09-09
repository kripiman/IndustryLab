#!/usr/bin/env python3
"""
IndustryLab — Airgapped Industrial Process HMI Web Dashboard
Serves responsive, self-contained SVG & HTML5 process telemetry visualization over HTTP :8085.
100% offline, zero internet dependencies, works in isolated OT/DMZ networks.
"""

import sys
import json
import logging
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from pathlib import Path

logger = logging.getLogger("HMIServer")

HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>IndustryLab — HMI Industrial OT/ICS (IEC 62443)</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel-bg: #1e293b;
      --text: #f8fafc;
      --accent: #0284c7;
      --green: #10b981;
      --yellow: #f59e0b;
      --red: #ef4444;
      --border: #334155;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 20px; }
    header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border); padding-bottom: 15px; margin-bottom: 20px; }
    h1 { font-size: 1.5rem; color: #38bdf8; display: flex; align-items: center; gap: 10px; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; background: #0369a1; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
    .card { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }
    .card-title { font-size: 1.1rem; color: #94a3b8; margin-bottom: 15px; border-bottom: 1px solid var(--border); padding-bottom: 8px; font-weight: 600; }
    .metric-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #33415555; }
    .metric-label { color: #94a3b8; }
    .metric-val { font-weight: bold; font-size: 1.1rem; font-family: monospace; }
    .val-normal { color: var(--green); }
    .val-warn { color: var(--yellow); }
    .val-crit { color: var(--red); }
    .alarm-box { background: #450a0a; border: 1px solid var(--red); border-radius: 6px; padding: 12px; margin-top: 15px; font-size: 0.9rem; }
    svg { width: 100%; height: 180px; }
  </style>
</head>
<body>
  <header>
    <h1>🏭 IndustryLab — HMI Industrial Central (IEC 62443 PERA)</h1>
    <div>
      <span class="badge">ZONA: IDMZ (Nivel 3.5)</span>
      <span id="sys-status-badge" class="badge" style="background:#15803d;">SISTEMA: EN LÍNEA</span>
    </div>
  </header>

  <div class="grid">
    <!-- Panel 1: Loop de Enfriamiento -->
    <div class="card">
      <div class="card-title">❄️ Intercambiador de Calor y Enfriamiento (E-101)</div>
      <svg viewBox="0 0 400 150">
        <!-- Piping -->
        <path d="M 30 75 L 120 75 L 120 50 L 280 50 L 280 75 L 370 75" fill="none" stroke="#38bdf8" stroke-width="8" />
        <!-- Heat Exchanger Body -->
        <rect x="140" y="25" width="120" height="90" rx="8" fill="#1e293b" stroke="#0284c7" stroke-width="3" />
        <text x="200" y="65" fill="#f8fafc" font-size="12" text-anchor="middle" font-weight="bold">HEAT EXCHANGER</text>
        <text id="svg-temp" x="200" y="90" fill="#10b981" font-size="18" text-anchor="middle" font-weight="bold">45.0 °C</text>
        <!-- Pump -->
        <circle cx="80" cy="75" r="22" fill="#0f172a" stroke="#38bdf8" stroke-width="3" />
        <text x="80" y="80" fill="#38bdf8" font-size="11" text-anchor="middle">P-101</text>
        <!-- Valve -->
        <polygon points="320,60 340,75 320,90" fill="#f59e0b" />
        <polygon points="340,60 320,75 340,90" fill="#f59e0b" />
      </svg>
      <div class="metric-row"><span class="metric-label">Temperatura de Proceso (PV):</span><span class="metric-val" id="val-temp">45.0 °C</span></div>
      <div class="metric-row"><span class="metric-label">Posición Válvula Enfriamiento:</span><span class="metric-val" id="val-valve">35 %</span></div>
      <div class="metric-row"><span class="metric-label">Caudal Refrigerante:</span><span class="metric-val" id="val-flow">120 L/min</span></div>
      <div class="metric-row"><span class="metric-label">Estado Bomba P-101:</span><span class="metric-val val-normal" id="val-pump">MARCHA</span></div>
    </div>

    <!-- Panel 2: Molienda y Correa Transportadora -->
    <div class="card">
      <div class="card-title">⛰️ Correa Alimentadora y Molino SAG (CV-201 / ML-201)</div>
      <svg viewBox="0 0 400 150">
        <!-- Conveyor belt -->
        <line x1="40" y1="85" x2="220" y2="85" stroke="#94a3b8" stroke-width="6" stroke-dasharray="8 4" />
        <circle cx="40" cy="85" r="14" fill="#334155" stroke="#cbd5e1" stroke-width="2" />
        <circle cx="220" cy="85" r="14" fill="#334155" stroke="#cbd5e1" stroke-width="2" />
        <text x="130" y="70" fill="#94a3b8" font-size="12" text-anchor="middle">CORREA CV-201</text>
        <!-- SAG Mill Drum -->
        <circle cx="310" cy="80" r="45" fill="#1e293b" stroke="#f59e0b" stroke-width="4" />
        <text x="310" y="80" fill="#f8fafc" font-size="11" text-anchor="middle" font-weight="bold">MOLINO SAG</text>
        <text id="svg-vib" x="310" y="100" fill="#10b981" font-size="14" text-anchor="middle">3.2 mm/s</text>
      </svg>
      <div class="metric-row"><span class="metric-label">Velocidad Correa:</span><span class="metric-val" id="val-speed">70 %</span></div>
      <div class="metric-row"><span class="metric-label">Alimentación de Mineral:</span><span class="metric-val" id="val-feed">840 TPH</span></div>
      <div class="metric-row"><span class="metric-label">Vibración Rodamientos SAG:</span><span class="metric-val" id="val-vib">3.2 mm/s</span></div>
      <div class="metric-row"><span class="metric-label">Presión Aceite Lubricación:</span><span class="metric-val" id="val-lube">3.5 bar</span></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">🚨 Panel de Alarmas y Eventos en Tiempo Real (SOC / Blue Team)</div>
    <div id="alarms-container">
      <div style="color:#64748b; font-style:italic;">No hay alarmas activas. Proceso operando bajo parámetros nominales IEC 62443.</div>
    </div>
  </div>

  <script>
    async function updateDashboard() {
      try {
        const res = await fetch('/api/snapshot');
        if (!res.ok) {
          showLossOfView('PÉRDIDA DE VISIÓN / COMUNICACIÓN CAÍDA');
          return;
        }
        const data = await res.json();
        const c = data.telemetry ? data.telemetry.cooling : null;
        const cv = data.telemetry ? data.telemetry.conveyor : null;

        const coolingOnline = c && c.online !== false;
        const conveyorOnline = cv && cv.online !== false;

        const badge = document.getElementById('sys-status-badge');
        if (badge) {
          if (coolingOnline && conveyorOnline) {
            badge.style.background = '#15803d';
            badge.innerText = 'SISTEMA: EN LÍNEA';
          } else {
            badge.style.background = '#ef4444';
            badge.innerText = 'PÉRDIDA DE VISIÓN / COMUNICACIÓN CAÍDA';
          }
        }

        // Update Cooling
        if (!coolingOnline) {
          document.getElementById('val-temp').innerText = 'COMM FAULT';
          document.getElementById('val-temp').className = 'metric-val val-crit';
          document.getElementById('svg-temp').innerText = 'LOSS OF VIEW';
          document.getElementById('svg-temp').setAttribute('fill', '#ef4444');
        } else {
          document.getElementById('val-temp').innerText = c.temp_c.toFixed(1) + ' °C';
          document.getElementById('svg-temp').innerText = c.temp_c.toFixed(1) + ' °C';
          document.getElementById('val-valve').innerText = c.valve_pct + ' %';
          document.getElementById('val-flow').innerText = c.flow_lpm.toFixed(0) + ' L/min';
          document.getElementById('val-pump').innerText = c.pump_run ? 'MARCHA' : 'DETENIDA';
          document.getElementById('val-pump').className = 'metric-val ' + (c.pump_run ? 'val-normal' : 'val-crit');

          if (c.temp_c >= 95.0) {
            document.getElementById('val-temp').className = 'metric-val val-crit';
            document.getElementById('svg-temp').setAttribute('fill', '#ef4444');
          } else if (c.temp_c >= 85.0) {
            document.getElementById('val-temp').className = 'metric-val val-warn';
            document.getElementById('svg-temp').setAttribute('fill', '#f59e0b');
          } else {
            document.getElementById('val-temp').className = 'metric-val val-normal';
            document.getElementById('svg-temp').setAttribute('fill', '#10b981');
          }
        }

        // Update Conveyor
        if (!conveyorOnline) {
          document.getElementById('val-vib').innerText = 'COMM FAULT';
          document.getElementById('val-vib').className = 'metric-val val-crit';
          document.getElementById('svg-vib').innerText = 'LOSS OF VIEW';
          document.getElementById('svg-vib').setAttribute('fill', '#ef4444');
        } else {
          document.getElementById('val-speed').innerText = cv.belt_speed_pct + ' %';
          document.getElementById('val-feed').innerText = cv.feed_rate_tph + ' TPH';
          document.getElementById('val-vib').innerText = cv.vibration_mms.toFixed(1) + ' mm/s';
          document.getElementById('svg-vib').innerText = cv.vibration_mms.toFixed(1) + ' mm/s';
          document.getElementById('val-lube').innerText = cv.lube_pressure_bar.toFixed(1) + ' bar';
        }

        // Update Alarms
        const alarmContainer = document.getElementById('alarms-container');
        if (data.alarms && data.alarms.length > 0) {
          alarmContainer.innerHTML = data.alarms.slice(-5).reverse().map(a => `
            <div class="alarm-box">
              <strong>[${a.severity}] ${a.code}</strong> — ${a.message}
              <div style="font-size:0.75rem; color:#fca5a5; margin-top:3px;">${a.time_str}</div>
            </div>
          `).join('');
        }
      } catch (err) {
        showLossOfView('PÉRDIDA DE VISIÓN / COMUNICACIÓN CAÍDA');
      }
    }

    function showLossOfView(msg) {
      const badge = document.getElementById('sys-status-badge');
      if (badge) {
        badge.style.background = '#ef4444';
        badge.innerText = msg;
      }
      document.getElementById('val-temp').innerText = 'COMM FAULT';
      document.getElementById('val-temp').className = 'metric-val val-crit';
      document.getElementById('svg-temp').innerText = 'LOSS OF VIEW';
      document.getElementById('svg-temp').setAttribute('fill', '#ef4444');
      document.getElementById('val-vib').innerText = 'COMM FAULT';
      document.getElementById('val-vib').className = 'metric-val val-crit';
      document.getElementById('svg-vib').innerText = 'LOSS OF VIEW';
      document.getElementById('svg-vib').setAttribute('fill', '#ef4444');
    }
    setInterval(updateDashboard, 1500);
    updateDashboard();
  </script>
</body>
</html>
"""


class HmiRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif self.path.startswith("/api/"):
            # Reverse proxy to Historian (P2-03 / SEC-10)
            historian_url = getattr(self.server, "historian_url", "http://127.0.0.1:8080").rstrip("/")
            target_url = f"{historian_url}{self.path}"
            try:
                from urllib.request import Request
                req = Request(target_url)
                with urlopen(req, timeout=3.0) as resp:
                    data = resp.read()
                    self.send_response(resp.status)
                    self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                err_data = json.dumps({
                    "error": f"Historian gateway unreachable: {e}",
                    "online": False
                }).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_data)))
                self.end_headers()
                self.wfile.write(err_data)
        else:
            self.send_response(404)
            self.end_headers()


def run_hmi(host="0.0.0.0", port=8085, historian_url="http://127.0.0.1:8080"):
    import os
    if not historian_url:
        historian_url = os.environ.get("HISTORIAN_URL", "http://127.0.0.1:8080")
    server = HTTPServer((host, port), HmiRequestHandler)
    server.historian_url = historian_url.rstrip("/")
    logger.info(f"Airgapped HMI Dashboard active at http://{host}:{port} (proxying to {server.historian_url})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping HMI Server...")
        server.shutdown()


def main():
    import os
    parser = argparse.ArgumentParser(description="Airgapped Industrial Process HMI Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP bind host")
    parser.add_argument("--port", type=int, default=8085, help="HTTP bind port")
    parser.add_argument("--historian-url", default=os.environ.get("HISTORIAN_URL", "http://127.0.0.1:8080"), help="Upstream Historian URL")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_hmi(host=args.host, port=args.port, historian_url=args.historian_url)


if __name__ == "__main__":
    main()
