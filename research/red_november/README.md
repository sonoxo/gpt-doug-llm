# RED NOVEMBER / KRAKEN

A local CPU research-compute engine for **finite mathematical experiments**, integrated into GPT-DOUG-LLM.

## Run

Requires Python 3.9+ and no third-party packages:

```bash
python3 research/red_november/kraken.py --limit 1000000 --output red_november_report.json
```

## Investigations

- Goldbach: search for even integers in range without two-prime decompositions.
- Collatz: verify finite starting values reach 1; record longest trajectory.
- Twin primes: count finite pairs `(p, p+2)`.

Three independent CPU processes run the searches. The program checks known results at bound 25,000 and returns a nonzero exit code if any baseline check fails. Reports contain the tested bounds and SHA-256 content digest (the digest is printed after the report file is written).

## Limits and research integrity

**None of these finite tests proves a universal conjecture.** A reported candidate requires independent mathematical verification. Compute is deliberately capped at 1,000,000 and does not access external machines or third-party services.

## Validate

```bash
python3 research/red_november/kraken.py --limit 25000 --output /tmp/kraken-verify.json
python3 -m py_compile research/red_november/kraken.py
```

The historical `red_november_report.json` is a snapshot from a previous run; regenerate it for the current system and time.
