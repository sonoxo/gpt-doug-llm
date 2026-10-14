# GPT-Doug-MLM — Multi-Dimensional Millennium Engine

GPT-Doug-MLM is a proof-search and verification framework for the six open
Millennium Prize Problems, with the Poincare Conjecture retained as a solved
reference/formalization track.

It **does not claim that the open problems are solved**. Its purpose is to make
mathematical progress auditable: every claim has dependencies, evidence, barrier
checks, contradiction state, formal-verification state, and independent reviewers.

## Six active tracks

| Slug | Track | Decisive proof obligation |
|---|---|---|
| `riemann` | Riemann Hypothesis | Close a positivity/spectral/equivalent criterion forcing all nontrivial zeros to the critical line |
| `navier-stokes` | Navier-Stokes | Close a scale-critical global estimate or construct a valid finite-time singularity |
| `p-vs-np` | P vs NP | Obtain a decisive complexity result while addressing relativization, natural-proofs and algebrization barriers |
| `yang-mills` | Yang-Mills | Construct the continuum theory and prove a cutoff-independent positive mass gap |
| `bsd` | Birch-Swinnerton-Dyer | Control higher-rank arithmetic strongly enough for rank equality and the leading-term formula |
| `hodge` | Hodge | Produce algebraic cycles for arbitrary rational Hodge classes |

## Sixteen reasoning dimensions

Each track is projected into sixteen views:

1. formal statement
2. equivalent formulations
3. known theorems
4. known barriers
5. candidate lemmas
6. counterexamples
7. symbolic computation
8. numerical experiments
9. geometric interpretation
10. spectral interpretation
11. probabilistic interpretation
12. algebraic interpretation
13. topological interpretation
14. scale/asymptotics
15. formal proof
16. independent verification

## Proof gates

Claims may advance only one state at a time:

`UNTESTED -> NUMERICALLY_SUPPORTED -> SYMBOLICALLY_VERIFIED -> LEMMA_PROVEN -> FORMALLY_VERIFIED -> INDEPENDENTLY_VERIFIED -> PUBLISHABLE`

The engine intentionally rejects jumps. Numerical evidence can never be promoted
directly to a theorem.

## Multi-model operation

`gpt_doug_mlm.providers.ProviderRegistry` is an opt-in adapter registry. An operator
can register multiple authorized model backends and use them for proposal and review
roles. No external model is contacted automatically, and no credentials are stored
in this package.

A recommended ensemble assigns different models to different functions:

- proposer
- counterexample finder
- known-result redundancy checker
- barrier reviewer
- formalizer
- independent verifier

Agreement between models is not proof. A claim still needs the evidence gates above.

## CLI

~~~sh
gpt-doug-mlm status
gpt-doug-mlm problem riemann
gpt-doug-mlm matrix --problem navier-stokes --replicates 4 --limit 64
gpt-doug-mlm barriers p-vs-np --addressed relativization,natural_proofs,algebrization
~~~

A full default open-problem matrix with four replicates contains:

`6 problems x 16 dimensions x 4 roles x 4 replicates = 1,536 work items`

Increasing to 32 replicates yields 12,288 bounded logical investigations. Work-item
generation does not spawn processes or make external API calls.

## Research integrity

A candidate Millennium solution should not be labeled solved merely because it:

- works numerically for many instances;
- is supported by several LLMs;
- matches a symbolic-algebra experiment;
- proves a special case;
- restates an equivalent conjecture;
- relies on an unproved intermediate lemma.

The final standard is a complete mathematical proof with independently checkable
dependencies and, where feasible, proof-assistant verification.
