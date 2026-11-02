#!/usr/bin/env python3
"""Glass Onion source-reference controller. Python stdlib only; NEVER execute or clone sources."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

CATALOG=Path(__file__).resolve().parents[1]/"catalog/glass-onion-15.json"
GITHUB=re.compile(r"^https://github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GITLAB="https://gitlab.com/exploit-database/exploitdb"
GATES={"allowExecution":False,"allowAutoCloning":False,"allowCredentialCollection":False,"allowTargetScanning":False,"allowPayloadDeployment":False,"requireHumanReviewForSourceImport":True,"requireLicenseReview":True}

def load(path=CATALOG):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def validate(data):
    if data.get("schemaVersion")!="1.0.0": raise ValueError("Invalid schema")
    source=data.get("source",{})
    if source.get("videoId")!="rmkXyB6JBX8" or source.get("speakerClaimsIndependentlyVerified") is not False: raise ValueError("Unverified media gate failed")
    slots=data.get("slots",[])
    if len(slots)!=15 or sorted(s["rank"] for s in slots)!=list(range(1,16)): raise ValueError("Require 15 uniquely ranked slots")
    if len({s["id"] for s in slots})!=15: raise ValueError("Duplicate identifiers")
    if data.get("policies",{}).get("readOnlyEvidence") is not True: raise ValueError("Evidence must be read-only")
    all_urls=[]
    for slot in slots:
        if slot.get("status")!="reference_only": raise ValueError("Execution prohibited")
        if any(slot.get("policy",{}).get(k) is not v for k,v in GATES.items()): raise ValueError("Policy gate failed: "+slot["id"])
        if not slot.get("selectedRepos"): raise ValueError("Missing upstream reference")
        for repo in slot["selectedRepos"]:
            url=repo["url"]
            if not (GITHUB.fullmatch(url) or url==GITLAB): raise ValueError("Untrusted source URL")
            if repo.get("licenseReviewRequired") is not True: raise ValueError("License gate failed")
            all_urls.append(url)
    if len(all_urls)!=16 or len(set(all_urls))!=16: raise ValueError("Require 16 unique repo URLs")
    return {"slots":15,"sourceReferences":16,"openSourceSubstitutions":2}

def ontology(data):
    validate(data)
    nodes=[{"id":i,"type":t} for i,t in [("SHADOW_GLASS","PolicyBoundary"),("GLASS_ONION","EvidencePlane"),("THE_BLACK_HOUSE","IntelligenceBrief"),("GPT_DOUG","Agent"),("ZYRA","Agent"),("XUNIA","Agent")]]
    links=[{"from":a,"to":b,"type":t} for a,b,t in [("SHADOW_GLASS","GLASS_ONION","Governs"),("GLASS_ONION","THE_BLACK_HOUSE","ProducesEvidenceFor"),("THE_BLACK_HOUSE","GPT_DOUG","Informs"),("THE_BLACK_HOUSE","ZYRA","Informs"),("THE_BLACK_HOUSE","XUNIA","Informs")]]
    for slot in data["slots"]:
        sid="slot:"+slot["id"];nodes.append({"id":sid,"type":"SourceSlot","rank":slot["rank"]})
        links.append({"from":sid,"to":"GLASS_ONION","type":"ReferencesAsEvidence"})
        for repo in slot["selectedRepos"]:
            rid="source:"+repo["url"];nodes.append({"id":rid,"type":"PublicSource","url":repo["url"]})
            links.append({"from":sid,"to":rid,"type":"ReferencesPublicMetadata"})
    return {"ontology":"GlassOnion15PublicSourceInventory","nodes":nodes,"links":links,"executionAllowed":False}

def probe(url):
    if GITHUB.fullmatch(url):
        u=url.split("/");endpoint="https://api.github.com/repos/"+u[-2]+"/"+u[-1]; provider="github"
    elif url==GITLAB:
        endpoint="https://gitlab.com/api/v4/projects/exploit-database%2Fexploitdb";provider="gitlab"
    else: raise ValueError("Remote request refused")
    req=Request(endpoint,headers={"User-Agent":"GlassOnion-SourceInventory/1.0","Accept":"application/json"})
    try:
        with urlopen(req,timeout=5) as res: obj=json.load(res)
    except (HTTPError,URLError,OSError,TimeoutError,ValueError) as e:
        return {"url":url,"status":"unavailable","reason":type(e).__name__,"metadataOnly":True}
    license_obj=obj.get("license")
    return {"url":url,"provider":provider,"status":"reachable","archived":obj.get("archived",False),"defaultBranch":obj.get("default_branch"),"license":license_obj.get("spdx_id") if isinstance(license_obj,dict) else None,"metadataOnly":True}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--validate",action="store_true");p.add_argument("--report",action="store_true")
    p.add_argument("--ontology-out",type=Path);p.add_argument("--probe",action="store_true");p.add_argument("--probe-out",type=Path)
    p.add_argument("--catalog",type=Path,default=CATALOG);a=p.parse_args()
    try:
        data=load(a.catalog);counts=validate(data)
    except (OSError,ValueError,KeyError,TypeError) as e:
        print("GLASS ONION FAIL CLOSED: "+str(e),file=sys.stderr);return 2
    if a.validate or not (a.report or a.ontology_out or a.probe): print("PASS:",counts)
    if a.report:
        for s in sorted(data["slots"],key=lambda s:-s["rank"]):
            print(f'#{s["rank"]:02d} {s["name"]}: '+", ".join(r["url"] for r in s["selectedRepos"])+" [READ ONLY]")
    if a.ontology_out:
        a.ontology_out.parent.mkdir(parents=True,exist_ok=True)
        a.ontology_out.write_text(json.dumps(ontology(data),indent=2)+"\\n")
        print("Wrote ontology:",a.ontology_out)
    if a.probe:
        results=[probe(r["url"]) for s in data["slots"] for r in s["selectedRepos"]]
        output=json.dumps({"checkedAt":datetime.now(timezone.utc).isoformat(),"results":results,"readOnly":True},indent=2)
        if a.probe_out:
            a.probe_out.parent.mkdir(parents=True,exist_ok=True);a.probe_out.write_text(output+"\\n")
        else: print(output)
    return 0

if __name__=="__main__": raise SystemExit(main())
