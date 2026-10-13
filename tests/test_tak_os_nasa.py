"""No-network tests of the NASA and civil-satellite extension."""
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'docs'/'tak-os'

class Parser(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set();self.src=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get('id'):self.ids.add(attrs['id'])
        if tag=='script' and attrs.get('src'):self.src.append(attrs['src'])

class NASALayersContract(unittest.TestCase):
    def test_tabs_and_controls(self):
        html=(DIR/'index.html').read_text()
        parser=Parser();parser.feed(html)
        self.assertIn('data-view="nasa"',html)
        self.assertIn('nasa-layers.js',html)
        self.assertIn('nasa-layers.css',html)
        for key in ('view-nasa','nasa-source-status','nasa-imagery-select','nasa-date',
                    'nasa-imagery-toggle','nasa-events-toggle','nasa-opacity','nasa-open-map',
                    'nasa-load-feeds','nasa-stop-feeds','nasa-events-list','nasa-country-filter',
                    'nasa-mission-list','nasa-imagery-tiles','nasa-map-markers'):
            self.assertIn(key,parser.ids)
        self.assertEqual(parser.src[-1],'./nasa-layers.js')

    def test_official_public_sources_and_no_tracking(self):
        js=(DIR/'nasa-layers.js').read_text()
        for host in ('gibs.earthdata.nasa.gov','eonet.gsfc.nasa.gov','services.swpc.noaa.gov','space.oscar.wmo.int'):
            self.assertIn(host,js)
        for unsafe in ('Celestrak','Starlink live','TLE propagation','satellite tracking feed','weapons control','api.openai.com','remote shell','NASA_API_KEY'):
            self.assertNotIn(unsafe,js)
        self.assertIn('credentials:\'omit\'',js)
        self.assertIn('new AbortController()',js)
        self.assertIn('No automatic fetch',js)
        self.assertIn('Number.isFinite',js)
        self.assertIn('encodeURIComponent(id)',js)
        self.assertIn('eonet.gsfc.nasa.gov/api/v3/events?',js)
        self.assertIn('noaa-planetary-k-index.json',js)

    def test_csp_allowlist_and_host_lock(self):
        gateway=(DIR/'gateway.py').read_text()
        for endpoint in ('gibs.earthdata.nasa.gov','eonet.gsfc.nasa.gov','services.swpc.noaa.gov'):
            self.assertIn(endpoint,gateway)
        self.assertIn('"nasa-layers.js"',gateway)
        self.assertIn('"nasa-layers.css"',gateway)
        self.assertIn('localhost Host header required',gateway)
        self.assertIn('realTakConnected',gateway)

    def test_source_files_compile(self):
        subprocess.run(['node','--check',str(DIR/'nasa-layers.js')],check=True,timeout=10)
        subprocess.run(['python3','-m','py_compile',str(DIR/'gateway.py')],check=True,timeout=10)

    def test_service_worker_offline(self):
        script=(DIR/'sw.js').read_text()
        self.assertIn("'./nasa-layers.js'",script)
        self.assertIn("'./nasa-layers.css'",script)
        self.assertIn("url.pathname.includes('/api/')",script)
        self.assertNotIn('gibs.earthdata.nasa.gov',script)
        self.assertNotIn('eonet.gsfc.nasa.gov',script)

    def test_signed_off_sources_documented(self):
        doc=(DIR/'NASA_SATELLITE_README.md').read_text()
        for term in ('NASA EONET','NASA GIBS','NOAA SWPC','WMO OSCAR','China','Russia','Landsat'):
            self.assertIn(term,doc)
        self.assertIn('no nasa api key',doc.lower())

if __name__=='__main__':unittest.main()
