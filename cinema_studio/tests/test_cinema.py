"""Functional end-to-end Cinema Studio: FFmpeg -> HTTP -> MP4/manifest -> persisted gallery."""
import base64
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen, Request

from cinema_studio import engine, server

PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/R9sAAAAASUVORK5CYII="
ROOT = Path(__file__).resolve().parents[2]


class RequestTests(unittest.TestCase):
    def test_governed_modes(self):
        for mode in ("motion", "image", "wan"):
            req = {"mode": mode, "prompt": "luminous reactor", "seconds": 2, "fps": 8}
            if mode == "image": req["image"] = "data:image/png;base64," + PNG
            if mode == "wan":
                with patch.object(engine, "status", return_value={"ai_ready": False}):
                    with self.assertRaises(engine.StudioError): engine.normalize_request(req)
            else:
                out = engine.normalize_request(req)
                self.assertEqual(out["mode"], mode)

    def test_refuses_bad_media(self):
        for uri in ("data:image/png;base64,%%%%", "data:image/png;base64," + base64.b64encode(b"not png content"*2).decode(),
                    "data:image/svg+xml;base64," + PNG):
            with self.assertRaises(engine.StudioError):
                engine.normalize_request({"mode":"image", "prompt":"hello", "image": uri})

    def test_rejects_limits_and_invalid_types(self):
        tests = [{"prompt": ""}, {"prompt": "x"*601}, {"prompt":"test", "seconds":False},
                 {"prompt":"test", "fps":30}, {"prompt":"test", "seed": -3},
                 {"prompt":"test", "storyboard":"\n".join("a" for _ in range(5))},
                 {"prompt":"test", "camera":"../../tmp"},
                 {"prompt":"test", "quality":"4k"},
                 {"prompt":"test", "mode":"wan", "storyboard":"one\ntwo"}]
        for case in tests:
            with self.subTest(case=case):
                with self.assertRaises(engine.StudioError):engine.normalize_request(case)

    def test_browser_assets_and_no_external_javascript(self):
        html = (ROOT/"cinema_studio/web/index.html").read_text()
        js = (ROOT/"cinema_studio/web/app.js").read_text()
        self.assertIn('id="studioForm"',html)
        self.assertIn('id="gallery"',html)
        self.assertIn('id="downloadVideo"',html)
        self.assertIn('"/api/jobs"',js)
        self.assertNotIn("eval(",js)
        self.assertNotIn('<script src="https://',html)

    def test_bootstrap_is_non_destructive(self):
        for name in ("bootstrap_mac.sh", "run_mac.sh", "install_ai_mac.sh"):
            path=ROOT/"cinema_studio"/name
            result=subprocess.run(["bash","-n",str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        content=(ROOT/"cinema_studio/bootstrap_mac.sh").read_text()
        self.assertNotIn("rm -rf",content)
        self.assertNotIn("sudo",content)
        self.assertIn("sparse-checkout",content)


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg required for actual output validation")
class FilmE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.store=server.Studio(Path(cls.tmp.name))
        cls.handler=type("CinemaTestHandler", (server.Handler,), {"studio": cls.store})
        cls.httpd=ThreadingHTTPServer(("127.0.0.1", 0), cls.handler)
        cls.httpd.daemon_threads=True
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=3)
        cls.tmp.cleanup()

    def _post(self, route, data, origin=None):
        request=Request(self.base+route,method="POST",data=json.dumps(data).encode("utf-8"),
                        headers={"Content-Type":"application/json", "Origin": origin or self.base})
        return urlopen(request, timeout=15)

    def _poll(self, jid, timeout=22):
        start=time.monotonic()
        while time.monotonic() - start < timeout:
            with urlopen(self.base+"/api/jobs/"+jid,timeout=5) as res:
                job=json.load(res)["job"]
            if job["status"] in {"completed","failed"}:return job
            time.sleep(.1)
        self.fail("Timed out waiting for local MP4")

    def _render(self,payload):
        with self._post("/api/jobs",payload) as res:
            self.assertEqual(res.status,202)
            jid=json.load(res)["job"]["id"]
        result=self._poll(jid)
        self.assertEqual(result["status"],"completed",result.get("error"))
        with urlopen(self.base+result["video"],timeout=8) as res:
            self.assertEqual(res.headers.get_content_type(),"video/mp4")
            video=res.read()
        self.assertGreater(len(video),1200)
        self.assertIn(b"ftyp",video[:64])
        with urlopen(self.base+result["manifest"],timeout=8) as res:
            meta=json.load(res)
        self.assertEqual(meta["schema"],"gpt-doug.cinema-studio.v1")
        self.assertEqual(meta["mode"],payload["mode"])
        return result,meta,video

    def test_01_health_and_public_assets(self):
        with urlopen(self.base+"/api/health") as res: status=json.load(res)
        self.assertTrue(status["ok"])
        self.assertTrue(status["renderer"]["ffmpeg"])
        self.assertTrue(status["renderer"]["no_paid_api"])
        for path,marker in (("/",b"CINEMA OS"),("/app.js",b"/api/jobs"),("/style.css",b".panel")):
            with urlopen(self.base+path) as res:self.assertIn(marker,res.read())

    def test_02_motion_mp4_and_ambient_sound(self):
        job,meta,video=self._render({"mode":"motion","prompt":"original cosmic reactor","camera":"dolly",
                                     "seconds":2,"fps":12,"quality":"draft","palette":"violet","sound":True})
        self.assertEqual(meta["audio"],"original minimal synth tone")
        self.assertIn("not a generative AI model",meta["model"])
        with tempfile.TemporaryDirectory() as folder:
            movie=Path(folder)/"movie.mp4";movie.write_bytes(video)
            proc=subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type","-of","json",str(movie)],capture_output=True,text=True)
            if shutil.which("ffprobe"):
                self.assertEqual(proc.returncode,0,proc.stderr)
                self.assertIn("audio",proc.stdout)

    def test_03_real_uploaded_image_mp4(self):
        job,meta,video=self._render({"mode":"image","prompt":"slow pan over reference", "image":"data:image/png;base64,"+PNG,
                                     "seconds":2,"fps":8,"quality":"draft","camera":"pan-left"})
        self.assertEqual(meta["mode"],"image")
        self.assertEqual(job["stage"],"MP4 ready")

    def test_04_storyboard_concat_and_catalog_persistence(self):
        job,meta,_=self._render({"mode":"motion","prompt":"refracted neon","storyboard":"opening\nclosing",
                                 "seconds":2,"fps":8,"quality":"draft"})
        self.assertEqual(len(meta["shots"]),2)
        recent=self.store.list()
        self.assertTrue(any(item["id"]==job["id"] for item in recent))
        restored=server.Studio(Path(self.tmp.name))
        self.assertTrue(any(item["id"]==job["id"] for item in restored.list()))

    def test_05_scope_origin_and_path_guards(self):
        with self.assertRaises(HTTPError) as err:self._post("/api/jobs",{"mode":"motion","prompt":"allowed"},origin="https://evil.example")
        self.assertEqual(err.exception.code,403)
        with self.assertRaises(HTTPError) as err:urlopen(self.base+"/api/assets/0000000000000000/../../etc/passwd")
        self.assertEqual(err.exception.code,404)
        with self.assertRaises(HTTPError) as err:self._post("/api/jobs",{"mode":"motion","prompt":""})
        self.assertEqual(err.exception.code,400)
        with self.assertRaises(HTTPError) as err:self._post("/api/jobs",{"mode":"wan","prompt":"cinema"})
        self.assertEqual(err.exception.code,400)


if __name__ == "__main__":unittest.main()
