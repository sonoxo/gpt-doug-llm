"""XUNIA Open Web Atlas — offline safety and functional tests."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.robotparser import RobotFileParser

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import xunia_web_mirror as mirror

class MirrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site=ROOT/"docs/open-web-atlas"
        cls.seed=json.loads((cls.site/"seed-map.json").read_text(encoding="utf-8"))

    def test_safe_urls_and_query_redaction(self):
        host="example.org"
        self.assertEqual(mirror.normalize_url("https://example.org/a?token=secret#frag",host),"https://example.org/a")
        for url in ("http://example.org/","https://example.org:8443/","https://example.org.evil.org/",
                    "file:///etc/passwd","https://127.0.0.1/","https://example.org/login",
                    "https://example.org/file.zip","https://user:password@example.org/"):
            self.assertIsNone(mirror.normalize_url(url,host),url)

    def test_html_strips_script_and_forms(self):
        d=mirror.PageText()
        d.feed("<html><title>Public article</title><p>Allowed paragraph</p>"
               "<script>SECRET_TOKEN=42</script><form><input value='private'>secret fields</form>"
               "<a href='/next'>Another page</a></html>")
        self.assertEqual(d.title,"Public article")
        self.assertIn("Allowed paragraph",d.text())
        self.assertNotIn("SECRET_TOKEN",d.text())
        self.assertNotIn("secret fields",d.text())
        self.assertIn("/next",d.hrefs)

    def test_noindex_and_nofollow(self):
        d=mirror.PageText()
        d.feed("<meta name='robots' content='noindex, nofollow'><p>Not indexable</p>")
        self.assertTrue(d.noindex)
        self.assertTrue(d.nofollow)

    def test_robots_and_host_scope(self):
        root="https://example.org/"
        robots=RobotFileParser()
        robots.parse(["User-agent: *","Disallow: /blocked"])
        pages={
            root: b"<title>Home</title><p>Hello world</p><a href='/allowed'>Page</a>"
                  b"<a href='/blocked'>Blocked</a><a href='/noindex'>Hidden</a>"
                  b"<a href='https://external.example.net/'>Outside</a>",
            root+"allowed": b"<title>Allowed</title><p>Second text page</p><a href='/child'>Child</a>",
            root+"noindex": b"<meta name='robots' content='noindex'><title>Private index</title><p>No archive</p>",
            root+"child": b"<title>Child</title><p>End</p>"
        }
        def fake_fetch(url,host,timeout):
            return pages[url],url
        with patch.object(mirror.guard,"verified_addresses",return_value=True):
            data=mirror.mirror(root,"example.org",max_pages=10,max_depth=2,
                               delay=1,robots=robots,fetcher=fake_fetch,sleeper=lambda _:None)
        urls={p["url"] for p in data["pages"]}
        self.assertEqual(urls,{root,root+"allowed",root+"child"})
        self.assertNotIn(root+"noindex",urls)
        self.assertEqual(data["coverage"]["skipped"]["robots"],1)
        self.assertEqual(data["coverage"]["skipped"]["noindex"],1)
        self.assertTrue(data["policy"]["sameHostOnly"])
        self.assertFalse(data["coverage"]["completeInternet"])
        self.assertEqual(data["outboundDomains"][0]["host"],"external.example.net")
        self.assertEqual(len(data["edges"]),2)
        self.assertTrue(all("sha256" in p and "text" in p for p in data["pages"]))

    def test_maximum_bounds(self):
        with self.assertRaises(ValueError):
            mirror.mirror("https://example.org/","example.org",max_pages=51)
        with self.assertRaises(ValueError):
            mirror.mirror("https://example.org/","example.org",delay=0.1)

    def test_authorization_required(self):
        with self.assertRaises(SystemExit) as ex:
            mirror.main(["--base-url","https://example.org/","--allow-host","example.org"])
        self.assertEqual(ex.exception.code,2)

    def test_documented_preview_not_misrepresented(self):
        self.assertEqual(self.seed["schema"],mirror.SCHEMA)
        self.assertEqual(self.seed["mode"],"documented-route-preview")
        self.assertEqual(self.seed["coverage"]["pagesStored"],0)
        self.assertTrue(all(p["archived"] is False and p["text"]=="" for p in self.seed["pages"]))

    def test_frontend_and_navigation(self):
        for path in ("index.html","app.js","style.css","seed-map.json"):
            self.assertTrue((self.site/path).is_file())
        html=(self.site/"index.html").read_text(encoding="utf-8")
        js=(self.site/"app.js").read_text(encoding="utf-8")
        self.assertIn("connect-src 'self'",html)
        self.assertIn("id=\"graph\"",html)
        self.assertIn("snapshot.pages",js)
        self.assertNotIn("eval(",js)
        self.assertNotIn("<script src=\"https://",html)
        home=(ROOT/"docs/index.html").read_text(encoding="utf-8")
        self.assertIn('href="./open-web-atlas/"',home)
        resources=json.loads((ROOT/"docs/resources.json").read_text(encoding="utf-8"))["items"]
        matches=[x for x in resources if x["id"]=="xunia-open-web-atlas"]
        self.assertEqual(len(matches),1)
        self.assertTrue(matches[0]["free"])

if __name__=="__main__":unittest.main()
