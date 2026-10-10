# Bio-Gpt // GPT-Doug + Pineal + Shaggoth + Chaos + Redpanda

**Project name:** `Bio-Gpt`  
**Repository:** `sonoxo/gpt-doug-llm`  
**Model class:** exactly specified, globally dissipative Hilbert-space toy dynamics.

This is a mathematical/software integration, not measured biological computing, a neural implant, a new physical law, consciousness, independent AI autonomy, or proof of universal intelligence. The five existing components are **hardcoded as mathematical operators and source provenance**, without importing, starting, granting access to, or communicating with their real runtime services.

## The equation (six channels, infinitely many layers)

Let `H = ell2(N;R^6)` with `X_0=0`. Extend the existing `research_lab.bio_hilbert` field `F0`:

```text
  dX_j/dt = F0(X)_j + S X_j + U_j(t)       j = 1, 2, ...
  F0(X)_j = -alpha X_j + kappa(X_(j-1)-2X_j+X_(j+1))
              + Omega X_j + beta sat(X_j)
  sat(z)   = z/(1+abs(z)) coordinatewise
  S        = sum_(r in ROLES) eta_r J_(a_r,b_r)
  (J_ab x)_a = -x_b; (J_ab x)_b = x_a; all other entries = 0
```

Each named component has a fixed, testable channel-operator edge:

| Name | Input -> output channel pair | Existing source in repo |
|---|---|---|
| `GPT-Doug` | neural <-> metabolic | `gpt_brain/math_mitochondria.py` |
| `GPT-Pineal` | metabolic <-> memory | `integrations/gpt-doug-pineal/src/pineal/store.py` |
| `GPT-Doug-Shaggoth` | immune <-> epigenetic | `gpt_zyra_shaggoth/bridge.py` |
| `GPT-Doug-Chaos` | epigenetic <-> sensory | `gpt_chaos/runtime.py` |
| `GPT-Doug-Redpanda` | sensory <-> memory | `redpanda-desktop/gpt_redpanda_llm.py` |

**These are active operators in `bio_gpt.py`**, not decorative labels. For `eta_r != 0`, changing any one role alters the six-dimensional field. The edges connect all six channels into a single graph. Source paths are traceability anchors only; this module does not run arbitrary source code.

## Exact infinite-space stability certificate

Assume `alpha > beta >= 0`, `kappa >= 0`, bounded rational `eta_r`, and skew-symmetric baseline `Omega`. Each `J_ab` satisfies `J_ab^T=-J_ab`, hence `<X_j, S X_j>=0`. The energy identity is

```text
  1/2 d||X||_H^2/dt = -alpha||X||_H^2
     - kappa sum_(j>=0)||X_(j+1)-X_j||_2^2
     + beta sum_(j,a) X_(j,a)^2/(1+|X_(j,a)|)
     + <X,U>.
```

Therefore, `delta=alpha-beta>0` gives the established norm bound

```text
  ||X(t)||_H <= exp(-delta*t)||X(0)||_H     [when U=0].
```

The five additional operators are bounded on `H`, with `||S|| <= sum_r |eta_r|`. Thus the full field is globally Lipschitz with conservative upper bound

```text
  L = alpha + 4*kappa + max(|omega_1|,|omega_2|,|omega_3|)
      + beta + sum_r |eta_r|.
```

The analytic theorem establishes a unique global mild/classical-in-state solution for the toy ODE in `H`; it is not a theorem about arbitrary biological tissue or nonlinear PDEs. For locally integrable input `U`, standard variation-of-constants/Gronwall estimates yield the forced norm bound stated in the certificate.

For explicit rational Euler of step `h`, a sufficient finite-mode energy certificate is

```text
  q = 1 - 2*h*(alpha-beta) + h*h*L*L,     0 <= q < 1;
  ||X[k+1]||^2 <= q||X[k]||^2.
```

All numerical checks use Python's exact `Fraction` arithmetic, including skew-energy cancellation. The Euler simulation has 1–128 layers (6–768 coordinates), 0–8 steps and fixed complexity caps. A single Euler step only spreads support by one layer; the truncation bound accounts for the otherwise missing `(n+1)`st layer. **Continuous time has no such finite exact-propagation horizon.**

## Interactive Terminal: Bio-Gpt

The original `bio-gpt demo` is a one-shot **JSON** output, not an interactive application. The corrected standalone package includes both required Python modules (`bio_gpt.py` and `bio_hilbert.py`), a text-based menu, and a Mac-compatible `run-Bio-Gpt.command` launcher. It uses only Python 3.9+ and makes **no network or API calls**.

From the repository root:

```sh
bash run-Bio-Gpt.command
# Or use the GPT-Doug launcher:
bash scripts/doug-max bio-gpt open
```

The `open` action shows four options: run the mathematical simulation, inspect five named operators, view the dimension hierarchy, and replay the proof certificate. Enter `q` to exit. Run `bash run-Bio-Gpt.command --once` to print a single dashboard and exit, for CI or diagnosis.

To launch from **any working directory**, pass an absolute path to `run-Bio-Gpt.command`. The script moves into its own directory first. The original JSON commands such as `bash scripts/doug-max bio-gpt demo` still work.

**What opens:** an interactive ASCII research console in an existing Terminal window. There is no native Mac graphical application or running agent swarm. A GitHub review branch must be checked out before using these new commands; the default `main` branch does not yet contain them.

## Command-line integration

After checking out the new review branch, from the repository root:

```sh
bash scripts/doug-max bio-gpt manifest
bash scripts/doug-max bio-gpt demo
bash scripts/doug-max bio-gpt analyze research_lab/examples/bio_gpt.json > bio_gpt_certificate.json
bash scripts/doug-max bio-gpt verify bio_gpt_certificate.json
bash scripts/doug-max bio-gpt hierarchy research_lab/examples/bio_gpt_hierarchy.json --levels 1,2,4,8,16,32
python3 -m unittest discover -s research_lab/tests -p 'test_bio_gpt.py' -v
```

`manifest` prints the five hardcoded roles and real repository source anchors. `analyze` outputs the exact finite trace and analytic proof assumptions; `verify` independently regenerates every field, rejecting altered certificates. The SHA-256 is a content digest, **not an authenticity signature**. No API key or cloud compute is required. The existing mathematical module `bio_hilbert.py` remains unchanged; a zero-strength Bio-Gpt role configuration exactly reproduces it.

## Demo parameters

```
alpha=3, beta=1, kappa=1/4, omega=[1/4,1/8,1/16], h=1/16
eta=(1/32,1/32,1/32,1/32,1/32)
delta=2, L=173/32, q=226537/262144 < 1
```

These are illustrative coefficients, **not measured neural, metabolic, immune or genomic values**. Role names are conceptual software architecture handles. There are no external actions, secret scanning, credential access, physical manipulation, or perpetual agent processes.