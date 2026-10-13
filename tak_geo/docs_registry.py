"""Public TAK documentation index, capability coverage and local private-doc inventory.

This module stores reference metadata only. Never download an authenticated
TAK.gov document or upload, embed, mirror or commit locally supplied manuals.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCHEMA = "xunia.tak.documentation.v1"
PUBLIC_ATAK_SHA = "9f6893dd657feacc35ec5de03dad721c2e44170e"
PUBLIC_SERVER_SHA = "5187abd46d827d37cfc5708805eced197a837e49"
ATAK_MAPS_SHA = "9dd45641a6849bf52e56b279e39b27126573c434"
SOURCE_BASE = "https://github.com/TAK-Product-Center/atak-civ/blob/" + PUBLIC_ATAK_SHA + "/"
SERVER_BASE = "https://github.com/TAK-Product-Center/Server/blob/" + PUBLIC_SERVER_SHA + "/"
MAPS_BASE = "https://github.com/sonoxo/ATAK-Maps/blob/" + ATAK_MAPS_SHA + "/"
ALLOWED_DOMAINS = {"tak.gov", "www.tak.gov", "github.com"}
VALID_ACCESS = {"public", "login_required"}
VALID_STATUS = {"implemented", "partial", "reference_only", "access_required"}
AREAS = {
    "access_governance", "atak_civ", "plugins", "cot_schemas", "tak_protocol",
    "tak_server", "mapping_imagery", "development_tooling", "training",
}
FILE_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".xml", ".json", ".pdf", ".odt"}
TEXT_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".xml", ".json"}
MAX_FILES = 160
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TEXT_SEARCH = 1024 * 1024

# Authenticated TAK resources are a reference and access requirement only.
# All other references are public source links independently verified from
# TAK.gov public pages or TAK-Product-Center GitHub code/documentation.
DOCS: tuple[dict[str, Any], ...] = (
    dict(id="tak-resource-library", title="TAK.gov Documentation Resources", area="access_governance",
         url="https://tak.gov/documentation/resources", access="login_required",
         origin="TAK.gov", status="access_required",
         summary="Authentication-gated documentation listing; contents not retrieved.",
         mapping="Local authorized-document inventory only", evidence="AUTH_REDIRECT_CONFIRMED"),
    dict(id="tak-developer-policies", title="TAK.gov Development and Distribution Policies", area="access_governance",
         url="https://tak.gov/pages/our-process", access="public", origin="TAK.gov", status="implemented",
         summary="Developer categories, SDK access, licensing, distribution and operational approval boundaries.",
         mapping="Public-source licensing and access-policy guards"),
    dict(id="tak-faq", title="TAK.gov FAQ", area="access_governance",
         url="https://tak.gov/faq", access="public", origin="TAK.gov", status="implemented",
         summary="General software access, authority-to-operate and map/SDK questions.",
         mapping="Compliance disclosure and documentation gating"),
    dict(id="tak-sdks", title="TAK.gov SDKs", area="development_tooling",
         url="https://tak.gov/pages/sdks", access="public", origin="TAK.gov", status="reference_only",
         summary="Public SDK overview and links, not a grant of private SDK repository access.",
         mapping="Future separately authorized SDK build assessment"),
    dict(id="tak-civil-usage", title="TAK.gov Civilian and Emergency Solutions", area="atak_civ",
         url="https://tak.gov/solutions/emergency", access="public", origin="TAK.gov", status="reference_only",
         summary="Public TAK product roles, client and server use-case overview.",
         mapping="Non-operational role and capability matrix"),
    dict(id="tak-dev-track", title="TAK Offsite Developer Track", area="training",
         url="https://tak.gov/events/2021-dev-track", access="public", origin="TAK.gov", status="reference_only",
         summary="Developer training categories and access prerequisites; event is historical.",
         mapping="Developer training roadmap"),
    dict(id="atak-civ-overview", title="Official ATAK-CIV README", area="atak_civ",
         url=SOURCE_BASE+"README.md", access="public", origin="TAK Product Center", status="reference_only",
         summary="Official open-source ATAK-CIV project overview and dependency/license pointers.",
         mapping="Public code provenance; no SDK binaries copied"),
    dict(id="atak-civ-build", title="ATAK-CIV Developer README", area="development_tooling",
         url=SOURCE_BASE+"atak/README.md", access="public", origin="TAK Product Center", status="reference_only",
         summary="Current official ATAK Android toolchain requirements and build variants.",
         mapping="Standalone Android development compatibility plan"),
    dict(id="atak-civ-license", title="ATAK-CIV Public Repository License", area="access_governance",
         url=SOURCE_BASE+"LICENSE.md", access="public", origin="TAK Product Center", status="reference_only",
         summary="License terms for official open-source repository; different from gated TAK software EULAs.",
         mapping="Package provenance and redistributability review"),
    dict(id="atak-civ-thirdparty", title="ATAK-CIV Third-Party Dependencies", area="access_governance",
         url=SOURCE_BASE+"THIRDPARTY.md", access="public", origin="TAK Product Center", status="reference_only",
         summary="Dependency license and attribution reference.",
         mapping="Software bill-of-materials/license review gate"),
    dict(id="atak-plugin-architecture", title="ATAK Plugin Architecture README", area="plugins",
         url=SOURCE_BASE+"atak/README.md", access="public", origin="TAK Product Center", status="reference_only",
         summary="Development overview; plugin architecture further documented in official plugin examples.",
         mapping="Plugin integration design only; no unsigned APK"),
    dict(id="atak-plugin-hello", title="ATAK HelloWorld Plugin Example", area="plugins",
         url=SOURCE_BASE+"plugin-examples/helloworld/README.md", access="public", origin="TAK Product Center",
         status="reference_only", summary="Minimal plugin structure, lifecycle/tool descriptors and Android contexts.",
         mapping="Future source-backed plugin skeleton with separate approval"),
    dict(id="atak-plugin-custom-tiles", title="ATAK Custom Tiles Example", area="plugins",
         url=SOURCE_BASE+"plugin-examples/customtiles/README.md", access="public", origin="TAK Product Center",
         status="reference_only", summary="Public plugin example directory; README has limited implementation detail.",
         mapping="MOBAC compatibility investigation"),
    dict(id="tak-cot-overview", title="TAK Cursor-on-Target Schema README", area="cot_schemas",
         url=SOURCE_BASE+"takcot/README.md", access="public", origin="TAK Product Center", status="partial",
         summary="Official CoT schema collection including MITRE base definitions and TAK details.",
         mapping="Local CoT point importer; full XSD validation is not implemented"),
    dict(id="tak-cot-point-schema", title="CoT Point XSD", area="cot_schemas",
         url=SOURCE_BASE+"takcot/xsd/event/point.xsd", access="public", origin="TAK Product Center",
         status="partial", summary="Schema reference for CoT WGS84 point properties.",
         mapping="CoT lat/lon parsing and range checks"),
    dict(id="tak-cot-route-schema", title="TAK CoT Route XSD", area="cot_schemas",
         url=SOURCE_BASE+"takcot/xsd/Route.xsd", access="public", origin="TAK Product Center",
         status="reference_only", summary="Documented route CoT shape and detail extension schema.",
         mapping="Route support requires independent CoT schema parser"),
    dict(id="tak-protocol-reference", title="TAK Protocol Documentation", area="tak_protocol",
         url=SOURCE_BASE+"takproto/README.txt", access="public", origin="TAK Product Center", status="partial",
         summary="Legacy CoT XML protocol and versioned protobuf payload conventions.",
         mapping="Local CoT XML supported; no live streams or protobuf negotiation"),
    dict(id="tak-protocol-cotevent", title="TAK Protocol CoT Event Message", area="tak_protocol",
         url=SOURCE_BASE+"takproto/cotevent.proto", access="public", origin="TAK Product Center",
         status="reference_only", summary="Public protobuf schema definitions for CoT events.",
         mapping="Future offline protobuf importer if licensed/approved"),
    dict(id="tak-protocol-message", title="TAK Protocol Message Schema", area="tak_protocol",
         url=SOURCE_BASE+"takproto/takmessage.proto", access="public", origin="TAK Product Center",
         status="reference_only", summary="Public TAK message protobuf container specification.",
         mapping="Future offline protobuf framing review"),
    dict(id="tak-server-readme", title="TAK Server Public README", area="tak_server",
         url=SERVER_BASE+"README.md", access="public", origin="TAK Product Center", status="reference_only",
         summary="Public TAK Server development, build, local PostGIS and API overview.",
         mapping="Documentation-only TAK Server contract; no connection"),
    dict(id="tak-server-testing", title="TAK Server Testing Guide", area="tak_server",
         url=SERVER_BASE+"src/takserver-takcl-core/docs/testing.md", access="public",
         origin="TAK Product Center", status="reference_only",
         summary="Public TAK Server test execution guidance; not a service credential.",
         mapping="Future authenticated test integration only"),
    dict(id="tak-server-dev", title="TAK Server Development Guide", area="tak_server",
         url=SERVER_BASE+"src/takserver-takcl-core/docs/Development.md", access="public",
         origin="TAK Product Center", status="reference_only",
         summary="Public TAK Server test architecture and development notes.",
         mapping="Server interoperability planning and boundaries"),
    dict(id="atak-maps-reference", title="ATAK-Maps MOBAC XML Reference", area="mapping_imagery",
         url=MAPS_BASE+"docs/xml-reference.md", access="public", origin="ATAK-Maps community",
         status="implemented", summary="XML source definitions for TMS, WMS and multilayer raster maps.",
         mapping="MOBAC parser, map-source registry and source provenance"),
    dict(id="atak-maps-install", title="ATAK-Maps Installation Guide", area="mapping_imagery",
         url=MAPS_BASE+"docs/install-guide.md", access="public", origin="ATAK-Maps community",
         status="partial", summary="ATAK import paths and offline tile caching procedures.",
         mapping="Offline metadata catalog; no tile caching performed"),
    dict(id="atak-maps-schema", title="ATAK-Maps XML Schema", area="mapping_imagery",
         url=MAPS_BASE+"schema/mobac-maps.xsd", access="public", origin="ATAK-Maps community",
         status="partial", summary="Syntax schema for basic map sources, WMS and composites.",
         mapping="Structural checks only; full XSD checking delegated to upstream"),
)


def validate_document_refs(records: tuple[dict[str, Any], ...] = DOCS) -> None:
    seen: set[str] = set()
    for record in records:
        key = record.get("id")
        if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,70}", key):
            raise ValueError("documentation ID must be a lowercase slug")
        if key in seen:
            raise ValueError(f"duplicate documentation ID: {key}")
        seen.add(key)
        if record.get("area") not in AREAS or record.get("access") not in VALID_ACCESS:
            raise ValueError(f"invalid documentation area/access: {key}")
        if record.get("status") not in VALID_STATUS:
            raise ValueError(f"invalid documentation implementation status: {key}")
        parsed = urlsplit(record.get("url", ""))
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOMAINS or parsed.username or parsed.password:
            raise ValueError(f"untrusted documentation URL for {key}")
        if not isinstance(record.get("summary"), str) or not record["summary"].strip():
            raise ValueError(f"missing documentation description: {key}")
        if record["access"] == "login_required" and record["status"] != "access_required":
            raise ValueError("login-restricted docs may not be marked implemented")


def public_registry() -> dict[str, Any]:
    validate_document_refs()
    records = [dict(item) for item in DOCS]
    by_area = {}
    for area in sorted(AREAS):
        subset = [r for r in records if r["area"] == area]
        by_area[area] = {
            "references": len(subset),
            "public": sum(x["access"] == "public" for x in subset),
            "login_required": sum(x["access"] == "login_required" for x in subset),
            "implemented_or_partial": sum(x["status"] in {"implemented", "partial"} for x in subset),
        }
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SCHEMA,
        "system": "GPT-DOUG TAK DOCUMENTATION REGISTRY",
        "authority": "PUBLIC_REFERENCES_ONLY",
        "official_login_required": True,
        "authenticated_library_scraped": False,
        "public_full_text_mirrored": False,
        "sdk_installed": False,
        "tak_server_connected": False,
        "document_count": len(records),
        "public_references": sum(r["access"] == "public" for r in records),
        "login_required_references": sum(r["access"] == "login_required" for r in records),
        "source_commits": {
            "atak_civ": PUBLIC_ATAK_SHA, "tak_server": PUBLIC_SERVER_SHA,
            "atak_maps": ATAK_MAPS_SHA,
        },
        "areas": by_area,
        "records": records,
        "registry_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "limitations": [
            "Authenticated TAK.gov resource-library contents have not been retrieved",
            "The catalog indexes titles, links and engineering implications, not every available manual",
            "Reference documentation does not authorize SDK, signing, distribution, network or operational use",
            "Source links are public references, not automatically synchronized or cached",
        ],
    }


def documentation_graph(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or public_registry()
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    nodes["docportal:tak"] = {"id": "docportal:tak", "type": "DocumentationRegistry",
                              "label": "GPT-Doug TAK Documentation", "access": "REFERENCE_ONLY"}
    for record in registry["records"]:
        ref_id = "doc:" + record["id"]
        area_id = "area:" + record["area"]
        access_id = "access:" + record["access"]
        nodes[ref_id] = {
            "id": ref_id, "type": "DocumentReference", "label": record["title"],
            "url": record["url"], "origin": record["origin"],
            "access": record["access"], "implementation": record["status"],
        }
        nodes[area_id] = {"id": area_id, "type": "DocumentationDomain",
                          "label": record["area"]}
        nodes[access_id] = {"id": access_id, "type": "AccessPolicy",
                            "label": record["access"]}
        edges.extend([
            {"from": "docportal:tak", "to": ref_id, "relationship": "INDEXES_PUBLIC_METADATA"},
            {"from": ref_id, "to": area_id, "relationship": "DOCUMENTS_DOMAIN"},
            {"from": ref_id, "to": access_id, "relationship": "SUBJECT_TO_ACCESS"},
        ])
    graph = {
        "schema": "xunia.tak.docs-ontology.v1",
        "authority": "REFERENCE_LINKS_ONLY",
        "runtime_connections": 0, "scraped_authenticated_content": False,
        "nodes": sorted(nodes.values(), key=lambda x: x["id"]),
        "edges": sorted(edges, key=lambda x: (x["from"], x["to"], x["relationship"])),
        "docs_registry_sha256": registry["registry_sha256"],
    }
    return graph


def inventory_local_documents(root: Path, *, include_names: bool = False) -> dict:
    """Read only names, file lengths and local hashes; no contents leave host."""
    root = Path(root).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("local document root must be an existing nonsymlink directory")
    records: list[dict] = []
    ignored = 0
    for file in sorted(root.rglob("*")):
        if file.is_symlink():
            ignored += 1
            continue
        if not file.is_file() or file.suffix.lower() not in FILE_EXTENSIONS:
            continue
        if len(file.relative_to(root).parts) > 5:
            ignored += 1
            continue
        size = file.stat().st_size
        if size > MAX_FILE_BYTES:
            ignored += 1
            continue
        if len(records) >= MAX_FILES:
            raise ValueError("local document inventory exceeds 160-file cap")
        digest = hashlib.sha256()
        with file.open("rb") as stream:
            while True:
                buffer = stream.read(1024 * 1024)
                if not buffer:
                    break
                digest.update(buffer)
        record = {"format": file.suffix.lower(), "size_bytes": size,
                  "sha256": digest.hexdigest(), "text_search_supported": file.suffix.lower() in TEXT_EXTENSIONS}
        if include_names:
            record["relative_path"] = file.relative_to(root).as_posix()
        records.append(record)
    return {
        "system": "GPT-DOUG LOCAL DOCUMENT INVENTORY",
        "authority": "USER_PROVIDED_LOCAL_FILES_UNVERIFIED",
        "files": len(records), "ignored": ignored,
        "formats": dict(sorted(Counter(r["format"] for r in records).items())),
        "metadata_only": True, "files_uploaded": 0,
        "network_actions": 0, "local_paths_disclosed": include_names,
        "records": records,
    }


def local_text_search(root: Path, query: str, *, limit: int = 12) -> dict:
    """Ad-hoc terminal search for authorized *local* textual docs; no DB/network."""
    term = query.strip()
    if len(term) < 2 or len(term) > 120:
        raise ValueError("query must contain 2 to 120 characters")
    if not 1 <= limit <= 30:
        raise ValueError("result limit must be 1..30")
    root = Path(root).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("local document root must be an existing nonsymlink directory")
    results = []
    checked = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if len(path.relative_to(root).parts) > 5 or path.stat().st_size > MAX_TEXT_SEARCH:
            continue
        checked += 1
        if checked > MAX_FILES:
            raise ValueError("local text search exceeds 160 document cap")
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            index = line.casefold().find(term.casefold())
            if index < 0:
                continue
            start = max(0, index - 70)
            snippet = line[start:start + 240].strip()
            results.append({"file": path.relative_to(root).as_posix(), "line": number, "snippet": snippet})
            if len(results) >= limit:
                return {"query": term, "results": results, "searched_files": checked,
                        "network_actions": 0, "persisted_index": False}
    return {"query": term, "results": results, "searched_files": checked,
            "network_actions": 0, "persisted_index": False}


def write_docs_portal(output: Path, *, force: bool = False) -> dict:
    output = Path(output).expanduser()
    generated = ("docs.html", "docs-registry.json", "docs-ontology.json")
    if not force and any((output / name).exists() for name in generated):
        raise ValueError("documentation files exist; use --force to update")
    registry = public_registry()
    output.mkdir(parents=True, exist_ok=True)
    (output / "docs-registry.json").write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    (output / "docs-ontology.json").write_text(
        json.dumps(documentation_graph(registry), indent=2) + "\n", encoding="utf-8")
    template = Path(__file__).with_name("docs_portal.html").read_text(encoding="utf-8")
    if template.count("__TAK_DOCS_REGISTRY__") != 1:
        raise ValueError("documentation HTML template is invalid")
    payload = json.dumps(registry, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    (output / "docs.html").write_text(template.replace("__TAK_DOCS_REGISTRY__", payload), encoding="utf-8")
    return {"system": registry["system"], "references": registry["document_count"],
            "public_references": registry["public_references"],
            "login_required": registry["login_required_references"],
            "network_actions": 0, "authenticated_library_scraped": False,
            "output": str(output / "docs.html")}
