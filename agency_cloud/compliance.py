from __future__ import annotations

from typing import Final

from agency_cloud.advisory import advisory_policy
from agency_cloud.config import Settings
from agency_cloud.platform import PUBLIC_EVENT_CLASSES

REVIEWED_AT: Final = "2026-10-07"

STANDARDS: Final = [
    {"id":"nist-csf-2","name":"NIST Cybersecurity Framework 2.0","version":"2.0","authority":"NIST","url":"https://www.nist.gov/cyberframework","status":"CURRENT"},
    {"id":"nist-ai-rmf","name":"NIST AI Risk Management Framework","version":"1.0 (revision in progress)","authority":"NIST","url":"https://www.nist.gov/itl/ai-risk-management-framework","status":"CURRENT_WITH_REVISION_IN_PROGRESS"},
    {"id":"nist-ai-600-1","name":"NIST AI 600-1 Generative AI Profile","version":"600-1","authority":"NIST","url":"https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence","status":"CURRENT"},
    {"id":"nist-800-53","name":"NIST SP 800-53 Rev. 5","version":"Rev. 5","authority":"NIST","url":"https://csrc.nist.gov/pubs/sp/800/53/r5/final","status":"CURRENT"},
    {"id":"nist-800-53a","name":"NIST SP 800-53A Rev. 5","version":"Release 5.2.0","authority":"NIST","url":"https://csrc.nist.gov/pubs/sp/800/53/a/r5/final","status":"CURRENT"},
    {"id":"nist-800-53b","name":"NIST SP 800-53B","version":"Release 5.2.0","authority":"NIST","url":"https://csrc.nist.gov/pubs/sp/800/53/b/upd1/final","status":"CURRENT"},
    {"id":"nist-800-171","name":"NIST SP 800-171 Rev. 3","version":"Rev. 3","authority":"NIST","url":"https://csrc.nist.gov/pubs/sp/800/171/r3/final","status":"CURRENT"},
    {"id":"nist-800-171a","name":"NIST SP 800-171A Rev. 3","version":"Rev. 3","authority":"NIST","url":"https://csrc.nist.gov/pubs/sp/800/171/a/r3/final","status":"CURRENT"},
    {"id":"cmmc","name":"Cybersecurity Maturity Model Certification Program","version":"32 CFR Part 170 / current DFARS implementation","authority":"U.S. Department of Defense","url":"https://www.acquisition.gov/dfars/subpart-204.75-cybersecurity-maturity-model-certification","status":"PHASED_IMPLEMENTATION"},
    {"id":"cisa-zttm","name":"CISA Zero Trust Maturity Model","version":"2.0","authority":"CISA","url":"https://www.cisa.gov/resources-tools/resources/zero-trust-maturity-model","status":"CURRENT"},
    {"id":"fedramp","name":"FedRAMP Rev. 5 / Consolidated Rules for 2026","version":"2026","authority":"FedRAMP","url":"https://www.fedramp.gov/2026/reference/rev5/d/fedramp-certification/","status":"CURRENT"},
    {"id":"fips-140-3","name":"FIPS 140-3","version":"140-3","authority":"NIST / CMVP","url":"https://csrc.nist.gov/pubs/fips/140-3/final","status":"CURRENT"},
    {"id":"nist-ssdf","name":"NIST SP 800-218 Secure Software Development Framework","version":"1.1","authority":"NIST","url":"https://csrc.nist.gov/projects/ssdf","status":"CURRENT"},
]

EXTERNAL_DETERMINATIONS: Final = [
    "CMMC assessment/status",
    "FedRAMP authorization/certification",
    "FIPS module validation",
    "RMF authorization / ATO",
    "contract clause applicability",
]

