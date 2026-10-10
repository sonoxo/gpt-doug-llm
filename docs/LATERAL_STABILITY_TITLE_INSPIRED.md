# GPT-Doug — Lateral Stability & Mobility Tests (independent numerical model)

**Public source metadata recovered from YouTube oEmbed:** "Lateral Stability & Mobility Tests" — NoLimits AI, https://www.youtube.com/shorts/eNIFAcuEFVU?feature=share. The GitHub runner recovered a **public JPEG poster** depicting what appear to be robot-like machines during an indoor test, but moving video, frames extracted from the video, and captions were **not** accessible when this module was authored. This model is an independent demonstration inspired **only by the verified title**, not the video's hidden code or its observed mechanics.

## Dynamical system (exact 1D toy model)

For lateral position p, velocity v, timestep h, proportional and damping gains kp/kd, and bounded external disturbance d:

```
a = -kp*p - kd*v + d
v_next = v + h*a
p_next = p + h*v_next
```

The exact rational state equation is

\[ \binom{p_{k+1}}{v_{k+1}}
= \begin{pmatrix}1-h^2k_p&h(1-hk_d)\\-hk_p&1-hk_d\end{pmatrix}
\binom{p_k}{v_k} + \binom{h^2}{h}d_k. \]

Let \(\mu=\lVert A\rVert_\infty\) and \(\beta=\lVert B\rVert_\infty\). For any bounded perturbation \(\lvert d_k\rvert\le D\) and \(\mu<1\), exact vector-norm submultiplicativity yields

\[ \lVert x_k\rVert_\infty\le \mu^k\lVert x_0\rVert_\infty + \frac{\beta D(1-\mu^k)}{1-\mu}\le \max\left(\lVert x_0\rVert_\infty,\frac{\beta D}{1-\mu}\right). \]

This guarantees lateral position lies within a **chosen numerical corridor** of half-width `w` when that maximum is no greater than `w`. No claim about actual fall safety, locomotion, sensor reliability, physical center-of-pressure, human balance, joint torques or medical deployment follows.

## Sample exact certified case

Using h=1/2, kp=1, kd=2, p0=1/20, v0=0, D=1/100, w=1/10, the matrix and input are

\[A=\begin{pmatrix}3/4&0\\-1/2&0\end{pmatrix}, \quad B=\binom{1/4}{1/2}.\]

Then `mu=3/4`, `beta=1/2`, steady bound `beta*D/(1-mu)=1/50`, and initial norm `1/20`, so every position in this idealized model remains within `1/20 < 1/10` for **every disturbance sequence satisfying the specified bound**, not just the sampled sequence. The solver also checks exact finite steps and replays its SHA-256-digested report.

## Reproduce

```bash
bash scripts/doug-max lateral-stability demo > stability-report.json
bash scripts/doug-max lateral-stability verify stability-report.json
python3 -m unittest discover -s tests -p 'test_lateral_stability.py' -v
```

*This is an independent safe research feature corresponding to a subject identified by public metadata; it is **not an extraction or faithful reproduction** of the YouTube Short's unpublished code.* For real robotics tests, require contact dynamics, calibrated physical hardware, sensor models, actuator limits, motion safety engineering, and a safety review.
