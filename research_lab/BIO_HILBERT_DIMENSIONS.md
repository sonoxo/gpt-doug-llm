# GPT-Doug Bio-Hilbert: dimensions 6 to infinity

## Mathematical status

This is an **original engineering specification of a toy model using standard mathematical results**, not a newly proven theorem in mathematics, not evidence of a biological computer, not measured brain/immune system dynamics, and not a physical infinite-dimensional processor. The design is reproducible with Python's standard library and exact rational arithmetic.

Six *conceptual* channels per layer are ordered as neural, metabolic, immune, epigenetic, sensory and memory. Their labels have no operational biomedical interpretation without empirical identification and validation.

## Infinite-dimensional field equation

Let `H = ell^2(N; R^6)` be the real Hilbert space of square-summable sequences of six-dimensional blocks. For each layer `j = 1,2,...`, with left Dirichlet boundary `X_0 = 0`, define

```text
  dX_j/dt = -alpha*X_j
            + kappa*(X_(j-1) - 2*X_j + X_(j+1))
            + Omega*X_j + beta*sat(X_j) + U_j(t)
  sat(z) = z/(1+abs(z)) coordinatewise.
```

`Omega` is block-diagonal with the three skew-symmetric blocks:

```text
  [ 0   -omega_1 ]    [ 0   -omega_2 ]    [ 0   -omega_3 ]
  [ omega_1  0  ]    [ omega_2  0  ]    [ omega_3  0  ]
```

The intended channel-pair connections are conceptual and do not imply measured biochemical couplings. All coefficients in the implementation are exact rational numbers.

Assume `alpha > beta >= 0` and `kappa >= 0`. Allow `U` to be locally integrable with values in H, or set `U = 0` as the simulator does. Define `delta = alpha-beta > 0`.

### Analytical statement: existence and decay

- The discrete half-line Laplacian `D X_j = X_(j-1)-2X_j+X_(j+1)` is a **bounded** linear operator on H, with `||D|| <= 4`, and `<X,D X> = -sum_(j>=0)||X_(j+1)-X_j||^2` for `X_0 = 0`.
- Since `z/(1+|z|)` is 1-Lipschitz and vanishes at zero, it induces a globally 1-Lipschitz map on H. The skew operator `Omega` is bounded with norm `max_i |omega_i|`.
- Consequently the nonlinear vector field is globally Lipschitz with bound `L = alpha + 4*kappa + max_i |omega_i| + beta`; the system has a unique global solution for each `X(0) in H` (and suitable forcing U).
- Because `<X,Omega X> = 0` and `z*sat(z) <= z^2`, the energy `E = ||X||^2/2` satisfies

```text
  dE/dt <= -delta*||X||^2 + <X,U>.
```

For `U=0`, this implies `||X(t)|| <= exp(-delta*t)*||X(0)||`. For `U != 0` it implies the standard input-to-state estimate

```text
  ||X(t)|| <= exp(-delta*t)*||X(0)||
           + integral_0^t exp(-delta*(t-s))*||U(s)|| ds.
```

This is a theorem about the **specific toy equation** on H, **not** a universal result about biological intelligence, the Navier–Stokes equations, or arbitrary nonlinear PDEs. The model's memory channel decays without input; persistent external knowledge requires a separate durable storage system.

### Exact finite truncation and Euler certificate

Use the `n`-layer Galerkin truncation with `X_0=X_(n+1)=0`. It has `6n` coordinates; **n may grow arbitrarily in the theorem**, while the executable currently caps `n<=128` for safety and reproducibility.

For exact-rational explicit Euler with step `h`, compute

```text
  X[k+1] = X[k] + h*F_n(X[k])
  q = 1 - 2*h*delta + h^2*L^2.
```

If `0 < h < 2*delta/L^2`, then `0 <= q < 1`, and

```text
  ||X[k+1]||^2 <= q*||X[k]||^2.
```

This follows from `<X,F_n(X)> <= -delta*||X||^2` and `||F_n(X)|| <= L||X||`. The code checks every step with **exact fractions**, without numerical tolerance or claims of an exact continuous-time trajectory.

### Honest finite-to-infinite computational error

For finite Euler vectors padded with zeros in H, the **only omitted mode** of the infinite Euler map is the `(n+1)`st, equal to `h*kappa*X_n`. The infinite Euler map contracts distances by at most `sqrt(q)`, bounded above by the rational number `rho = (1+q)/2`. Hence its true approximation error is bounded by the recursively computed rational quantity

```text
  e[0] = 0
  e[k+1] = rho*e[k] + h*kappa*sum_(a=1)^6 abs(X_n[k,a]).
```

For finite-support initial data with largest nonzero layer `m`, nearest-neighbor interactions ensure the **infinite Euler state is represented exactly** after `K` steps whenever `n >= m+K`; the code certifies this sufficient condition. This is **not** a statement that the continuous-time infinite solution has strictly finite-speed propagation. The stored boundary residual has squared norm `kappa^2*||X_n||^2` for the continuous generator at the current finite state.

## Exact worked example

Choose `alpha=3`, `beta=1`, `kappa=1/4`, `(omega_1,omega_2,omega_3)=(1/4,1/8,1/16)` and `h=1/16`.

Then `delta=2`, `L=21/4`, `q=3513/4096`, and the continuous norm decay bound is `exp(-2t)`. With the first layer initialized as `(1,0,0,0,0,0)` and all other layers zero, the exact first Euler step at layer 1 is `(13/16,1/64,0,0,0,0)` and the newly activated second layer is `(1/64,0,0,0,0,0)`. A one-layer truncation misses the latter, while two layers reproduce the entire first infinite Euler step exactly.

For **one** layer the squared norm after one step is `2705/4096`. For **two or more** layers it is `2706/4096`. The finite-truncation error after one step is exactly `1/64` in the H norm for the one-layer approximation; the algorithm's rational upper bound is also `1/64`. These are exact results for a specific discrete-time Euler update of the model, not observational biocomputing measurements.

## Run from the GitHub repository root

```sh
bash scripts/doug-max bio-infinity demo
bash scripts/doug-max bio-infinity analyze research_lab/examples/bio_hilbert_6_to_infinity.json > bio_certificate.json
bash scripts/doug-max bio-infinity verify bio_certificate.json
bash scripts/doug-max bio-infinity hierarchy research_lab/examples/bio_hilbert_hierarchy.json --levels 1,2,4,8,16,32
python3 -m unittest discover -s research_lab/tests -p 'test_bio_hilbert.py' -v
```

The hierarchy command accepts a problem containing only `model`, `initial`, and `steps`; its different finite sizes all represent the same initial condition. Use `git switch` to the review branch until the pull request is merged.

Input caps: `n<=128` (at most 768 coordinates per step), at most 8 exact Euler steps, max 64 KiB JSON input, 8192-bit rational numerator/denominator, no external requests and no model or API tokens. All output contains replayable exact results with a SHA-256 **integrity digest** (not an authenticated signature). The verification command recomputes every certificate and rejects tampering.

### Reference mathematics

The Banach-space Picard theorem and global Lipschitz theory are standard, e.g. J. K. Hunter, *Nonlinear Evolution Equations*, UC Davis lecture notes, https://www.math.ucdavis.edu/~hunter/notes/nonlinev.pdf. The fact that smooth non-globally-Lipschitz infinite-dimensional systems can behave differently is discussed in Dahmen & Glockner (2014), https://arxiv.org/abs/1402.1692. The assumptions here are purposely global Lipschitz to avoid such issues.
