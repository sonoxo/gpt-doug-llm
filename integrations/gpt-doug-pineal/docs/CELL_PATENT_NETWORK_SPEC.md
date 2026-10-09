# PINEAL Cell Atlas + Patent Knowledge Network — Specification

## Deliverable
Extend the existing local-first GPT-Doug Pineal gateway with a **read-only, educational human-cell ontology**, a **symbolic state simulator**, a **globally extensible patent-publication index**, safe opt-in official patent metadata lookup, and an animated Mac terminal `blink` display. Each result must distinguish the information source, model status, and data-connection state.

## Boundary and trust
- Humans are biological systems; DNA is not computer binary, and a numerical/symbolic simulation does not create a living cell or a human.
- No wet-lab protocols, embryo-development procedures, genome-editing instructions or neural read/write claims are produced by this package.
- Human parthenogenesis is a research topic: human parthenogenetic reproduction is not established; genomic imprinting is a critical biological barrier. Patent disclosure is *not* proof of scientific validity, safety, efficacy, freedom to operate, or any product status.
- Patent ingestion is only from user-held public/authorized metadata exports or opt-in official endpoints; never scrape PATENTSCOPE or evade an API's authentication, licenses, rate limits, or terms.
- All import and search works offline by default; live lookup is a one-record EPO bibliographic lookup **only when user passes `--online`**. Other jurisdictions use public/authorized export and future licensed adapters. No assertion of universal completeness.
- All persistent mutations are local SQLite transactions with provenance and hash-chain audit. Reject suspicious credentials, oversized files, invalid publication IDs, unauthorized URL hosts, and malformed dates. Import is atomic: all accepted or none.
- Python >=3.10, standard-library runtime, pytest; terminal must support ANSI and non-TTY (no forced color). No API keys required for offline mode.

## CLI / API
- `pineal cells list` returns curated human cell classes, functions, lineage descriptions, and research evidence notes.
- `pineal cells simulate CELL --steps N` returns deterministic SYMBOLIC stages; no claims of experimental prediction.
- `pineal patents sources|import FILE|search TEXT|stats|fetch EPXXXXXXXA1 --online`: local import/search/catalog + opt-in single EPO lookup. Local JSONL/CSV source file uses `publication_id,title,publication_date,abstract,source,source_url,cpc,cell_tags` metadata. `source_url` restricted to recognized official/public metadata hosts. `fetch` must reject other jurisdictions and no `--online`.
- `pineal blink [--watch] [--frames N] [--interval SEC] [--no-color]` renders an educational cell heartbeat and patent index count in terminal; Ctrl-C stops, not a background daemon.
- `pineal context QUERY` and authenticated `/v1/context?q=` combine local patent citation matches, curated cell references, ontology and external memory (without treating patent abstracts as verified knowledge).
- Authenticated read-only `GET /v1/cells`, `/v1/patents`, `/v1/patents/sources`; external connections never implied.
- Existing federation dashboard adds cell atlas/patent count + trusted-source notice; no network calls.

## Data contracts
- Dedupe keyed by normalized publication ID (jurisdiction, numeric identifier and kind code); repeated imports skip matching records. A conflicting record for same identifier fails closed instead of silently replacing provenance.
- URL source host is validated exactly (not suffix-matched) against a curated official metadata whitelist. No redirect to an unapproved host.
- Optional cell links are curated human cell-type IDs; title/abstract keywords alone cannot assert scientific validation.
- Search uses bounded SQL substring matching across publication ID/title/abstract/CPC, with no arbitrary SQL and no remote lookups.
- EPO live JSON records are stored only if publication ID and metadata are validated; source must be official and marked as unverified publication metadata.
