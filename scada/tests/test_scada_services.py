"""Unit tests for SCADA Historian and Alarm Monitoring."""
import json
import time
import urllib.request
from scada.historian_service import HistorianStore, ScadaHistorian


def test_historian_store_and_alarms():
    store = HistorianStore()

    # 1. Nominal update
    store.update_cooling(temp_c=45.0, flow_lpm=120.0, valve_pct=35, pump_run=True)
    snap = store.get_snapshot()
    assert snap["telemetry"]["cooling"]["temp_c"] == 45.0
    assert len(snap["alarms"]) == 0

    # 2. Warning high temp (86 C)
    store.update_cooling(temp_c=86.0, flow_lpm=100.0, valve_pct=50, pump_run=True)
    snap = store.get_snapshot()
    assert any(a["code"] == "COOLING_HIGH_TEMP" for a in snap["alarms"])

    # 3. Emergency trip (96 C)
    store.update_cooling(temp_c=96.0, flow_lpm=50.0, valve_pct=100, pump_run=True)
    snap = store.get_snapshot()
    assert any(a["code"] == "COOLING_EMERGENCY_TRIP" for a in snap["alarms"])

    # 4. Conveyor vibration trip (12.5 mm/s)
    store.update_conveyor(speed_pct=70, feed_tph=840, vib_mms=12.5, lube_bar=3.0, current_a=380)
    snap = store.get_snapshot()
    assert any(a["code"] == "CONVEYOR_VIBRATION_TRIP" for a in snap["alarms"])

    # 5. Loss of View Watchdog: 3 failures
    store.record_failure("cooling")
    store.record_failure("cooling")
    store.record_failure("cooling")
    snap = store.get_snapshot()
    assert snap["telemetry"]["cooling"]["online"] is False
    assert any(a["code"] == "LOSS_OF_VIEW" for a in snap["alarms"])


def test_scada_historian_rest_api():
    port = 18080
    historian = ScadaHistorian(api_host="127.0.0.1", api_port=port)
    historian.start(background=True)
    time.sleep(0.2)

    try:
        # Test /api/telemetry
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/telemetry") as res:
            assert res.status == 200
            data = json.loads(res.read().decode('utf-8'))
            assert "cooling" in data
            assert "conveyor" in data

        # Test /api/alarms
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/alarms") as res:
            assert res.status == 200
            data = json.loads(res.read().decode('utf-8'))
            assert isinstance(data, list)
    finally:
        historian.stop()
