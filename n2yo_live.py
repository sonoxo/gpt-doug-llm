"""N2YO live orbital-data provider for GPT-DOUG / XUNIA.

The preferred topology is to point XUNIA_N2YO_PROXY_URL at the MMGIS
`/api/n2yo` adapter so all apps share one quota-aware cache. Direct N2YO mode
is supported for standalone/local use when N2YO_API_KEY is configured.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

N2YO_BASE_URL = "https://api.n2yo.com/rest/v1/satellite"


class N2YOError(RuntimeError):
    """Raised when the live orbital provider cannot satisfy a request."""


@dataclass(frozen=True)
class Observer:
    latitude: float
    longitude: float
    altitude_m: float = 0.0

    def validate(self) -> "Observer":
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        if not -500 <= self.altitude_m <= 100000:
            raise ValueError("altitude_m must be between -500 and 100000")
        return self


class N2YOLiveProvider:
    """Small, dependency-free N2YO client with proxy-first routing."""

    def __init__(
        self,
        *,
        proxy_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self.proxy_url = (proxy_url or os.getenv("XUNIA_N2YO_PROXY_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("N2YO_API_KEY")
        self.timeout = timeout

    @property
    def mode(self) -> str:
        if self.proxy_url:
            return "xunia-proxy"
        if self.api_key:
            return "direct-n2yo"
        return "unconfigured"

    def health(self) -> Dict[str, Any]:
        if self.proxy_url:
            return self._get_json(f"{self.proxy_url}/health")
        return {
            "status": "success" if self.api_key else "failure",
            "body": {
                "provider": "n2yo",
                "domain": "orbital",
                "mode": self.mode,
                "configured": bool(self.api_key),
            },
        }

    def tle(self, norad_id: int) -> Dict[str, Any]:
        norad_id = self._norad_id(norad_id)
        if self.proxy_url:
            return self._unwrap(self._get_json(f"{self.proxy_url}/tle/{norad_id}"))
        return self._direct(f"tle/{norad_id}", trailing_slash=False)

    def positions(
        self,
        norad_id: int,
        observer: Observer,
        *,
        seconds: int = 300,
    ) -> Dict[str, Any]:
        norad_id = self._norad_id(norad_id)
        observer.validate()
        seconds = self._integer("seconds", seconds, 1, 300)
        if self.proxy_url:
            query = self._query(observer, seconds=seconds)
            return self._unwrap(
                self._get_json(f"{self.proxy_url}/positions/{norad_id}?{query}")
            )
        return self._direct(
            "positions/{}/{}/{}/{}/{}".format(
                norad_id,
                observer.latitude,
                observer.longitude,
                observer.altitude_m,
                seconds,
            )
        )

    def positions_geojson(
        self,
        norad_id: int,
        observer: Observer,
        *,
        seconds: int = 300,
    ) -> Dict[str, Any]:
        norad_id = self._norad_id(norad_id)
        observer.validate()
        seconds = self._integer("seconds", seconds, 1, 300)
        if self.proxy_url:
            query = self._query(observer, seconds=seconds)
            return self._get_json(
                f"{self.proxy_url}/positions/{norad_id}/geojson?{query}"
            )
        return self._positions_to_geojson(self.positions(norad_id, observer, seconds=seconds))

    def positions_czml_url(
        self,
        norad_id: int,
        observer: Observer,
        *,
        seconds: int = 300,
    ) -> str:
        """Return the quota-aware CZML URL exposed by the XUNIA/MMGIS proxy."""
        if not self.proxy_url:
            raise N2YOError("CZML URL requires XUNIA_N2YO_PROXY_URL")
        norad_id = self._norad_id(norad_id)
        observer.validate()
        seconds = self._integer("seconds", seconds, 1, 300)
        query = self._query(observer, seconds=seconds)
        return f"{self.proxy_url}/positions/{norad_id}/czml?{query}"

    def stream_url(
        self,
        norad_id: int,
        observer: Observer,
        *,
        seconds: int = 300,
    ) -> str:
        """Return the shared Server-Sent Events endpoint for one live satellite."""
        if not self.proxy_url:
            raise N2YOError("SSE stream requires XUNIA_N2YO_PROXY_URL")
        norad_id = self._norad_id(norad_id)
        observer.validate()
        seconds = self._integer("seconds", seconds, 30, 300)
        query = self._query(observer, seconds=seconds)
        return f"{self.proxy_url}/stream/{norad_id}?{query}"

    def visual_passes(
        self,
        norad_id: int,
        observer: Observer,
        *,
        days: int = 2,
        min_visibility: int = 60,
    ) -> Dict[str, Any]:
        norad_id = self._norad_id(norad_id)
        observer.validate()
        days = self._integer("days", days, 1, 10)
        min_visibility = self._integer("min_visibility", min_visibility, 0, 86400)
        if self.proxy_url:
            query = self._query(
                observer, days=days, minVisibility=min_visibility
            )
            return self._unwrap(
                self._get_json(f"{self.proxy_url}/visualpasses/{norad_id}?{query}")
            )
        return self._direct(
            "visualpasses/{}/{}/{}/{}/{}/{}".format(
                norad_id,
                observer.latitude,
                observer.longitude,
                observer.altitude_m,
                days,
                min_visibility,
            )
        )

    def radio_passes(
        self,
        norad_id: int,
        observer: Observer,
        *,
        days: int = 2,
        min_elevation: int = 20,
    ) -> Dict[str, Any]:
        norad_id = self._norad_id(norad_id)
        observer.validate()
        days = self._integer("days", days, 1, 10)
        min_elevation = self._integer("min_elevation", min_elevation, 0, 90)
        if self.proxy_url:
            query = self._query(observer, days=days, minElevation=min_elevation)
            return self._unwrap(
                self._get_json(f"{self.proxy_url}/radiopasses/{norad_id}?{query}")
            )
        return self._direct(
            "radiopasses/{}/{}/{}/{}/{}/{}".format(
                norad_id,
                observer.latitude,
                observer.longitude,
                observer.altitude_m,
                days,
                min_elevation,
            )
        )

    def above(
        self,
        observer: Observer,
        *,
        radius: int = 90,
        category: int = 0,
    ) -> Dict[str, Any]:
        observer.validate()
        radius = self._integer("radius", radius, 0, 90)
        category = self._integer("category", category, 0, 9999)
        if self.proxy_url:
            query = self._query(observer, radius=radius, category=category)
            return self._unwrap(self._get_json(f"{self.proxy_url}/above?{query}"))
        return self._direct(
            "above/{}/{}/{}/{}/{}".format(
                observer.latitude,
                observer.longitude,
                observer.altitude_m,
                radius,
                category,
            )
        )

    def above_geojson(
        self,
        observer: Observer,
        *,
        radius: int = 90,
        category: int = 0,
    ) -> Dict[str, Any]:
        observer.validate()
        radius = self._integer("radius", radius, 0, 90)
        category = self._integer("category", category, 0, 9999)
        if self.proxy_url:
            query = self._query(observer, radius=radius, category=category)
            return self._get_json(f"{self.proxy_url}/above/geojson?{query}")
        return self._above_to_geojson(self.above(observer, radius=radius, category=category))

    def _direct(self, path: str, *, trailing_slash: bool = True) -> Dict[str, Any]:
        if not self.api_key:
            raise N2YOError(
                "N2YO is not configured: set XUNIA_N2YO_PROXY_URL (preferred) or N2YO_API_KEY"
            )
        separator = "/&" if trailing_slash else "&"
        url = f"{N2YO_BASE_URL}/{path}{separator}apiKey={urllib.parse.quote(self.api_key)}"
        return self._get_json(url)

    def _get_json(self, url: str) -> Dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "GPT-DOUG-XUNIA-N2YO/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise N2YOError(f"N2YO HTTP {exc.code}: {detail[:300]}") from exc
        except urllib.error.URLError as exc:
            raise N2YOError(f"N2YO network error: {exc.reason}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise N2YOError("N2YO returned non-JSON data") from exc

    @staticmethod
    def _unwrap(payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload.get("status") == "failure":
            raise N2YOError(payload.get("message", "XUNIA N2YO proxy failure"))
        return payload.get("body", payload)

    @staticmethod
    def _norad_id(value: int) -> int:
        return N2YOLiveProvider._integer("norad_id", value, 1, 999999999)

    @staticmethod
    def _integer(name: str, value: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer") from exc
        if parsed < minimum or parsed > maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return parsed

    @staticmethod
    def _query(observer: Observer, **extra: Any) -> str:
        payload: Dict[str, Any] = {
            "lat": observer.latitude,
            "lng": observer.longitude,
            "alt": observer.altitude_m,
        }
        payload.update(extra)
        return urllib.parse.urlencode(payload)

    @staticmethod
    def _positions_to_geojson(data: Dict[str, Any]) -> Dict[str, Any]:
        positions = data.get("positions", [])
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": str(data.get("info", {}).get("satid", "satellite")),
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [p["satlongitude"], p["satlatitude"], p.get("sataltitude", 0) * 1000]
                            for p in positions
                        ],
                    },
                    "properties": {
                        "provider": "n2yo",
                        "domain": "orbital",
                        "noradId": data.get("info", {}).get("satid"),
                        "name": data.get("info", {}).get("satname"),
                        "timestamps": [p.get("timestamp") for p in positions],
                    },
                }
            ],
        }

    @staticmethod
    def _above_to_geojson(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": str(sat["satid"]),
                    "geometry": {
                        "type": "Point",
                        "coordinates": [sat["satlng"], sat["satlat"], sat.get("satalt", 0) * 1000],
                    },
                    "properties": {
                        "provider": "n2yo",
                        "domain": "orbital",
                        "noradId": sat["satid"],
                        "name": sat.get("satname"),
                        "internationalDesignator": sat.get("intDesignator"),
                        "launchDate": sat.get("launchDate"),
                        "altitudeKm": sat.get("satalt"),
                    },
                }
                for sat in data.get("above", [])
            ],
        }


__all__ = ["N2YOError", "N2YOLiveProvider", "Observer"]
