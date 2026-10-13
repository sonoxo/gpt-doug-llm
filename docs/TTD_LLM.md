# GPT-Doug TTD-LLM — Talk to Data

A **local-first, read-only, ontology/schema-grounded data assistant** for the GPT-Doug-LLM ecosystem. This is a new application-level data-query layer and an Ollama *model specialization*, **not** newly trained foundation-model weights.

## Pipeline

```
Operator selects a local file and allowed tables
             |
     Inspected schema (ontology)
             |
  Local Ollama maps the question to JSON
             |
   Strict plan validator + compiler
             |
   SQLite SELECT + bound parameters
             |
  Bounded rows + source / SQL evidence
             |
   Local Ollama explains the query result
```

The LLM never executes model-generated SQL, shell commands, plugins, connectors, or mutations. The planner may choose only an inspected table and column, one of six comparison operators or `contains`, optional sorting, grouping, and approved aggregates (`count`, `sum`, `avg`, `min`, `max`). Bad model plans fail closed. Dataset values are treated as untrusted text.

## Free local setup

Requires Python 3.9+ and optionally [Ollama](https://ollama.com/) installed locally. No hosted LLM account, paid API key, or cloud database is needed.

```sh
# From the repository root, run a fully offline deterministic demonstration:
python3 -m ttd_llm --csv data/ttd_demo.csv --plan-file data/ttd_demo_plan.json

# To enable natural-language questions, install Ollama and start its local server.
# In another terminal (if Ollama is not already running):
ollama serve
ollama pull qwen2.5-coder:7b
ollama create gpt-doug-ttd -f Modelfile.ttd
python3 -m ttd_llm --csv data/ttd_demo.csv --ask 'Total revenue by region?'
```

A successful deterministic demonstration returns East **7600** and West **6800** with `SELECT`, bound parameters and source provenance. The custom Ollama model name `gpt-doug-ttd` is created only by `ollama create`; it is not included as model weights in the repository.

## Connect your own data

```sh
# Inspect schema first; no model required:
python3 -m ttd_llm --sqlite ./your_database.sqlite3 --table orders --schema

# Read-only natural-language question, with table allowlist:
python3 -m ttd_llm --sqlite ./your_database.sqlite3 --table orders --ask 'How many orders are there?'

# CSV/JSON: temporary in-memory SQLite import (table name is always "data"):
python3 -m ttd_llm --json ./my_records.json --ask 'Count records by category'

# Install from checkout if you prefer the console command:
python3 -m pip install -e .
gpt-doug-ttd --csv data/ttd_demo.csv --plan-file data/ttd_demo_plan.json
```

CLI returns JSON with `answer`, reviewed `plan`, bounded `rows`, `returned_rows`, `row_limit`, and `evidence` (`source`, `table`, `sql`, `params`). `DataCatalog.execute(plan)` is available directly in Python for higher-level GPT-Doug components to call. No data is persisted by the importer.

## Security, limitations, and future integration

- SQLite opens with `mode=ro` and `PRAGMA query_only=ON`; CSV/JSON are imported to in-memory SQLite and switched to query-only before queries.
- Dataset source files are explicitly chosen. For SQLite, use `--table` one or more times to restrict model-visible tables. There is **no row-level or per-user authorization**; do not expose this CLI to untrusted users or attach sensitive databases without an upstream access-control layer.
- Parameterized values, double-quoted schema-resolved identifiers, a small fixed query vocabulary, ≤8 filters, ≤50 result rows and an SQLite VM-step budget constrain queries. No joins, raw SQL, network connectors, arbitrary tools, database writes, or cross-source federation.
- CSV and JSON imports: ≤10 MB, ≤10,000 records, ≤64 unique columns; JSON must be an array of flat objects. Values longer than 500 characters are clipped in returned evidence; aggregation output must be reviewed for accuracy. Results may be partial at the query row cap.
- Model inference connects **only** to fixed `127.0.0.1:<port>` and honors the existing `ai_killswitch` emergency-stop hook. The host must secure the local Ollama service and files.
- Generated natural-language answers are **not guaranteed correct**. The returned rows and compiled SQL are the verification artifacts. For consequential decisions, require human review and dataset-specific validation.
- Next phases: ontology mappings with business synonyms, credentialed connectors with row-level policies, temporal semantics, retrieval over documents, confidence/evaluations, UI dashboards, and authorized publication to the GPT-Doug memory layer.

Run the isolated checks:

```sh
python3 -m unittest discover -s tests -p 'test_ttd_llm.py' -v
```

## Global Open Data Fabric (explicit opt-in)

Five public, official or openly documented read-only interfaces can be synchronized into
an **operator-controlled local SQLite snapshot**. This does not put the model on a
third-party network, scan the internet, or subscribe to all datasets worldwide.

| Source ID | Publisher | Dataset | Measurement |
| --- | --- | --- | --- |
| `usgs_earthquakes` | U.S. Geological Survey | Earthquakes during the previous day | Magnitude |
| `nasa_eonet` | NASA EONET | Current natural events | Event count |
| `worldbank_population` | World Bank Indicators V2 | Latest available country population | People |
| `worldbank_gdp` | World Bank Indicators V2 | Latest available country GDP | Current USD |
| `openalex_works` | OpenAlex | Bounded page of scholarly works | Citation count |

List sources and preview a reproducible randomized subset with **no network calls**:

```sh
python3 -m ttd_llm open-data sources
python3 -m ttd_llm open-data sync --all --randomize --seed 20261013 --sample-sources 3 --max-records 50 --db ttd_open_data.sqlite3 --dry-run
```

To perform one controlled synchronization (real HTTPS requests), remove `--dry-run`:

```sh
python3 -m ttd_llm open-data sync --all --randomize --seed 20261013 --sample-sources 3 --max-records 50 --db ttd_open_data.sqlite3
python3 -m ttd_llm --sqlite ttd_open_data.sqlite3 --table open_records --schema
python3 -m ttd_llm --sqlite ttd_open_data.sqlite3 --table open_records --plan-file data/ttd_open_data_plan.json
python3 -m ttd_llm --sqlite ttd_open_data.sqlite3 --table open_records --ask 'Count records by public data source.'
```

The last command requires the local Ollama model from the setup section. If the
snapshot already exists, synchronization refuses to replace it until `--replace`
is supplied. The snapshot is not scheduled, uploaded, shared, or published.

`--randomize` randomizes **only approved source order, optional source subset and
bounded record samples**. A reported seed permits repeating the same choices
against identical upstream data; the data may of course change over time. It
never randomizes IP addresses, proxies, identities, endpoint hosts, or rate limits.

The `open_records` table includes source ID, exact endpoint URL, record URL,
measurement and unit, source-observed time, fetch time, and individual record
SHA-256. The `source_receipts` table records publisher, documentation URL,
whole-response SHA-256, counts, and sampling seed. The read-only query model
should normally be authorized only for `open_records`; humans can inspect
`source_receipts` separately for provenance.

**Guardrails:** no arbitrary URLs, credentials, scraping, write-back, unattended
polling, or network exploration. Connections use HTTPS, strict endpoints,
no redirects/proxies, a ten-second timeout and 2.5 MB response cap. Sources are
queried sequentially, once per explicit invocation; sampling caps are 200 records
per source, with 50 by default. Failed sources are disclosed; if all fail the
existing snapshot remains unchanged. Public-data licensing and API terms still
apply. Statistics across incompatible units (magnitude vs. people vs. dollars)
are meaningless; always filter by `measure` when aggregating values.

Run regression coverage for both layers:

```sh
python3 -m unittest discover -s tests -p 'test_ttd*.py' -v
```
