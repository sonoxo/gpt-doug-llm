#!/usr/bin/env python3
import argparse, json, os, shutil, subprocess, sys, time
from urllib import request

ESC="\x1b["
RESET=ESC+"0m"; BOLD=ESC+"1m"; DIM=ESC+"2m"
GREEN=ESC+"38;5;82m"; CYAN=ESC+"38;5;51m"; GOLD=ESC+"38;5;220m"
ORANGE=ESC+"38;5;208m"; VIOLET=ESC+"38;5;141m"; WHITE=ESC+"38;5;255m"

DRONE_URL=os.environ.get("DOUG_MAVEN_DRONE_URL","https://gpt-doug-robotics-intel.onrender.com/maven-broadcast.html?drone=1")
MAVEN_URL=os.environ.get("DOUG_MAVEN_URL","https://xunia.org/maven.html")
QNTMCIA_URL=os.environ.get("DOUG_QNTMCIA_URL","https://xunia.org/qntmcia.html")
OPS_URL=os.environ.get("DOUG_OPS_URL","https://xunia-ops-api.onrender.com/health")
CLOUD_URL=os.environ.get("DOUG_CLOUD_URL","https://gpt-doug-cloud-swarm.onrender.com/health")

FACE=[
"          ╭──────────────────────╮",
"          │   ◢██████████████◣   │",
"          │  ███  ◉      ◉  ███  │",
"          │  ███     ▄▄     ███  │",
"          │   ███   ╰──╯   ███   │",
"          │    ◥████████████◤    │",
"          ╰────────╥──╥───────────╯",
"                   ║  ║",
"             ╭─────╨──╨─────╮",
"             │ DOUG-GPT-MAVEN│",
"             ╰───────────────╯",
]

def clear():
    sys.stdout.write(ESC+"2J"+ESC+"H"); sys.stdout.flush()

def open_url(url):
    if sys.platform == "darwin":
        subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print(url)

def probe(url, timeout=6):
    started=time.time()
    try:
        req=request.Request(url,headers={"User-Agent":"DOUG-GPT-MAVEN/1.0","Accept":"application/json,text/html,*/*"})
        with request.urlopen(req,timeout=timeout) as r:
            return {"ok":200 <= r.status < 500,"status":r.status,"ms":round((time.time()-started)*1000)}
    except Exception as exc:
        return {"ok":False,"status":0,"ms":round((time.time()-started)*1000),"error":str(exc)}

def banner(frame=0,msg="SYSTEM READY"):
    clear()
    pulse=["◐","◓","◑","◒"][frame%4]
    print(ORANGE+BOLD+"🍂 DOUG-GPT-MAVEN // DARK FALL ONLINE 🍁"+RESET)
    print(DIM+"═"*72+RESET)
    color=[CYAN,VIOLET,GOLD,GREEN][frame%4]
    for line in FACE: print(color+line+RESET)
    print()
    print(f"{GREEN}● HUMAN_FIRST{RESET}  {GREEN}● SYNTHETIC FLIGHT{RESET}  {GREEN}● AUTHORIZED OBSERVATION{RESET}")
    print(f"{CYAN}{pulse} HIVE{RESET}  ◉◉◉◉    {VIOLET}SWARM{RESET}  ✦✦✦✦✦✦✦✦")
    print(f"{GOLD}MAVEN PIPELINE{RESET}  SURVEY → SEGMENT → CLASSIFY → TRACK → EVENT → HUMAN REVIEW")
    print(f"{DIM}{msg}{RESET}")
    print(DIM+"═"*72+RESET)

def animate(msg="INITIALIZING", seconds=2.2):
    start=time.time(); frame=0
    while time.time()-start < seconds:
        banner(frame,msg)
        frame+=1
        time.sleep(.18)

def show_status():
    animate("CHECKING CLOUD FABRIC",1.1)
    checks=[
        ("MAVEN DRONE",DRONE_URL),
        ("XUNIA OPS",OPS_URL),
        ("CLOUD SWARM",CLOUD_URL),
    ]
    banner(0,"LIVE STATUS")
    for name,url in checks:
        result=probe(url)
        mark=(GREEN+"ONLINE"+RESET) if result["ok"] else (ORANGE+"DEGRADED"+RESET)
        print(f"{name:<14} {mark:<20} HTTP {result['status']}  {result['ms']} ms")
    print()
    input(DIM+"Press Enter to return…"+RESET)

def matrix(seconds=5):
    chars="01ΔΣΨΩ✦◇◆░▒▓     "
    import random
    start=time.time()
    while time.time()-start < seconds:
        clear()
        cols,rows=shutil.get_terminal_size((90,28))
        print(GREEN+BOLD+"DOUG-GPT-MAVEN // HIVE MATRIX"+RESET)
        for _ in range(max(6,rows-2)):
            print(GREEN+"".join(random.choice(chars) for _ in range(cols))+RESET)
        time.sleep(.08)

def launch_drone():
    animate("OPENING MAVEN DRONE SYSTEM",1.4)
    open_url(DRONE_URL)
    banner(0,"DRONE DECK REQUESTED IN BROWSER")
    time.sleep(1.0)

def interactive():
    animate("BOOTING MAVEN CONTROL PLANE")
    while True:
        banner(int(time.time()*4),"COMMAND BUS ONLINE")
        print(f"{WHITE}1{RESET}  DRONE SYSTEM")
        print(f"{WHITE}2{RESET}  MAVEN HQ")
        print(f"{WHITE}3{RESET}  QNTMCIA")
        print(f"{WHITE}4{RESET}  CLOUD STATUS")
        print(f"{WHITE}5{RESET}  MATRIX EFFECTS")
        print(f"{WHITE}q{RESET}  QUIT")
        try: cmd=input(ORANGE+"doug-gpt-maven> "+RESET).strip().lower()
        except (EOFError,KeyboardInterrupt): print(); return
        if cmd in {"1","drone","d"}: launch_drone()
        elif cmd in {"2","maven","m"}: open_url(MAVEN_URL)
        elif cmd in {"3","qntmcia","qnt"}: open_url(QNTMCIA_URL)
        elif cmd in {"4","status","s"}: show_status()
        elif cmd in {"5","matrix","fx"}: matrix()
        elif cmd in {"q","quit","exit"}: return

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--drone",action="store_true")
    ap.add_argument("--maven",action="store_true")
    ap.add_argument("--status",action="store_true")
    ap.add_argument("--matrix",action="store_true")
    args=ap.parse_args()
    if args.drone: launch_drone()
    elif args.maven: animate("OPENING MAVEN HQ",1); open_url(MAVEN_URL)
    elif args.status: show_status()
    elif args.matrix: matrix()
    else: interactive()

if __name__=="__main__":
    main()
