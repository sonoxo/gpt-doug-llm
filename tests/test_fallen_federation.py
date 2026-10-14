import pytest

from fallen_federation.core import (
    Federation,
    FederationPolicy,
    RepositoryTarget,
    default_workers,
)
from fallen_federation.public_bio import public_only, source_catalog


def test_default_worker_portfolio_is_555():
    workers = default_workers()
    assert len(workers) == 555
    assert {w.role for w in workers} == {
        "discovery",
        "evidence_verification",
        "experimental_design",
        "replication_adversarial",
        "translation_deployment",
    }


def test_unauthorized_repository_fails_closed():
    federation = Federation(
        policy=FederationPolicy(),
        workers=[],
        repositories=[RepositoryTarget("example/repo", authorized=False)],
    )
    with pytest.raises(PermissionError):
        federation.deployment_plan()


def test_self_propagation_is_rejected():
    with pytest.raises(ValueError):
        FederationPolicy(allow_self_propagation=True).validate()


def test_plan_requires_human_merge_by_default():
    federation = Federation(
        policy=FederationPolicy(max_workers=555),
        workers=default_workers(),
        repositories=[RepositoryTarget("sonoxo/gpt-doug-llm", authorized=True)],
    )
    plan = federation.deployment_plan()
    assert plan[0]["workers"] == 555
    assert plan[0]["human_merge_required"] is True


def test_public_source_catalog_has_provenance_classes():
    catalog = source_catalog()
    assert len(catalog) >= 6
    assert all("kind" in item and "access" in item for item in catalog)
    assert all(item["access"] in {"public", "public_metadata"} for item in public_only())
