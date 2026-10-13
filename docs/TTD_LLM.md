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
