from pathlib import Path

from godseye.planetary import planetary_layers, planetary_plan, planetary_status


PLANET_HTML = """<!doctype html><script>const BASE='https://xunia-mmgis-forge.onrender.com/';</script>"""


def test_planetary_status_reads_wrapper_and_research_refs(tmp_path: Path):
    planet = tmp_path / "index.html"
    planet.write_text(PLANET_HTML, encoding="utf-8")
    registry = [
        {"id": "public-space", "name": "Public Space", "mode": "PUBLIC", "freshnessSeconds": 3600},
        {"id": "robot-sim", "name": "Robot Sim", "mode": "SIMULATION", "freshnessSeconds": 5},
    ]

    result = planetary_status(planet_path=planet, source_registry=registry)

    assert result["schema"] == "gpt-doug.planetary-status.v1"
    assert result["status"] == "ONLINE"
    assert result["mmgis"]["forgeUrl"] == "https://xunia-mmgis-forge.onrender.com/"
    assert result["sourceCount"] == 2
    assert any(item["repository"] == "Roboparty/roboto_origin" for item in result["researchReferences"])
    assert all(item["actuation"] is False for item in result["researchReferences"])


def test_missing_planet_wrapper_degrades(tmp_path: Path):
    result = planetary_status(planet_path=tmp_path / "missing.html", source_registry=[])
    assert result["status"] == "DEGRADED"
    assert result["partial"] is True
    assert result["errors"]


def test_planetary_layers_normalize_registry(tmp_path: Path):
    planet = tmp_path / "index.html"
    planet.write_text(PLANET_HTML, encoding="utf-8")
    status = planetary_status(
        planet_path=planet,
        source_registry=[{"id": "public-space", "name": "Space", "mode": "PUBLIC", "freshnessSeconds": 120}],
    )
    assert planetary_layers(status) == [
        {"id": "public-space", "name": "Space", "mode": "PUBLIC", "freshnessSeconds": 120, "enabled": True}
    ]


def test_planetary_plan_uses_bounded_warhawk(tmp_path: Path):
    planet = tmp_path / "index.html"
    planet.write_text(PLANET_HTML, encoding="utf-8")

    class FakeWarHawk:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def plan(self, mission: str):
            return {"status": "PLANNED", "mission": mission, "execution": "DRY_RUN"}

    def status_fn():
        return planetary_status(planet_path=planet, source_registry=[])

    result = planetary_plan(
        "compare visible infrastructure dependencies",
        warhawk_factory=FakeWarHawk,
        status_fn=status_fn,
    )
    assert result["schema"] == "gpt-doug.planetary-plan.v1"
    assert result["mission"] == "compare visible infrastructure dependencies"
    assert result["planetary"]["status"] == "ONLINE"
    assert result["warhawk"]["execution"] == "DRY_RUN"


def test_planetary_plan_rejects_empty_mission():
    try:
        planetary_plan("   ", warhawk_factory=lambda **kwargs: None, status_fn=lambda: {})
    except ValueError as exc:
        assert "mission" in str(exc)
    else:
        raise AssertionError("expected ValueError")
