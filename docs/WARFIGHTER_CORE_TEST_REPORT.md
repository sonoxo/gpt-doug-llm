# Warfighter Research Core - Local build verification

**Date:** 2026-10-12

**Environment:** Isolated working directory; Python 3.13.5; Linux; no cloned GitHub repository or independent worker/reviewer available in this sandbox.

**Validated:** A synthetic scenario passes bounded schema validation, deterministic hypothetical calculations, SHA-256 and implementation-hash replay, explicit local TTY review, research-only publication, immutable-event audit checking, publication revocation, and optional PINEAL projection through a test double. Source and tests are supplied as downloadable overlay and patch.

**Unavailable local integration checks:** Existing full repository's Bio-Hilbert and exact-linear modules, actual PINEAL SQLite store and old GPT-Doug/Zyra regression suites. These are not reported as passing. GitHub source branch not updated by local testing.

**Gates not claimed:** Independent subagent code review, DoD authorization, quantum-hardware execution, string-theory validation, real military operational readiness, external service connection, security certification.

Run after applying patch to the full repository:

```sh
python3 -m unittest discover -s research_lab/warfighter/tests -p 'test_*.py' -v
python3 -m unittest research_lab.tests.test_bio_hilbert research_lab.tests.test_multidimensional -v
python3 -m pytest -q tests/test_zyra_mss.py
PYTHONPATH=integrations/gpt-doug-pineal/src:. python3 -m pytest -q integrations/gpt-doug-pineal/tests/test_federation_store.py
```
