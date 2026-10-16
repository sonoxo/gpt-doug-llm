# GPT-Shoggoth Colony Router

Routes scoped research questions among `gpt-doug-llm`, `gpt-doug-mlm`, `gpt-biochip`, `gpt-humanoid`, and `gpt-organoid`.

Shoggoth is a real **task router with SQLite records**, not a deployed large language model, self-developing organism, or unrestricted autonomous swarm.

```sh
python3 -m colony.shoggoth --db colony.sqlite3 status
python3 -m colony.shoggoth --db colony.sqlite3 route --domain cellular --question "Compare published organoid studies"
python3 -m colony.shoggoth --db colony.sqlite3 route --domain biochip --question "Review digital sensing signal model" --evidence "source:reviewed-paper"
python3 -m unittest discover -s colony -p 'test_*.py' -v
```

Task states: `needs_evidence` or `awaiting_human_review`. External execution, autonomous experiments, system modification and robot operations are deliberately not available. This component does not make scientific conclusions from unsourced inputs.
