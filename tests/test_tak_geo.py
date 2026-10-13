from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from gpt_brain.router import BrainRouter
from tak_geo.cli import main
from tak_geo.core import (
    GeoInputError, cot_to_geojson, load_file, normalize_geojson,
    render_dashboard, write_dashboard,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "tak_geo" / "synthetic-civilian-exercise.geojson"
COT = ROOT / "examples" / "tak_geo" / "sample-event.cot"


def test_demo_fixture_is_explicitly_synthetic():
    data = load_file(DATA)
    assert len(data["features"]) == 6
    assert {f["geometry"]["type"] for f in data["features"]} == {
        "Point", "LineString", "Polygon",
    }
    assert all(f["properties"]["source_kind"] == "SYNTHETIC" for f in data["features"])


def test_cot_xml_import_is_local_and_has_valid_location():
    data = load_file(COT)
    item = data["features"][0]
    assert item["properties"]["name"] == "SYNTHETIC-LAB"
    assert item["properties"]["source_kind"] == "LOCAL_COT_FILE"
    assert item["geometry"]["coordinates"] == [-77.436, 37.541]


@pytest.mark.parametrize("xml", [
    b'<!DOCTYPE event [<!ENTITY secret "x">]><event>&secret;</event>',
    b'<event uid="x"><point lat="91" lon="-77"/></event>',
    b'<event uid="x"><point lat="37"/></event>',
    b'<event><point lat="nan" lon="0"/></event>',
    b'<event><point lat="37" lon="181"/></event>',
    b'<root><event><point lat="0" lon="0"/></event></root>',
])
def test_invalid_cot_rejected(xml):
    with pytest.raises(GeoInputError):
        cot_to_geojson(xml)


def test_large_cot_rejected():
    with pytest.raises(GeoInputError, match="2 MB"):
        cot_to_geojson(b"x" * 2_000_001)


def test_coordinates_must_be_wgs84_and_finite():
    obj = json.loads(DATA.read_text())
    obj["features"][0]["geometry"]["coordinates"] = [float("inf"), 20]
    with pytest.raises(GeoInputError):
        normalize_geojson(obj)
    obj["features"][0]["geometry"]["coordinates"] = [-181, 20]
    with pytest.raises(GeoInputError):
        normalize_geojson(obj)


def test_deny_unsupported_geometry():
    obj = json.loads(DATA.read_text())
    obj["features"][0]["geometry"]["type"] = "GeometryCollection"
    with pytest.raises(GeoInputError):
        normalize_geojson(obj)


def test_geometry_vertex_cap():
    obj = json.loads(DATA.read_text())
    obj["features"][4]["geometry"]["coordinates"] = [[-77.4, 37.5]] * 10_001
    with pytest.raises(GeoInputError):
        normalize_geojson(obj)


def test_untrusted_html_labels_are_escaped():
    obj = json.loads(DATA.read_text())
    obj["features"][0]["properties"]["name"] = '</script><img src=x onerror=alert(1)>'
    template = '<script>const DEMO = __TAK_GEO_DATA__;</script>'
    rendered = render_dashboard(obj, template)
    assert "</script><img" not in rendered
    assert "\\u003c/script\\u003e" in rendered


def test_dashboard_outputs_and_offline_posture(tmp_path):
    report = write_dashboard(load_file(DATA), tmp_path / "geo")
    folder = tmp_path / "geo"
    assert report["feature_count"] == 6
    assert report["tak_server_connected"] is False
    assert report["external_requests_by_default"] is False
    for filename in ("index.html", "data.geojson", "manifest.json"):
        assert (folder / filename).is_file()
    markup = (folder / "index.html").read_text()
    assert "USGSImageryOnly" in markup and "USGSTopo" in markup
    assert '<option value="offline">' in markup
    assert "const DEMO = {" in markup


def test_output_overwrite_requires_explicit_flag(tmp_path):
    data = load_file(DATA)
    write_dashboard(data, tmp_path / "viewer")
    with pytest.raises(GeoInputError, match="--force"):
        write_dashboard(data, tmp_path / "viewer")
    write_dashboard(data, tmp_path / "viewer", overwrite=True)


def test_local_cli_status_and_demo(tmp_path, capsys):
    assert main(["status"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["authorized_tak_server_connection"] is False
    assert main(["demo", "--output", str(tmp_path / "viewer")]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["feature_count"] == 6
    assert (tmp_path / "viewer" / "index.html").exists()


def test_cli_convert_cot_without_server(tmp_path, capsys):
    dest = tmp_path / "event.geojson"
    assert main(["convert", str(COT), "--output", str(dest)]) == 0
    assert json.loads(dest.read_text())["features"][0]["geometry"]["type"] == "Point"
    assert main(["convert", str(COT), "--output", str(dest)]) == 2
    assert "already exists" in capsys.readouterr().err


def test_router_includes_geospatial_specialist():
    names = [a.name for a in BrainRouter().route("ATAK geojson mapping and imagery", max_agents=4)]
    assert "geospatial" in names


def test_unsupported_file_extension_fails(tmp_path):
    path = tmp_path / "malicious.html"
    path.write_text("hello")
    with pytest.raises(GeoInputError):
        load_file(path)
