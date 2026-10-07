from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Final

from agency_cloud.compliance import STANDARDS as US_STANDARDS
from agency_cloud.config import Settings

REVIEWED_AT: Final = "2026-10-07"

GLOBAL_CONTROL_DOMAINS: Final = [
    {"id": "GOV", "name": "Governance and accountability"},
    {"id": "RISK", "name": "Enterprise and AI risk management"},
    {"id": "IAM", "name": "Identity, MFA, privileged access, and service identities"},
    {"id": "ASSET", "name": "Asset, software, model, and data inventory"},
    {"id": "DATA", "name": "Data classification, privacy, residency, and transfer"},
    {"id": "SDLC", "name": "Secure development, SBOM, provenance, and vulnerability handling"},
    {"id": "CONFIG", "name": "Configuration, hardening, and change management"},
    {"id": "CRYPTO", "name": "Cryptography, keys, secrets, and certificate lifecycle"},
    {"id": "LOG", "name": "Logging, evidence integrity, detection, and monitoring"},
    {"id": "IR", "name": "Incident response, notification, forensics, and lessons learned"},
    {"id": "BCP", "name": "Business continuity, backups, recovery, and resilience"},
    {"id": "SUPPLY", "name": "Third-party, cloud, supplier, and software supply-chain risk"},
    {"id": "ZT", "name": "Zero trust, segmentation, device posture, and workload identity"},
    {"id": "AI", "name": "AI lifecycle governance, TEVV, impact assessment, and human oversight"},
    {"id": "ASSURE", "name": "Assessment, certification, authorization, and continuous evidence"},
]

