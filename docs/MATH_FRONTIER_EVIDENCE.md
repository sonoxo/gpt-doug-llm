# GPT-Doug Math Frontier: finite, replayable evidence

This component accelerates reproducible *bounded* mathematical research on authorized compute. It **does not solve** the infinite Goldbach or Collatz conjectures, the Riemann hypothesis, P versus NP, or any Millennium Prize problem. It is not quantum hardware, a quantum-speedup claim, or a formal proof assistant. Computed experimental evidence remains separate from mathematical theorem proofs.

## Run and verify real computations

From the repository root, Python 3.9+ (no dependency installation or provider token needed):

```sh
python3 -m gpt_brain.math_frontier catalogue
python3 -m gpt_brain.math_frontier run goldbach --start 4 --end 2000 --output goldbach-evidence.json
python3 -m gpt_brain.math_frontier verify goldbach-evidence.json
python3 -m gpt_brain.math_frontier run collatz --start 1 --end 1000 --output collatz-evidence.json
python3 -m gpt_brain.math_frontier verify collatz-evidence.json
python3 -m gpt_brain.cli math frontier run goldbach --start 4 --end 100
python3 -m unittest -v tests.test_math_frontier
```

Evidence files are written **only** when `--output` is explicitly provided. An existing file is never overwritten. No API keys, Internet access, background processes or external data permissions are required. Do not commit generated evidence to `main` without review; GitHub Actions stores per-shard artifacts.

## What is independently checked?

| Workload | Candidate algorithm | Certificate replayer | Truth established |
| --- | --- | --- | --- |
| Goldbach | Eratosthenes sieve and minimal prime-pair witness | Separate trial-division primality, exact sum, and minimality | Each tested even integer has a pair of prime summands in the stated range |
| Collatz | Exact iterative integer trajectory with bounded steps | Separate exact integer replay and peak/length comparison | Each *terminated* starting value reaches 1 within the stated step bound |

The verifier checks exact schema, coverage, case order, type constraints, status, mathematical witnesses and SHA-256 commitment. SHA-256 is an integrity checksum, **not** a signature, independent third-party audit, formal proof, or tamper-proof storage. Even complete success in a large finite range cannot establish a universal conjecture. Cases exceeding their step bound are **incomplete**, not counterexamples. Any Goldbach failure is marked for independent external review, never announced as a discovery automatically.

Per-call hard bounds control resource consumption: up to 2,000 tested cases, Goldbach upper endpoint 100,000, Collatz upper endpoint 20,000 and 5,000 steps per starting value. For larger ranges, partition jobs and combine separately verified artifacts; no unlimited computation or privilege escalation occurs.

## Scalable research infrastructure

[`.github/workflows/math-frontier-evidence.yml`](../.github/workflows/math-frontier-evidence.yml) creates a matrix of GitHub-hosted, isolated, bounded shards. Each job runs the generator and independent replayer, runs unit tests, and stores the machine-checkable evidence as a GitHub Actions artifact (30-day retention). Its scheduled run covers finite test ranges—not continuous infrastructure control. A green CI run establishes that these finite checks passed, nothing more. External or confidential data is not collected.

Possible future upgrades, separately reviewed: verified interval arithmetic for rigorously bounded numerical estimates; Lean or Coq checker integration with explicit proof artifacts; challenge registries with authoritative publication references; redundant independent implementations and reproducibility audits; workload scheduling across explicitly authorized runners; human-reviewed promotion into a distinct research-only ontology namespace. Model-generated proofs remain untrusted until checked against a sound, clearly documented proof system.

## Failure modes and gatekeeping

- A verification mismatch returns a nonzero exit code and does not write a success record.
- Duplicate JSON keys, missing cases, edited results, false universal claims, out-of-bounds work and altered digests are rejected.
- This code never takes control of outside networks or machines. A repository owner controls any GitHub Actions runs; no credentials or background deployments are established by these source files.
- A conjecture is not “solved” without a complete proof or rigorous counterexample and independent expert validation.
