#!/usr/bin/env python3
'''Generate the Kraken Jutsu ecosystem + infrastructure README diagram.

This runs after generate_ecosystem_diagrams.py so the README's canonical
ecosystem-flow.svg stays Kraken-aware while remaining derived from repo state.
No third-party packages are required.
'''
from __future__ import annotations

import html
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "ecosystem-flow.svg"
OUT.parent.mkdir(parents=True, exist_ok=True)
SHA = os.getenv("GITHUB_SHA", "local")[:7]


def exists(*paths: str) -> bool:
    return any((ROOT / path).exists() for path in paths)


def exists_glob(*patterns: str) -> bool:
    return any(any(ROOT.glob(pattern)) for pattern in patterns)


def status(flag: bool) -> tuple[str, str]:
    return ("LIVE", "#7CFF6B") if flag else ("OPTIONAL", "#FFB454")


def card(x: int, y: int, w: int, h: int, title: str, lines: list[str],
         accent: str, flag: bool = True) -> str:
    state, state_color = status(flag)
    body = []
    yy = 62
    for line in lines:
        body.append(
            f'<text x="28" y="{yy}" class="sub">{html.escape(line)}</text>'
        )
        yy += 24
    return f'''<g transform="translate({x} {y})">
<rect width="{w}" height="{h}" rx="20" fill="#111821" stroke="{accent}" stroke-width="2"/>
<rect x="0" y="0" width="9" height="{h}" rx="4" fill="{accent}"/>
<text x="28" y="34" class="title">{html.escape(title)}</text>
{''.join(body)}
<circle cx="{w-78}" cy="31" r="6" fill="{state_color}"><animate attributeName="opacity" values=".35;1;.35" dur="2.2s" repeatCount="indefinite"/></circle>
<text x="{w-64}" y="36" class="state" fill="{state_color}">{state}</text>
</g>'''


def edge(x1: int, y1: int, x2: int, y2: int, color: str = "#3DE1FF",
         dashed: bool = True) -> str:
    dash = ' stroke-dasharray="10 10"' if dashed else ""
    anim = '<animate attributeName="stroke-dashoffset" values="20;0" dur="1.25s" repeatCount="indefinite"/>' if dashed else ""
    return (
        f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{color}" stroke-width="3" '
        f'fill="none" marker-end="url(#arrow)"{dash}>{anim}</path>'
    )


def main() -> None:
    kraken_live = exists("kraken_jutsu")
    black_house_live = exists("the-black-house")
    guard_live = exists("safety-shield")
    wakeup_live = exists("wakeup3lm")
    palantir_live = exists("foundry") or exists_glob("palantir*.py")
    actions_live = exists(".github/workflows")
    tests_live = exists("tests")
    usb_live = exists("kraken_jutsu/usb_v031.py") or exists("kraken_jutsu/usb.py")

    svg = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1120" width="1600" height="1120" role="img" aria-labelledby="title desc">
<title id="title">Release the Kraken — ecosystem and infrastructure map</title>
<desc id="desc">Kraken Jutsu receives attributed evidence, normalizes and corroborates it, grounds decisions in an ontology, routes defensive or authorized lab simulation modes through policy and approval gates, and connects GPT-DOUG, Wakeup3lm, ZYRAPALANTIR, ZYRA/XUNIA, edge, cloud, and authorized enterprise infrastructure with verification evidence.</desc>
<rect width="1600" height="1120" rx="30" fill="#070B10"/>
<defs>
  <filter id="glow"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <radialGradient id="krakenCore"><stop offset="0%" stop-color="#A970FF" stop-opacity=".95"/><stop offset="100%" stop-color="#111821" stop-opacity="1"/></radialGradient>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#3DE1FF"/></marker>
