from xbox_gdk_docs_resolver import resolve, search_sources


def test_resolves_xtaskqueue():
    matches = search_sources("XTaskQueue async")
    assert matches
    assert matches[0]["id"] == "xtaskqueue"


def test_marks_authorized_topics_without_bypass():
    result = resolve("XSAPI")
    assert result["licensedAccessRequired"]
    assert result["policy"]["authorizationBypass"] is False


def test_console_packaging_source_is_known():
    result = resolve("Xbox console packaging XVC")
    assert any(item["id"] == "packaging-console" for item in result["matches"])
