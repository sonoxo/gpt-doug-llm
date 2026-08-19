#!/usr/bin/env python3
"""Responsive local-only ZYRA terminal chat for GPT-DOUG-LLM."""
from __future__ import annotations
import json, os, subprocess, urllib.error, urllib.request
from pathlib import Path
from zyra import Zyra

ROOT = Path(__file__).resolve().parent
BASE_URL = os.environ.get('OLLAMA_BASE_URL','http://127.0.0.1:11434').rstrip('/')
REQUESTED_MODEL = os.environ.get('ZYRA_MODEL') or os.environ.get('OLLAMA_MODEL') or os.environ.get('GPT_DOUG_FAST_MODEL') or 'gpt-doug'
TIMEOUT = float(os.environ.get('ZYRA_TIMEOUT','90'))
MAX_TURNS = max(2,int(os.environ.get('ZYRA_MAX_TURNS','10')))
CONFIG_DIR = Path.home()/'.config'/'gpt-doug'
AUTOSTART_FLAG = CONFIG_DIR/'zyra-autostart'

SYSTEM = '''You are ZYRA, the responsive local conversational assistant for GPT-DOUG-LLM.
Answer ordinary user messages directly and naturally. Harmless fictional games and simulations are allowed.
Never reply with PASS or BLOCKED unless the deterministic local policy layer actually produced that status.
Do not claim background work, consciousness, government authority, or access you do not have.
The fleet means local agent/orchestration code in this repository, not a physical location.
Keep one user message to one bounded model response. No recursive self-calls or autonomous loops.
Be concise by default. For terminal questions, prefer one tested command or one short next step.
'''

def _request(path, body=None):
    data=None if body is None else json.dumps(body).encode()
    return urllib.request.Request(f'{BASE_URL}{path}',data=data,headers={'Accept':'application/json','Content-Type':'application/json'},method='GET' if body is None else 'POST')

def _json_request(path, body=None, timeout=None):
    with urllib.request.urlopen(_request(path,body),timeout=timeout or TIMEOUT) as r: return json.loads(r.read().decode())

def installed_models():
    return [x.get('name','') for x in _json_request('/api/tags',timeout=4).get('models',[]) if x.get('name')]

def choose_model(models):
    if not models: raise RuntimeError('No Ollama models are installed.')
    for wanted in (REQUESTED_MODEL,'gpt-doug','qwen2.5-coder','qwen2.5'):
        for name in models:
            if name==wanted or name.startswith(wanted+':'): return name
    return models[0]

def git_run(*args):
    try:
        r=subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,text=True,timeout=4)
        return r.returncode,(r.stdout.strip() or r.stderr.strip())
    except Exception: return 1,'unavailable'

def show_dashboard(model, mode):
    brc,b=git_run('branch','--show-current'); src,s=git_run('status','--short')
    changed=len([x for x in s.splitlines() if x.strip()]) if src==0 else '?'
    print('\n🟣 ZYRA // GPT-DOUG-LLM')
    print(f'🧠 Model: {model}')
    print(f'⚡ Mode: {mode.upper()}')
    print(f'🌿 Branch: {b if brc==0 and b else "unknown"}')
    print(f'📝 Working tree: {changed} changed')
    print(f'🚀 Default terminal: {"ON" if AUTOSTART_FLAG.exists() else "OFF"}')
    print('🛡️ Local streaming chat // bounded memory // no recursive loop')
    print('⌨️  /help /status /fleet /xunia /fast /balanced /default-on /default-off /clear /quit\n')

def show_fleet():
    agents=sorted(p.name for p in (ROOT/'agents').glob('*.py') if not p.name.startswith('__'))
    workers_dir=ROOT/'workers'; workers=sorted(p.name for p in workers_dir.rglob('*.py')) if workers_dir.exists() else []
    print(f'🤖 Fleet inventory: {len(agents)} agent modules + {len(workers)} worker modules')
    if agents: print('   agents:',', '.join(agents[:12]))
    if workers: print('   workers:',', '.join(workers[:12]))

