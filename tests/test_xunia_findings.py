import json
import unittest
from datetime import datetime, timezone

from xunia_findings import normalize_evidence
from xunia_security_executor import ExecutionEvidence


NOW = datetime.now(timezone.utc).isoformat()


def evidence(tool_id: str, payload) -> ExecutionEvidence:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return ExecutionEvidence(
        engagement_id="finding-test",
        planned_evidence_id="f" * 64,
        tool_id=tool_id,
        target_type="path",
        target=".",
        argv=(tool_id,),
        started_at=NOW,
        finished_at=NOW,
        returncode=0,
        stdout_sha256="a" * 64,
        stderr_sha256="b" * 64,
        stdout_preview=text,
        stderr_preview="",
        output_truncated=False,
        status="COMPLETED",
    )


class XuniaFindingNormalizerTests(unittest.TestCase):
    def test_nuclei_jsonl_becomes_finding(self):
        item = {
            "template-id": "example-check",
            "matched-at": "https://lab.example.test",
            "info": {"name": "Example finding", "severity": "high", "description": "Test description"},
        }
        result = normalize_evidence(evidence("nuclei", json.dumps(item) + "\n"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].severity, "high")
        self.assertEqual(result[0].title, "Example finding")

    def test_trivy_vulnerability_becomes_remediation_item(self):
        payload = {
            "Results": [{
                "Target": "app",
                "Vulnerabilities": [{
                    "VulnerabilityID": "CVE-TEST-1",
                    "PkgName": "demo",
                    "InstalledVersion": "1.0",
                    "Severity": "CRITICAL",
                    "Title": "Demo package issue",
                }],
            }]
        }
        result = normalize_evidence(evidence("trivy", payload))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].severity, "critical")
        self.assertIn("Upgrade", result[0].remediation)

    def test_gitleaks_is_high_severity_and_does_not_copy_secret_value(self):
        payload = [{"RuleID": "generic-api-key", "Description": "Potential API key", "File": "config.py", "StartLine": 4, "Secret": "do-not-copy"}]
        result = normalize_evidence(evidence("gitleaks", payload))
        self.assertEqual(result[0].severity, "high")
        self.assertNotIn("do-not-copy", result[0].description)
        self.assertNotIn("do-not-copy", result[0].remediation)


if __name__ == "__main__":
    unittest.main()
