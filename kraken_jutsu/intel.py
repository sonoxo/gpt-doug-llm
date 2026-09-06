from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class IntelSource:
    source_id: str
    owner: str
    repository: str
    role: str
    ingest_strategy: str
    canonical_url: str
    data_url: str | None = None
    government_backed: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_SOURCES = (
    IntelSource("cisa-kev", "cisagov", "kev-data", "known-exploited-vulnerability priority", "consume-live-data", "https://github.com/cisagov/kev-data", "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"),
    IntelSource("cisa-vulnrichment", "cisagov", "vulnrichment", "CVE SSVC/CWE/CVSS enrichment", "consume-cve-adp-data", "https://github.com/cisagov/vulnrichment"),
    IntelSource("cisa-decider", "cisagov", "Decider", "guided ATT&CK behavior mapping", "fork-only-if-guided-ui-needed", "https://github.com/cisagov/Decider"),
    IntelSource("nist-oscal", "usnistgov", "OSCAL", "security control/assessment schema", "consume-schema", "https://github.com/usnistgov/OSCAL"),
    IntelSource("nist-oscal-content", "usnistgov", "oscal-content", "NIST SP 800-53 controls/baselines", "consume-content", "https://github.com/usnistgov/oscal-content"),
    IntelSource("mitre-attack-stix", "mitre-attack", "attack-stix-data", "ATT&CK behavior graph", "consume-live-data", "https://github.com/mitre-attack/attack-stix-data", "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json", False),
    IntelSource("cisa-malcolm", "cisagov", "Malcolm", "network defensive telemetry", "adapter-later", "https://github.com/cisagov/Malcolm"),
)


class GovernmentSourceRegistry:
    def __init__(self, sources=DEFAULT_SOURCES) -> None:
        self.sources = {s.source_id: s for s in sources}

    def manifest(self) -> list[dict]:
        return [self.sources[k].to_dict() for k in sorted(self.sources)]

    def fetch_json(self, source_id: str, *, timeout: int = 20) -> dict:
        source = self.sources[source_id]
        if not source.data_url:
            raise ValueError(f"{source_id} has no direct JSON data URL")
        req = Request(source.data_url, headers={"User-Agent": "krakenXYZ-Kraken-Jutsu/0.2"})
        with urlopen(req, timeout=timeout) as response:
            return json.load(response)

    @staticmethod
    def kev_index(payload: dict) -> dict[str, dict]:
        return {row["cveID"]: row for row in payload.get("vulnerabilities", []) if isinstance(row, dict) and row.get("cveID")}


class OSINTQueryPolicy(str, Enum):
    OWNED_ASSET = "owned_asset"
    CONSENTED = "consented"
    AUTHORIZED_CASE = "authorized_case"


@dataclass(slots=True)
class OSINTIndustriesAdapter:
    api_key: str | None = None
    endpoint: str = "https://api.osint.industries/v2/request"

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("OSINT_INDUSTRIES_API_KEY")

    @staticmethod
    def query_fingerprint(query: str) -> str:
        return sha256(query.encode("utf-8")).hexdigest()[:20]

    def search(self, *, query_type: str, query: str, policy: OSINTQueryPolicy, timeout: int = 60, exact_match: bool = True, premium: bool = False) -> dict:
        if not self.api_key:
            raise RuntimeError("OSINT Industries API key not configured; use export ingestion or OSINT_INDUSTRIES_API_KEY.")
        if query_type not in {"email", "phone", "username", "name", "wallet"}:
            raise ValueError("Unsupported OSINT Industries query type")
        if not 25 <= timeout <= 80:
            raise ValueError("timeout must be between 25 and 80 seconds")
        body = json.dumps({"type": query_type, "query": query, "timeout": timeout, "exact_match": exact_match, "premium": premium}).encode("utf-8")
        req = Request(self.endpoint, data=body, method="POST", headers={"api-key": self.api_key, "content-type": "application/json", "user-agent": "krakenXYZ-Kraken-Jutsu/0.2"})
        with urlopen(req, timeout=timeout + 5) as response:
            payload = json.load(response)
        return {"provider": "osint-industries", "query_type": query_type, "query_fingerprint": self.query_fingerprint(query), "policy": policy.value, "premium": premium, "raw": payload}

    @staticmethod
    def normalize_export(payload: object, *, query_type: str = "unknown") -> dict:
        if isinstance(payload, dict):
            fields, count = sorted(str(k) for k in payload), len(payload)
        elif isinstance(payload, list):
            fields, count = [], len(payload)
        else:
            fields, count = [], 1
        return {"provider": "osint-industries-export", "query_type": query_type, "result_count": count, "top_level_fields": fields[:50], "raw": payload}
