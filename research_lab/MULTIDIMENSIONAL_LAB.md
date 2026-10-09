# GPT-Doug // Exact Multidimensional Mathematics Lab

## Scope and limits

This local-first research component examines **specified, finite-dimensional linear dynamical systems with exact rational matrix coefficients**. It is not an omniscient system, a universal-intelligence oracle, a proof of nonlinear global regularity, or a solution to a Millennium Prize problem.

**Brute force** means *bounded and reproducible enumeration of mathematical integer vectors*, not attempts to discover credentials, bypass access controls, or scan external systems. No model provider, paid API, cloud account, network request, key or special compute is needed.

The engine supports dimensions 1–6. It performs two complementary analyses:

1. **Proof by rational Lyapunov certificate:** solve for symmetric positive-definite \(P\) satisfying the exact matrix identity:
   - Discrete \(x_{k+1}=Ax_k:\quad P-A^\top PA=I\).
   - Continuous \(\dot x=Ax:\quad A^\top P+PA=-I\).
   It rechecks all leading principal minors of \(P\), the equation residual, and exact rational coefficients, proving global exponential/asymptotic decay for that particular linear model.
2. **Finite integer-lattice exploration:** enumerate \(v \in [-r,r]^n\setminus\{0\}\), seeking positive \(\|Av\|_2^2-\|v\|_2^2\) (discrete) or \(2v^\top Av\) (continuous). A positive witness proves only **instantaneous/one-step Euclidean norm growth**, not long-term instability. No witness in a finite box proves nothing about all real vectors or arbitrary nonlinear evolutions.

## Run

From repository root, with **Python 3.9+**, using only the standard library:

~~~bash
bash scripts/doug-max math-lattice demo
bash scripts/doug-max math-lattice analyze research_lab/examples/multidimensional_nonnormal.json > certificate.json
bash scripts/doug-max math-lattice verify certificate.json
python3 -m unittest discover -s research_lab/tests -p 'test_multidimensional.py' -v
~~~

Alternatively, run as a module: \`python3 -m research_lab.multidimensional demo\`.

The CLI returns JSON. Analyze exits 0 for proven stability, 1 for INCONCLUSIVE, 2 for invalid input; the independent *replay* command exits 0 only when the entire report recomputes exactly. Its SHA-256 field is a content digest, not a signature or attestation of external facts.

Input schema:

~~~json
{
  "matrix": [["1/2", "2"], ["0", "1/2"]],
  "mode": "discrete",
  "radius": 2,
  "max_evaluations": 10000
}
~~~

- \`mode\`: \`discrete\` or \`continuous\`.
- Matrix coefficients: integer or exact rational strings; **no floating-point input**.
- Maximum matrix dimension: 6. Maximum search radius: 5. Maximum evaluations: 100,000, with deterministic traversal and an explicit \`SEARCH_LIMIT_REACHED\` outcome.
- File input is capped at 64 KiB and matrix coefficient numerators/denominators at \(10^6\).

## Independently checked demonstration

For

\[
A=\begin{pmatrix} 1/2 & 2 \\ 0 & 1/2 \end{pmatrix}
\]

the exact Lyapunov solution is

\[
P=\begin{pmatrix}4/3 & 16/9\\16/9 &356/27\end{pmatrix}.
\]

Both leading principal minors are positive (\(4/3\) and \(1168/81\)), and the identity \(P-A^\top PA=I\) has **exactly zero residual**. The system is globally asymptotically stable with the certified decay factor \(V_{k+1}\le(365/392)V_k\) for \(V(x)=x^\top Px\).

Yet the bounded integer search discovers \(v=(-2,-2)\) with

\[
\|Av\|_2^2-\|v\|_2^2=18>0.
\]

This is transient Euclidean amplification in a provably stable system. SymPy 1.14 independently confirmed the exact matrix residual, determinant, and witness magnitude in a local audit. This is an established linear algebra fact, **not a new theorem**.

## Evidence ontology

The accompanying [multidimensional_ontology.json](multidimensional_ontology.json) describes \`RationalLinearModel\`, \`LyapunovCertificate\`, \`FiniteLatticeExperiment\`, \`AmplificationWitness\`, and \`EvidenceRecord\` types. This schema is **not** automatically merged into GPT-Doug's canonical authority ontology and does not grant actions or external access.

The research record must maintain the distinction between a mathematical certificate, an empirical grid result, an unverified hypothesis, and a claim about real-world observations. Generalizing to nonlinear/PDE systems requires separately stated hypotheses, independent proofs and expert review.
