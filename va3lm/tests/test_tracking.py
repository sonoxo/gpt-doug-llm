from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from va3lm.tracking import TrackingObservation, normalize_track, sample_track, to_geojson, tracking_manifest


def test_tracking_manifest_is_authorized_and_non_identifying():
    manifest = tracking_manifest()
    assert manifest["mode"] == "AUTHORIZED_NON_IDENTIFYING"
    assert manifest["mapTechnology"]["provider"] == "Google Maps Platform"
    assert "Om-OyjADgTA" in manifest["sourceVideo"]["youtube"]
    assert "no covert person tracking" in manifest["boundaries"]


def test_sample_track_is_ordered_google_maps_compatible_geojson():
    geojson = to_geojson(sample_track())
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 3
    assert geojson["va3lm"]["provider"] == "Google Maps Platform compatible GeoJSON"
    assert [item["properties"]["sequence"] for item in geojson["features"]] == [1, 2, 3]
    first = geojson["features"][0]
    assert first["geometry"]["type"] == "Point"
    assert first["geometry"]["coordinates"] == [-77.43605, 37.54072]


def test_identity_metadata_is_rejected():
    with pytest.raises(ValidationError, match="identity-oriented tracking field"):
        TrackingObservation(
            track_id="demo-asset",
            entity_type="asset",
            label="Demo asset",
            latitude=37.54,
            longitude=-77.43,
            observed_at=datetime.now(timezone.utc),
            source="authorized test",
            metadata={"nested": {"person_name": "not allowed"}},
        )


def test_normalize_track_rejects_mixed_track_ids():
    observations = sample_track()
    second_track = observations[0].model_copy(update={"track_id": "demo-asset-rva-002"})
    with pytest.raises(ValueError, match="exactly one track_id"):
        normalize_track([observations[0], second_track])
