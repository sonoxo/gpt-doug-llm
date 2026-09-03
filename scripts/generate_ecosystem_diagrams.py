#!/usr/bin/env python3
"""Generate GitHub-safe, responsive SVG ecosystem diagrams from the live repo.

No third-party packages. The diagrams intentionally derive labels/counts from the
checked-out repository so README visuals evolve with code, tests, ontology and
workflow changes.
"""
from __future__ import annotations

import ast
import html
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)
SHA = os.getenv("GITHUB_SHA", "local")[:7]


def exists_any(*patterns: str) -> bool:
    return any(any(ROOT.glob(p)) for p in patterns)


def ontology_count() -> int:
    path = ROOT / "wakeup3lm" / "ontology.py"
    if not path.exists():
        return 0
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "CORE_TYPES":
                        value = ast.literal_eval(node.value)
                        return len(value)
    except Exception:
        pass
    return 0


def workflow_names() -> list[str]:
    p = ROOT / ".github" / "workflows"
    if not p.exists():
        return []
    return sorted(x.name for x in p.glob("*.yml")) + sorted(x.name for x in p.glob("*.yaml"))


def security_workflows() -> list[str]:
    needles = ("security", "compliance", "lock", "gate", "readiness", "palantir", "defensive")
    return [name for name in workflow_names() if any(n in name.lower() for n in needles)]


def test_count() -> int:
    p = ROOT / "tests"
    return len(list(p.rglob("test_*.py"))) if p.exists() else 0


def chip(x: int, y: int, w: int, title: str, subtitle: str, accent: str, live: bool = True) -> str:
    state = "LIVE" if live else "NOT DETECTED"
    state_color = "#7CFF6B" if live else "#FFB454"
    return f'''<g transform="translate({x} {y})">
      <rect width="{w}" height="112" rx="20" fill="#111821" stroke="{accent}" stroke-width="2"/>
      <rect x="18" y="18" width="8" height="76" rx="4" fill="{accent}"/>
      <text x="44" y="43" class="title">{html.escape(title)}</text>
      <text x="44" y="68" class="sub">{html.escape(subtitle)}</text>
      <circle cx="{w-79}" cy="86" r="6" fill="{state_color}"><animate attributeName="opacity" values=".35;1;.35" dur="2.2s" repeatCount="indefinite"/></circle>
      <text x="{w-65}" y="91" class="state" fill="{state_color}">{state}</text>
    </g>'''


def arrow(x1: int, y1: int, x2: int, y2: int, color: str = "#3DE1FF") -> str:
    return f'''<path d="M{x1} {y1} L{x2} {y2}" stroke="{color}" stroke-width="3" fill="none" marker-end="url(#arrow)" stroke-dasharray="10 10">
      <animate attributeName="stroke-dashoffset" values="20;0" dur="1.2s" repeatCount="indefinite"/>
    </path>'''


STYLE = '''
  <defs>
    <filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#3DE1FF"/></marker>
  </defs>
  <style>
    .h1{font:700 34px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#F8FBFF}.h2{font:600 18px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#9FB2C8}
    .title{font:700 18px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#F8FBFF}.sub{font:500 13px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#AAB8C8}
    .state{font:800 10px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:1px}.small{font:600 12px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#AAB8C8}
  </style>
'''


def write_ecosystem() -> None:
    cards = [
        ("GPT-DOUG-LLM MAX", "orchestration + reasoning", "#A970FF", exists_any("zyra_chat.py", "*doug*.py")),
        ("Wakeup3lm", "IDE-native LLM execution kernel", "#3DE1FF", exists_any("wakeup3lm/runtime.py")),
        ("Ontology", f"typed graph • {ontology_count()} core object types", "#7CFF6B", exists_any("wakeup3lm/ontology.py", "safety-shield/ontology/*")),
        ("Palantir AIP / Foundry", "model + Logic + authorized Ontology", "#FFB454", exists_any("palantir*aip*.py", "palantir_stack.py", "palantir_foundry.py")),
        ("Agent + Tool Runtime", "files • terminal • build • validation", "#FF6BD6", exists_any("agents/**", "wakeup3lm/workspace.py")),
        ("Security Gates", f"{len(security_workflows())} repo security/control workflows", "#FF5D73", len(security_workflows()) > 0),
        ("Evidence", f"{test_count()} Python test modules + audit state", "#FFD166", test_count() > 0),
        ("Ship", "preview • release • deployment adapters", "#2DD4BF", exists_any(".github/workflows/docker-publish.yml", "*apollo*.py")),
    ]
    out = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 790" width="1400" height="790" role="img" aria-labelledby="t d">
<title id="t">Black House ecosystem flow</title><desc id="d">Beginner-readable flow from user intent through GPT-DOUG MAX, Wakeup3lm, ontology, Palantir layers, agent tools, security gates, evidence and shipping.</desc>
<rect width="1400" height="790" rx="28" fill="#080D12"/>{STYLE}
<text x="70" y="70" class="h1">THE BLACK HOUSE // HOW THE ECOSYSTEM FLOWS</text>
<text x="70" y="103" class="h2">Prompt → governed reasoning → ontology context → tools → proof → ship</text>
<text x="1270" y="70" text-anchor="end" class="small">repo {SHA}</text>
''']
    positions = [(70,150),(385,150),(700,150),(1015,150),(1015,390),(700,390),(385,390),(70,390)]
    for (title, sub, accent, live), (x,y) in zip(cards, positions):
        out.append(chip(x,y,250,title,sub,accent,live))
    centers=[(320,206,385,206),(635,206,700,206),(950,206,1015,206),(1140,262,1140,390),(1015,446,950,446),(700,446,635,446),(385,446,320,446)]
    out += [arrow(*a) for a in centers]
    out.append('''<g transform="translate(70 585)"><rect width="1260" height="125" rx="22" fill="#0D141C" stroke="#263746"/>
