import unittest

from shaggoth_swarm.catalogs.open_source_everything import build_index, parse_catalog, search_index


SAMPLE = """
<div><h1><img src="x"> AI Tools &amp; Services </h1></div>
<div><h3>AI Chatbots</h3></div>
<table><tr><td><a href="https://example.test/ollama">Ollama</a></td></tr></table>
<div><h1>Security &amp; Privacy</h1></div>
<div><h3>Password Managers</h3></div>
<table><tr><td><a href="https://example.test/keepassxc">KeePassXC</a></td></tr></table>
<div><h1>Mirrors</h1></div>
<a href="https://example.test/not-a-tool">Mirror</a>
"""


class OpenSourceEverythingTests(unittest.TestCase):
    def test_parses_supported_sections_only(self):
        entries = parse_catalog(SAMPLE)
        self.assertEqual([entry.name for entry in entries], ["Ollama", "KeePassXC"])
        self.assertEqual(entries[0].section, "AI Tools & Services")
        self.assertEqual(entries[1].subsection, "Password Managers")

    def test_index_keeps_provenance(self):
        index = build_index(SAMPLE)
        self.assertEqual(index["source"]["license"], "GPL-3.0")
        self.assertEqual(index["source"]["repository"], "An-anonymous-coder/Open-Source-Everything")
        self.assertEqual(index["entry_count"], 2)

    def test_search_matches_name_and_category(self):
        index = build_index(SAMPLE)
        by_name = search_index(index, "Ollama")
        by_category = search_index(index, "Security Privacy")
        self.assertEqual(by_name[0]["name"], "Ollama")
        self.assertEqual(by_category[0]["name"], "KeePassXC")

    def test_search_limit_is_bounded(self):
        index = build_index(SAMPLE)
        with self.assertRaises(ValueError):
            search_index(index, "test", limit=101)


if __name__ == "__main__":
    unittest.main()
