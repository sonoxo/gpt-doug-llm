from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "platform_one" / "repo1-qbio"


def test_repo1_seed_has_required_root_files():
    required = {
        "Dockerfile",
        "hardening_manifest.yaml",
        "LICENSE",
        "README.md",
        "renovate.json",
        "SECURITY.md",
    }
    assert required.issubset({path.name for path in SEED.iterdir()})
    assert not (SEED / ".gitlab-ci.yml").exists()


def test_dockerfile_matches_iron_bank_baseline_controls():
    text = (SEED / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG BASE_REGISTRY=registry1.dso.mil" in text
    assert "ARG BASE_IMAGE=ironbank/redhat/ubi/ubi9-minimal" in text
    assert "ARG BASE_TAG=9.8" in text
    assert "HEALTHCHECK" in text
    assert "USER 1001" in text
    assert "\nADD " not in "\n" + text
    assert "\nLABEL " not in "\n" + text


def test_hardening_manifest_contains_required_sections():
    text = (SEED / "hardening_manifest.yaml").read_text(encoding="utf-8")
    for marker in (
        "apiVersion: v1",
        "name:",
        "tags:",
        "args:",
        "BASE_IMAGE:",
        "BASE_TAG:",
        "labels:",
        "maintainers:",
    ):
        assert marker in text


def test_standalone_service_unit_suite_passes():
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=SEED,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
