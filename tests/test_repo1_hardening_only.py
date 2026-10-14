from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "platform_one" / "repo1-hardening"


def test_hardening_project_contains_no_binary_and_only_permitted_runtime_script():
    forbidden_suffixes = {".pyc", ".whl", ".so", ".bin", ".exe"}
    files = [path for path in SEED.rglob("*") if path.is_file()]
    assert all(path.suffix.lower() not in forbidden_suffixes for path in files)
    python_files = [path.relative_to(SEED).as_posix() for path in files if path.suffix == ".py"]
    assert python_files == ["scripts/service.py"]


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
    assert text.count('type: "sha256"') == 1
    values = re.findall(r'value: "([0-9a-f]{64})"', text)
    assert len(values) == 1
    assert "ae81a7dcceac5d27b5d42d9614a71d296abc6f18" in text


def test_manifest_does_not_hide_maintainer_placeholders():
    text = (SEED / "hardening_manifest.yaml").read_text(encoding="utf-8")
    assert text.count("REPLACE_WITH_") == 3


def test_entrypoint_script_is_repo_local_and_not_manifest_resource():
    docker = (SEED / "Dockerfile").read_text(encoding="utf-8")
    manifest = (SEED / "hardening_manifest.yaml").read_text(encoding="utf-8")
    assert "COPY --chown=${APP_UID}:0 scripts/service.py /opt/qbio/service.py" in docker
    assert (SEED / "scripts" / "service.py").is_file()
    assert 'filename: "service.py"' not in manifest


def test_readme_contains_kubernetes_and_resource_requirements():
    text = (SEED / "README.md").read_text(encoding="utf-8")
    for marker in (
        "apiVersion: apps/v1",
        "kind: Deployment",
        "CPU",
        "Memory",
        "Ephemeral storage",
        "Persistent volumes",
        "Containers / replicas",
    ):
        assert marker in text