def stream_chat(model,messages,mode):
    options={'temperature':0.25,'num_ctx':4096,'num_predict':256} if mode=='fast' else {'temperature':0.35,'num_ctx':8192,'num_predict':512}
    body={'model':model,'messages':messages,'stream':True,'keep_alive':'30m','options':options}
    chunks=[]; done_reason=''
    with urllib.request.urlopen(_request('/api/chat',body),timeout=TIMEOUT) as response:
        for raw in response:
            line=raw.decode(errors='replace').strip()
            if not line: continue
            event=json.loads(line)
            if event.get('error'): raise RuntimeError(str(event['error']))
            text=(event.get('message') or {}).get('content','')
            if text: print(text,end='',flush=True); chunks.append(text)
            if event.get('done'): done_reason=str(event.get('done_reason') or ''); break
    answer=''.join(chunks).strip()
    if not answer: raise RuntimeError(done_reason or 'empty model response')
    print(); return answer

def main():
    zyra=Zyra(); mode=os.environ.get('ZYRA_MODE','fast').lower(); mode=mode if mode in {'fast','balanced'} else 'fast'
    try: model=choose_model(installed_models())
    except Exception as exc:
        print(f'ZYRA OFFLINE // Ollama check failed: {exc}'); print('Start Ollama and confirm at least one local model is installed.'); return 1
    show_dashboard(model,mode)
    history=[{'role':'system','content':SYSTEM}]
    while True:
        try: prompt=input('ZYRA > ').strip()
        except (EOFError,KeyboardInterrupt): print('\nZYRA // session closed'); return 0
        if not prompt: continue
        command=prompt.lower()
        if command in {'/quit','/exit'}: return 0
        if command=='/help': print('/status /fleet /xunia /fast /balanced /default-on /default-off /clear /quit'); continue
        if command in {'/status','/xunia','/dashboard'}: show_dashboard(model,mode); continue
        if command=='/fleet': show_fleet(); continue
        if command=='/fast': mode='fast'; print('⚡ FAST mode enabled.'); continue
        if command=='/balanced': mode='balanced'; print('🧠 BALANCED mode enabled.'); continue
        if command=='/default-on': CONFIG_DIR.mkdir(parents=True,exist_ok=True); AUTOSTART_FLAG.touch(); print('🚀 ZYRA will open automatically in new interactive Terminal windows.'); continue
        if command=='/default-off': AUTOSTART_FLAG.unlink(missing_ok=True); print('🛑 ZYRA terminal autostart disabled.'); continue
        if command=='/clear': history=[{'role':'system','content':SYSTEM}]; print('🧹 Conversation memory cleared.'); continue
        verdict=zyra.inspect(prompt,'input')
        if not verdict.allowed: print('ZYRA BLOCKED // '+'; '.join(verdict.reasons)); continue
        history.append({'role':'user','content':verdict.text}); request_history=history[:1]+history[-(MAX_TURNS*2):]
        print('🧠 ZYRA thinking…',flush=True)
        try: answer=stream_chat(model,request_history,mode)
        except urllib.error.HTTPError as exc: print(f'ZYRA ERROR // Ollama HTTP {exc.code}'); continue
        except urllib.error.URLError: print('ZYRA ERROR // Ollama became unreachable'); continue
        except TimeoutError: print('ZYRA ERROR // model response timed out'); continue
        except Exception as exc: print(f'ZYRA ERROR // {type(exc).__name__}: {exc}'); continue
        output=zyra.inspect(answer,'output')
        if not output.allowed: print('ZYRA OUTPUT BLOCKED // '+'; '.join(output.reasons)); continue
        if output.text!=answer: print('ZYRA // output sanitized by policy')
        history.append({'role':'assistant','content':output.text})
if __name__=='__main__': raise SystemExit(main())