def posture(settings: Settings) -> dict:
    root = settings.repo_root
    db_is_postgres = settings.database_url.startswith("postgresql")
    cors = tuple(origin for origin in settings.cors_origins if origin)
    checks = [
        {"id":"GOV-HUMAN-01","family":"Governance","status":"PASS" if advisory_policy().get("mode")=="ADVISORY_ONLY" else "GAP","title":"Advisory-only AI authority","detail":"AI may recommend and influence; execution remains outside the AI control plane."},
        {"id":"AC-DEMO-01","family":"Access Control","status":"PASS" if not settings.allow_demo_auth else "GAP","title":"Demo authentication disabled","detail":"Production boundaries must not accept built-in demo credentials."},
        {"id":"IA-SECRET-01","family":"Identification and Authentication","status":"PASS" if all([settings.director_token,settings.analyst_token,settings.auditor_token,settings.client_token]) else "GAP","title":"Role authentication secrets configured","detail":"Static role tokens are interim; OIDC/MFA is the target state."},
        {"id":"AU-INTEGRITY-01","family":"Audit and Accountability","status":"PASS" if bool(settings.audit_key) else "GAP","title":"Dedicated audit integrity key","detail":"Hash-chained audit records require a non-development secret."},
        {"id":"CP-DATA-01","family":"Contingency Planning","status":"PASS" if db_is_postgres else "GAP","title":"Durable production data plane","detail":"Ephemeral local storage is not a durable production event/case store."},
        {"id":"SC-CORS-01","family":"System and Communications Protection","status":"PASS" if cors and "*" not in cors else "GAP","title":"Explicit browser origin boundary","detail":"Browser API access is restricted to configured origins."},
        {"id":"SA-SEC-01","family":"System and Services Acquisition","status":"PASS" if (root/"SECURITY.md").exists() else "GAP","title":"Security policy artifact","detail":"Repository security policy is expected."},
        {"id":"CA-CI-01","family":"Assessment, Authorization and Monitoring","status":"PASS" if (root/".github/workflows").exists() else "GAP","title":"Continuous integration evidence","detail":"CI should include tests, scanning, and provenance checks."},
        {"id":"SC-PUBLIC-01","family":"System and Communications Protection","status":"PASS" if PUBLIC_EVENT_CLASSES=={"PUBLIC","TRAINING","SIMULATION"} else "GAP","title":"Public realtime data boundary","detail":"Public streaming is limited to public/training/simulation classes."},
        {"id":"CA-CMMC-EXT","family":"Assessment, Authorization and Monitoring","status":"EXTERNAL","title":"CMMC assessment/status","detail":"Software self-assessment cannot grant CMMC status."},
        {"id":"CA-FEDRAMP-EXT","family":"Assessment, Authorization and Monitoring","status":"EXTERNAL","title":"FedRAMP authorization","detail":"Deployment on a commercial cloud is not itself FedRAMP authorization."},
        {"id":"SC-FIPS-EXT","family":"System and Communications Protection","status":"EXTERNAL","title":"FIPS 140-3 module validation","detail":"Validation must be supported by CMVP records for modules actually used."},
        {"id":"CA-ATO-EXT","family":"Assessment, Authorization and Monitoring","status":"EXTERNAL","title":"RMF authorization / ATO","detail":"Authorization decisions remain external."},
    ]
    counts={k:sum(1 for i in checks if i["status"]==k) for k in ("PASS","GAP","EXTERNAL")}
    return {"schema":"gpt-doug.compliance-posture.v1","reviewedAt":REVIEWED_AT,"claim":"Engineering readiness evidence only; no certification or authorization is claimed.","counts":counts,"checks":checks,"externalDeterminations":EXTERNAL_DETERMINATIONS}

def catalog() -> dict:
    return {"schema":"gpt-doug.us-compliance-catalog.v1","reviewedAt":REVIEWED_AT,"standards":STANDARDS,"operatingPrinciple":{"mode":"ADVISORY_ONLY","rule":"AI recommendations may influence a human decision but do not execute consequential actions.","humanAuthority":True,"autonomousExecution":False},"disclaimer":"Applicability is system-, contract-, data-, agency-, and authorization-boundary-specific."}
