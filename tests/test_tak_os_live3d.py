"""Live public Cesium route: no false telemetry and no loosening of existing local gateways."""
from pathlib import Path
import importlib.util
import subprocess
import unittest
import threading
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'docs'/'tak-os'

spec=importlib.util.spec_from_file_location('live3d_local_gateway',APP/'gateway.py')
gateway=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

class Live3DRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server,cls.state=gateway.build_server(port=0)
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.state.stopped.set()
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)
        cls.state.close()
    def get(self,path):
        with urllib.request.urlopen(self.url+path,timeout=5) as response:
            return response.status,response.headers,response.read().decode('utf-8')
    def test_live_globe_route_and_external_csp(self):
        status,headers,page=self.get('/live-3d/')
        self.assertEqual(status,200)
        self.assertIn('REAL PUBLIC OBSERVATIONS',page)
        self.assertIn('https://cdn.jsdelivr.net',headers['Content-Security-Policy'])
        self.assertIn('https://earthquake.usgs.gov',headers['Content-Security-Policy'])
        self.assertIn('https://celestrak.org',headers['Content-Security-Policy'])
        for file in ('live-earth.js','ontology.js','style.css','cesium-config.js'):
            with self.subTest(file=file):
                code,_,body=self.get('/live-3d/'+file)
                self.assertEqual(code,200)
                self.assertGreater(len(body),110)
    def test_legacy_simulator_remains_restricted(self):
        _,headers,page=self.get('/')
        self.assertNotIn('https://cdn.jsdelivr.net',headers['Content-Security-Policy'])
        self.assertIn('LIVE EARTH 3D',page)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.get('/live-3d/../../gateway.py')
        self.assertEqual(error.exception.code,404)
    def test_real_only_launcher_and_static_server(self):
        import socket
        import os
        import time
        import subprocess
        subprocess.run(['sh','-n',str(APP/'live-3d/start-local.sh')],check=True,timeout=5)
        proc=subprocess.Popen(['sh',str(APP/'live-3d/start-local.sh')],cwd=APP/'live-3d',
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'PYTHONUNBUFFERED':'1'})
        try:
            line=proc.stdout.readline().decode('utf-8')
            address=proc.stdout.readline().decode('utf-8')
            self.assertIn('NO SYNTHETIC DATA',line)
            self.assertIn('127.0.0.1:',address)
            url=address.split('Open ')[1].split(' in your')[0]
            for _ in range(30):
                try:
                    with urllib.request.urlopen(url,timeout=1) as resp:
                        self.assertIn('LIVE EARTH 3D',resp.read().decode('utf-8'))
                    break
                except (OSError,urllib.error.URLError):
                    time.sleep(.05)
            else:
                self.fail('Real 3D local server did not become available')
        finally:
            proc.terminate()
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=2)
            proc.stdout.close();proc.stderr.close()

    def test_iphone_grid_routes_and_real_only_install(self):
        import json
        for filename in ('iphone-grid.js','iphone-grid.css','manifest.webmanifest','sw.js'):
            with self.subTest(file=filename):
                status, _, body=self.get('/live-3d/'+filename)
                self.assertEqual(status,200)
                self.assertGreater(len(body),100)
        _, _, manifest_text=self.get('/live-3d/manifest.webmanifest')
        manifest=json.loads(manifest_text)
        self.assertEqual(manifest['start_url'],'./')
        self.assertEqual(manifest['display'],'standalone')
        self.assertNotIn('synthetic',manifest['name'].lower())
        _, _, page=self.get('/live-3d/')
        self.assertIn('viewport-fit=cover',page)
        self.assertIn('iphone-grid-nav',page)
        self.assertIn('TAK SERVER: NOT CONNECTED',page)
        _, _, worker=self.get('/live-3d/sw.js')
        self.assertNotIn('earthquake.usgs.gov',worker)
        self.assertNotIn('/api/',worker)
        self.assertNotIn('gibs.earthdata.nasa.gov',worker)
        self.assertIn('ALLOWED',worker)

    def test_static_js_syntax_and_real_data_guards(self):
        for file in ('ontology.js','live-earth.js','cesium-config.js','iphone-grid.js','sw.js'):
            subprocess.run(['node','--check',str(APP/'live-3d'/file)],check=True,timeout=5)
        data=(APP/'live-3d/ontology.js').read_text()
        self.assertNotIn('sampleEvents',data)
        self.assertIn('validCoord',data)
        self.assertIn('invented building heights', (APP/'live-3d/README.md').read_text().lower())

if __name__=='__main__':unittest.main()
