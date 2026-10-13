"""BioPineal: offline, provenance-first comparative knowledge atlas.

This is a research index, not evidence of anomalous technology or AGI.
No network crawling, self-replication, external API calls or hardware access.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict, dataclass
from typing import Literal

Evidence = Literal["primary-text", "established-history", "government-report", "vendor-documentation", "hypothesis"]

@dataclass(frozen=True)
class Entry:
    id: str
    topic: str
    proposition: str
    classification: Evidence
    source_title: str
    source_url: str
    caveat: str

ENTRIES = (
    Entry("hermeticism-corpus", "Hermeticism", "Hermetic writings reflect late-antique philosophical and religious traditions.", "primary-text", "Corpus Hermeticum", "https://www.tertullian.org/rpearse/manuscripts/corpus_hermeticum.htm", "Claims of supernatural efficacy or physical laws are not established by the text."),
    Entry("emerald-tablet", "Hermeticism", "The Emerald Tablet is a historically influential alchemical text with multiple transmission and translation traditions.", "primary-text", "Emerald Tablet textual history", "https://www.britannica.com/topic/Emerald-Tablet", "Interpret symbolism as historical ideas, not validated empirical laws."),
    Entry("atlantis-plato", "Atlantis", "Atlantis appears in Plato's Timaeus and Critias.", "primary-text", "Plato, Timaeus", "https://www.perseus.tufts.edu/hopper/text?doc=Plat.+Tim.", "The existence of an advanced sunken civilization is not established by this source."),
    Entry("egypt-history", "Ancient Egypt", "Ancient Egyptian material culture can be studied through museum collections.", "established-history", "The Metropolitan Museum of Art: Egyptian Art", "https://www.metmuseum.org/about-the-met/collection-areas/egyptian-art", "Specific claims require object-level dating, inscriptions, and provenance."),
    Entry("uap-nasa", "UAP", "NASA published a 2023 independent study recommending better data collection and scientific analysis of UAP.", "government-report", "NASA UAP Independent Study", "https://science.nasa.gov/uap/", "Unidentified does not establish extraterrestrial origin."),
    Entry("uap-unknown", "UAP", "The extraterrestrial origin of unidentified observations is a hypothesis, not a verified finding.", "hypothesis", "NASA UAP Independent Study", "https://science.nasa.gov/uap/", "Do not promote hypotheses into facts without independent reproducible evidence."),
    Entry("cl1-simulator", "BioComputing", "The Cortical Labs simulator generates synthetic non-learning control data.", "vendor-documentation", "Cortical Labs CL SDK", "https://github.com/Cortical-Labs/cl-sdk", "Vendor documentation describes synthetic simulator behavior, not biological learning."),
)

def query(topic: str | None = None) -> list[dict]:
    return [asdict(e) for e in ENTRIES if topic is None or topic.casefold() in e.topic.casefold()]

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", help="Case-insensitive filter by topic")
    p.add_argument("--format", choices=("json", "jsonl"), default="json")
    args = p.parse_args()
    rows = query(args.topic)
    if args.format == "jsonl":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    else:
        print(json.dumps({"engine": "gpt-doug-biointel-atlas-v1", "entries": rows, "count": len(rows), "asserts_superintelligence": False}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
