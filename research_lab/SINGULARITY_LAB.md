# GPT-Doug Singularity Lab — exact scalar-ODE certificates

This is an offline, Python-standard-library research benchmark, **not** a solution to the Navier-Stokes, Einstein, or other open singularity problems. The certificates encode established differential-inequality arguments; no novel theorem or mathematical priority is claimed.

## Run

From the root of `sonoxo/gpt-doug-llm` with Python 3.9+:

```bash
python3 -m research_lab.singularity demo
python3 -m research_lab.singularity scan --coeffs '2,-3,1' --x0 4
python3 -m research_lab.singularity blowup --coeffs '2,-3,1' --x0 4 --p 2 --a 1/4
python3 -m research_lab.singularity bounded --coeffs '0,1,0,-1' --x0 1/2 --lo -1 --hi 1
python3 -m unittest research_lab.tests.test_singularity -v
```

Coefficients appear in increasing powers. For example, `2,-3,1` represents `P(x)=2-3x+x²`. The CLI outputs JSON containing exact rational witnesses. Save a single certificate to `proof.json`, then check it independently with:

```bash
python3 -m research_lab.singularity verify proof.json
```

Exit statuses: 0 success, 1 no certificate/invalid certificate, 2 invalid input. No tokens, API keys, external compute or network access are needed.

## Finite-time blow-up

For `x'=P(x)` with `x(0)=x0>0`, choose rational `a>0` and integer `p>=2`. Expand `Q(z)=P(x0+z)-a(x0+z)^p`. If **all coefficients of Q are nonnegative**, then `P(x)>=a*x^p` on `x>=x0`. Comparison gives finite-time blow-up by `T<=1/[a(p-1)x0^(p-1)]`. Example: `P(x)=x²-3x+2`, `x0=4`, `a=1/4`, `p=2` yields `Q(z)=2+3z+3z²/4` and `T<=1`.

This test is sufficient, **not necessary**; failure means inconclusive. It depends on standard local existence, uniqueness and continuation for polynomial ODEs.

## Global boundedness

For rational `lo<=x0<=hi` with `lo<hi`, check `P(lo)>=0` and `P(hi)<=0`. The closed interval is positively invariant for the scalar autonomous ODE; therefore its solution remains bounded and can be continued for all future time. Example: `P(x)=x-x³`, `x0=1/2`, `lo=-1`, `hi=1`.

## Research integrity and roadmap

- Store assumptions, exact witnesses, the source of each result, verification status and reproducible test evidence; integrate through existing research lineage and ontology controls, not new unrestricted execution privileges.
- Distinguish `BLOWUP_CERTIFIED`, `GLOBALLY_BOUNDED_CERTIFIED`, and `INCONCLUSIVE`. These are statements about scalar autonomous polynomial ODEs only, **not** partial differential equations.
- Verify known theorems first, then formulate precise conjectures, try counterexamples, and subject new findings to external expert review and ideally a Lean/Mathlib formalization.
- Expand toward certified polynomial barriers, verified PDE numerics with error bounds, fluid regularity criteria, gravitational singularity models and literature graphs.

### Current external research

- [OpenAI's September 8, 2026 Navier–Stokes research](https://openai.com/index/navier-stokes-solution/)
- [Clay Mathematics Institute's September 11, 2026 Navier–Stokes statement](https://www.claymath.org/news/navier-stokes-announcement/)

This module does not reimplement those results. An independently checked certificate in this repository does not establish novelty or solve a Millennium Prize Problem.
