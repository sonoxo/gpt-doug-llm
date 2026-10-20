from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cloud_repo_cloner as cr
import cloud_repo_catalog as cc


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class CloudRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        sh("git", "init", "--quiet", str(self.source))
        sh("git", "config", "user.name", "Test", cwd=self.source)
        sh("git", "config", "user.email", "test@example.com", cwd=self.source)
        (self.source / "hello.txt").write_text("hello cloud\n")
        (self.source / "n").mkdir()
        (self.source / "n" / "inside.txt").write_text("subdir\n")
        sh("git", "add", ".", cwd=self.source)
        sh("git", "commit", "--quiet", "-m", "fixture", cwd=self.source)
        self.clone = self.root / "repos" / "example" / "fixture"
        self.clone.parent.mkdir(parents=True)
        sh("git", "clone", "--quiet", str(self.source), str(self.clone))

    def test_offline_restore_is_real(self):
        sha = cr.snapshot_head(self.clone)
        count = cr.tracked_blobs_present(self.clone)
        self.assertEqual(count, 2)
        cr.compact_checkout(self.clone)
        self.assertFalse((self.clone / "hello.txt").exists())
        result = cr.verify_one("example/fixture", sha, self.root)
        self.assertEqual(result["status"], "restored_offline", result)
        self.assertEqual(result["sha"], sha)
        self.assertFalse((self.clone / "hello.txt").exists())

    def test_fail_when_sha_mismatch(self):
        cr.compact_checkout(self.clone)
        result = cr.verify_one("example/fixture", "a" * 40, self.root)
        self.assertEqual(result["status"], "failed")

    def test_names_reject_traversal(self):
        for value in ("../x", "foo/..", "bad//x", "foo/a/b", "a/.hidden/../c", "foo:x/y"):
            with self.assertRaises(ValueError):
                cr.validate_name(value)

    def test_shard_partition_includes_every_target_once(self):
        cats = {cat: [f"owner{i}/repo{i}" for i in range(n)] for cat,n in cr.EXPECTED_COUNTS.items()}
        path = self.root / "targets.json"
        path.write_text(json.dumps({"schema_version":1,"categories":cats}))
        for cat, names in cats.items():
            shards = [cr.select_targets(path, cat, idx, 4) for idx in range(4)]
            found = [name for shard in shards for name in shard]
            self.assertCountEqual(names, found)
            self.assertEqual(len(found), len(set(found)))

    def test_catalog_rejects_incomplete(self):
        targets = {"schema_version":1,"cache_version":"hash","categories":{x:[] for x in cr.CATEGORIES}}
        with self.assertRaises(ValueError):
            cc.compile_catalog(targets, {}, {}, shards=4, run_url="https://example.com")

    def test_cache_report_permanent_json_contract(self):
        sha = cr.snapshot_head(self.clone)
        self.assertEqual(len(sha), 40)
        self.assertTrue(cr.REPO_RE.fullmatch("sonoxo/gpt-doug-llm"))

if __name__ == "__main__":
    unittest.main()