GLOBAL_REGIMES: Final = [
    {
        "id": "iso-27001",
        "region": "GLOBAL",
        "jurisdiction": "International",
        "name": "ISO/IEC 27001:2022",
        "authority": "ISO/IEC",
        "type": "STANDARD",
        "status": "CURRENT",
        "appliesTo": ["information-security-management"],
        "domains": ["GOV", "RISK", "IAM", "ASSET", "DATA", "SDLC", "CONFIG", "CRYPTO", "LOG", "IR", "BCP", "SUPPLY", "ASSURE"],
        "url": "https://www.iso.org/standard/27001",
        "nextMilestone": None,
    },
    {
        "id": "iso-42001",
        "region": "GLOBAL",
        "jurisdiction": "International",
        "name": "ISO/IEC 42001:2023 AI management systems",
        "authority": "ISO/IEC",
        "type": "STANDARD",
        "status": "CURRENT",
        "appliesTo": ["ai-providers", "ai-deployers"],
        "domains": ["GOV", "RISK", "AI", "DATA", "LOG", "ASSURE"],
        "url": "https://www.iso.org/standard/81230.html",
        "nextMilestone": None,
    },
    {
        "id": "iso-42005",
        "region": "GLOBAL",
        "jurisdiction": "International",
        "name": "ISO/IEC 42005:2025 AI system impact assessment",
        "authority": "ISO/IEC",
        "type": "STANDARD",
        "status": "CURRENT",
        "appliesTo": ["ai-providers", "ai-deployers"],
        "domains": ["GOV", "RISK", "AI", "ASSURE"],
        "url": "https://www.iso.org/",
        "nextMilestone": None,
    },
    {
        "id": "pci-dss-4-0-1",
        "region": "GLOBAL",
        "jurisdiction": "Payment card ecosystem",
        "name": "PCI DSS v4.0.1",
        "authority": "PCI Security Standards Council",
        "type": "INDUSTRY_STANDARD",
        "status": "CURRENT",
        "appliesTo": ["payment-card-environments"],
        "domains": ["IAM", "ASSET", "DATA", "CONFIG", "CRYPTO", "LOG", "IR", "ASSURE"],
        "url": "https://www.pcisecuritystandards.org/",
        "nextMilestone": None,
    },
    {
        "id": "eu-ai-act",
        "region": "EU",
        "jurisdiction": "European Union",
        "name": "EU AI Act",
        "authority": "European Commission / Member State authorities",
        "type": "LAW",
        "status": "IN_FORCE_PHASED",
        "appliesTo": ["ai-providers", "ai-deployers", "gpai-providers"],
        "domains": ["GOV", "RISK", "AI", "DATA", "LOG", "ASSURE"],
        "url": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
        "nextMilestone": "2027-12-02",
    },
    {
        "id": "eu-cra",
        "region": "EU",
        "jurisdiction": "European Union",
        "name": "Cyber Resilience Act",
        "authority": "European Commission / market-surveillance authorities",
        "type": "LAW",
        "status": "REPORTING_ACTIVE_FULL_APPLICATION_2027",
        "appliesTo": ["products-with-digital-elements", "software", "hardware"],
        "domains": ["RISK", "SDLC", "CONFIG", "IR", "SUPPLY", "ASSURE"],
        "url": "https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act",
        "nextMilestone": "2027-12-11",
    },
    {
        "id": "eu-nis2",
        "region": "EU",
        "jurisdiction": "European Union / national transposition",
        "name": "NIS2 Directive",
        "authority": "EU / Member State competent authorities",
        "type": "LAW",
        "status": "CURRENT_NATIONAL_IMPLEMENTATION",
        "appliesTo": ["essential-entities", "important-entities", "critical-sectors"],
        "domains": ["GOV", "RISK", "IAM", "IR", "BCP", "SUPPLY", "CRYPTO", "ASSURE"],
        "url": "https://www.enisa.europa.eu/topics/state-of-cybersecurity-in-the-eu/threats-and-incidents",
        "nextMilestone": None,
    },
    {
        "id": "eu-dora",
        "region": "EU",
        "jurisdiction": "European Union",
        "name": "Digital Operational Resilience Act",
        "authority": "EU financial supervisory authorities",
        "type": "LAW",
        "status": "APPLICABLE",
        "appliesTo": ["financial-entities", "critical-ict-third-parties"],
        "domains": ["GOV", "RISK", "IR", "BCP", "SUPPLY", "LOG", "ASSURE"],
        "url": "https://finance.ec.europa.eu/news/digital-finance-2024-12-19_en",
        "nextMilestone": None,
    },
    {
        "id": "uk-caf-4",
        "region": "UK",
        "jurisdiction": "United Kingdom",
        "name": "NCSC Cyber Assessment Framework v4.0",
        "authority": "UK National Cyber Security Centre",
        "type": "FRAMEWORK",
        "status": "CURRENT",
        "appliesTo": ["critical-national-infrastructure", "essential-functions", "public-sector"],
        "domains": ["GOV", "RISK", "IAM", "ASSET", "LOG", "IR", "BCP", "SUPPLY", "ASSURE"],
        "url": "https://www.ncsc.gov.uk/collection/cyber-assessment-framework",
        "nextMilestone": None,
    },
    {
        "id": "uk-cyber-governance",
        "region": "UK",
        "jurisdiction": "United Kingdom",
        "name": "Cyber Governance Code of Practice",
        "authority": "UK Government / NCSC",
        "type": "CODE_OF_PRACTICE",
        "status": "CURRENT",
        "appliesTo": ["boards", "directors", "organizations"],
        "domains": ["GOV", "RISK", "IR", "BCP", "SUPPLY"],
        "url": "https://www.gov.uk/government/publications/cyber-governance-code-of-practice/cyber-governance-code-of-practice",
        "nextMilestone": None,
    },
    {
        "id": "uk-ai-cyber-code",
        "region": "UK",
        "jurisdiction": "United Kingdom",
        "name": "AI Cyber Security Code of Practice",
        "authority": "UK Government",
        "type": "CODE_OF_PRACTICE",
        "status": "CURRENT",
        "appliesTo": ["ai-systems", "ai-developers", "ai-operators"],
        "domains": ["AI", "RISK", "SDLC", "SUPPLY", "LOG", "IR"],
        "url": "https://www.gov.uk/government/collections/cyber-security-codes-of-practice",
        "nextMilestone": None,
    },
    {
        "id": "canada-itsp-10-033",
        "region": "CANADA",
        "jurisdiction": "Canada",
        "name": "Security and privacy controls and assurance activities catalogue",
        "authority": "Canadian Centre for Cyber Security",
        "type": "GOVERNMENT_GUIDANCE",
        "status": "EFFECTIVE_2026_03_31",
        "appliesTo": ["government", "regulated-and-aligned-organizations"],
        "domains": ["GOV", "RISK", "IAM", "ASSET", "DATA", "SDLC", "CONFIG", "CRYPTO", "LOG", "IR", "BCP", "SUPPLY", "ASSURE"],
        "url": "https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/foreword-overview-introduction",
        "nextMilestone": None,
    },
    {
        "id": "canada-osfi-b13",
        "region": "CANADA",
        "jurisdiction": "Canada",
        "name": "OSFI Guideline B-13 Technology and Cyber Risk Management",
        "authority": "Office of the Superintendent of Financial Institutions",
        "type": "REGULATORY_GUIDANCE",
        "status": "CURRENT",
        "appliesTo": ["federally-regulated-financial-institutions"],
        "domains": ["GOV", "RISK", "IR", "BCP", "SUPPLY", "LOG", "ASSURE"],
        "url": "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/technology-cyber-risk-management",
        "nextMilestone": None,
    },
    {
        "id": "australia-ism-2026-09",
        "region": "AUSTRALIA",
        "jurisdiction": "Australia",
        "name": "ASD Information Security Manual",
        "authority": "Australian Signals Directorate",
        "type": "GOVERNMENT_FRAMEWORK",
        "status": "CURRENT_2026_09",
        "appliesTo": ["government", "critical-infrastructure", "risk-based-organizations"],
        "domains": ["GOV", "RISK", "IAM", "ASSET", "DATA", "SDLC", "CONFIG", "CRYPTO", "LOG", "IR", "BCP", "SUPPLY", "ASSURE"],
        "url": "https://www.cyber.gov.au/ism/2026-09/using-the-cyber-security-framework",
        "nextMilestone": None,
    },
    {
        "id": "australia-essential-eight",
        "region": "AUSTRALIA",
        "jurisdiction": "Australia",
        "name": "Essential Eight Maturity Model",
        "authority": "Australian Signals Directorate",
        "type": "GOVERNMENT_BASELINE",
        "status": "CURRENT",
        "appliesTo": ["internet-connected-it-networks"],
        "domains": ["IAM", "CONFIG", "SDLC", "BCP", "ASSURE"],
        "url": "https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/essential-eight/essential-eight-maturity-model",
        "nextMilestone": None,
    },
    {
        "id": "singapore-cybersecurity-act",
        "region": "SINGAPORE",
        "jurisdiction": "Singapore",
        "name": "Cybersecurity Act with 2024 amendments",
        "authority": "Cyber Security Agency of Singapore",
        "type": "LAW",
        "status": "AMENDMENTS_EFFECTIVE_2025_10_31",
        "appliesTo": ["critical-information-infrastructure", "regulated-cybersecurity-systems"],
        "domains": ["GOV", "RISK", "IR", "BCP", "SUPPLY", "ASSURE"],
        "url": "https://www.csa.gov.sg/legislation/cybersecurity-act/",
        "nextMilestone": None,
    },
    {
        "id": "india-dpdp-rules-2025",
        "region": "INDIA",
        "jurisdiction": "India",
        "name": "Digital Personal Data Protection Rules 2025",
        "authority": "Ministry of Electronics and Information Technology",
        "type": "LAW_AND_RULES",
        "status": "PHASED_COMMENCEMENT",
        "appliesTo": ["personal-data-processing"],
        "domains": ["GOV", "DATA", "IAM", "IR", "SUPPLY", "ASSURE"],
        "url": "https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digit",
        "nextMilestone": "VERIFY_RULE_SPECIFIC_EFFECTIVE_DATES",
    },
    {
        "id": "saudi-ecc-2-2024",
        "region": "SAUDI_ARABIA",
        "jurisdiction": "Saudi Arabia",
        "name": "Essential Cybersecurity Controls ECC 2-2024",
        "authority": "National Cybersecurity Authority",
        "type": "NATIONAL_CONTROLS",
        "status": "CURRENT",
        "appliesTo": ["national-entities", "regulated-organizations"],
        "domains": ["GOV", "RISK", "IAM", "ASSET", "DATA", "CONFIG", "CRYPTO", "LOG", "IR", "BCP", "SUPPLY", "ASSURE"],
        "url": "https://nca.gov.sa/en/regulatory-documents/controls-list/ecc/",
        "nextMilestone": None,
    },
    {
        "id": "brazil-lgpd-incident",
        "region": "BRAZIL",
        "jurisdiction": "Brazil",
        "name": "LGPD Security Incident Reporting Regulation (ANPD Resolution 15/2024)",
        "authority": "Autoridade Nacional de Proteção de Dados",
        "type": "LAW_AND_REGULATION",
        "status": "CURRENT",
        "appliesTo": ["personal-data-controllers"],
        "domains": ["GOV", "DATA", "IR", "LOG", "ASSURE"],
        "url": "https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-aprova-o-regulamento-de-comunicacao-de-incidente-de-seguranca",
        "nextMilestone": None,
    },
]

