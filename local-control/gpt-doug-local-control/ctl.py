#!/usr/bin/env python3
import json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN = (ROOT/'runtime'/'token.txt').read_text().strip() if (ROOT/'runtime'/'token.txt').exists() else ''
BASE='http://127.0.0.1:8765'

def post(path, body):
    req=urllib.request.Request(BASE+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+TOKEN,'Host':'127.0.0.1:8765'},method='POST')
    with urllib.request.urlopen(req) as r: print(r.read().decode())

cmd = sys.argv[1] if len(sys.argv)>1 else 'status'
if cmd=='status':
    req=urllib.request.Request(BASE+'/status',headers={'Host':'127.0.0.1:8765'})
    print(urllib.request.urlopen(req).read().decode())
elif cmd=='arm': post('/arm',{'seconds':300})
elif cmd=='disarm': post('/disarm',{})
elif cmd=='panic': post('/panic',{})
elif cmd=='clear-panic': post('/clear-panic',{})
elif cmd=='exec': post('/execute', json.loads(sys.argv[2]))
else: raise SystemExit('usage: ctl.py status|arm|disarm|panic|clear-panic|exec <json>')
