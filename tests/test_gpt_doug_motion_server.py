"""Offline localhost studio security and functional tests."""
from __future__ import annotations

from http.server import HTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from open_video_model import studio


class MotionStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server = HTTPServer(("127.0.0.1", 0), studio.MotionHandler)
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.output_patch = patch.object(studio, "OUTPUT_DIR", Path(cls.tmp.name)/"renders")
        cls.output_patch.start()
        cls.checkpoint_patch = patch.object(studio, "DEFAULT_CHECKPOINT", Path(cls.tmp.name)/"missing-weights.pt")
        cls.checkpoint_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()
        cls.output_patch.stop()
        cls.checkpoint_patch.stop()
        cls.tmp.cleanup()

    def post(self,path,payload,headers=None):
        request=Request(self.base+path,data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type":"application/json",**(headers or {})},method="POST")
        return urlopen(request,timeout=15)

    def test_health_no_fake_checkpoint(self):
        with urlopen(self.base+"/api/health",timeout=5) as res:
            status=json.load(res)
        self.assertTrue(status["ok"] and status["local"])
        self.assertFalse(status["trained_checkpoint_present"])
        self.assertTrue(status["generation_requires_training"])

    def test_frontend_assets_served(self):
        for path, marker in (("/",b"MOTION-1"),("/app.js",b"api/preview"),("/style.css",b".hero")):
            with urlopen(self.base+path,timeout=5) as res:
                self.assertIn(marker,res.read())
                self.assertIsNone(res.headers.get("Access-Control-Allow-Origin"))

    def test_neural_generation_refuses_untrained_checkpoint(self):
        with self.assertRaises(HTTPError) as e:
            self.post("/api/generate",{"prompt":"a square moving left","seed":9,"fps":8})
        self.assertEqual(e.exception.code,409)

    def test_procedural_preview_works_and_serves_real_gif(self):
        with self.post("/api/preview",{"prompt":"blue square moving right","seed":2,"fps":8}) as res:
            data=json.load(res)
        self.assertTrue(data["preview_not_ml"])
        self.assertRegex(data["url"],r"^/renders/motion1-[0-9a-f]{16}\.gif$")
        with urlopen(self.base+data["url"],timeout=5) as res:
            self.assertEqual(res.headers.get_content_type(),"image/gif")
            self.assertTrue(res.read().startswith(b"GIF8"))

    def test_foreign_origin_cannot_post(self):
        with self.assertRaises(HTTPError) as err:
            self.post("/api/preview",{"prompt":"red circle"},headers={"Origin":"https://evil.example"})
        self.assertEqual(err.exception.code,403)

    def test_unknown_route_and_traversal_refused(self):
        for path in ("/renders/../private.gif","/api/secrets","/unknown"):
            with self.assertRaises(HTTPError) as e:
                urlopen(self.base+path,timeout=5)
            self.assertEqual(e.exception.code,404)

    def test_request_validation(self):
        for payload in ({"prompt":""},{"prompt":"x"*401},{"prompt":"hello","seed":True},{"prompt":"hello","fps":100}):
            with self.assertRaises(HTTPError) as e:
                self.post("/api/preview",payload)
            self.assertEqual(e.exception.code,400)


if __name__=="__main__":
    unittest.main()
