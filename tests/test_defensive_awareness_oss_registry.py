import json
import pathlib


REGISTRY = pathlib.Path("safety-shield/integrations/defensive-awareness-oss.json")


def _load_registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_registry_contains_expected_open_source_components():
    registry = _load_registry()
    repos = {component["repository"] for component in registry["components"]}
    assert repos == {
        "https://github.com/nasa/openmct",
        "https://github.com/CesiumGS/cesium",
        "https://github.com/dstl/Stone-Soup",
        "https://github.com/sandialabs/tracktable",
        "https://github.com/postgis/postgis",
        "https://github.com/maplibre/maplibre-gl-js",
    }


def test_registry_allows_defensive_awareness_but_not_weapon_control():
    registry = _load_registry()
    contract = registry["dataContract"]
    guardrails = registry["guardrails"]

    assert registry["mode"] == "DEFENSIVE_AWARENESS_ONLY"
    assert contract["authorizedLiveTelemetry"] is True
    assert contract["realWorldGeospatialAwareness"] is True
    assert contract["humanReviewedAlerts"] is True
    assert contract["externalWritesDefault"] == "DENY"

    assert guardrails["weaponTargeting"] is False
    assert guardrails["aimpointGeneration"] is False
    assert guardrails["interceptGuidance"] is False
    assert guardrails["fireControl"] is False
    assert guardrails["autonomousEngagement"] is False
    assert guardrails["weaponsRelease"] is False
    assert guardrails["humanAuthorityRequiredForMaterialAction"] is True
