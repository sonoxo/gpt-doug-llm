# SHAGGOTH-KRAKEN Patent Knowledge Network

This is a **local patent-publication metadata index**, not a global mirror of patents, a validated experimental biology database, a live financial feed, or a legal freedom-to-operate opinion. The term "wire to all patents" is implemented as a **source-agnostic bibliographic import contract**, plus a deliberately limited on-demand EPO public-reference adapter. Coverage remains 0 until records are imported or retrieved explicitly.

## Patent sources, availability and restrictions

| Source | Integration | Credential and usage constraint |
| --- | --- | --- |
| EPO Linked Open EP Data | Opt-in **single known EP publication** lookup (metadata only) | Occasional use, fair-use limits, attribution under CC BY 4.0; do not use as a bulk production database. The adapter's live response schema and availability must be checked against current EPO documentation before production reliance. |
| EPO Publication Server | Source reference / permitted user-supplied export | Separate fair-use terms; not an automated downloader in this build. |
| USPTO Open Data Portal | Local authorized metadata import | Registration and API key required for ODP API; this repository does not provide them. |
| PatentsView | Local authorized metadata import | As of 2026, its API may require a key; provider availability may change. |
| WIPO PATENTSCOPE | Links/authorized metadata import only | **No automated scraping, public-site bulk collection, or programmatic search** without an appropriate agreement. |
| Other jurisdictions | Valid metadata import from documents you may lawfully use | The core ID format is authority code + number + kind (e.g. `JP...A1`); official-source URL whitelist must be extended/validated for each source before import. |

Sources:
- EPO overview and licensing: https://www.epo.org/en/searching-for-patents/data/linked-open-data
- EPO linked data API reference: https://data.epo.org/linked-data/documentation/api-reference
- EPO developer API (OAuth for OPS): https://developers.epo.org/home-page
- USPTO Open Data Portal: https://data.uspto.gov/apis/bulk-data/search
- WIPO PATENTSCOPE usage restrictions: https://www.wipo.int/en/web/patentscope/data/terms_patentscope
- PatentsView API key notes: https://github.com/PatentsView/PatentSearch-API/blob/main/docs/docs/Search%20API/Examples.md

## Local import (offline)

Import your own authorized patent-publication metadata, not complete specifications or molecular sequences. A JSONL file contains exactly one metadata object per line:

```json
{"publication_id":"US20260313851A1","title":"System and method for supplemental power and cooling","publication_date":"2026-10-08","abstract":"Describes supplemental power and cooling for an electrical load.","source":"USPTO user-supplied public excerpt","source_url":"https://patents.google.com/patent/US20260313851A1/en","cpc":"H05K7/20772","cell_tags":[]}
```

The record above references a public server-cooling patent application, **not** a human-cell creation method. Source/title/metadata must be independently verified before any research or business decision. The example can be saved locally as `my-patents.jsonl`.

```bash
pineal patents sources
pineal patents import my-patents.jsonl
pineal patents search cooling
pineal patents stats
pineal blink --watch --interval 0.7
```

Alternatively, `pineal patents import records.csv` supports a CSV with columns `publication_id,title,publication_date,abstract,source,source_url,cpc,cell_tags` (last column comma-separated). Limits: **8 MiB** per file, **1,000** records by default (configurable 1–10,000, still 8 MiB limit), citation-source host allowlist, no APIs called. The import validates all records and writes in a single transaction; duplicates with identical metadata are skipped, conflicting IDs abort the entire import. Index data lives only in your own PINEAL SQLite state store. No patient, biometrics, or government-restricted data.

## Opt-in direct metadata lookup

```bash
pineal patents fetch EP0084638A1 --online
```

This sends **one** request to EPO's Linked Open Data known-publication endpoint over HTTPS, with a short timeout, redirect blocking and a **128 KiB** response cap. It will reject malformed/unexpected responses and will not start crawlers. No proof of endpoint uptime or successful live fetch is claimed in this repository; source-specific and network constraints still apply.

## Scientific boundaries

A published patent application can describe a proposed technology without showing that it works. The **human cell ontology** is curated educational information; its deterministic states are symbolic, not a molecular dynamics, developmental biology, or tissue-engineering simulation. DNA encodes biochemical information and is not binary computer code. Human parthenogenesis is not an established means of producing viable humans; genomic imprinting is a critical biological barrier. Research involving embryos or derived cell lines involves significant scientific, ethical and legal limits.

Research background:
- Kono, "Genomic imprinting is a barrier to parthenogenesis in mammals": https://pubmed.ncbi.nlm.nih.gov/16575160/
- Review, "Parthenogenesis and Human Assisted Reproduction": https://pmc.ncbi.nlm.nih.gov/articles/PMC4655294/
- NIH Grants Policy Statement human embryo research/cloning restrictions: https://www.grants.nih.gov/grants/policy/nihgps/HTML5/section_4/4.2.4_human_embryo_research_and_cloning_ban.htm

No code in this package creates, cultures, modifies or implants human cells or embryos, accesses private model or human thoughts, or directs physical equipment.
