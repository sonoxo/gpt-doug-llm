#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, platform, shutil, subprocess, time
from pathlib import Path

ROOT=Path.home()/ "gpt-doug-llm"
STATE=Path.home()/".gpt-doug"/"max-shell-state.json"
EMOTE=Path.home()/".gpt-doug"/"visual-emote.json"
WALK=Path.home()/".gpt-doug"/"visual-walk.json"

R="\033[0m"; H="\033[H"; C="\033[2J"; X="\033[?25l"; S="\033[?25h"
G="\033[38;2;55;255;125m"; BG="\033[38;2;185;255;210m"; DG="\033[38;2;25;110;60m"
CY="\033[38;2;0;230;255m"; WH="\033[38;2;235;255;240m"; GR="\033[38;2;100;140;115m"
MG="\033[38;2;255;75;220m"; Y="\033[38;2;255;220;90m"

def readj(p, default):
    try:
        d=json.loads(p.read_text())
        return d if isinstance(d,dict) else default
    except Exception:
        return default

def sh(*args):
    try:
        return subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=1.0).stdout.strip()
    except Exception:
        return ""

def meter(v,w=15):
    v=max(0,min(1,v)); n=int(round(v*w))
    return G+"▰"*n+DG+"▱"*(w-n)+R

def wave(t,w=24):
    chars=" ▁▂▃▄▅▆▇█"; out=[]
    for x in range(w):
        y=math.sin(t*4+x*.45)+.35*math.sin(t*7+x*.2)
        i=int((y+1.35)/2.7*(len(chars)-1)); i=max(0,min(len(chars)-1,i))
        out.append(chars[i])
    return CY+"".join(out)+R

def code_strip(t,w):
    chars=[]
    for x in range(w):
        on=((x*7+int(t*9))%13)<7
        chars.append("1" if ((x+int(t*5))&1) else "0" if on else " ")
    return DG+"".join(chars)+R

def main():
    print(C+X,end="",flush=True)
    start=time.monotonic()
    try:
        while True:
            t=time.monotonic()-start
            cols,rows=shutil.get_terminal_size((46,52))
            width=max(34,cols-1)
            st=readj(STATE,{"state":"IDLE","provider":"none","model":"unknown","detail":"waiting"})
            em=readj(EMOTE,{"name":"auto"})
            wk=readj(WALK,{"mode":"off","speed":1.0,"range":0.82})
            branch=sh("git","branch","--show-current") or "detached"
            sha=sh("git","rev-parse","--short","HEAD") or "-------"
            dirty=bool(sh("git","status","--short"))
            provider=str(st.get("provider","none")); model=str(st.get("model","unknown"))
            mode=str(st.get("state","IDLE")).upper(); detail=str(st.get("detail",""))
            brain=provider.lower() not in {"","none","unknown","offline"}
            xunia=(ROOT/"xunia_godis.py").exists(); zyra=(ROOT/"zyra_agent.py").exists()
            visual=(ROOT/"tools"/"gptdoug_supreme_visual_v4.py").exists()
            try: load=os.getloadavg()[0]
            except Exception: load=0.0
            disk=shutil.disk_usage(ROOT); used=1-disk.free/max(1,disk.total)
            blink="◆" if int(t*5)%2 else "◇"

            lines=[
                G+"╭─[ MATRIXOPS // GPT-DOUG ]─╮"+R,
                G+f"│ {blink} LINKED // LIVE RESPONSE"+R,
                G+"╰────────────────────────────╯"+R,
                code_strip(t,width),
                "",
                WH+"🧠 INTELLIGENCE"+R,
                f" brain   {(G+'● ONLINE') if brain else (Y+'● STANDBY')}"+R,
                f" XUNIA   {(G+'● ONLINE') if xunia else (Y+'● MISSING')}"+R,
                f" ZYRA    {(G+'● ONLINE') if zyra else (Y+'● MISSING')}"+R,
                f" visual  {(G+'● ONLINE') if visual else (Y+'● MISSING')}"+R,
                "",
                CY+"⚡ RESPONSE STATE"+R,
                f" mode    {BG}{mode}{R}",
                f" emote   {MG}{str(em.get('name','auto'))}{R}",
                f" walk    {CY}{str(wk.get('mode','off'))}{R}",
                f" speed   {str(wk.get('speed',1.0))}",
                f" detail  {GR}{detail[:28]}{R}",
                "",
                WH+"📟 MACHINE"+R,
                f" load    {meter(min(1,load/8))} {load:.2f}",
                f" disk    {meter(used)}",
                f" host    {CY}{platform.node()[:18]}{R}",
                "",
                WH+"🗂 GIT"+R,
                f" branch  {CY}{branch[:20]}{R}",
                f" commit  {MG}{sha}{R}",
                f" tree    {(Y+'DIRTY') if dirty else (G+'CLEAN')}{R}",
                "",
                WH+"〰 SIGNAL"+R,
                wave(t,min(width,26)),
                "",
                DG+"walk // think // talk // react // repeat"+R,
            ]
            out=H
            for line in lines[:rows]:
                out+=line+"\033[K\n"
            out+="\033[J"
            print(out,end="",flush=True)
            time.sleep(.125)
    except KeyboardInterrupt:
        return 0
    finally:
        print(R+S,end="",flush=True)

if __name__=="__main__":
    raise SystemExit(main())