HORIZON_2027: Final = [
    {
        "date": "2027-01-01",
        "region": "US",
        "regime": "FedRAMP Consolidated Rules for 2026",
        "event": "Mandatory adoption takes effect for stakeholders, subject to rule-specific applicability.",
        "priority": "CRITICAL_FOR_FEDERAL_CLOUD",
        "url": "https://www.fedramp.gov/2026/timeline/",
    },
    {
        "date": "2027-06-11",
        "region": "US",
        "regime": "FedRAMP",
        "event": "FedRAMP stops accepting applications for new Rev5 certifications.",
        "priority": "HIGH_FOR_FEDERAL_CLOUD",
        "url": "https://www.fedramp.gov/2026/timeline/",
    },
    {
        "date": "2027-08-02",
        "region": "EU",
        "regime": "EU AI Act GPAI",
        "event": "GPAI models placed on the market before 2 August 2025 must comply with applicable GPAI obligations.",
        "priority": "HIGH_FOR_GPAI_PROVIDERS",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/guidelines-gpai-providers",
    },
    {
        "date": "2027-12-02",
        "region": "EU",
        "regime": "EU AI Act",
        "event": "High-risk AI rules for Annex III use cases apply.",
        "priority": "CRITICAL_FOR_HIGH_RISK_AI",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
    },
    {
        "date": "2027-12-11",
        "region": "EU",
        "regime": "Cyber Resilience Act",
        "event": "Full application of the CRA main obligations.",
        "priority": "CRITICAL_FOR_DIGITAL_PRODUCTS",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/cra-summary",
    },
]

