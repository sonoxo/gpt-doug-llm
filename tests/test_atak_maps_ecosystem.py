"""ATAK-Maps XML catalog integration: deterministic offline contract tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tak_geo.atlas_ontology import build_ontology
from tak_geo.cli import main
from tak_geo.map_sources import CatalogError, inspect_checkout, render_catalog_page, write_ecosystem


def _write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def local_repo(root: Path) -> Path:
    _write(root, "README.md", "# Local test ATAK-Maps clone\n")
    _write(root, "schema/mobac-maps.xsd", '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>')
    _write(root, "descriptions.yml", """
usgs-usgs-usgsimageryonly:
  category: Satellite
  text: "USGS national map imagery."
grg-fema:
  category: Overlay
  text: "Synthetic WMS metadata test."
""".strip())
    _write(root, "usgs/usgs_usgsimageryonly.xml", """<?xml version="1.0"?>
<customMapSource>
<name>USGS - Usgsimageryonly</name><minZoom>0</minZoom><maxZoom>15</maxZoom>
<tileType>png</tileType>
<url>https://basemap.nationalmap.gov/ArcGIS/rest/services/USGSImageryOnly/MapServer/tile/{$z}/{$y}/{$x}</url>
</customMapSource>
""")
    _write(root, "GRG/fema.xml", """<?xml version="1.0"?>
<customWmsMapSource>
<name>FEMA sample</name><minZoom>5</minZoom><maxZoom>19</maxZoom>
<tileType>PNG</tileType><version>1.3.0</version><layers>12</layers>
<url>https://hazards.fema.gov/arcgis/services/public/NFHLWMS/MapServer/WMSServer?</url>
<aditionalparameters>&amp;TRANSPARENT=TRUE</aditionalparameters>
</customWmsMapSource>
""")
    _write(root, "BLM/composite.xml", """<?xml version="1.0"?>
<customMultiLayerMapSource><name>Example composite</name><layersAlpha>1.0 0.5</layersAlpha>
<layers>
<customMapSource><name>Image</name><maxZoom>14</maxZoom>
<url>https://example.org/imagery/{$z}/{$x}/{$y}.jpg</url></customMapSource>
<customMapSource><name>Overlay</name><maxZoom>14</maxZoom>
<url>https://public.example.com/land/{$z}/{$x}/{$y}.png</url></customMapSource>
</layers>
</customMultiLayerMapSource>""")
    _write(root, "OrdnanceSurvey/os_road.xml", """<?xml version="1.0"?>
<customMapSource><name>OS Road</name><maxZoom>16</maxZoom>
<url>https://api.os.uk/maps/raster/v1/zxy/Road_3857/{$z}/{$x}/{$y}.png?key=API_KEY_HERE</url>
</customMapSource>""")
    return root


def test_real_mobac_schema_variants_are_catalogued(tmp_path):
    report = inspect_checkout(local_repo(tmp_path / "ATAK-Maps"))
    assert report["source"]["source_xml_files"] == 4
    assert report["summary"]["sources"] == 4
    assert report["summary"]["providers"] == 4
    assert report["summary"]["issues"] == 0
    assert report["summary"]["optional_usgs_preview"] == 1
    assert report["summary"]["requires_key"] == 1
    assert report["summary"]["formats"] == {"Multi-Layer": 1, "WMS": 1, "TMS": 2}
    assert report["policy"]["network_access"] is False
    assert report["source"]["provider_imagery_rights"] == "NOT_CONVEYED_BY_REPOSITORY_LICENSE"
    item = next(e for e in report["entries"] if e["provider"] == "BLM")
    assert item["layers_alpha"] == [1.0, 0.5]
    assert item["layer_names"] == ["Image", "Overlay"]
    assert item["url_templates_emitted"] is False
    assert "Satellite" in {e["category"] for e in report["entries"]}


def test_ontology_is_deterministic_and_does_not_claim_live_data(tmp_path):
    catalog = inspect_checkout(local_repo(tmp_path / "ATAK-Maps"))
    one = build_ontology(catalog)
    two = build_ontology(catalog)
    assert one == two
    assert len(one["nodes"]) >= 4 + 4
    assert one["no_live_device_inference"] is True
    assert one["runtime_connections"] == 0
    assert all("access_policy" in node["properties"] for node in one["nodes"] if node["type"] == "MapSource")
    assert any(edge["relationship"] == "OPTIONAL_OPERATOR_OPT_IN_PREVIEW" for edge in one["edges"])


def test_exported_local_atlas_has_viewer_and_documented_provenance(tmp_path):
    root = local_repo(tmp_path / "ATAK-Maps")
    output = tmp_path / "build"
    first = write_ecosystem(root, output)
    assert first["summary"]["sources"] == 4
    assert first["network_calls"] == 0
    assert first["tak_server_connected"] is False
    for filename in ("atlas.html", "index.html", "data.geojson", "catalog.json",
                     "atlas-ontology.json", "ecosystem-status.json"):
        assert (output / filename).is_file()
    embedded = (output / "atlas.html").read_text(encoding="utf-8")
    assert "const catalog = {" in embedded
    assert "provider graph" in embedded.lower()
    assert "MIT" in embedded and "Joshua Fuller" in embedded
    with pytest.raises(CatalogError, match="--force"):
        write_ecosystem(root, output)
    assert write_ecosystem(root, output, force=True) == first


def test_cannot_embed_html_or_script_in_catalog_json(tmp_path):
    root = local_repo(tmp_path / "ATAK-Maps")
    _write(root, "descriptions.yml", """
