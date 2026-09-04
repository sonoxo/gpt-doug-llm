from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "the-green-house" / "bin" / "worldmonitor-convergence.py"
SPEC = importlib.util.spec_from_file_location("worldmonitor_convergence", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_build_request_uses_canonical_worldmonitor_key_header():
    request = MODULE.build_mcp_request("wm_test_key", min_domains=3)
    headers = dict(request.header_items())
    assert headers["X-worldmonitor-key"] == "wm_test_key"
    assert "Authorization" not in headers
    body = json.loads(request.data.decode("utf-8"))
    assert body["params"]["name"] == "get_signal_convergence"
    assert body["params"]["arguments"]["min_domains"] == 3


def test_extracts_structured_content():
    payload = {"result": {"structuredContent": {"stale": False, "data": {"alerts": []}}}}
    assert MODULE._extract_mcp_payload(payload)["data"]["alerts"] == []


def test_extracts_text_content_json():
    inner = {"stale": False, "data": {"alerts": [{"cellId": "1,2"}]}}
    envelope = {"result": {"content": [{"type": "text", "text": json.dumps(inner)}]}}
    assert MODULE._extract_mcp_payload(envelope) == inner


def test_mena_filter_and_score_normalization():
    regions = {
        "MENA": MODULE.RegionBounds(
            name="MENA",
            min_lat=12,
            max_lat=42,
            min_lon=-18,
            max_lon=65,
            description="test bounds",
        )
    }
    upstream = {
        "stale": False,
        "cached_at": "2026-09-04T00:00:00Z",
        "data": {
            "min_domains": 3,
            "feeds": {"military_flights": 4, "protests": 2},
            "alerts": [
                {
                    "cellId": "34,35",
                    "lat": 34.05,
                    "lon": 35.12,
                    "types": ["military_flight", "military_vessel", "protest"],
                    "totalEvents": 7,
                    "score": 89,
                    "location": "Eastern Mediterranean",
                },
                {
                    "cellId": "50,100",
                    "lat": 50.0,
                    "lon": 100.0,
                    "types": ["military_flight", "military_vessel", "earthquake"],
                    "totalEvents": 5,
                    "score": 85,
                },
            ],
        },
    }
    result = MODULE.adapt_response(upstream, region="MENA", time_window="6h", regions=regions)
    assert result["status"] == "success"
    assert len(result["data"]) == 1
    alert = result["data"][0]
    assert alert["location"]["lat"] == 34.05
    assert alert["location"]["lng"] == 35.12
    assert alert["confidence"] == 0.89
    assert alert["signals"] == ["military_flight", "military_vessel", "protest"]
    assert result["meta"]["requested_time_window"] == "6h"
    assert result["meta"]["source_time_window"] == "24h"
    assert result["meta"]["window_exact"] is False


def test_24h_request_is_exact():
    result = MODULE.adapt_response({"data": {"alerts": []}}, time_window="24h")
    assert result["meta"]["window_exact"] is True
