from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "platform_one" / "repo1-hardening"


def test_hardening_project_contains_no_application_source_or_binary():
    forbidden_suffixes = {".py", ".pyc", ".whl", ".so", ".bin", ".exe"}
    files = [path for path in SEED.rglob("*") if path.is_file()]
    assert all(path.suffix.lower() not in forbidden_suffixes for path in files)


def test_required_iron_bank_files_exist():
    for name in ("Dockerfile", "hardening_manifest.yaml", "LICENSE", "README.md"):
        assert (SEED / name).is_file()


def test_dockerfile_is_hardening_friendly():
    text = (SEED / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG BASE_REGISTRY=registry1.dso.mil" in text
    assert "ARG BASE_IMAGE=ironbank/redhat/ubi/ubi9-minimal" in text
    assert "ARG BASE_TAG=9.8" in text
    assert "USER 1001" in text
    assert re.search(r"^\s*ADD\b", text, re.MULTILINE) is None
    assert re.search(r"^\s*LABEL\b", text, re.MULTILINE) is None
    assert "curl " not in text
    assert "wget " not in text


def test_manifest_has_pinned_checksum_resources():
    text = (SEED / "hardening_manifest.yaml").read_text(encoding="utf-8")
    assert "resources:" in text
    assert text.count('type: "sha256"') == 2
    values = re.findall(r'value: "([0-9a-f]{64})"', text)
    assert len(values) == 2
    assert "ae81a7dcceac5d27b5d42d9614a71d296abc6f18" in text


def test_manifest_does_not_hide_maintainer_placeholders():
    text = (SEED / "hardening_manifest.yaml").read_text(encoding="utf-8")
    assert text.count("REPLACE_WITH_") == 3