UNIVERSAL_RISK_BASELINE: Final = [
    {"id": "identity-compromise", "title": "Identity and credential compromise", "domains": ["IAM", "ZT"], "minimum": ["phishing-resistant MFA where appropriate", "privileged-access separation", "service identities", "session revocation"]},
    {"id": "software-supply-chain", "title": "Software and dependency supply-chain compromise", "domains": ["SDLC", "SUPPLY"], "minimum": ["SBOM", "dependency scanning", "signed provenance", "release traceability", "vulnerability intake"]},
    {"id": "cloud-misconfiguration", "title": "Cloud and configuration exposure", "domains": ["CONFIG", "ZT"], "minimum": ["configuration baselines", "least privilege", "network segmentation", "secret isolation", "drift detection"]},
    {"id": "ransomware-resilience", "title": "Ransomware and destructive disruption", "domains": ["IR", "BCP"], "minimum": ["immutable or protected backups", "restore testing", "incident playbooks", "segmentation", "recovery objectives"]},
    {"id": "data-loss-privacy", "title": "Data loss, privacy breach, and cross-border exposure", "domains": ["DATA", "IR"], "minimum": ["data inventory", "classification", "retention", "transfer rules", "breach decision matrix"]},
    {"id": "third-party-risk", "title": "Third-party and concentration risk", "domains": ["SUPPLY", "BCP"], "minimum": ["supplier inventory", "criticality tiers", "security clauses", "exit plans", "concentration monitoring"]},
    {"id": "ai-model-risk", "title": "AI model and agent risk", "domains": ["AI", "RISK"], "minimum": ["model inventory", "impact assessment", "TEVV", "human oversight", "logging", "misuse testing"]},
    {"id": "vulnerability-exploitation", "title": "Known and zero-day vulnerability exploitation", "domains": ["SDLC", "CONFIG", "IR"], "minimum": ["asset inventory", "vulnerability triage", "KEV-aware prioritization", "patch SLAs", "coordinated disclosure"]},
]


def _us_regimes() -> list[dict]:
    items = []
    for standard in US_STANDARDS:
        item = dict(standard)
        item.update(
            {
                "region": "US",
                "jurisdiction": "United States",
                "type": "STANDARD_OR_PROGRAM",
                "appliesTo": [],
                "domains": ["GOV", "RISK", "ASSURE"],
                "nextMilestone": None,
            }
        )
        items.append(item)
    return items