</defs>
<style>
.h1{{font:800 38px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#F8FBFF}}
.h2{{font:600 18px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#9FB2C8}}
.title{{font:750 17px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#F8FBFF}}
.sub{{font:500 13px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#AAB8C8}}
.state{{font:800 10px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:1px}}
.label{{font:800 11px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#3DE1FF;letter-spacing:1.4px}}
.core{{font:850 28px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#FFFFFF}}
.coreSub{{font:650 14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#D7E3F2}}
.footer{{font:650 14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#D8E4EE}}
</style>
<text x="70" y="68" class="h1">RELEASE THE KRAKEN // ECOSYSTEM + INFRASTRUCTURE</text>
<text x="70" y="101" class="h2">Evidence → normalize → corroborate → ontology judgment → D / O-D routing → approval → bounded execution → proof</text>
<text x="1515" y="68" text-anchor="end" class="sub">repo {SHA}</text>

<text x="70" y="142" class="label">01 // EVIDENCE + TELEMETRY PLANE</text>
''']

    sources = [
        (70, "GOV / STANDARDS", ["CISA KEV • NIST NVD", "NIST OSCAL / 800-53"], "#2DD4BF", kraken_live),
        (450, "BEHAVIOR GRAPH", ["MITRE ATT&CK", "mapped techniques + controls"], "#FFB454", kraken_live),
        (830, "OSINT EVIDENCE", ["API / offline exports", "untrusted until corroborated"], "#A970FF", kraken_live),
        (1210, "EDGE / USB AGENTS", ["fingerprint • quarantine", "portable evidence intake"], "#3DE1FF", usb_live),
    ]
    for x, title, lines, accent, flag in sources:
        svg.append(card(x, 165, 320, 120, title, lines, accent, flag))

    for x in (230, 610, 990, 1370):
        svg.append(edge(x, 285, 800, 370, "#3DE1FF"))

    svg.append('''
<text x="70" y="360" class="label">02 // KRAKEN JUTSU DECISION CORE</text>
<g filter="url(#glow)">
  <circle cx="800" cy="500" r="138" fill="url(#krakenCore)" stroke="#A970FF" stroke-width="3"/>
  <circle cx="800" cy="500" r="113" fill="none" stroke="#3DE1FF" stroke-width="1.5" stroke-dasharray="7 10"/>
  <text x="800" y="463" text-anchor="middle" class="core">KRAKEN JUTSU</text>
  <text x="800" y="491" text-anchor="middle" class="coreSub">NORMALIZE • CORROBORATE</text>
  <text x="800" y="516" text-anchor="middle" class="coreSub">ONTOLOGY JUDGE</text>
  <text x="800" y="541" text-anchor="middle" class="coreSub">D ↔ O-D MODE ROUTER</text>
  <text x="800" y="566" text-anchor="middle" class="coreSub">ACTION PROPOSAL + AUDIT</text>
  <path d="M708 577 C665 622 689 661 643 686" stroke="#A970FF" stroke-width="8" fill="none" stroke-linecap="round"/>
  <path d="M748 605 C722 650 744 686 718 711" stroke="#3DE1FF" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M800 613 C800 666 800 687 800 720" stroke="#7CFF6B" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M852 605 C878 650 856 686 882 711" stroke="#3DE1FF" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M892 577 C935 622 911 661 957 686" stroke="#A970FF" stroke-width="8" fill="none" stroke-linecap="round"/>
</g>
''')

    svg.append(card(70, 405, 430, 190, "SHADOW GLASS / GLASS ONION", [
        "identity • provenance • confidence • policy",
        "role ≠ permission • least privilege",
        "high-authority actions require approval",
        "append-only evidence / rollback posture",
    ], "#FF5D73", guard_live))
    svg.append(edge(500, 500, 650, 500, "#FF5D73"))

    svg.append(card(1100, 405, 430, 190, "BLACK HOUSE CONTROL PLANE", [
        "GPT-DOUG MAX → governed mission",
        "Wakeup3lm → tool / repair loop",
        "ZYRAPALANTIR → ontology + simulation",
        "ZYRA / XUNIA → bounded product surfaces",
    ], "#FFD166", black_house_live and wakeup_live))
    svg.append(edge(950, 500, 1100, 500, "#FFD166"))

    svg.append('''
<g transform="translate(615 650)">
  <rect width="370" height="80" rx="18" fill="#0D141C" stroke="#3DE1FF" stroke-width="2"/>
  <text x="185" y="30" text-anchor="middle" class="title">MODE CONTRACT</text>
  <text x="185" y="52" text-anchor="middle" class="sub">D = defensive action</text>
  <text x="185" y="70" text-anchor="middle" class="sub">O-D = D + authorized lab / digital-twin emulation only</text>
</g>
''')

    svg.append('<text x="70" y="785" class="label">03 // EXECUTION + INFRASTRUCTURE PLANES</text>')
    svg.append(card(70, 810, 450, 150, "EDGE / USB // KRAKENXYZ", [
        ".krakenxyz/ontology.db • WAL storage",
        "audit.jsonl • agent inbox • quarantine",
        "local fingerprints + portable recovery",
    ], "#3DE1FF", usb_live))
    svg.append(card(575, 810, 450, 150, "CLOUD / REPO // PROOF PIPELINE", [
        "GitHub Actions • policy gates • tests",
        "build / preview / logs / checkpoints",
        "deploy adapters only after verification",
    ], "#7CFF6B", actions_live and tests_live))
    svg.append(card(1080, 810, 450, 150, "AUTHORIZED ENTERPRISE // ZYRAPALANTIR", [
        "Foundry Ontology • AIP • published Logic",
        "simulation / governed actions / audit",
        "external tenant permissions stay authoritative",
    ], "#FFB454", palantir_live))

    svg.append(edge(650, 705, 295, 810, "#3DE1FF"))
    svg.append(edge(800, 720, 800, 810, "#7CFF6B"))
    svg.append(edge(950, 705, 1305, 810, "#FFB454"))

    svg.append('''
<g transform="translate(70 995)">
  <rect width="1460" height="86" rx="20" fill="#0B1219" stroke="#FF5D73" stroke-width="2"/>
  <text x="28" y="31" class="title">SAFETY / AUTHORITY BOUNDARY</text>
  <text x="28" y="57" class="footer">Material infrastructure actions remain human-controlled and approval-gated. No autonomous external dispatch.</text>
  <text x="28" y="77" class="footer">Kraken can analyze, simulate, defend, verify, and recommend; offensive emulation is restricted to owned / authorized lab or digital-twin environments.</text>
</g>
</svg>''')

    OUT.write_text("".join(svg), encoding="utf-8")
    print(f"generated Kraken ecosystem diagram from repo {SHA}")


if __name__ == "__main__":
    main()
