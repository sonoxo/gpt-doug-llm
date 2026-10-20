"""Actual Git object-store tests: no external model or GitHub network required."""
from __future__ import annotations

import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from gpt_brain.recursive_repo import (
    RecursiveRepoModel,
    RepoAugmentedOntology,
    _chunks,
    _origin,
    main,
    sync_repo,
)


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


class RecursiveRepoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.db = Path(self.temp.name) / "index.sqlite"
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.org")
        git(self.root, "config", "user.name", "Test")
        git(self.root, "remote", "add", "origin", "https://github.com/sonoxo/gpt-doug-llm.git")
        (self.root / "pkg").mkdir()
        (self.root / "web").mkdir()
        (self.root / "README.md").write_text("my root quantum wonderland project\n", encoding="utf-8")
        (self.root / "pkg" / "util.py").write_text(
            "def recursive_ontology():\n    return 'red panda'\n", encoding="utf-8"
        )
        (self.root / "pkg" / "use.py").write_text(
            "from pkg import util\n\ndef f():\n    return util.recursive_ontology()\n",
            encoding="utf-8",
        )
        (self.root / "web" / "module.ts").write_text(
            "export const TRACER = 'science';\n", encoding="utf-8"
        )
        (self.root / "web" / "index.ts").write_text(
            "import { TRACER } from './module';\n", encoding="utf-8"
        )
        (self.root / "asset.bin").write_bytes(bytes(range(256)))
        (self.root / "secret.env").write_text(
            "token=abcdefghijklmnopabcdefghijklmnop\n", encoding="utf-8"
        )
        (self.root / "linked").symlink_to("README.md")
        git(self.root, "add", ".")
        git(
            self.root, "update-index", "--add", "--cacheinfo",
            "160000," + "a" * 40 + ",vendor/linked",
        )
        git(self.root, "commit", "-qm", "initial")
        self.commit = git(self.root, "rev-parse", "HEAD").decode().strip()

    def index(self):
        result = sync_repo(self.root, self.db)
        return result, RecursiveRepoModel(self.db)

    def test_complete_git_tree_all_object_types(self):
        result, model = self.index()
        self.assertTrue(result["complete"])
        self.assertEqual(int(result["tracked_count"]), 9)
        self.assertEqual(result["submodule_count"], 1)
        self.assertEqual(result["file_count"], 8)
        self.assertEqual(result["binary_count"], 1)
        self.assertEqual(result["protected_count"], 1)
        self.assertEqual(model.verify(self.root)["tracked_count"], 9)
        self.assertEqual(model.metadata()["commit"], self.commit)
        self.assertEqual(model.stored_file("asset.bin", allow_protected=True), bytes(range(256)))
        self.assertEqual(model.stored_file("linked", allow_protected=True), b"README.md")
        with self.assertRaises(ValueError):
            model.stored_file("vendor/linked", allow_protected=True)
        self.assertEqual(model.stats()["submodules"], 1)

    def test_real_recursive_tree_directory_and_import_links(self):
        _, model = self.index()
        root_children = model.children(".")
        self.assertIn("pkg", [n["path"] for n in root_children["entries"]])
        self.assertEqual(model.imports("pkg/use.py"), ["pkg/util.py"])
        self.assertEqual(model.imports("web/index.ts"), ["web/module.ts"])
        self.assertIn("pkg/use.py", [n["path"] for n in model.walk(depth=2)["entries"]])

    def test_queries_are_provenance_pinned(self):
        _, model = self.index()
        hits = model.search("recursive_ontology")
        self.assertTrue(hits)
        self.assertTrue(any("pkg/util.py" in row["path"] for row in hits))
        self.assertIn("https://github.com/sonoxo/gpt-doug-llm/blob/", hits[0]["source"])
        self.assertIn(self.commit, hits[0]["source"])
        packet = model.context("recursive_ontology", max_chars=280)
        self.assertTrue(packet["matches"])
        self.assertIn("Untrusted", packet["boundary"])

    def test_secrets_in_snapshot_not_retrieval(self):
        _, model = self.index()
        self.assertEqual(model.search("abcdefghijklmnopabcdefghijklmnop"), [])
        with self.assertRaises(PermissionError):
            model.stored_file("secret.env")
        self.assertIn(b"token=", model.stored_file("secret.env", allow_protected=True))

    def test_frozen_commit_even_when_checkout_is_dirty(self):
        _, model = self.index()
        (self.root / "pkg" / "util.py").write_text("changed but not committed\n")
        (self.root / "untracked.txt").write_text("not stored\n")
        self.assertIn(b"recursive_ontology", model.stored_file("pkg/util.py"))
        self.assertFalse(model.search("changed but not committed"))
        self.assertFalse(any(row["path"] == "untracked.txt" for row in model.children(".")["entries"]))
        self.assertTrue(model.verify(self.root)["ok"])

    def test_reindex_updates_commit_and_is_atomic_on_failure(self):
        _, model = self.index()
        (self.root / "README.md").write_text("new revision raspberry logic\n")
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-qm", "revision")
        with self.assertRaises(ValueError):
            sync_repo(self.root, self.db, max_blob_bytes=1, max_total_bytes=2)
        self.assertEqual(model.metadata()["commit"], self.commit)
        result = sync_repo(self.root, self.db)
        self.assertNotEqual(result["commit"], self.commit)
        self.assertTrue(RecursiveRepoModel(self.db).search("raspberry"))
        self.assertTrue(RecursiveRepoModel(self.db).verify(self.root)["ok"])

    def test_invalid_repo_ref_and_destination_fail_closed(self):
        with self.assertRaises(ValueError):
            sync_repo(self.root, self.root / "temp.sqlite")
        with self.assertRaises(ValueError):
            sync_repo(self.root, self.db, ref="--output=/tmp/evil")

    def test_search_special_characters_are_inert(self):
        _, model = self.index()
        for query in ["' OR 1=1 --", 'recursive_ontology" OR NOT', ";DROP TABLE chunks;"]:
            model.search(query)
        self.assertTrue(model.verify()["ok"])

    def test_path_protection_and_missing(self):
        _, model = self.index()
        with self.assertRaises(PermissionError):
            model.stored_file("asset.bin")
        with self.assertRaises(ValueError):
            model.children("secret.env")
        with self.assertRaises(ValueError):
            model.stored_file("missing.py")
        with self.assertRaises(ValueError):
            model.context("model", max_chars=10)

    def test_corrupted_blob_fails_integrity_verification(self):
        _, model = self.index()
        db = sqlite3.connect(self.db)
        try:
            db.execute(
                "UPDATE blobs SET sha256='bad' "
                "WHERE oid=(SELECT oid FROM nodes WHERE path='README.md')"
            )
            db.commit()
        finally:
            db.close()
        with self.assertRaises(ValueError):
            model.verify()

    def test_external_cli(self):
        self.assertEqual(main(["index", "--repo", str(self.root), "--db", str(self.db)]), 0)
        self.assertEqual(main(["verify", "--db", str(self.db), "--repo", str(self.root)]), 0)
        self.assertEqual(main(["query", "recursive_ontology", "--db", str(self.db)]), 0)

    def test_secret_names_from_git_are_stored_but_not_searchable(self):
        (self.root / ".env.production").write_text("hostname=my-service\n")
        git(self.root, "add", ".env.production")
        git(self.root, "commit", "-qm", "add protected")
        _, model = self.index()
        self.assertFalse(model.search("hostname"))
        with self.assertRaises(PermissionError):
            model.stored_file(".env.production")

    def test_checkout_is_not_necessary_for_git_objects(self):
        self.index()
        (self.root / "README.md").unlink()
        self.assertTrue(RecursiveRepoModel(self.db).search("quantum"))
        self.assertTrue(RecursiveRepoModel(self.db).verify(self.root)["ok"])

    def test_chunk_ranges_for_long_lines(self):
        chunks = list(_chunks("first\n" + "a" * 3000 + "\nthird"))
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0][0], 1)
        self.assertEqual(chunks[-1][1], 3)

    def test_brain_ontology_adapter_preserves_existing_ontology(self):
        _, model = self.index()

        class Base:
            def search(self, query, limit):
                return [{"path": "$.ontology", "value": "existing facts", "score": 1.0}][:limit]

        hits = RepoAugmentedOntology(model, base=Base()).search("recursive_ontology", limit=4)
        self.assertEqual(hits[0]["path"], "$.ontology")
        self.assertTrue(any(h["path"].startswith("repo-source:https://github.com/") for h in hits))
        self.assertTrue(any(
            h.get("value", {}).get("classification") == "UNTRUSTED_REPOSITORY_TEXT_DATA_ONLY"
            for h in hits if isinstance(h["value"], dict)
        ))

    def test_manifest_path_tampering_fails_verification(self):
        _, model = self.index()
        db = sqlite3.connect(self.db)
        try:
            db.execute("UPDATE nodes SET path='fake.py' WHERE path='README.md'")
            db.commit()
        finally:
            db.close()
        with self.assertRaises(ValueError):
            model.verify()

    def test_lfs_pointer_is_preserved_but_not_exposed(self):
        (self.root / "large-video.bin").write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:" + "b" * 64 + "\nsize 123456\n"
        )
        git(self.root, "add", "large-video.bin")
        git(self.root, "commit", "-qm", "lfs pointer")
        result, model = self.index()
        self.assertEqual(result["lfs_pointer_count"], 1)
        self.assertTrue(model.verify(self.root)["ok"])
        with self.assertRaises(PermissionError):
            model.stored_file("large-video.bin")

    def test_origin_normalization(self):
        self.assertEqual(_origin(self.root), "sonoxo/gpt-doug-llm")


if __name__ == "__main__":
    unittest.main()
