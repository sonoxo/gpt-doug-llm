# Federal contracting readiness: six evidence gates

This module connects Sonoxo's **public development evidence** to a six-gate reviewer workflow without falsely certifying federal readiness. Run from the repository root:

```sh
python3 scripts/federal_readiness.py --repository sonoxo/gpt-doug-llm --output federal-readiness-report.json
python3 -m unittest discover -s tests -p 'test_federal_readiness.py' -v
```

All gates start **incomplete**. An absent or inaccessible record is **unverified**, not failed. A GitHub repository and passing CI prove development activity, not SAM registration, a government ATO, FedRAMP/CMMC certification, or clearance. This tool does not use credentials, send outreach, or access restricted systems.

To attach verified evidence, create a local JSON manifest **outside the repository** (never commit PII, CUI, classified records, UEI-linked sensitive documents, contracts or credentials):

```json
{
  "evidence": {
    "capability": {
      "capability_statement": {
        "status": "verified",
        "reviewed": true,
        "reviewer": "Authorized reviewer name",
        "reference": "internal-approved-evidence-reference"
      }
    }
  }
}
```

Run with `--manifest /secure/path/evidence.json`. Each subcheck requires a reviewer, explicit review flag, and a reference. This reports **evidence_reviewed**, not external certification. No external record is assumed valid solely from user input.

## Connections and authorization gates

| Gate | Connection | Verification authority |
| --- | --- | --- |
| Business | SAM.gov entity registration; SBA business guidance | Entity administrator / SAM record |
| Capability | Signed agency-specific capability brief | Business owner and approved reviewer |
| Demo | Recorded reproducible workflows, test logs, deployment evidence | Independent technical reviewer |
| Security | NIST mappings, independent findings and risk sign-off | Designated security assessor |
| Performance | Client-issued records and qualified personnel | Client and credential issuer |
| Clearance | Facility clearance / sponsored teaming | DCSA and authorized sponsoring organization |

Source-code metadata may be collected read-only from the official public GitHub API. SAM.gov, DCSA and classified/acquisition portals are provided as human verification links only: no unauthorized APIs, no account takeover, no scraping gated data, no auto-clearance claims. Required evidence should remain in an approved secure repository. Audit outputs include reference IDs, not sensitive source documents.

This system is advisory. Only authorized officials determine contracting eligibility and clearance.
