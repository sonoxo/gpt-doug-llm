"""Zero-paid-dependency contracts for expanded TAK-OS HTML/CSS/JS and local gateway."""
from html.parser import HTMLParser
from pathlib import Path
import json
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'docs'/'tak-os'

class Parse(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=set(); self.scripts=[]; self.styles=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='script' and a.get('src'):self.scripts.append(a['src'])
        if tag=='link' and a.get('rel')=='stylesheet':self.styles.append(a.get('href'))

class StaticContracts(unittest.TestCase):
    def test_local_assets(self):
        for path in ('index.html','app.js','bridge.js','styles.css','gateway.py','start.sh','Dockerfile','compose.yaml','sw.js','manifest.webmanifest','icon.svg','README.md','LEGACY_COMPATIBILITY.md','vm/README.md','vm/launch.sh'):
            with self.subTest(path=path):self.assertTrue((APP/path).is_file())

    def test_interactive_page_has_actual_controls(self):
        html=(APP/'index.html').read_text()
        parser=Parse();parser.feed(html)
        for element in ('view-map','view-system','view-feeds','view-events','view-ontology','view-settings','map-stage','map-markers','sim-play','cot-input','cot-validate','topology','events-list','vm-cpus','ontology-list','settings-tiles'):
            self.assertIn(element,parser.ids)
        self.assertEqual(parser.scripts,['./app.js','./bridge.js'])
        self.assertIn('./styles.css',parser.styles)
        self.assertIn('NOT TAK PRODUCT CENTER SOFTWARE',html)

    def test_original_app_is_integrated_not_a_mockup(self):
        js=(APP/'app.js').read_text()
        for functionality in ('function renderMap','function renderEvents','function advance','function validateCot','setGatewayUnits','setGatewayConnection','window.TAKOSApp'):
            self.assertIn(functionality,js)
        bridge=(APP/'bridge.js').read_text()
        for path in ('session','snapshot','cot','incident','ack','stream'):
            self.assertIn(path,bridge)
        self.assertIn('EventSource',bridge)

    def test_no_paid_runtime_or_sensitive_credentials(self):
        html=(APP/'index.html').read_text()
        self.assertNotIn('<script src="https://',html)
        self.assertNotIn('OPENAI_API_KEY',html)
        self.assertNotIn('sk-proj-',html)
        docker=(APP/'compose.yaml').read_text()
        self.assertIn('127.0.0.1:',docker)
        self.assertIn('read_only: true',docker)
        self.assertIn('no-new-privileges:true',docker)
        backend=(APP/'gateway.py').read_text()
        self.assertIn('"127.0.0.1"',backend)
        self.assertIn('realTakConnected',backend)
        self.assertIn('not a TAK Server', (APP/'LEGACY_COMPATIBILITY.md').read_text())

    def test_syntax_without_npm_or_pip(self):
        for name in ('app.js','bridge.js','sw.js'):
            with self.subTest(name=name):
                subprocess.run(['node','--check',str(APP/name)],check=True,capture_output=True)
        subprocess.run(['python3','-m','py_compile',str(APP/'gateway.py')],check=True,capture_output=True)

    def test_shell_launcher_syntax_and_busy_port_diagnostics(self):
        import os
        import socket
        subprocess.run(['sh', '-n', str(APP / 'start.sh')],
                       check=True, capture_output=True, timeout=5)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen(1)
            port = occupied.getsockname()[1]
            env = os.environ.copy()
            env['TAK_OS_PORT'] = str(port)
            outcome = subprocess.run(['sh', str(APP / 'start.sh'), 'web'],
                                     cwd=APP, env=env, capture_output=True,
                                     text=True, timeout=5)
            self.assertEqual(outcome.returncode, 3)
            self.assertIn('already in use', outcome.stderr)
            self.assertNotIn('Traceback', outcome.stderr)

    def test_pwa_cache_ignores_api(self):
        cache=(APP/'sw.js').read_text()
        self.assertIn("url.pathname.includes('/api/')",cache)
        self.assertIn('bridge.js',cache)
        self.assertEqual(json.loads((APP/'manifest.webmanifest').read_text())['scope'],'./')

if __name__=='__main__': unittest.main()