<text x="28" y="38" class="title">BEGINNER RULE</text>
<text x="28" y="68" class="sub">The model can propose. The Ontology supplies context. Policy decides what is allowed. Tools do the work.</text>
<text x="28" y="94" class="sub">Tests, logs and probes produce evidence before a result is kept or deployed. External platforms keep their own permissions.</text></g></svg>''')
    (ASSETS / "ecosystem-flow.svg").write_text("".join(out), encoding="utf-8")


def write_agent_loop() -> None:
    steps = [
        ("1", "ASK", "Describe the app or change"), ("2", "PLAN", "Wakeup3lm structures the mission"),
        ("3", "GROUND", "Ontology + authorized AIP context"), ("4", "ACT", "Allowlisted tools edit/run/build"),
        ("5", "VERIFY", "Tests + security gates + preview"), ("6", "REPAIR", "Failures feed the next decision"),
        ("7", "CHECKPOINT", "Keep evidence + rollback point"), ("8", "SHIP", "Publish only through approved path"),
    ]
    out=[f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 560" width="1400" height="560" role="img" aria-labelledby="t2 d2"><title id="t2">Wakeup3lm coding loop</title><desc id="d2">Eight step autonomous but governed coding loop.</desc><rect width="1400" height="560" rx="28" fill="#080D12"/>{STYLE}<text x="70" y="70" class="h1">WAKEUP3LM // VIBE-CODE LOOP</text><text x="70" y="103" class="h2">Every action is observable. Every failure has a return path.</text>''']
    x0,y0=70,150
    for i,(num,title,sub) in enumerate(steps):
        col=i%4; row=i//4; x=x0+col*320; y=y0+row*180
        accent=("#3DE1FF","#A970FF","#7CFF6B","#FFB454","#FFD166","#FF5D73","#FF6BD6","#2DD4BF")[i]
        out.append(f'''<g transform="translate({x} {y})"><rect width="270" height="118" rx="20" fill="#111821" stroke="{accent}" stroke-width="2"/><circle cx="36" cy="36" r="18" fill="{accent}" opacity=".18"/><text x="36" y="42" text-anchor="middle" class="title" fill="{accent}">{num}</text><text x="66" y="39" class="title">{title}</text><text x="24" y="78" class="sub">{html.escape(sub)}</text></g>''')
    for x in (340,660,980): out.append(arrow(x,209,x+50,209))
    for x in (980,660,340): out.append(arrow(x+50,389,x,389))
    out.append(arrow(1200,268,1200,330))
    out.append('''<path d="M70 450 C35 450 35 210 70 210" stroke="#FF5D73" stroke-width="3" fill="none" stroke-dasharray="8 10"><animate attributeName="stroke-dashoffset" values="18;0" dur="1.4s" repeatCount="indefinite"/></path><text x="82" y="492" class="small">repair loop returns failed verification to the next governed decision</text></svg>''')
    (ASSETS / "wakeup3lm-agent-loop.svg").write_text("".join(out), encoding="utf-8")


def write_security() -> None:
    gates = security_workflows()
    shown = gates[:12]
    rows = (len(shown) + 1) // 2
    bottom = 150 + rows * 72 + 35
    canvas_height = max(760, bottom + 123)
    out=[f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 {canvas_height}" width="1400" height="{canvas_height}" role="img" aria-labelledby="t3 d3"><title id="t3">Security gate map</title><desc id="d3">Repository security and control gates discovered from GitHub Actions workflow files.</desc><rect width="1400" height="{canvas_height}" rx="28" fill="#080D12"/>{STYLE}<text x="70" y="70" class="h1">SECURITY CONTROL PLANE // DISCOVERED FROM THE REPO</text><text x="70" y="103" class="h2">{len(gates)} security / compliance / lock / readiness workflows detected • generated from .github/workflows</text>''']
    y=150
    for i,name in enumerate(shown):
        col=i%2; row=i//2; x=70+col*650; yy=y+row*72
        out.append(f'''<g transform="translate({x} {yy})"><rect width="600" height="54" rx="14" fill="#111821" stroke="#263746"/><circle cx="28" cy="27" r="7" fill="#7CFF6B"><animate attributeName="opacity" values=".4;1;.4" dur="2.3s" repeatCount="indefinite"/></circle><text x="48" y="33" class="title">{html.escape(name)}</text><text x="545" y="33" class="state" fill="#9FB2C8">CONFIGURED</text></g>''')
    out.append(f'''<g transform="translate(70 {bottom})"><rect width="1250" height="98" rx="20" fill="#0D141C" stroke="#FF5D73"/><text x="28" y="37" class="title">READ THIS CORRECTLY</text><text x="28" y="68" class="sub">This diagram proves the gates are configured in the repository. The README badges / GitHub Actions runs prove whether the latest execution passed.</text></g></svg>''')
    (ASSETS / "security-gates.svg").write_text("".join(out), encoding="utf-8")


if __name__ == "__main__":
    write_ecosystem()
    write_agent_loop()
    write_security()
    print(f"generated ecosystem diagrams from repo {SHA}")
