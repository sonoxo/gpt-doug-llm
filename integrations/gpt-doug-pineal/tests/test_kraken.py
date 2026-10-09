import pytest

from pineal.kraken import KrakenController, Telemetry
from pineal.store import PinealStore


def test_thresholds_and_hysteresis(tmp_path):
    control = KrakenController()
    assert control.evaluate(Telemetry(55, 160, 0.8)).mode == "nominal"
    assert control.evaluate(Telemetry(84, 250, 0.8)).mode == "throttle"
    assert control.evaluate(Telemetry(92, 250, 0.8)).mode == "safe_stop"
    assert control.evaluate(Telemetry(89, 250, 0.8), "safe_stop").mode == "safe_stop"
    assert control.evaluate(Telemetry(70, 250, 0.8), "safe_stop").mode == "nominal"
    assert control.evaluate(Telemetry(55, 160, 0.1)).mode == "conserve"
    assert control.evaluate(Telemetry(55, 160, 0.1)).actuated is False


def test_records_advisory_only(tmp_path):
    store = PinealStore(tmp_path / "db.sqlite3")
    rec = store.record_telemetry(temperature_c=55, power_w=160, water_fraction=0.8,
                                 mode="nominal", rationale="simulated")
    assert rec["actuated"] is False
    assert store.latest_telemetry()["temperature_c"] == 55
    assert store.verify_audit()["ok"]
    with pytest.raises(ValueError):
        store.record_telemetry(temperature_c=float("nan"), power_w=160, water_fraction=0.8,
                               mode="nominal", rationale="bad")
