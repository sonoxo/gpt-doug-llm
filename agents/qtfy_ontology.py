"""Ontology primitives for defensive QTFY intelligence operations.

The graph is defensive, evidence-first, provenance-preserving, and publication
locked. Indicators are investigative leads. Containment remains limited to owned
or explicitly authorized assets and requires human review where specified.
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
    organizations: Iterable[Mapping[str, Any]] = (),
    tools: Iterable[Mapping[str, Any]] = (),
    vulnerabilities: Iterable[Mapping[str, Any]] = (),
    campaign_events: Iterable[Mapping[str, Any]] = (),
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
            attributionState="SOURCE_ATTRIBUTION_ONLY",
        ),
    ]
    links: list[dict[str, str]] = [_link("AdvisoryProfilesThreat", advisory_ref, threat_ref)]

    for technique_id, name in techniques.items():
        ref = f"AttackTechnique:{technique_id}"
        objects.append(
            _object(
                "AttackTechnique",
                technique_id,
                name=name,
                framework="MITRE ATT&CK Enterprise v19",
            )
        )
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

    for organization in organizations:
        organization_id = str(organization["id"])
        ref = f"Organization:{organization_id}"
        objects.append(
            _object(
                "Organization",
                organization_id,
                name=str(organization.get("name", organization_id)),
                role=str(organization.get("role", "ADVISORY_MENTIONED_ENTITY")),
                sourcePage=organization.get("sourcePage"),
                claimNature="AUTHORING_AGENCY_REPORTING",
            )
        )
        links.append(_link("AdvisoryMentionsOrganization", advisory_ref, ref))

    tool_refs: dict[str, str] = {}
    for tool in tools:
        tool_id = str(tool["id"])
        ref = f"ThreatTool:{tool_id}"
        tool_refs[tool_id] = ref
        objects.append(
            _object(
                "ThreatTool",
                tool_id,
                name=str(tool.get("name", tool_id)),
                category=str(tool.get("category", "UNSPECIFIED")),
                sourcePage=tool.get("sourcePage"),
            )
        )
        links.append(_link("AdvisoryDescribesTool", advisory_ref, ref))
        links.append(_link("ThreatUsesTool", threat_ref, ref))

    vulnerability_refs: dict[str, str] = {}
    for vulnerability in vulnerabilities:
        vulnerability_id = str(vulnerability["id"])
        ref = f"Vulnerability:{vulnerability_id}"
        vulnerability_refs[vulnerability_id] = ref
        objects.append(
            _object(
                "Vulnerability",
                vulnerability_id,
                cve=vulnerability_id,
                context=str(vulnerability.get("context", "")),
                sourcePage=vulnerability.get("sourcePage"),
            )
        )
        links.append(_link("AdvisoryMentionsVulnerability", advisory_ref, ref))

    for event in campaign_events:
        event_id = str(event["id"])
        ref = f"CampaignEvent:{event_id}"
        objects.append(
            _object(
                "CampaignEvent",
                event_id,
                date=str(event.get("date", "")),
                targetCategory=str(event.get("targetCategory", "")),
                activity=str(event.get("activity", "")),
                outcome=str(event.get("outcome", "")),
                sourcePage=event.get("sourcePage"),
                claimNature="AUTHORING_AGENCY_REPORTING",
            )
        )
        links.append(_link("AdvisoryDescribesEvent", advisory_ref, ref))
        for tool_id in event.get("toolIds", ()):
            tool_ref = tool_refs.get(str(tool_id))
            if tool_ref:
                links.append(_link("EventUsesTool", ref, tool_ref))
        for vulnerability_id in event.get("vulnerabilityIds", ()):
            vulnerability_ref = vulnerability_refs.get(str(vulnerability_id))
            if vulnerability_ref:
                links.append(_link("EventReferencesVulnerability", ref, vulnerability_ref))

    return {
        "name": "VA3LM QTFY Defensive Intelligence Ontology",
        "version": "0.3.0",
        "mode": "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY",
        "objectTypes": [
            "CyberAdvisory",
            "ThreatProfile",
            "Organization",
            "CriticalSector",
            "AttackTechnique",
            "ThreatTool",
            "Vulnerability",
            "CampaignEvent",
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
            "AdvisoryMentionsOrganization",
            "AdvisoryTargetsSector",
            "AdvisoryUsesTechnique",
            "ThreatUsesTechnique",
            "AdvisoryDescribesTool",
            "ThreatUsesTool",
            "AdvisoryMentionsVulnerability",
            "AdvisoryDescribesEvent",
            "EventUsesTool",
            "EventReferencesVulnerability",
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
            "attributionHandling": "PRESERVE_SOURCE_CLAIM_NATURE",
            "masterLockRequiredForPublish": True,
            "masterLockRule": "ALL_SUBAGENTS_PASS_BEFORE_PUBLISH",
            "masterLockManifest": "intel/qtfy/master-lock.json",
        },
    }
