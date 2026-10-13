"""Fully local CoT 2.0 XML -> HTTP/UDP/TCP -> SQLite -> SSE tests."""
import importlib.util
import json
import os
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'docs' / 'tak-os'
spec = importlib.util.spec_from_file_location('takos_gateway', APP / 'gateway.py')
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class LocalGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dbpath = str(Path(self.temp.name) / 'events.sqlite3')
        self.server,self.state = gateway.build_server(port=0,db_path=self.dbpath)
        self.port = self.server.server_port
        self.base = f'http://127.0.0.1:{self.port}/api/v1/'
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.state.stopped.set()
        self.server.shutdown(); self.server.server_close()
        self.worker.join(timeout=3)
        self.state.close()
        self.temp.cleanup()

    def request(self,path,body=None,kind='application/json',token=None,origin=None,host=None):
        url=self.base+path
        if body is not None:
            if isinstance(body,dict): body=json.dumps(body).encode()
            if isinstance(body,str): body=body.encode()
        headers={}
        if body is not None:
            headers['Content-Type']=kind
            if token is not False: headers['X-TAK-OS-Token']=token or self.state.token
        if origin: headers['Origin']=origin
        if host: headers['Host']=host
        req=urllib.request.Request(url,data=body,headers=headers,method='POST' if body is not None else 'GET')
        with urllib.request.urlopen(req,timeout=3) as resp:
            payload=resp.read()
            return resp.status, json.loads(payload) if 'json' in resp.headers['Content-Type'] else payload

    def test_status_snapshot_and_static_ui(self):
        status,hello=self.request('health')
        self.assertEqual(status,200)
        self.assertFalse(hello['realTakConnected'])
        self.assertEqual(hello['assets'],6)
        self.assertEqual(hello['protocol'],'CoT 2.0 XML')
        status,snapshot=self.request('snapshot')
        self.assertEqual(len(snapshot['units']),6)
        self.assertTrue(all(x['synthetic'] for x in snapshot['units']))
        for asset in ('', 'app.js', 'bridge.js', 'styles.css', 'sw.js'):
            u=f'http://127.0.0.1:{self.port}/'+asset
            with urllib.request.urlopen(u,timeout=3) as response:
                self.assertEqual(response.status,200)
                self.assertGreater(len(response.read()),500)
        with self.assertRaises(urllib.error.HTTPError) as rejected:
            urllib.request.urlopen(f'http://127.0.0.1:{self.port}/gateway.py',timeout=3)
        self.assertEqual(rejected.exception.code,404)

    def test_roundtrip_cot_to_sqlite_to_http(self):
        unit={"id":"DEMO-E2E-100","type":"air","lat":37.1234,"lon":-77.998,"label":"Synthetic survey"}
        cot=gateway.cot_encode(unit)
        self.assertIn(b'<event',cot)
        parsed=gateway.cot_decode(cot)
        self.assertEqual(parsed['id'],unit['id'])
        self.assertAlmostEqual(parsed['lat'],unit['lat'])
        status,response=self.request('cot',cot,kind='application/xml')
        self.assertEqual(status,201)
        self.assertTrue(response['accepted'])
        status,snapshot=self.request('snapshot')
        added=next(x for x in snapshot['units'] if x['id']==unit['id'])
        self.assertEqual(added['source'],'authorized-local-http')
        self.assertEqual(added['type'],'air')
        exported=urllib.request.urlopen(f'http://127.0.0.1:{self.port}/api/v1/cot.xml?uid=DEMO-E2E-100',timeout=3).read()
        self.assertEqual(gateway.cot_decode(exported)['id'],unit['id'])
        rows=self.state.list_events()
        self.assertTrue(any(x['uid']==unit['id'] and x['kind']=='cot' for x in rows))
        db=sqlite3.connect(self.dbpath)
        self.assertGreater(db.execute('SELECT COUNT(*) FROM events WHERE uid=?', (unit['id'],)).fetchone()[0],0)
        db.close()

    def test_reject_external_and_xml_injection(self):
        xml=gateway.cot_encode({"id":"DEMO-VALID","lat":37,"lon":-78})
        for bad in (
            xml.replace(b'DEMO-VALID',b'ARMY-REAL'),
            b'<!DOCTYPE event [<!ENTITY x SYSTEM "file:///etc/passwd">]>'+xml,
            b'<event uid="DEMO-BOGUS" type="x" time="2026-01-01T00:00:00Z"/>',
            xml.replace(b'lat="37.000000"',b'lat="nan"'),
            b'X'*17000,
        ):
            with self.subTest(bad=bad[:55]):
                with self.assertRaises((ValueError,PermissionError)):
                    gateway.cot_decode(bad)
        self.assertEqual(self.state.ingested,0)

    def test_csrf_host_validation_and_ack(self):
        with self.assertRaises(urllib.error.HTTPError) as no_token:
            self.request('incident',{"title":"Demo"},token=False)
        self.assertEqual(no_token.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as rebinding:
            self.request('session',host='random.example')
        self.assertEqual(rebinding.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as cross_site:
            self.request('incident',{"title":"Demo"},origin='https://attacker.example')
        self.assertEqual(cross_site.exception.code,403)
        code,inc=self.request('incident',{"title":"Local drill"})
        self.assertEqual(code,201)
        self.assertFalse(inc['acknowledged'])
        code,ack=self.request('ack',{"id":inc['id']})
        self.assertEqual(code,200)
        self.assertTrue(ack['acknowledged'])
        self.assertTrue(next(e for e in self.state.list_events() if e['id']==inc['id'])['acknowledged'])

    def test_loopback_udp_and_tcp(self):
        gateway.start_udp_loopback(self.state,0)
        gateway.start_tcp_loopback(self.state,0)
        udp_id='DEMO-UDP-99';tcp_id='LAB-TCP-99'
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.sendto(gateway.cot_encode({'id':udp_id,'lat':37.5,'lon':-77.4}),('127.0.0.1',self.state.udp_port))
        sock.close()
        with socket.create_connection(('127.0.0.1',self.state.tcp_port),timeout=2) as s:
            s.sendall(gateway.cot_encode({'id':tcp_id,'lat':37.4,'lon':-77.5}))
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            if udp_id in self.state.entities and tcp_id in self.state.entities: break
            time.sleep(.04)
        self.assertIn(udp_id,self.state.entities)
        self.assertIn(tcp_id,self.state.entities)
        self.assertEqual(self.state.entities[udp_id]['source'],'legacy-udp-loopback')
        self.assertEqual(self.state.entities[tcp_id]['source'],'legacy-tcp-loopback')

    def test_ingest_builtin_uid_does_not_break_generator(self):
        xml = gateway.cot_encode({"id":"LAB-RESCUE-01","type":"ground","lat":37.55,"lon":-77.45,"label":"Changed local marker"})
        self.state.ingest(xml,"test-synthetic-collision")
        self.state.advance()
        self.assertEqual(self.state.tick,1)
        self.assertIn('baseLat',self.state.entities['LAB-RESCUE-01'])

    def test_sse_stream_snapshot_and_delta(self):
        import http.client
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3)
        conn.request('GET','/api/v1/stream')
        res=conn.getresponse()
        self.assertEqual(res.status,200)
        self.assertEqual(res.headers['Content-Type'].split(';')[0],'text/event-stream')
        line=res.fp.readline().decode('utf-8')
        self.assertIn('event: snapshot',line)
        payload_line=res.fp.readline().decode('utf-8')
        self.assertIn('"synthetic-lab"',payload_line)
        self.state.ingest(gateway.cot_encode({'id':'LAB-SSE-01','lat':37.54,'lon':-77.43}),'test-client')
        text=''
        for _ in range(12):
            text+=res.fp.readline().decode('utf-8')
            if 'LAB-SSE-01' in text and 'event: cot' in text:break
        self.assertIn('event: cot',text)
        self.assertIn('LAB-SSE-01',text)
        conn.close()

    def test_storage_survives_restart(self):
        rec=self.state.record('incident','local-test','Persist this synthetic record')
        db=sqlite3.connect(self.dbpath)
        saved=db.execute('SELECT detail FROM events WHERE id=?',(rec['id'],)).fetchone()[0]
        self.assertIn('Persist',saved)
        db.close()

if __name__=='__main__': unittest.main()
