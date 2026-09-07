#!/usr/bin/env python3
"""
IndustryLab — IEC 62443 Purdue Model Mininet Network Topology
Builds a lightweight 5-zone industrial network with a multi-homed Linux firewall router.
"""

import sys
import time
import argparse
from pathlib import Path

# Optional Mininet imports (only loaded when executed on Mininet host)
try:
    from mininet.net import Mininet
    from mininet.node import Host, Node
    from mininet.topo import Topo
    from mininet.log import setLogLevel, info
    from mininet.cli import CLI
    MININET_AVAILABLE = True
except ImportError:
    MININET_AVAILABLE = False


class LinuxRouter(Node):
    """A Node with IP forwarding and iptables capability acting as an IEC 62443 Firewall."""
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


class PurdueTopo(Topo):
    """
    Purdue Reference Architecture Topo:
    Zone 1: Enterprise (10.10.1.0/24)
    Zone 2: Industrial DMZ (10.10.2.0/24)
    Zone 3: Engineering Workstation (10.10.3.0/24)
    Zone 4: Control & OT Cell (10.10.4.0/24)
    Zone 5: Attacker / External (10.10.99.0/24)
    """
    def build(self, **_opts):
        # Multi-homed border firewall router
        fw = self.addNode('fw', cls=LinuxRouter, ip='10.10.1.1/24')

        # Layer 2 switches for each zone
        s_corp = self.addSwitch('s_corp')
        s_dmz = self.addSwitch('s_dmz')
        s_ews = self.addSwitch('s_ews')
        s_ot = self.addSwitch('s_ot')
        s_att = self.addSwitch('s_att')

        # Connect switches to Firewall router
        self.addLink(s_corp, fw, intfName2='fw-eth0', params2={'ip': '10.10.1.1/24'})
        self.addLink(s_dmz, fw, intfName2='fw-eth1', params2={'ip': '10.10.2.1/24'})
        self.addLink(s_ews, fw, intfName2='fw-eth2', params2={'ip': '10.10.3.1/24'})
        self.addLink(s_ot, fw, intfName2='fw-eth3', params2={'ip': '10.10.4.1/24'})
        self.addLink(s_att, fw, intfName2='fw-eth4', params2={'ip': '10.10.99.1/24'})

        # Enterprise Zone Hosts
        h_corp = self.addHost('h_corp', ip='10.10.1.50/24', defaultRoute='via 10.10.1.1')
        self.addLink(h_corp, s_corp)

        # DMZ Zone Hosts
        h_jump = self.addHost('h_jump', ip='10.10.2.10/24', defaultRoute='via 10.10.2.1')
        h_hist = self.addHost('h_hist', ip='10.10.2.20/24', defaultRoute='via 10.10.2.1')
        h_hmi = self.addHost('h_hmi', ip='10.10.2.30/24', defaultRoute='via 10.10.2.1')
        h_dpi = self.addHost('h_dpi', ip='10.10.2.40/24', defaultRoute='via 10.10.2.1')
        self.addLink(h_jump, s_dmz)
        self.addLink(h_hist, s_dmz)
        self.addLink(h_hmi, s_dmz)
        self.addLink(h_dpi, s_dmz)

        # Engineering Zone Host
        h_ews = self.addHost('h_ews', ip='10.10.3.50/24', defaultRoute='via 10.10.3.1')
        self.addLink(h_ews, s_ews)

        # OT Cell Zone Hosts
        h_plc_cool = self.addHost('h_plc_cool', ip='10.10.4.10/24', defaultRoute='via 10.10.4.1')
        h_plc_conv = self.addHost('h_plc_conv', ip='10.10.4.11/24', defaultRoute='via 10.10.4.1')
        h_icssim = self.addHost('h_icssim', ip='10.10.4.20/24', defaultRoute='via 10.10.4.1')
        self.addLink(h_plc_cool, s_ot)
        self.addLink(h_plc_conv, s_ot)
        self.addLink(h_icssim, s_ot)

        # Attacker Host
        h_att = self.addHost('h_att', ip='10.10.99.10/24', defaultRoute='via 10.10.99.1')
        self.addLink(h_att, s_att)


def apply_firewall_rules(fw_node):
    """Configures iptables on the fw node to implement IEC 62443 conduits."""
    script_path = Path(__file__).resolve().parent / "firewall_rules.sh"
    cmd = f"bash {script_path}"
    return fw_node.cmd(cmd)


def run_connectivity_tests(net):
    """Automated test validating IEC 62443 isolation policies."""
    print("\n--- Running IEC 62443 Connectivity Policy Checks ---")
    h_corp = net.get('h_corp')
    h_hist = net.get('h_hist')
    h_plc_cool = net.get('h_plc_cool')
    h_att = net.get('h_att')

    results = []

    # 1. IT -> DMZ should succeed (HTTP/ping)
    ping_corp_dmz = h_corp.cmd('ping -c 1 -W 1 10.10.2.20')
    ok_it_dmz = "1 packets transmitted, 1 received" in ping_corp_dmz or "0% packet loss" in ping_corp_dmz
    results.append(("Conduit C-01: IT to DMZ Ping", ok_it_dmz))

    # 2. IT -> OT MUST FAIL (Strict Drop)
    ping_corp_ot = h_corp.cmd('ping -c 1 -W 1 10.10.4.10')
    blocked_it_ot = "100% packet loss" in ping_corp_ot or "Destination Port Unreachable" in ping_corp_ot or ping_corp_ot == ""
    results.append(("Conduit C-02: IT to OT Isolation (Direct Ping Blocked)", blocked_it_ot))

    # 3. Attacker -> OT MUST FAIL
    ping_att_ot = h_att.cmd('ping -c 1 -W 1 10.10.4.10')
    blocked_att_ot = "100% packet loss" in ping_att_ot or "Destination Port Unreachable" in ping_att_ot or ping_att_ot == ""
    results.append(("Conduit C-05: Attacker to OT Isolation", blocked_att_ot))

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f" {status} {name}")

    all_passed = all(p for _, p in results)
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="IndustryLab IEC 62443 Mininet Cyber Range")
    parser.add_argument('--test', action='store_true', help="Run automated conduit validation and exit")
    parser.add_argument('--cli', action='store_true', help="Drop into Mininet interactive CLI")
    args = parser.parse_args()

    if not MININET_AVAILABLE:
        print("[!] Mininet is not installed in the current Python environment.")
        print("    You can still use Docker Compose or Kathará for containerized deployment.")
        sys.exit(1)

    setLogLevel('info')
    topo = PurdueTopo()
    net = Mininet(topo=topo, autoSetMacs=True)
    net.start()

    fw = net.get('fw')
    info("[*] Configuring firewall rules on router_fw...\n")
    apply_firewall_rules(fw)

    if args.test:
        success = run_connectivity_tests(net)
        net.stop()
        sys.exit(0 if success else 1)
    else:
        info("[*] Network started. Opening Mininet CLI. Type 'exit' to quit.\n")
        CLI(net)
        net.stop()


if __name__ == '__main__':
    main()
