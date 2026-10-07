from pathlib import Path


PLANET = Path(__file__).resolve().parents[1] / "docs" / "planet" / "index.html"


def test_planet_wrapper_contains_bounded_copilot():
    text = PLANET.read_text(encoding="utf-8")
    for dom_id in [
        "dougPanel",
        "dougToggle",
        "dougQuestion",
        "dougAsk",
        "dougPlan",
        "dougOutput",
        "dougContext",
    ]:
        assert f'id="{dom_id}"' in text
    assert "http://127.0.0.1:8090" in text
    assert "godseyeApi" in text
    assert "/api/v1/godseye/query" in text
    assert "/api/v1/planetary/plan" in text
    assert "navigator.geolocation" not in text
    assert "textContent" in text
    assert "innerHTML" not in text


def test_untrusted_messages_are_ignored_before_state_update():
    text = PLANET.read_text(encoding="utf-8")
    origin_guard = "if(e.origin!=='https://xunia-mmgis-forge.onrender.com')return;"
    assert origin_guard in text
    assert text.index(origin_guard) < text.index("xunia:share-state")
    assert "trustedShareState" in text


def test_copilot_has_explicit_offline_state_without_fallback_service():
    text = PLANET.read_text(encoding="utf-8")
    assert "OFFLINE" in text
    assert "GODSEYE OFFLINE" in text
    assert "function currentMapContext" in text
    assert "function askDoug" in text
    assert "function planMission" in text
    assert "fetch(apiBase+'/api/v1/godseye/query'" in text.replace(" ", "")
    assert "fetch(apiBase+'/api/v1/planetary/plan'" in text.replace(" ", "")
    assert "localhost:8090" not in text
    assert "api.openai.com" not in text
