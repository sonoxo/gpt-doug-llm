"""Offline regression tests for the public-only OpenAI model mirror."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

from integrations.openai_model_mirror import mirror as m

SHA = "a" * 40
ROW = NS(id="openai/gpt-oss-20b", sha=SHA, gated=False, disabled=False, private=False,
         tags=["license:apache-2.0"])
FILES = [NS(rfilename="model.safetensors", size=4), NS(rfilename="README.md", size=5)]


class StubApi:
    def __init__(self, listed=None, info=None):
        self.listed = listed or [ROW]
        self.info = info or NS(id=ROW.id, sha=SHA, gated=False, tags=ROW.tags, siblings=FILES)
        self.calls = []

    def list_models(self, **kwargs):
        self.calls.append(("list", kwargs))
        return iter(self.listed)

    def model_info(self, repo_id, **kwargs):
        self.calls.append(("info", repo_id, kwargs))
        return self.info


class Contracts(unittest.TestCase):
    def test_only_official_owner(self):
        for value in ("other/gpt-oss-20b", "openai/../fake", "openai/test/a", "OPENAI/gpt-oss", "openai/.bad", "openai/a;echo"):
            with self.assertRaises(m.MirrorError):
                m.valid_repo(value)

    def test_catalog_pins_revisions_and_license(self):
        api = StubApi()
        result = m.catalog(api)
        self.assertEqual(result[0]["sha"], SHA)
        self.assertTrue(result[0]["eligible"])
        self.assertEqual(api.calls[0][1]["token"], False)

    def test_block_private_gated_unknown_license(self):
        for variant in ({"private": True}, {"gated": "auto"}, {"tags": ["license:other"]}):
            info = NS(**{**ROW.__dict__, **variant})
            self.assertFalse(m.catalog(StubApi(listed=[info]))[0]["eligible"])

    def test_selection_is_explicit_and_catalog_verified(self):
        records = m.catalog(StubApi())
        self.assertEqual(m.select_models(records, all_models=False, models=ROW.id)[0]["repo_id"], ROW.id)
        for opts in ((False, None), (True, ROW.id), (False, "openai/missing")):
            with self.assertRaises(m.MirrorError):
                m.select_models(records, all_models=opts[0], models=opts[1])

    def test_plan_known_sizes_and_revision(self):
        api = StubApi()
        p = m.plan(api, m.catalog(api))
        self.assertEqual(p["total_bytes"], 9)
        self.assertEqual(p["eligible"], 1)
        self.assertEqual(api.calls[1][2]["revision"], SHA)

    def test_unknown_file_size_blocks_without_guessing(self):
        api = StubApi(info=NS(id=ROW.id, sha=SHA, gated=False, tags=ROW.tags,
                              siblings=[NS(rfilename="model.safetensors", size=None)]))
        plan = m.plan(api, m.catalog(api))
        self.assertEqual(plan["blocked"], 1)
        self.assertEqual(plan["total_bytes"], 0)

    def test_no_download_without_explicit_yes(self):
        api = StubApi()
        plan = m.plan(api, m.catalog(api))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(m.MirrorError):
                m.sync_models(plan, Path(td), 1, yes=False, allow_partial=False,
                              snapshot_download=lambda **kwargs: self.fail("download should not run"))

    def test_budget_blocks_before_any_download(self):
        api = StubApi()
        plan = m.plan(api, m.catalog(api))
        plan["total_bytes"] = 2 * 10**9
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(m.MirrorError):
                m.sync_models(plan, Path(td), 1, yes=True, allow_partial=False,
                              snapshot_download=lambda **kwargs: self.fail("download should not run"))

    def test_offline_mirror_checksums(self):
        api = StubApi()
        plan = m.plan(api, m.catalog(api))
        with tempfile.TemporaryDirectory() as td:
            def fake_download(**kwargs):
                self.assertEqual(kwargs["revision"], SHA)
                self.assertFalse(kwargs["token"])
                self.assertEqual(kwargs["repo_id"], ROW.id)
                directory = Path(kwargs["local_dir"])
                (directory / "model.safetensors").write_bytes(b"demo")
                (directory / "README.md").write_bytes(b"hello")
            receipt = m.sync_models(plan, Path(td), 1, yes=True, allow_partial=False, snapshot_download=fake_download)
            self.assertEqual(receipt["results"][0]["status"], "mirrored-local")
            manifest = json.loads((Path(td) / ".manifests" / "gpt-oss-20b.json").read_text())
            self.assertEqual(manifest["revision"], SHA)
            self.assertEqual(manifest["files"][1]["sha256"], hashlib.sha256(b"demo").hexdigest())
            self.assertFalse(manifest["command_execution"])

    def test_rea_static_inspection_receipt(self):
        api = StubApi()
        plan = m.plan(api, m.catalog(api))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def fake_download(**kwargs):
                (Path(kwargs["local_dir"]) / "model.safetensors").write_bytes(b"demo")
            m.sync_models(plan, root, 1, yes=True, allow_partial=False, snapshot_download=fake_download)
            rea = root / "rea"
            rea.write_text("#!/usr/bin/env python3\nimport json,sys,pathlib\na=sys.argv\npathlib.Path(a[a.index('--evidence_output')+1]).write_text(json.dumps({'evidence':'offline'}))\nprint(json.dumps({'status':'fixture'}))\n")
            rea.chmod(0o700)
            report = m.inspect_with_rea(root, ROW.id, rea_bin=str(rea))
            self.assertEqual(report["status"], "rea-static-inspection")
            self.assertEqual(report["results"][0]["summary"]["status"], "fixture")
            self.assertTrue(Path(report["results"][0]["evidence_path"]).exists())

    def test_rea_rejects_tampered_weights(self):
        api = StubApi()
        plan = m.plan(api, m.catalog(api))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m.sync_models(plan, root, 1, yes=True, allow_partial=False, snapshot_download=lambda **kw: (Path(kw["local_dir"])/"model.safetensors").write_bytes(b"demo"))
            (root / ROW.id / "model.safetensors").write_bytes(b"BAD")
            rea = root / "rea"
            rea.write_text("stub")
            with self.assertRaises(m.MirrorError):
                m.inspect_with_rea(root, ROW.id, rea_bin=str(rea))

    def test_model_file_name_traversal_is_rejected(self):
        api = StubApi(info=NS(id=ROW.id, sha=SHA, gated=False, tags=ROW.tags,
                              siblings=[NS(rfilename="../model.safetensors", size=4)]))
        self.assertEqual(m.plan(api, m.catalog(api))["blocked"], 1)


if __name__ == "__main__":
    unittest.main()