def global_catalog() -> dict:
    regimes = _us_regimes() + list(GLOBAL_REGIMES)
    return {
        "schema": "gpt-doug.global-compliance-catalog.v1",
        "reviewedAt": REVIEWED_AT,
        "scope": "Global engineering-readiness registry; applicability remains jurisdiction, sector, data, contract, product, and system-boundary specific.",
        "controlDomains": GLOBAL_CONTROL_DOMAINS,
        "regimes": regimes,
        "riskBaseline": UNIVERSAL_RISK_BASELINE,
        "horizon2027": HORIZON_2027,
        "coverage": {
            "regions": sorted({item["region"] for item in regimes}),
            "regimeCount": len(regimes),
            "horizonEventCount": len(HORIZON_2027),
        },
        "claim": "No certification, authorization, legal opinion, or universal compliance claim is made.",
    }


def jurisdiction_profile(regions: list[str]) -> dict:
    wanted = {str(region).strip().upper() for region in regions if str(region).strip()}
    regimes = [
        item
        for item in (_us_regimes() + list(GLOBAL_REGIMES))
        if item["region"].upper() in wanted or item["region"] == "GLOBAL"
    ]
    domains = sorted({domain for item in regimes for domain in item.get("domains", [])})
    return {
        "schema": "gpt-doug.jurisdiction-profile.v1",
        "reviewedAt": REVIEWED_AT,
        "regions": sorted(wanted),
        "regimes": regimes,
        "requiredEngineeringDomains": domains,
        "claim": "Engineering applicability profile only; legal and certification determinations remain external.",
    }


def horizon_2027() -> dict:
    return {
        "schema": "gpt-doug.compliance-horizon.2027.v1",
        "reviewedAt": REVIEWED_AT,
        "events": HORIZON_2027,
        "rule": "Track official sources continuously and re-verify before treating a milestone as applicable.",
    }


def global_posture(settings: Settings) -> dict:
    root: Path = settings.repo_root
    artifacts = {
        "security_policy": root / "SECURITY.md",
        "govsec_baseline": root / "GOVSEC_AI_BASELINE.md",
        "control_matrix": root / "compliance" / "control-evidence-matrix.json",
        "poam": root / "compliance" / "POAM_ENGINEERING.md",
        "incident_matrix": root / "compliance" / "GLOBAL_INCIDENT_MATRIX.md",
        "global_baseline": root / "compliance" / "GLOBAL_ENGINEERING_BASELINE_2027.md",
    }
    checks = [
        {"id": "GLOBAL-GOV-01", "status": "PASS" if artifacts["security_policy"].exists() else "GAP", "title": "Global security policy"},
        {"id": "GLOBAL-GOV-02", "status": "PASS" if artifacts["control_matrix"].exists() else "GAP", "title": "Control-to-evidence matrix"},
        {"id": "GLOBAL-GOV-03", "status": "PASS" if artifacts["poam"].exists() else "GAP", "title": "Engineering POA&M"},
        {"id": "GLOBAL-IR-01", "status": "PASS" if artifacts["incident_matrix"].exists() else "GAP", "title": "Jurisdiction-aware incident reporting matrix"},
        {"id": "GLOBAL-ROADMAP-01", "status": "PASS" if artifacts["global_baseline"].exists() else "GAP", "title": "2027 global engineering baseline"},
        {"id": "GLOBAL-IAM-01", "status": "GAP", "title": "Federated OIDC/MFA production identity"},
        {"id": "GLOBAL-BCP-01", "status": "PASS" if settings.database_url.startswith("postgresql") else "GAP", "title": "Durable production data plane and recovery foundation"},
        {"id": "GLOBAL-ASSURE-01", "status": "EXTERNAL", "title": "Jurisdiction/sector-specific external assessment and certification"},
    ]
    counts = {key: sum(1 for item in checks if item["status"] == key) for key in ("PASS", "GAP", "EXTERNAL")}
    return {
        "schema": "gpt-doug.global-posture.v1",
        "reviewedAt": REVIEWED_AT,
        "counts": counts,
        "checks": checks,
        "claim": "Engineering readiness only; no global legal compliance claim is made.",
    }
