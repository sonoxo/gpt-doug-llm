import tempfile
import unittest
from pathlib import Path

import hdd_swarm


class HDDSwarmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "code").mkdir()
        (self.root / "music").mkdir()
        (self.root / "code" / "app.py").write_text("print('ok')")
        (self.root / "music" / "song.wav").write_bytes(b"0" * 128)
        (self.root / "notes.md").write_text("notes")
        self.old_index = hdd_swarm.INDEX_FILE
        self.old_meta = hdd_swarm.META_FILE
        hdd_swarm.INDEX_FILE = self.root / "index.jsonl"
        hdd_swarm.META_FILE = self.root / "meta.json"

    def tearDown(self):
        hdd_swarm.INDEX_FILE = self.old_index
        hdd_swarm.META_FILE = self.old_meta
        self.tmp.cleanup()

    def test_index_and_search(self):
        out = hdd_swarm.build_index(self.root, lambda p: False, workers=4, max_files=100)
        self.assertEqual(out["indexed_files"], 3)
        self.assertFalse(out["content_read"])
        self.assertFalse(out["cloud_egress"])
        found = hdd_swarm.search_index("app.py")
        self.assertEqual(found["count"], 1)
        self.assertEqual(found["results"][0]["category"], "code")

    def test_summary(self):
        hdd_swarm.build_index(self.root, lambda p: False, workers=2, max_files=100)
        data = hdd_swarm.summary()
        self.assertEqual(data["summary"]["files"], 3)
        self.assertEqual(data["summary"]["categories"]["audio"], 1)

    def test_duplicate_candidates_are_metadata_only(self):
        (self.root / "copy").mkdir()
        (self.root / "copy" / "notes.md").write_text("notes")
        hdd_swarm.build_index(self.root, lambda p: False, workers=2, max_files=100)
        dupes = hdd_swarm.duplicate_candidates()
        self.assertGreaterEqual(dupes["count"], 1)
        self.assertIn("no content hashing", dupes["method"])


if __name__ == "__main__":
    unittest.main()
