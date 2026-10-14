"""Evidence-grounded CL1 mitochondrial reference model.

This module never connects to CL1 hardware or Cortical Cloud. It exposes a
scientific reference model of canonical neuronal mitochondrial anatomy and a
versioned evidence registry. It does not claim that a CL1-specific mitochondrion
has been imaged or reconstructed.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "intel" / "sources" / "cl1-mitochondria-2026-10-13-evidence.json"


def load_evidence() -> dict:
    data = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "gpt-doug-cl1-mitochondria-evidence/v1":
        raise ValueError("unexpected CL1 mitochondrial evidence schema")
    return data


def model() -> dict:
    data = load_evidence()
    return {
        "id": "cl1-neuronal-mitochondrion-reference-v1",
        "status": "scientifically_grounded_reference_model",
        "device_specific_reconstruction": False,
        "hardware_connection": False,
        "source_registry": str(EVIDENCE_PATH.relative_to(ROOT)),
        "components": data["model_components"],
        "geometry": {
            "body": {"shape": "prolate_ellipsoid", "normalized_axes": [1.0, 0.52, 0.52]},
            "outer_membrane": {"relative_radius": 1.0},
            "inner_membrane": {"relative_radius": 0.84},
            "cristae": {"count": 11, "layout": "folded_lamellae_reference"},
            "matrix": {"relative_radius": 0.78},
            "mtdna": {"representation": "two_closed_loops_reference"},
            "atp_synthase": {"representation": "distributed_inner_membrane_markers"},
            "micos": {"representation": "crista_junction_markers"},
        },
        "claim_limits": data["prohibited_inferences"],
    }


def html_document() -> str:
    m = model()
    cards = "".join(
        f"<li><b>{html.escape(item['label'])}</b><span>{html.escape(item['evidence'])}</span></li>"
        for item in m["components"]
    )
    return f"""<!doctype html>
<meta charset="utf-8">
<title>GPT-Doug CL1 Mitochondrial Reference Model</title>
<style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif;background:#071019;color:#eaf7ff}}
body{{max-width:1100px;margin:0 auto;padding:28px}}
h1{{margin:0 0 6px}} .note{{color:#9fc1cf;margin-bottom:24px}}
.grid{{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(260px,.8fr);gap:24px}}
.stage{{min-height:470px;display:grid;place-items:center;border:1px solid #28424f;border-radius:18px;background:#0b1722;perspective:900px;overflow:hidden}}
.mito{{position:relative;width:min(76vw,560px);aspect-ratio:1.9/1;border:10px solid #6ab7c9;border-radius:50%;transform:rotateX(-12deg) rotateY(18deg);box-shadow:inset 0 0 0 18px #132b38,inset 0 0 60px #0008}}
.inner{{position:absolute;inset:14%;border:5px solid #b7dde8;border-radius:48%}}
.crista{{position:absolute;left:20%;right:20%;height:6%;border-radius:999px;background:#d9f2f8;opacity:.9;transform-origin:center}}
.crista:nth-child(1){{top:24%;transform:rotate(16deg)}} .crista:nth-child(2){{top:36%;transform:rotate(-13deg)}} .crista:nth-child(3){{top:48%;transform:rotate(18deg)}} .crista:nth-child(4){{top:60%;transform:rotate(-17deg)}} .crista:nth-child(5){{top:72%;transform:rotate(11deg)}}
.dna{{position:absolute;width:54px;height:54px;border:4px solid #f2d66b;border-radius:50%;left:44%;top:41%;box-shadow:18px 0 0 -12px #071019,18px 0 0 -8px #f2d66b}}
ul{{list-style:none;padding:0;margin:0;display:grid;gap:10px}} li{{border-bottom:1px solid #203946;padding:10px 0}} li span{{display:block;color:#9fc1cf;font-size:.9rem;margin-top:3px}}
.badge{{display:inline-block;padding:5px 9px;border:1px solid #376070;border-radius:999px;color:#a8d6e3;font-size:.8rem}}
@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.stage{{min-height:360px}}}}
</style>
<h1>CL1 neuronal mitochondrion — reference anatomy</h1>
<p class="note"><span class="badge">RESEARCH ONLY</span> Not a CL1 microscopy reconstruction. The CL1 public API exposes neural electrical activity, not mitochondrial imaging or ATP telemetry.</p>
<div class="grid">
<section class="stage" aria-label="3D-style mitochondrial reference model">
  <div class="mito"><div class="inner"><i class="crista"></i><i class="crista"></i><i class="crista"></i><i class="crista"></i><i class="crista"></i><div class="dna" title="mtDNA reference"></div></div></div>
</section>
<section><h2>Evidence-linked anatomy</h2><ul>{cards}</ul></section>
</div>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("evidence")
    sub.add_parser("model")
    h = sub.add_parser("html")
    h.add_argument("--output", type=Path, default=Path("cl1-mitochondria.html"))
    args = parser.parse_args(argv)

    if args.cmd == "evidence":
        print(json.dumps(load_evidence(), indent=2))
    elif args.cmd == "model":
        print(json.dumps(model(), indent=2))
    else:
        out = args.output.expanduser().resolve()
        out.write_text(html_document(), encoding="utf-8")
        print(json.dumps({"status": "written", "output": str(out), "device_specific_reconstruction": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
