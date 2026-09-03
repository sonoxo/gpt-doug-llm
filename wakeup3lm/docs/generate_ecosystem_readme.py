from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAKEUP = ROOT / "wakeup3lm"
README = WAKEUP / "README.md"
ASSET_DIR = WAKEUP / "assets"
SVG = ASSET_DIR / "ecosystem.svg"

START = "<!-- WAKEUP3LM:AUTO:START -->"
END = "<!-- WAKEUP3LM:AUTO:END -->"


def count_files(path: Path, pattern: str) -> int:
    return sum(1 for p in path.rglob(pattern) if p.is_file()) if path.exists() else 0


def ontology_types() -> list[str]:
    source = (WAKEUP / "ontology.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CORE_TYPES":
                    value = ast.literal_eval(node.value)
                    return sorted(str(x) for x in value)
    return []


def capability(label: str, *paths: str) -> tuple[str, bool]:
    return label, all((ROOT / p).exists() for p in paths)


def render_svg(metrics: dict[str, int]) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" role="img" aria-labelledby="title desc">
<title id="title">Wakeup3lm Black House ecosystem</title>
<desc id="desc">Animated ontology-first IDE LLM architecture from user intent through model reasoning, ontology, tools, workspace, verification and deployment.</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#050807"/><stop offset="1" stop-color="#0d1511"/></linearGradient>
  <linearGradient id="volt" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#7CFF45"/><stop offset=".5" stop-color="#D6FF46"/><stop offset="1" stop-color="#7CFF45"/></linearGradient>
  <filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect width="1200" height="520" rx="28" fill="url(#bg)"/>
<rect x="20" y="20" width="1160" height="480" rx="22" fill="none" stroke="#26352d"/>
<text x="60" y="75" fill="#F1F7F3" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="30" font-weight="700">WAKEUP3LM // THE BLACK HOUSE IDE LLM</text>
<text x="60" y="110" fill="#9EB2A5" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="15">ontology-first • tool-governed • verification-driven • adaptive repo telemetry</text>

<path d="M100 250 H1100" stroke="#26352d" stroke-width="8" stroke-linecap="round"/>
<path d="M100 250 H1100" stroke="url(#volt)" stroke-width="3" stroke-linecap="round" stroke-dasharray="18 22" filter="url(#glow)">
  <animate attributeName="stroke-dashoffset" values="0;-80" dur="2.8s" repeatCount="indefinite"/>
</path>

{node(100, 250, 'USER', 'intent')}
{node(300, 250, 'WAKEUP3LM', 'model')}
{node(500, 250, 'ONTOLOGY', 'state + policy')}
{node(700, 250, 'TOOLS', 'files + runtime')}
{node(900, 250, 'VERIFY', 'build + repair')}
{node(1100, 250, 'SHIP', 'preview + deploy')}

<g font-family="ui-monospace, SFMono-Regular, Menlo, monospace">
  <text x="60" y="390" fill="#7CFF45" font-size="16">LIVE REPO PULSE</text>
  <text x="60" y="425" fill="#E8F0EA" font-size="22">{metrics['modules']}</text><text x="100" y="425" fill="#8EA096" font-size="14"> Wakeup3lm modules</text>
  <text x="310" y="425" fill="#E8F0EA" font-size="22">{metrics['tests']}</text><text x="350" y="425" fill="#8EA096" font-size="14"> test files</text>
  <text x="530" y="425" fill="#E8F0EA" font-size="22">{metrics['workflows']}</text><text x="570" y="425" fill="#8EA096" font-size="14"> GitHub workflows</text>
  <text x="790" y="425" fill="#E8F0EA" font-size="22">{metrics['ontology']}</text><text x="830" y="425" fill="#8EA096" font-size="14"> ontology object types</text>
  <text x="60" y="465" fill="#627169" font-size="12">Generated from repository state. Visual motion is SVG-native so the README remains portable and GitHub-friendly.</text>
</g>

<rect x="35" y="35" width="5" height="450" fill="#7CFF45" opacity=".1">
  <animate attributeName="x" values="35;1160;35" dur="8s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values=".05;.28;.05" dur="8s" repeatCount="indefinite"/>
</rect>
</svg>'''


def node(x: int, y: int, title: str, sub: str) -> str:
    return f'''<g transform="translate({x} {y})" font-family="ui-monospace, SFMono-Regular, Menlo, monospace">
<circle r="46" fill="#0A100D" stroke="#7CFF45" stroke-width="2"/>
<circle r="52" fill="none" stroke="#7CFF45" opacity=".22" stroke-dasharray="8 10"><animateTransform attributeName="transform" type="rotate" values="0;360" dur="12s" repeatCount="indefinite"/></circle>
<text y="-4" text-anchor="middle" fill="#F2F7F3" font-size="13" font-weight="700">{title}</text>
<text y="16" text-anchor="middle" fill="#8EA096" font-size="10">{sub}</text>
</g>'''


def render_auto_block() -> str:
    ont = ontology_types()
    metrics = {
        "modules": count_files(WAKEUP, "*.py"),
        "tests": count_files(ROOT / "tests", "test_*.py"),
        "workflows": count_files(ROOT / ".github" / "workflows", "*.yml") + count_files(ROOT / ".github" / "workflows", "*.yaml"),
        "ontology": len(ont),
    }
    checks = [
        capability("Ontology kernel", "wakeup3lm/ontology.py"),
        capability("Structured agent decisions", "wakeup3lm/runtime.py"),
        capability("Secure workspace filesystem", "wakeup3lm/workspace.py"),
        capability("Kernel regression CI", ".github/workflows/wakeup3lm.yml"),
        capability("Browser IDE shell", "wakeup3lm/web/package.json"),
        capability("Monaco editor", "wakeup3lm/web/src/components/CodeEditor.tsx"),
        capability("xterm terminal", "wakeup3lm/web/src/components/Terminal.tsx"),
        capability("Preview gateway", "wakeup3lm/server/preview.py"),
        capability("Deployment adapter", "wakeup3lm/deployment.py"),
    ]
    rows = "\n".join(f"| {'✅' if ready else '🧭'} | {label} | {'Implemented' if ready else 'Next layer'} |" for label, ready in checks)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    SVG.write_text(render_svg(metrics), encoding="utf-8")
    return f'''{START}
## Live ecosystem pulse

> Generated automatically from the repository. Last refresh: **{stamp}**

<p align="center"><img src="./assets/ecosystem.svg" alt="Wakeup3lm animated ecosystem architecture" width="100%" /></p>

| State | Capability | Meaning |
| --- | --- | --- |
{rows}

**Repo telemetry:** `{metrics['modules']}` Wakeup3lm Python modules · `{metrics['tests']}` test files · `{metrics['workflows']}` workflows · `{metrics['ontology']}` ontology object types.

**Current ontology:** {', '.join(f'`{x}`' for x in ont)}.
{END}'''


def main() -> None:
    text = README.read_text(encoding="utf-8")
    block = render_auto_block()
    if START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        text = before + "\n\n" + block + "\n\n" + after
    else:
        anchor = "## Identity"
        if anchor in text:
            text = text.replace(anchor, block + "\n\n" + anchor, 1)
        else:
            text += "\n\n" + block + "\n"
    README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
