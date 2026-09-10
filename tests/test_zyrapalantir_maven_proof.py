import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class MavenProofTests(unittest.TestCase):
    def test_field_loader_exposes_only_non_secret_roundtrip_proof(self):
        field = load_module("zyrapalantir_field_test", ROOT / "scripts" / "zyrapalantir_field.py")
        with tempfile.TemporaryDirectory() as td:
            proof_path = pathlib.Path(td) / "proof.json"
            proof_path.write_text(json.dumps({
                "schema": "xunia.palantir-maven-readiness.v1",
                "verified_at": "2026-09-10T11:49:08+00:00",
                "ok": True,
                "defense_ready": True,
                "coordinates": "com.xunia:defense-readiness-test:0.1.0-readiness-test",
                "host": "example.palantirfoundry.com",
                "publish": {"pom_status": 204, "jar_status": 204},
                "retrieve": {"pom_status": 200, "jar_status": 200},
                "integrity": {"pom_match": True, "jar_match": True, "pom_sha256": "a"*64, "jar_sha256": "b"*64},
                "token": "MUST_NOT_LEAK"
            }))
            old = field.MAVEN_PROOF
            field.MAVEN_PROOF = proof_path
            try:
                proof = field.latest_maven_proof()
            finally:
                field.MAVEN_PROOF = old
        self.assertTrue(proof["ok"])
        self.assertEqual(proof["publish"]["jar_status"], 204)
        self.assertEqual(proof["retrieve"]["jar_status"], 200)
        self.assertTrue(proof["integrity"]["jar_match"])
        self.assertNotIn("token", proof)

    def test_visual_assistant_reports_actual_roundtrip_values(self):
        visual = load_module("zyrapalantir_visual_test_proof", ROOT / "scripts" / "zyrapalantir_visual.py")
        state = {
            "maven_proof": {
                "ok": True,
                "defense_ready": True,
                "coordinates": "com.xunia:defense-readiness-test:real-version",
                "host": "tenant.palantirfoundry.com",
                "publish": {"pom_status": 204, "jar_status": 204},
                "retrieve": {"pom_status": 200, "jar_status": 200},
                "integrity": {"pom_match": True, "jar_match": True},
            }
        }
        reply = visual.assistant_reply("show maven proof", state)
        self.assertIn("real-version", reply)
        self.assertIn("204/204", reply)
        self.assertIn("200/200", reply)
        self.assertIn("JAR match=True", reply)


if __name__ == "__main__":
    unittest.main()
