#!/usr/bin/env bash
# ==============================================================================
# IndustryLab — IEC 62443 / Purdue Model Firewall Conduits & Filter Rules
# Enforces strict isolation between Enterprise (L4/5), DMZ (L3.5), and OT (L0-2).
# ==============================================================================

set -euo pipefail

# Allow dry-run or inspection mode if running without root / iptables
if [[ "${1:-}" == "--print-rules" ]]; then
    echo "=== IEC 62443 PERA Conduits Ruleset ==="
    echo "Default Policy: FORWARD DROP, INPUT DROP, OUTPUT ACCEPT"
    echo "Conduit C-01: IT (10.10.1.0/24) -> IDMZ (10.10.2.0/24) [TCP 22, 8085]"
    echo "Conduit C-02: IT (10.10.1.0/24) -> OT (10.10.4.0/24) [STRICT DROP + LOG]"
    echo "Conduit C-03: IDMZ Historian/DPI -> OT (10.10.4.0/24) [TCP 502, 5020]"
    echo "Conduit C-04: EWS (10.10.3.50) -> OT (10.10.4.0/24) [TCP 502, 8080]"
    echo "Conduit C-05: Attacker (10.10.99.0/24) -> OT [DROP]"
    exit 0
fi

if [[ $EUID -ne 0 ]]; then
    echo "[!] Root privileges required to apply live iptables rules. Use --print-rules for inspection."
    exit 1
fi

echo "[*] Applying IEC 62443 Purdue Firewall Ruleset..."

# 1. Enable IPv4 Forwarding on Router / Gateway
sysctl -w net.ipv4.ip_forward=1 >/dev/null

# 2. Flush existing rules and delete user chains
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# 3. Default Policies: Zero-Trust by default
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 3.1 Gateway Host Protection (SEC-09)
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -s 10.10.3.50 -p icmp -j ACCEPT
iptables -A INPUT -s 10.10.2.10 -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -s 10.10.3.50 -p tcp --dport 22 -j ACCEPT

# 4. Create custom logging chain for IEC 62443 security violations
iptables -N IEC62443_VIOLATION 2>/dev/null || true
iptables -F IEC62443_VIOLATION
iptables -A IEC62443_VIOLATION -m limit --limit 5/min -j LOG --log-prefix "[IEC62443-VIOLATION] " --log-level 4
iptables -A IEC62443_VIOLATION -j DROP

# 5. Loopback and Established State tracking
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# 6. Conduit C-02: Explicit Drop and Log of any direct IT (10.10.1.0/24) to OT (10.10.4.0/24)
iptables -A FORWARD -s 10.10.1.0/24 -d 10.10.4.0/24 -j IEC62443_VIOLATION

# 7. Conduit C-01: Enterprise to IDMZ (Jump Host & HMI Web Dashboard, plus diagnostic ICMP)
iptables -A FORWARD -s 10.10.1.0/24 -d 10.10.2.0/24 -p icmp --icmp-type echo-request -j ACCEPT
iptables -A FORWARD -s 10.10.1.0/24 -d 10.10.2.10 -p tcp --dport 22 -m state --state NEW -j ACCEPT
iptables -A FORWARD -s 10.10.1.0/24 -d 10.10.2.30 -p tcp --dport 8085 -m state --state NEW -j ACCEPT
iptables -A FORWARD -s 10.10.1.0/24 -d 10.10.2.20 -p tcp --dport 8080 -m state --state NEW -j ACCEPT

# 8. Conduit C-03: IDMZ to OT Cell (Historian & DPI Proxy polling Modbus PLCs)
iptables -A FORWARD -s 10.10.2.20 -d 10.10.4.0/24 -p tcp --dport 502 -m state --state NEW -j ACCEPT
iptables -A FORWARD -s 10.10.2.40 -d 10.10.4.0/24 -p tcp --dport 502 -m state --state NEW -j ACCEPT
iptables -A FORWARD -s 10.10.2.20 -d 10.10.4.20 -p tcp --dport 5020 -m state --state NEW -j ACCEPT

# 9. Conduit C-04: Engineering Workstation (EWS) to OT (PLC Programming & Diagnostics)
iptables -A FORWARD -s 10.10.3.50 -d 10.10.4.0/24 -p tcp --dport 502 -m state --state NEW -j ACCEPT
iptables -A FORWARD -s 10.10.3.50 -d 10.10.4.0/24 -p tcp --dport 8080 -m state --state NEW -j ACCEPT

# 10. Intra-OT Cell: Local traffic between PLCs and ICSSIM Physics Simulator
iptables -A FORWARD -s 10.10.4.0/24 -d 10.10.4.0/24 -j ACCEPT

# 11. Conduit C-05: Attacker Zone strict isolation
# Attacker cannot reach OT directly; must pivot through IT or IDMZ
iptables -A FORWARD -s 10.10.99.0/24 -d 10.10.4.0/24 -j IEC62443_VIOLATION
iptables -A FORWARD -s 10.10.99.0/24 -d 10.10.1.0/24 -j ACCEPT # Simulated initial IT breach

# 12. Catch-all DROP for anything unhandled in FORWARD
iptables -A FORWARD -j DROP

echo "[+] IEC 62443 Firewall Rules applied successfully."
