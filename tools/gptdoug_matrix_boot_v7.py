#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, random, shutil, signal, sys, time
from pathlib import Path

STATE_FILE = Path.home() / ".gpt-doug" / "max-shell-state.json"
RESET="\033[0m"; HIDE="\033[?25l"; SHOW="\033[?25h"; CLEAR="\033[2J"; HOME="\033[H"
GREEN="\033[38;2;50;255;120m"; BRIGHT="\033[38;2;180;255;210m"; CYAN="\033[38;2;0;230;255m"
DIM="\033[38;2;30;120;60m"; WHITE="\033[38;2;230;255;240m"; MAG="\033[38;2;255;70;220m"
running=True

def stop(*_):
    global running
    running=False
signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)

def size():
    return shutil.get_terminal_size((120, 40))

def center(s,w):
    return " " * max(0,(w-len(s))//2) + s

def bar(p,w=42):
    n=max(0,min(w,int(w*p)))
    return "["+BRIGHT+"█"*n+DIM+"░"*(w-n)+RESET+"]"

def rain_frame(cols,rows,t,rng):
    out=[[" "]*cols for _ in range(rows)]
    step=3
    for x in range(0,cols,step):
        head=int((t*(6+(x%7)) + x*1.7) % (rows+14))-7
        trail=4+(x%8)
        for d in range(trail):
            y=head-d
            if 0<=y<rows:
                ch="1" if ((x+y+d+int(t*10))&1) else "0"
                out[y][x]=ch
    return out

def render_rain(cols,rows,t):
    grid=rain_frame(cols,rows,t,random)
    lines=[]
    for y,row in enumerate(grid):
        s="".join(row)
        lines.append((BRIGHT if y%7==0 else DIM)+s+RESET)
    return "\n".join(lines)

def main():
    cols,rows=size()
    boot_rows=max(18,rows-4)
    sys.stdout.write(CLEAR+HOME+HIDE); sys.stdout.flush()
    start=time.monotonic()
    stages=[
        ("ROM","boot vector"),
        ("LINK","local runtime"),
        ("XUNIA","reasoning core"),
        ("ZYRA","agent runtime"),
        ("DOUG","master directive"),
        ("VISION","facial cortex"),
        ("WALK","locomotion field"),
        ("VOICE","speech interface"),
    ]
    try:
        for i,(name,detail) in enumerate(stages,1):
            if not running: return 130
            t=time.monotonic()-start
            cols,rows=size()
            title=center("GPT-DOUG // MATRIX WALK BOOT",cols)
            stage=center(f"{name:<7} :: {detail}",cols)
            pct=i/len(stages)
            code=render_rain(cols,min(12,max(6,rows//3)),t)
            sys.stdout.write(HOME)
            sys.stdout.write(DIM+"0 1 0 1 1 0 0 1 0 1 0 1".center(cols)+RESET+"\n")
            sys.stdout.write(GREEN+title+RESET+"\n\n")
            sys.stdout.write(code+"\n")
            sys.stdout.write(CYAN+stage+RESET+"\n")
            sys.stdout.write(center(bar(pct),cols)+"\n")
            sys.stdout.write(MAG+center("wake // link // move // respond",cols)+RESET+"\n")
            sys.stdout.write("\033[J")
            sys.stdout.flush()
            time.sleep(0.22)

        # short activation pulse
        for k in range(6):
            if not running: return 130
            color = BRIGHT if k%2==0 else CYAN
            sys.stdout.write(HOME+CLEAR)
            sys.stdout.write("\n"*max(2,rows//3))
            sys.stdout.write(color+center("◉ GPT-DOUG LINKED ◉",cols)+RESET+"\n")
            sys.stdout.write(GREEN+center("MATRIX WALK MODE // ONLINE",cols)+RESET+"\n")
            sys.stdout.flush()
            time.sleep(0.08)
        return 0
    finally:
        sys.stdout.write(RESET+SHOW)
        sys.stdout.flush()

if __name__=="__main__":
    raise SystemExit(main())
