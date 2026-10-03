# ZYRA-MSS USPTO Exhaustive Reader

This reader is the exhaustive corpus-ingestion path for a Patent Public Search result set. It is intentionally different from the curated patent-architecture sweep.

It performs:

1. PPUBS result enumeration through the documented external-search entry point.
2. Collection of every PDF link exposed by the result pages.
3. Bounded-concurrency PDF download (maximum six network workers).
4. PDF signature and SHA-256 verification.
5. Full-text extraction with `pdftotext` or `pypdf`.
6. SQLite FTS5 indexing of the complete extracted text.
7. A completion verdict that is `true` only when every discovered PDF was successfully indexed.

The 100 ZYRA-MSS workers are logical research/analysis roles. This tool does not claim 100 simultaneous external agents and does not bypass USPTO rate limits.

## Setup

On macOS with Google Chrome already installed:

```bash
python3 -m pip install --user playwright pypdf
brew install poppler   # optional but recommended for pdftotext
```

The script reuses the installed Chrome executable when available, so a separate Playwright Chromium download is normally unnecessary.

## Exhaustive Palantir corpus run

```bash
cd ~/gpt-doug-llm
python3 scripts/zyra_mss_uspto_reader.py crawl \
  --query palantir \
  --workers 6 \
  --output ~/.config/gpt-doug/zyra-mss-uspto-palantir
```

For a visible browser session during result enumeration, add `--headed`.

## Completion proof

```bash
python3 scripts/zyra_mss_uspto_reader.py doctor \
  --output ~/.config/gpt-doug/zyra-mss-uspto-palantir
```

`complete: true` is the only state that means every PDF discovered by the PPUBS result traversal was downloaded, hashed, text-extracted, and indexed. A partial run must remain `complete: false`.

## Search the completed corpus

```bash
python3 scripts/zyra_mss_uspto_reader.py search 'ontology AND permission'
python3 scripts/zyra_mss_uspto_reader.py search 'data migration'
python3 scripts/zyra_mss_uspto_reader.py search 'language model error analysis'
```

The corpus is stored at:

```text
~/.config/gpt-doug/zyra-mss-uspto-palantir/
  discovered.jsonl
  results.jsonl
  summary.json
  corpus.sqlite3
  pdf/
  text/
```

## Research and safety boundaries

Patent documents are treated as public prior-art/research material. ZYRA-MSS does not treat search hits as ownership proof, legal clearance, or freedom-to-operate analysis. Architecture derived from the corpus remains independently designed. Mission-support boundaries remain human-authorized and non-weapons: no autonomous targeting, weapons release, drone-swarm attack control, hostile engagement, critical-infrastructure disruption, or unattended real-world vehicle command.
