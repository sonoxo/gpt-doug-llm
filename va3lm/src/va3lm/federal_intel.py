from __future__ import annotations

from copy import deepcopy

CATALOG_VERSION = "0.4.0"
VERIFIED_AS_OF = "2026-09-01"
MODE = "PUBLIC_OSINT_ONLY"

_ENTITIES = [
    {
        "id": "cia",
        "name": "Central Intelligence Agency",
        "entityType": "agency",
        "owner": "U.S. Intelligence Community",
        "focus": ["foreign intelligence", "analysis", "public country reference data", "declassified records"],
        "officialGitHub": {
            "status": "NO_VERIFIED_OFFICIAL_ORG",
            "organizations": [],
            "note": "No official CIA GitHub organization was verified for this catalog date; do not treat third-party CIA-themed repositories as agency sources.",
        },
        "sources": [
            {"type": "official_web", "url": "https://www.cia.gov/", "label": "CIA"},
            {"type": "public_dataset", "url": "https://www.cia.gov/the-world-factbook/", "label": "The World Factbook"},
            {"type": "declassified_records", "url": "https://www.cia.gov/readingroom/", "label": "CIA FOIA Electronic Reading Room"},
        ],
    },
    {
        "id": "nsa",
        "name": "National Security Agency",
        "entityType": "agency",
        "owner": "U.S. Department of Defense / Intelligence Community",
        "focus": ["cybersecurity", "cryptography", "open-source software", "public technical guidance"],
        "officialGitHub": {
            "status": "VERIFIED_PUBLIC_ORGS",
            "organizations": [
                "https://github.com/NationalSecurityAgency",
                "https://github.com/nsacyber",
            ],
            "curatedRepositories": [
                "https://github.com/NationalSecurityAgency/ghidra",
                "https://github.com/NationalSecurityAgency/datawave",
                "https://github.com/NationalSecurityAgency/Foundation",
            ],
        },
        "sources": [
            {"type": "official_web", "url": "https://www.nsa.gov/", "label": "NSA"},
            {"type": "open_source_index", "url": "https://code.nsa.gov/", "label": "NSA Open Source"},
        ],
    },
    {
        "id": "nro",
        "name": "National Reconnaissance Office",
        "entityType": "agency",
        "owner": "U.S. Department of Defense / Intelligence Community",
        "focus": ["public space-reconnaissance programs", "public launch news", "commercial acquisition news", "declassified records"],
        "officialGitHub": {
            "status": "NO_VERIFIED_OFFICIAL_ORG",
            "organizations": [],
            "note": "No official NRO GitHub organization was verified for this catalog date.",
        },
        "sources": [
            {"type": "official_web", "url": "https://www.nro.gov/", "label": "NRO"},
            {"type": "public_news", "url": "https://www.nro.gov/news-media-featured-stories/", "label": "NRO News & Media"},
            {"type": "declassified_records", "url": "https://www.nro.gov/foia-home/foia-resources-reading-room/", "label": "NRO FOIA Electronic Reading Room"},
        ],
    },
    {
        "id": "ngp",
        "name": "National Geospatial-Intelligence Program",
        "entityType": "program",
        "owner": "National Geospatial-Intelligence Agency (NGA)",
        "focus": ["GEOINT", "geospatial standards", "mapping", "GeoPackage", "public geospatial software"],
        "officialGitHub": {
            "status": "VERIFIED_PUBLIC_ORG_VIA_NGA",
            "organizations": ["https://github.com/ngageoint"],
            "curatedRepositories": [
                "https://github.com/ngageoint/geoint-standards",
                "https://github.com/ngageoint/GeoPackage",
                "https://github.com/ngageoint/hootenanny",
                "https://github.com/ngageoint/mage-server",
            ],
        },
        "sources": [
            {"type": "official_web", "url": "https://www.nga.mil/", "label": "National Geospatial-Intelligence Agency"},
            {"type": "official_context", "url": "https://www.nga.mil/about/About_Us.html", "label": "NGA About / GEOINT mission"},
        ],
        "note": "NGP is represented as a program capability and mapped to NGA public sources; it is not modeled as a separate agency.",
    },
    {
        "id": "gdip",
        "name": "General Defense Intelligence Program",
        "entityType": "program",
        "owner": "Defense Intelligence Agency (DIA)",
        "focus": ["defense intelligence program context", "public military-intelligence publications", "FOIA releases"],
        "officialGitHub": {
            "status": "NO_VERIFIED_OFFICIAL_ORG",
            "organizations": [],
            "note": "No official DIA/GDIP GitHub organization was verified for this catalog date.",
        },
        "sources": [
            {"type": "official_web", "url": "https://www.dia.mil/", "label": "Defense Intelligence Agency"},
            {"type": "declassified_records", "url": "https://www.dia.mil/FOIA/FOIA-Electronic-Reading-Room/", "label": "DIA FOIA Electronic Reading Room"},
            {"type": "official_history", "url": "https://www.dia.mil/News-Features/The-DIA-60th-Anniversary/The-1970s/", "label": "DIA history of GDIP"},
        ],
        "note": "GDIP is modeled as a DIA-managed defense-intelligence program, not as a standalone agency.",
    },
]

_BOUNDARIES = [
    "publicly released and lawfully accessible sources only",
    "no classified, leaked, stolen, credentialed, or access-controlled material",
    "no communications interception or signals collection",
    "no covert person tracking, persistent person identifiers, or biometric identification",
    "no targeting, operational tasking, or evasion of government/security controls",
    "third-party repositories must never be labeled official without independent verification",
]


def federal_intel_manifest() -> dict:
    return {
        "name": "RVIA Federal Intel Public-Source Catalog",
        "version": CATALOG_VERSION,
        "verifiedAsOf": VERIFIED_AS_OF,
        "mode": MODE,
        "entities": deepcopy(_ENTITIES),
        "boundaries": list(_BOUNDARIES),
    }


def federal_intel_entity(entity_id: str) -> dict:
    normalized = entity_id.strip().lower()
    for entity in _ENTITIES:
        if entity["id"] == normalized:
            return deepcopy(entity)
    raise KeyError(f"unknown federal intel entity: {entity_id}")


def verified_github_sources() -> list[dict]:
    verified: list[dict] = []
    for entity in _ENTITIES:
        github = entity["officialGitHub"]
        if github["status"].startswith("VERIFIED"):
            verified.append(
                {
                    "id": entity["id"],
                    "name": entity["name"],
                    "status": github["status"],
                    "organizations": list(github.get("organizations", [])),
                    "repositories": list(github.get("curatedRepositories", [])),
                }
            )
    return verified