usgs-usgs-usgsimageryonly:
  category: Satellite
  text: "</script><img src=x onerror=alert(1)>"
""".strip())
    report = inspect_checkout(root)
    rendered = render_catalog_page(report, "<script>const catalog = __ATAK_MAPS_CATALOG__;</script>")
    assert '</script><img' not in rendered
    assert "\\u003c/script\\u003e" in rendered


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://127.0.0.1/tiles/{$z}/{$x}/{$y}",
    "http://169.254.169.254/metadata/{$z}/{$x}/{$y}",
    "http://localhost:8123/{$z}/{$x}/{$y}",
    "https://user:secret@example.com/{$z}/{$x}/{$y}",
    "https://public.example.com/{$z}/{$x}/{$y}?token=EXPOSED_SECRET",
])
def test_unsafe_url_is_rejected_without_exposing_credentials(tmp_path, url):
    root = local_repo(tmp_path / "ATAK-Maps")
    _write(root, "bad/evil.xml", """<customMapSource><name>bad</name><maxZoom>8</maxZoom><url>"""
           + url.replace("&", "&amp;") + "</url></customMapSource>")
    report = inspect_checkout(root)
    assert report["summary"]["issues"] == 1
    assert report["summary"]["sources"] == 4
    assert "EXPOSED_SECRET" not in json.dumps(report)


@pytest.mark.parametrize("bad_xml", [
    '<!DOCTYPE customMapSource [<!ENTITY x "secret">]><customMapSource><name>&x;</name></customMapSource>',
    '<customMapSource><name>Broken</name><maxZoom>1</maxZoom><url>https://example.com/a.png</url></customMapSource>',
    '<customMultiLayerMapSource><name>Broken</name><layersAlpha>0.2 0.4</layersAlpha><layers><customMapSource><name>One</name><maxZoom>5</maxZoom><url>https://example.org/{$z}/{$x}/{$y}</url></customMapSource></layers></customMultiLayerMapSource>',
    '<customMapSource><name>Missing zoom</name><url>https://example.com/{$z}/{$x}/{$y}</url></customMapSource>',
])
def test_invalid_xml_is_never_trusted(tmp_path, bad_xml):
    root = local_repo(tmp_path / "ATAK-Maps")
    _write(root, "bad/evil.xml", bad_xml)
    result = inspect_checkout(root)
    assert result["summary"]["issues"] == 1


def test_checkouts_must_have_upstream_schema_and_docs(tmp_path):
    with pytest.raises(CatalogError, match="ATAK-Maps checkout"):
        inspect_checkout(tmp_path)


def test_cli_diagnostics_and_ecosystem_export(tmp_path, capsys):
    root = local_repo(tmp_path / "ATAK-Maps")
    assert main(["maps-doctor", "--source", str(root)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["network_actions"] == 0
    assert out["ready_for_release"] is False
    dest = tmp_path / "outputs"
    assert main(["ecosystem", "--source", str(root), "--output", str(dest)]) == 0
    generated = json.loads(capsys.readouterr().out)
    assert generated["ok"] is True
    assert generated["summary"]["sources"] == 4
    assert (dest / "atlas-ontology.json").exists()


def test_symlink_input_is_not_followed(tmp_path):
    root = local_repo(tmp_path / "ATAK-Maps")
    source = tmp_path / "my-elsewhere.xml"
    source.write_text("<bad/>")
    (root / "GRG" / "symlink.xml").symlink_to(source)
    with pytest.raises(CatalogError, match="not a regular file"):
        inspect_checkout(root)
