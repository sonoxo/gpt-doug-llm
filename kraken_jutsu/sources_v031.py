from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _fetch_json(url: str, *, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    req = Request(
        url,
        headers={
            "User-Agent": "krakenXYZ-Kraken-Jutsu/0.3.1",
            "Accept": "application/json",
            **(headers or {}),
        },
    )
    with urlopen(req, timeout=timeout) as response:  # nosec B310 -- fixed HTTPS sources only.
        return json.load(response)


class CISAKEVSource:
    primary_url = (
        "https://raw.githubusercontent.com/cisagov/kev-data/develop/"
        "known_exploited_vulnerabilities.json"
    )
    fallback_url = (
        "https://www.cisa.gov/sites/default/files/feeds/"
        "known_exploited_vulnerabilities.json"
    )

    def fetch(self, timeout: int = 30) -> dict[str, Any]:
        errors: list[str] = []
        for url in (self.primary_url, self.fallback_url):
            try:
                payload = _fetch_json(url, timeout=timeout)
                if not isinstance(payload, dict) or "vulnerabilities" not in payload:
                    raise ValueError("KEV payload is missing vulnerabilities")
                payload["_kraken_source_url"] = url
                return payload
            except (OSError, URLError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{url}: {exc}")
        raise RuntimeError("CISA KEV sources unavailable: " + " | ".join(errors))


class NVDSource:
    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def fetch_cve(self, cve_id: str, timeout: int = 30) -> dict[str, Any]:
        url = self.base_url + "?" + urlencode({"cveId": cve_id})
        headers: dict[str, str] = {}
        if os.getenv("NVD_API_KEY"):
            headers["apiKey"] = os.environ["NVD_API_KEY"]
        payload = _fetch_json(url, headers=headers, timeout=timeout)
        if not isinstance(payload, dict):
            raise ValueError("NVD response must be a JSON object")
        return payload
