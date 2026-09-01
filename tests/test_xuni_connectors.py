from xuni_connectors import ConnectorRegistry, ConnectorState


def test_free_local_baseline_is_ready_without_secrets():
    registry = ConnectorRegistry(env={})
    registry.assert_free_local_baseline()
    for connector_id in ("xuni-local-cloud", "opentelemetry", "sqlite", "websocket-sse"):
        assert registry.health(connector_id).state is ConnectorState.READY


def test_playfab_requires_configuration_until_title_id_is_present():
    missing = ConnectorRegistry(env={}).health("playfab")
    assert missing.state is ConnectorState.CONFIG_REQUIRED
    assert missing.missing_env == ("XUNI_PLAYFAB_TITLE_ID",)

    ready = ConnectorRegistry(env={"XUNI_PLAYFAB_TITLE_ID": "TEST"}).health("playfab")
    assert ready.state is ConnectorState.READY


def test_gdk_never_claims_ready_without_licensed_runtime():
    registry = ConnectorRegistry(env={})
    assert registry.health("xbox-gdk").state is ConnectorState.LICENSED_RUNTIME_REQUIRED
    assert registry.health("xbox-gdk", licensed_runtime_available=True).state is ConnectorState.READY


def test_capability_resolution_prefers_ready_local_provider():
    registry = ConnectorRegistry(env={})
    save_connectors = registry.resolve_capability("cloud_saves")
    assert save_connectors[0].id == "xuni-local-cloud"
    assert save_connectors[0].state is ConnectorState.READY
    assert any(item.id == "playfab" for item in save_connectors)


def test_unknown_connector_is_explicit():
    registry = ConnectorRegistry(env={})
    try:
        registry.get("not-real")
    except KeyError as exc:
        assert "UNKNOWN_CONNECTOR:not-real" in str(exc)
    else:
        raise AssertionError("unknown connector must fail")
