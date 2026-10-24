"""GPT-Shoggoth: bounded multi-agent ontology router with persistent tasks.

No unrestricted self-modification, external actions or biological control.
Standard library only; agents are named routing roles, not live LLM instances.
"""
import argparse
import datetime as dt
import hashlib
import json
import sqlite3
import uuid

AGENTS = {
 "gpt-doug-llm": {"domains": ["molecular","cellular","tissue","organ","organism","ecosystem","biochip","robotics"], "role":"orchestrator"},
 "gpt-doug-mlm": {"domains": ["molecular","cellular","tissue","organ","organism","ecosystem"], "role":"evidence_synthesis"},
 "gpt-biochip": {"domains": ["biochip","cellular","molecular"], "role":"digital_biochip"},
 "gpt-humanoid": {"domains": ["robotics","organism"], "role":"embodied_simulation"},
 "gpt-organoid": {"domains": ["cellular","tissue","organ"], "role":"literature_review"},
 "gpt-shoggoth": {"domains": ["molecular","cellular","tissue","organ","organism","ecosystem","biochip","robotics"], "role":"colony_router"},
}
DISALLOWED = ("execute_shell","operate_robot","run_wetlab","modify_system","send_network")
class Shoggoth:
 def __init__(self, path):
  self.db=sqlite3.connect(path)
  self.db.executescript("""
  CREATE TABLE IF NOT EXISTS shoggoth_tasks(
    id TEXT PRIMARY KEY, domain TEXT NOT NULL, question TEXT NOT NULL,
    assigned_to TEXT NOT NULL, status TEXT NOT NULL,
    evidence TEXT NOT NULL, created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS shoggoth_audit(
    id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
    digest TEXT NOT NULL, created_at TEXT NOT NULL);
  """)
  self.db.commit()
 def log(self, event):
  timestamp=dt.datetime.now(dt.timezone.utc).isoformat()
  digest=hashlib.sha256((event+timestamp).encode()).hexdigest()
  self.db.execute("INSERT INTO shoggoth_audit(event,digest,created_at) VALUES(?,?,?)",(event,digest,timestamp))
 def route(self, domain, question, evidence=None, action="review"):
  if action in DISALLOWED or action != "review":
   raise PermissionError("Shoggoth only routes advisory research questions")
  if not question.strip() or len(question)>4000:
   raise ValueError("Question must contain 1-4000 nonblank characters")
  candidates=[(name,agent) for name,agent in AGENTS.items()
      if domain in agent["domains"] and name not in ("gpt-shoggoth","gpt-doug-llm")]
  if not candidates: raise ValueError("Unknown or unroutable domain")
  chosen=sorted(candidates,key=lambda item:(len(item[1]["domains"]),item[0]))[0][0]
  tid=uuid.uuid4().hex
  evidence=evidence or []
  if not isinstance(evidence,list) or any(not isinstance(x,str) for x in evidence):
   raise ValueError("Evidence must be a list of source identifiers")
  status="awaiting_human_review" if evidence else "needs_evidence"
  now=dt.datetime.now(dt.timezone.utc).isoformat()
  with self.db:
   self.db.execute("INSERT INTO shoggoth_tasks VALUES(?,?,?,?,?,?,?)",
        (tid,domain,question,chosen,status,json.dumps(evidence),now))
   self.log("route:"+tid+":"+chosen)
  return {"task_id":tid,"agent":chosen,"domain":domain,"status":status,
          "evidence":evidence,"external_execution":False}
 def status(self):
  rows=self.db.execute("SELECT assigned_to,status,COUNT(*) FROM shoggoth_tasks GROUP BY assigned_to,status").fetchall()
  return {"system":"gpt-shoggoth","mode":"advisory_only","agents":AGENTS,
       "task_counts":[{"agent":a,"status":s,"count":n} for a,s,n in rows],
       "audit_events":self.db.execute("SELECT COUNT(*) FROM shoggoth_audit").fetchone()[0]}
 def close(self): self.db.close()

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--db",default="colony.sqlite3")
 sub=p.add_subparsers(dest="command",required=True)
 sub.add_parser("status")
 r=sub.add_parser("route")
 r.add_argument("--domain",required=True)
 r.add_argument("--question",required=True)
 r.add_argument("--evidence",action="append",default=[])
 a=p.parse_args()
 c=Shoggoth(a.db)
 try:
  output=c.status() if a.command=="status" else c.route(a.domain,a.question,a.evidence)
  print(json.dumps(output,indent=2))
 finally: c.close()
if __name__=="__main__": main()
