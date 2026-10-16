# GPT-Doug Biochip / MLM Life Colony

A **working, local, standard-library-only digital research colony** connecting AI agent roles to eight modeling levels: molecular, cellular, tissue, organ, organism, ecosystem, biochip, and robotics.

## Architecture

- **Brain:** `gpt-doug-llm` routes questions.
- **Colony:** `gpt-doug-mlm` coordinates evidence synthesis.
- **Biochip:** `gpt-biochip` represents digital sensing and cellular interfaces, not implanted or cultured hardware.
- **Humanoid:** `gpt-humanoid` models perception and embodied systems with no real-world actuation.
- **Organoid:** `gpt-organoid` indexes organoid and tissue literature, never conducts culture procedures.
- **Long-term memory:** SQLite keeps evidence, proposals, and event provenance.
- **Heartbeat:** timestamped audit events, with digest; no background process is started.
- **Human boundary:** no external actions, wet-lab execution, robot control, or medical advice.

## Run

```sh
python3 -m colony.life_colony --db colony.sqlite3 status
python3 -m colony.life_colony --db colony.sqlite3 ingest --domain cellular --topic membrane --statement "Example source-backed observation" --source "https://example.org/paper" --confidence 0.4
python3 -m colony.life_colony --db colony.sqlite3 propose --agent gpt-organoid --domain cellular --question "Compare published organoid models"
python3 -m unittest discover -s colony -p 'test_*.py' -v
```

Evidence is never fabricated by the colony: source strings and confidence are user supplied, and proposals **always** require further review. Runtime data should not be committed. Literature supplied by others is not permission to reproduce patented techniques commercially.

This is a digital life-science ontology, **not a biological organism, autonomous general intelligence or functional physical biochip**.
