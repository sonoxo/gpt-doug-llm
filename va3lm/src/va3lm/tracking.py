from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SOURCE_VIDEO = {
    "title": "How We Found Bin Laden: The Basics of Foreign Signals Intelligence",
    "publisher": "National Security Agency",
    "youtube": "https://www.youtube.com/watch?v=Om-OyjADgTA",
    "officialPage": "https://www.nsa.gov/Podcast/View/Article/3895171/how-we-found-bin-laden-the-basics-of-foreign-signals-intelligence/",
    "adaptation": "High-level analytic workflow only: provenance, timestamps, multi-source correlation, confidence, uncertainty, and human review.",
}

GOOGLE_MAPS_TECH = {
    "provider": "Google Maps Platform",
    "browser": "Maps JavaScript API",
    "optional": ["Routes API", "Geocoding API"],
    "keyEnv": "GOOGLE_MAPS_BROWSER_KEY",
    "keyPolicy": "Use a browser-restricted key. Never commit API keys.",
}

ALLOWED_ENTITY_TYPES = {"asset", "vehicle", "sensor", "site", "event"}
FORBIDDEN_IDENTITY_KEYS = {
    "biometric",
    "face_embedding",
    "face_id",
    "identity",
    "identity_id",
    "imei",
    "imsi",
    "person_id",
    "person_name",
    "phone",
    "phone_number",
    "subject_id",
    "subject_name",
}


class TrackingObservation(BaseModel):
    """One authorized, non-identifying geospatial observation.

    The model is intentionally restricted to assets, vehicles, sensors, sites, and
    events. It does not provide collection, interception, biometric, or covert
    person-tracking functionality.
    """

    model_config = ConfigDict(extra="forbid")

    track_id: str = Field(min_length=1, max_length=128)
    entity_type: Literal["asset", "vehicle", "sensor", "site", "event"]
    label: str = Field(min_length=1, max_length=256)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    observed_at: datetime
    source: str = Field(min_length=1, max_length=256)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_identity_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        def scan(item: Any, path: str = "metadata") -> None:
            if isinstance(item, dict):
                for key, nested in item.items():
                    normalized = str(key).strip().lower()
                    if normalized in FORBIDDEN_IDENTITY_KEYS:
                        raise ValueError(f"identity-oriented tracking field is not permitted: {path}.{key}")
                    scan(nested, f"{path}.{key}")
            elif isinstance(item, (list, tuple)):
                for index, nested in enumerate(item):
                    scan(nested, f"{path}[{index}]")

        scan(value)
        return value


def tracking_manifest() -> dict[str, Any]:
    return {
        "name": "BIG VIRGINIA // VA3LM Geospatial Tracking",
        "mode": "AUTHORIZED_NON_IDENTIFYING",
        "sourceVideo": deepcopy(SOURCE_VIDEO),
        "mapTechnology": deepcopy(GOOGLE_MAPS_TECH),
        "workflow": [
            "collect authorized observations",
            "preserve source provenance and timestamps",
            "normalize coordinates",
            "correlate observations by non-person track_id",
            "retain confidence and uncertainty",
            "render map/timeline for analyst review",
            "require human approval before downstream action",
        ],
        "boundaries": [
            "no communications interception",
            "no biometric identification",
            "no covert person tracking",
            "no API keys committed to source control",
        ],
    }


def sample_track() -> list[TrackingObservation]:
    """Return a deterministic Virginia demo track for an imaginary authorized asset."""

    points = [
        (37.54072, -77.43605, "2026-09-01T20:00:00Z"),
        (37.54182, -77.43385, "2026-09-01T20:04:00Z"),
        (37.54310, -77.43160, "2026-09-01T20:08:00Z"),
    ]
    return [
        TrackingObservation(
            track_id="demo-asset-rva-001",
            entity_type="asset",
            label="Authorized demo asset",
            latitude=lat,
            longitude=lng,
            observed_at=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
            source="VA3LM deterministic demo",
            confidence=1.0,
            metadata={"demo": True, "sequence": index},
        )
        for index, (lat, lng, timestamp) in enumerate(points, start=1)
    ]


def normalize_track(observations: list[TrackingObservation]) -> list[TrackingObservation]:
    """Sort observations chronologically and require one non-person track id."""

    if not observations:
        return []
    track_ids = {item.track_id for item in observations}
    if len(track_ids) != 1:
        raise ValueError("a normalized track must contain exactly one track_id")
    return sorted(observations, key=lambda item: item.observed_at)


def to_geojson(observations: list[TrackingObservation]) -> dict[str, Any]:
    normalized = normalize_track(observations)
    features: list[dict[str, Any]] = []
    for sequence, item in enumerate(normalized, start=1):
        observed_at = item.observed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [item.longitude, item.latitude]},
                "properties": {
                    "trackId": item.track_id,
                    "entityType": item.entity_type,
                    "label": item.label,
                    "observedAt": observed_at,
                    "source": item.source,
                    "confidence": item.confidence,
                    "sequence": sequence,
                    "metadata": item.metadata,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "va3lm": {
            "mode": "AUTHORIZED_NON_IDENTIFYING",
            "provider": "Google Maps Platform compatible GeoJSON",
        },
    }
