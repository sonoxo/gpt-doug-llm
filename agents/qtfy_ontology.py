"""Ontology primitives for defensive QTFY intelligence operations.

The graph is intentionally defensive and evidence-first. Indicators are investigative
leads. Any containment action remains scoped to owned or explicitly authorized assets
and requires the repository's human-review and operational-safety gates.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


def _object(object_type: str, object_id: str, **properties: Any) -> dict[str, Any]:
    return {"objectType": object_type, "id": object_id, "properties": properties}


def _link(link_type: str, source: str, target: str) -> dict[str, str]:
    return {"linkType": link_type, "from": source, "to": target}


def build_defensive_ontology(
    *,
    advisory_id: str,
    advisory_url: str,
    threat_label: str,
    tlp: str,
    published: str,
    techniques: Mapping[str, str],
    controls: Iterable[Mapping[str, Any]],
    target_sectors: Iterable[str],
    ioc_feeds: Iterable[str],
) -> dict[str, Any]:
    """Build a Palantir-style object/link/action graph for the advisory."""

    advisory_ref = f"CyberAdvisory:{advisory_id}"
    threat_ref = f"ThreatProfile:{threat_label}"
    objects: list[dict[str, Any]] = [
        _object(
            "CyberAdvisory",
            advisory_id,
            title="China-Linked Hacking Group QTFY Targets Military and Critical Infrastructure with Malicious Distributed Systems",
            sourceUrl=advisory_url,
            tlp=tlp,
            published=published,
            reviewState="VERIFIED_PUBLIC_SOURCE",
        ),
        _object(
            "ThreatProfile",
            threat_label,
            label=threat_label,
            scope="PUBLIC_DEFENSIVE_INTELLIGENCE",
            disposition="MONITOR_AND_DEFEND",
        ),
    ]
    links: list[dict[str, str]] = [
        _link("AdvisoryProfilesThreat", advisory_ref, threat_ref),
    ]

    for technique_id, name in techniques.items():
        ref = f"AttackTechnique:{technique_id}"
        objects.append(_object("AttackTechnique", technique_id, name=name, framework="MITRE ATT&CK Enterprise v19"))
        links.append(_link("AdvisoryUsesTechnique", advisory_ref, ref))
        links.append(_link("ThreatUsesTechnique", threat_ref, ref))

    for control in controls:
        control_id = str(control["control_id"])
        ref = f"DefensiveControl:{control_id}"
        objects.append(
            _object(
                "DefensiveControl",
                control_id,
                objective=str(control["objective"]),
                va3lmLane=str(control["va3lm_lane"]),
                evidenceRequired=str(control["evidence_required"]),
                authorizedOnly=True,
            )
        )
        links.append(_link("AdvisoryRecommendsControl", advisory_ref, ref))

    for index, sector in enumerate(target_sectors, start=1):
        sector_id = f"sector-{index}"
        ref = f"CriticalSector:{sector_id}"
        objects.append(_object("CriticalSector", sector_id, name=sector))
        links.append(_link("AdvisoryTargetsSector", advisory_ref, ref))

    for index, feed_url in enumerate(ioc_feeds, start=1):
        feed_id = f"{advisory_id}-ioc-feed-{index}"
        ref = f"IOCFeed:{feed_id}"
        objects.append(
            _object(
                "IOCFeed",
                feed_id,
                sourceUrl=feed_url,
                tlp=tlp,
                ingestMode="DEFENSIVE_HUNTING",
                automaticBlocking=False,
                humanReviewRequired=True,
            )
        )
        links.append(_link("AdvisoryPublishesIOCFeed", advisory_ref, ref))

    return {
        "name": "VA3LM QTFY Defensive Intelligence Ontology",
        "version": "0.1.0",
        "mode": "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY",
        "objectTypes": [
            "CyberAdvisory",
            "ThreatProfile",
            "CriticalSector",
            "AttackTechnique",
            "IOCFeed",
            "Indicator",
            "Asset",
            "Detection",
            "Incident",
            "DefensiveControl",
            "DefensiveAction",
            "Evidence",
            "RecoveryValidation",
        ],
        "linkTypes": [
            "AdvisoryProfilesThreat",
            "AdvisoryTargetsSector",
            "AdvisoryUsesTechnique",
            "ThreatUsesTechnique",
            "AdvisoryPublishesIOCFeed",
            "AdvisoryRecommendsControl",
            "FeedContainsIndicator",
            "IndicatorObservedOnAsset",
            "DetectionMatchesIndicator",
            "DetectionUsesTechnique",
            "DetectionOpensIncident",
            "IncidentAffectsAsset",
            "IncidentRequiresControl",
            "IncidentHasAction",
            "ActionHasEvidence",
            "IncidentHasRecoveryValidation",
            "AssetDependsOnAsset",
        ],
        "actions": [
            {
                "apiName": "triageIndicator",
                "objectType": "Indicator",
                "effect": "set reviewState=UNDER_REVIEW",
                "requiresHumanReview": True,
            },
            {
                "apiName": "openDefensiveIncident",
                "objectType": "Detection",
                "effect": "create Incident and link DetectionOpensIncident",
                "requiresHumanReview": False,
            },
            {
                "apiName": "requestAuthorizedContainment",
                "objectType": "Incident",
                "effect": "create DefensiveAction with state=REQUESTED",
                "requiresHumanReview": True,
                "authorizedEnvironmentOnly": True,
            },
            {
                "apiName": "recordContainmentEvidence",
                "objectType": "DefensiveAction",
                "effect": "link ActionHasEvidence and set state=EVIDENCED",
                "requiresHumanReview": False,
            },
            {
                "apiName": "verifyRecovery",
                "objectType": "Incident",
                "effect": "create RecoveryValidation and link IncidentHasRecoveryValidation",
                "requiresHumanReview": True,
            },
        ],
        "objects": objects,
        "links": links,
        "guardrails": {
            "indicatorDefault": "INVESTIGATE_AND_VET",
            "automaticBlocking": False,
            "externalThirdPartyAction": False,
            "humanApprovalForContainment": True,
            "rawDataDefault": "REMAIN_WITH_OWNER",
        },
    }
