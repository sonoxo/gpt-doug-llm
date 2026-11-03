"""Offline XUNIA Public Ecosystem Observatory validation."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"docs/ecosystem-observatory"
sys.path.insert(0,str(ROOT/"scripts"))
import scan_sonoxo_public_repos as scanner

class ObservatoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot=json.loads((SITE/"snapshot.json").read_text(encoding="utf-8"))
        cls.repos=cls.snapshot["repositories"]
        cls.html=(SITE/"index.html").read_text(encoding="utf-8")
        cls.js=(SITE/"app.js").read_text(encoding="utf-8")

    def test_inventory_public_only(self):
        self.assertEqual(self.snapshot["schema"],"xunia.public-repo-scan.v1")
        self.assertEqual(self.snapshot["owner"],"sonoxo")
        self.assertTrue(self.snapshot["coverage"]["paginationComplete"])
        self.assertEqual(self.snapshot["coverage"]["publicRepositories"],len(self.repos))
        self.assertGreaterEqual(len(self.repos),100)
        self.assertEqual(len({r["id"] for r in self.repos}),len(self.repos))
        for r in self.repos:
            self.assertTrue(r["id"].startswith("sonoxo/"))
            self.assertEqual(r["url"],"https://github.com/"+r["id"])
            self.assertIn(r["classificationBasis"],("museum catalog","name heuristic","unclassified"))
            self.assertIn(r["archived"],(True,False))
            self.assertNotIn("token",r)

    def test_classification_is_explicit(self):
        counts=self.snapshot["categories"]
        self.assertEqual(sum(counts.values()),len(self.repos))
        for r in self.repos:
            self.assertIn(r["category"],counts)
        self.assertEqual(len([r for r in self.repos if r["classificationBasis"]=="museum catalog"]),62)

    def test_core_projects_present(self):
        names={r["name"] for r in self.repos}
        for name in ("gpt-doug-llm","xuniadao","zyra","thegreenhouse","Sonoxomus"):
            self.assertIn(name,names)

    def test_visualization_assets_and_navigation(self):
        for name in ("index.html","app.js","style.css","snapshot.json"):
            self.assertTrue((SITE/name).is_file())
        for a in ('href="./style.css"','src="./app.js"','id="graph"','id="refreshBtn"','id="table"'):
            self.assertIn(a,self.html)
        self.assertIn("connect-src 'self' https://api.github.com",self.html)
        self.assertNotIn('src="https://',self.html)

    def test_no_external_code_execution(self):
        for forbidden in ("child_process","eval(","new Function(","/admin/secrets","Authorization: Bearer"):
            self.assertNotIn(forbidden,self.js)
        self.assertIn("https://api.github.com/users/sonoxo/repos?",self.js)
        self.assertIn('x.private===true',self.js)

    def test_museum_navigation(self):
        self.assertIn('href="./ecosystem-observatory/"',(ROOT/"docs/index.html").read_text(encoding="utf-8"))
        self.assertIn('href="../ecosystem-observatory/"',(ROOT/"docs/darkweb/index.html").read_text(encoding="utf-8"))
        items=json.loads((ROOT/"docs/resources.json").read_text(encoding="utf-8"))["items"]
        matches=[i for i in items if i.get("id")=="xunia-ecosystem-observatory"]
        self.assertEqual(len(matches),1)
        self.assertTrue(matches[0]["free"])
        self.assertEqual(matches[0]["url"],"./ecosystem-observatory/")

    def test_scanner_excludes_private(self):
        sample={"owner":{"login":"sonoxo"},"full_name":"sonoxo/example","name":"example","private":False,
                "visibility":"public","default_branch":"main","archived":False,"size":1}
        self.assertTrue(scanner.is_public_repo(sample))
        self.assertFalse(scanner.is_public_repo({**sample,"private":True,"visibility":"private"}))
        self.assertFalse(scanner.is_public_repo({**sample,"owner":{"login":"someone-else"}}))

    def test_scanner_preserves_curated_provenance(self):
        prev={"schema":"xunia.public-repo-scan.v1","repositories":[{"id":"sonoxo/example","category":"XUNIA Core & Products","classificationBasis":"museum catalog"}]}
        data=[{"owner":{"login":"sonoxo"},"full_name":"sonoxo/example","name":"example","private":False,"visibility":"public","default_branch":"main","archived":False,"size":1,"language":"Python"}]
        res=scanner.scan(prev,fetcher=lambda page:data if page==1 else [])
        self.assertEqual(len(res["repositories"]),1)
        self.assertEqual(res["repositories"][0]["category"],"XUNIA Core & Products")
        self.assertEqual(res["repositories"][0]["classificationBasis"],"museum catalog")

    def test_scanner_fails_closed(self):
        self.assertRaises(ValueError,scanner.scan,{"repositories":[]},lambda page:[])
        self.assertRaises(ValueError,scanner.page_url,9)

if __name__=="__main__":unittest.main()
