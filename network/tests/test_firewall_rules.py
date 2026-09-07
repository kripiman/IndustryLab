"""Tests verifying IEC 62443 Purdue conduit policies and firewall rules."""
import subprocess
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_purdue_model_configuration_validity():
    config_file = REPO_ROOT / "config" / "purdue_model.yaml"
    assert config_file.exists(), "purdue_model.yaml must exist"

    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "zones" in data
    assert "conduits" in data

    zones = data["zones"]
    assert "enterprise" in zones
    assert "dmz" in zones
    assert "engineering" in zones
    assert "ot_cell" in zones
    assert "attacker" in zones

    # Check IP subnets
    assert zones["enterprise"]["subnet"] == "10.10.1.0/24"
    assert zones["dmz"]["subnet"] == "10.10.2.0/24"
    assert zones["engineering"]["subnet"] == "10.10.3.0/24"
    assert zones["ot_cell"]["subnet"] == "10.10.4.0/24"


def test_firewall_rules_dry_run_print():
    script_path = REPO_ROOT / "network" / "firewall_rules.sh"
    assert script_path.exists()

    result = subprocess.run(
        ["bash", str(script_path), "--print-rules"],
        capture_output=True,
        text=True,
        check=True
    )
    output = result.stdout
    assert "IEC 62443 PERA Conduits Ruleset" in output
    assert "Conduit C-01: IT" in output
    assert "Conduit C-02: IT (10.10.1.0/24) -> OT (10.10.4.0/24) [STRICT DROP + LOG]" in output
    assert "Conduit C-03: IDMZ Historian/DPI -> OT" in output
    assert "Conduit C-05: Attacker" in output


def test_firewall_script_syntax_and_conduits():
    script_path = REPO_ROOT / "network" / "firewall_rules.sh"
    content = script_path.read_text(encoding="utf-8")

    # Verify key iptables security directives
    assert "iptables -P FORWARD DROP" in content
    assert "iptables -A FORWARD -s 10.10.1.0/24 -d 10.10.4.0/24 -j IEC62443_VIOLATION" in content
    assert "iptables -A FORWARD -s 10.10.2.20 -d 10.10.4.0/24 -p tcp --dport 502" in content
    assert "iptables -A FORWARD -s 10.10.3.50 -d 10.10.4.0/24 -p tcp --dport 502" in content
