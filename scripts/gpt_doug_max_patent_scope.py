#!/usr/bin/env python3
"""Structured patent-scope library for GPT-DOUG-MAX.

Engineering research index only: not claim construction or legal advice.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATENT_DIR = ROOT / "safety-shield" / "agents" / "knowledge" / "patents"
SUPPORTED_SCHEMA = "xunia.patent-robotics.seed.v1"

def load_seed(path: Path) -> dict:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: raise SystemExit(f"NO-GO: cannot load {path}: {exc}") from exc
    if not isinstance(value, dict): raise SystemExit(f"NO-GO: patent seed must be object: {path}")
    return value

def seeds():
    rows=[]
    for path in sorted(PATENT_DIR.glob("*.json")) if PATENT_DIR.exists() else []:
        value=load_seed(path)
        if value.get("schema")==SUPPORTED_SCHEMA: rows.append((path,value))
    return rows

def norm(text): return re.sub(r"[^a-z0-9]+"," ",str(text).lower()).strip()
def toks(text): return {x for x in norm(text).split() if len(x)>=3}

def scope_terms(seed):
    out=[]
    for key in ("scope_tags","publicly_described_functional_concepts","classification_signals"):
        if isinstance(seed.get(key),list): out += [str(x) for x in seed[key]]
    model=seed.get("scope_model",{})
    if isinstance(model,dict):
        for v in model.values(): out += [str(x) for x in v] if isinstance(v,list) else ([str(v)] if isinstance(v,str) else [])
    return out

def score(seed, query):
    qn,qt=norm(query),toks(query); points=0; hits=[]
    title=str(seed.get("title",""))
    if title and norm(title) in qn: points+=20; hits.append("title:"+title)
    for tag in seed.get("scope_tags",[]):
        p=norm(tag); pt=toks(p); overlap=pt & qt
        if p and p in qn: points+=8; hits.append(str(tag))
        elif overlap: points += 2*len(overlap); hits.append(str(tag))
    for term in scope_terms(seed):
        overlap=toks(term)&qt
        if overlap: points += min(4,len(overlap)); hits.append(term)
    return points,list(dict.fromkeys(hits))

def validate(path, seed):
    errors=[]
    for key in ("patent_id","title","source_provenance","scope_tags","scope_model","independent_design_policy"):
        if not seed.get(key): errors.append(f"{path.name}: missing {key}")
    policy=seed.get("independent_design_policy",{})
    expected={"copy_claim_language":False,"copy_figures_or_drawings":False,"assert_freedom_to_operate":False,"claim_element_mapping_requires_human_review":True,"commercial_release_requires_patent_counsel_review":True}
    for k,v in expected.items():
        if policy.get(k) is not v: errors.append(f"{path.name}: {k} must be {v!r}")
    return errors

def status():
    rows=seeds(); print("GPT-DOUG-MAX // PATENT SCOPE LIBRARY"); print("Seeds ............",len(rows)); print("Mode ............. PUBLIC_PRIOR_ART_SCOPE_INDEX"); print("Claim construction HUMAN REVIEW REQUIRED"); print("FTO opinion ...... DISABLED"); return 0 if rows else 1

def list_cmd(as_json=False):
    data=[{"patent_id":s.get("patent_id"),"title":s.get("title"),"scope_tags":s.get("scope_tags",[]),"path":str(p.relative_to(ROOT))} for p,s in seeds()]
    if as_json: print(json.dumps(data,indent=2,sort_keys=True))
    else:
        for x in data: print(f"{x['patent_id']} // {x['title']}\n  scopes: "+", ".join(x['scope_tags']))
    return 0

def show(pid):
    for p,s in seeds():
        if str(s.get("patent_id","")).upper()==pid.upper(): print(json.dumps({"path":str(p.relative_to(ROOT)),**s},indent=2,sort_keys=True)); return 0
    raise SystemExit(f"NO-GO: patent not found: {pid}")

def match(query, top, as_json=False):
    data=[]
    for p,s in seeds():
        pts,hits=score(s,query); data.append({"score":pts,"patent_id":s.get("patent_id"),"title":s.get("title"),"matched_scope_signals":hits,"scope_tags":s.get("scope_tags",[]),"path":str(p.relative_to(ROOT))})
    data.sort(key=lambda x:(-x["score"],str(x["patent_id"]))); data=data[:max(1,top)]
    if as_json: print(json.dumps({"query":query,"results":data},indent=2,sort_keys=True))
    else:
        for x in data: print(f"{x['score']:>3}  {x['patent_id']} // {x['title']}")
        print("Research ranking only; claim scope/legal status require human review.")
    return 0

def doctor():
    rows=seeds(); errors=[]; ids=set()
    for p,s in rows:
        pid=str(s.get("patent_id","")); errors += ([f"duplicate patent_id: {pid}"] if pid in ids else []); ids.add(pid); errors += validate(p,s)
    if len(rows)<2: errors.append("expected at least two patent scope seeds")
    if errors:
        print("PATENT SCOPE DOCTOR: NO-GO"); [print(" -",e) for e in errors]; return 1
    print("PATENT SCOPE DOCTOR: GREEN"); print("Seeds ............",len(rows)); print("Unique IDs .......",len(ids)); print("Independent design ENFORCED"); return 0

def main():
    p=argparse.ArgumentParser(prog="doug-max patent-scope"); sp=p.add_subparsers(dest="command"); sp.add_parser("status"); lp=sp.add_parser("list"); lp.add_argument("--json",action="store_true"); sh=sp.add_parser("show"); sh.add_argument("patent_id"); mt=sp.add_parser("match"); mt.add_argument("query"); mt.add_argument("--top",type=int,default=5); mt.add_argument("--json",action="store_true"); sp.add_parser("doctor"); a=p.parse_args(); c=a.command or "status"
    return status() if c=="status" else list_cmd(a.json) if c=="list" else show(a.patent_id) if c=="show" else match(a.query,a.top,a.json) if c=="match" else doctor() if c=="doctor" else 2

if __name__=="__main__": raise SystemExit(main())
