from n2yo_live import N2YOError, N2YOLiveProvider, Observer


def test_observer_validation():
    assert Observer(37.54, -77.44, 0).validate().latitude == 37.54


def test_observer_rejects_invalid_latitude():
    try:
        Observer(91, 0, 0).validate()
    except ValueError as exc:
        assert "latitude" in str(exc)
    else:
        raise AssertionError("invalid latitude should fail")


def test_proxy_positions_builds_expected_route():
    provider = N2YOLiveProvider(proxy_url="https://example.test/api/n2yo")
    seen = {}

    def fake_get(url):
        seen["url"] = url
        return {"status": "success", "body": {"positions": []}}

    provider._get_json = fake_get
    result = provider.positions(25544, Observer(37.54, -77.44), seconds=300)

    assert result == {"positions": []}
    assert seen["url"].startswith("https://example.test/api/n2yo/positions/25544?")
    assert "seconds=300" in seen["url"]


def test_proxy_stream_url_uses_shared_quota_aware_backend():
    provider = N2YOLiveProvider(proxy_url="https://example.test/api/n2yo")
    url = provider.stream_url(25544, Observer(37.54, -77.44), seconds=300)
    assert url.startswith("https://example.test/api/n2yo/stream/25544?")


def test_stream_requires_proxy():
    provider = N2YOLiveProvider(api_key="test-only")
    try:
        provider.stream_url(25544, Observer(0, 0))
    except N2YOError as exc:
        assert "proxy" in str(exc).lower()
    else:
        raise AssertionError("stream_url should require the XUNIA proxy")


def test_positions_geojson_normalization():
    provider = N2YOLiveProvider(api_key="test-only")
    payload = {
        "info": {"satid": 25544, "satname": "SPACE STATION"},
        "positions": [
            {
                "satlongitude": -77.0,
                "satlatitude": 37.0,
                "sataltitude": 420.0,
                "timestamp": 123,
            }
        ],
    }
    geojson = provider._positions_to_geojson(payload)
    feature = geojson["features"][0]
    assert feature["geometry"]["coordinates"][0] == [-77.0, 37.0, 420000.0]
    assert feature["properties"]["provider"] == "n2yo"
    assert feature["properties"]["domain"] == "orbital"
