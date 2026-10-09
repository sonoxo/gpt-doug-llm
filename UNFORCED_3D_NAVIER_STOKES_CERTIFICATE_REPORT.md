# GPT-Doug Mathematics Research: Exact Unforced 3D Navier-Stokes Certificate

Date: 2026-10-09. Status: **VERIFIED CLASSICAL SPECIAL CASE**; **NOT A SOLUTION OF GENERAL 3D REGULARITY**.

## Target statement

For every smooth divergence-free initial velocity on a 3-dimensional periodic torus, does the corresponding incompressible Navier-Stokes solution with viscosity `nu>0` and zero external force remain smooth at all finite times? This general question is not settled by the computation here. The September 2026 OpenAI forced breakdown announcement addresses a separate alternative within Clay's formulation.

## A complete exact solution for a restricted but nonlinear 3D family

Let the periodic domain be `T^3 = (R/(2*pi Z))^3`. Fix any rational `A,B,C`, integer `k>0`, and positive rational viscosity `nu`. Define the ABC velocity field

    V(x,y,z)=(A sin(kz)+C cos(ky), B sin(kx)+A cos(kz),
              C sin(ky)+B cos(kx)).

It obeys

    div(V)=0, curl(V)=k*V, Delta(V)=-k^2*V.

This can be checked term-by-term. The vector-calculus identity

    (V dot grad)V = grad(|V|^2/2) - V cross curl(V)

therefore simplifies to `(V dot grad)V = grad(|V|^2/2)` because the velocity and curl are parallel. Now define

    u(t,x)=exp(-nu*k^2*t)*V(x)
    p(t,x)=-exp(-2*nu*k^2*t)*|V(x)|^2/2.

Direct substitution shows the *unforced* three-dimensional equations

    u_t+(u dot grad)u+grad(p)-nu*Delta(u)=0;  div(u)=0

hold exactly at every point and every t>=0. In particular, all spatial and temporal derivatives remain finite for every finite time. There is no forcing anywhere in this construction.

Parseval's identity gives the exact energy and helicity:

    int_T3 |u(t,x)|^2 dx = (2*pi)^3*(A^2+B^2+C^2)*exp(-2*nu*k^2*t).
    int_T3 u dot curl(u) dx = k*(2*pi)^3*(A^2+B^2+C^2)*exp(-2*nu*k^2*t).

For the worked case `(A,B,C,k,nu)=(1,2,3,1,1/10)`, the square L2 norm is `14*(2*pi)^3*exp(-t/5)` and is finite for all t>=0.

## More general finite-mode theorem (not a new theorem)

Let `V(x)=sum_q a_q exp(i q dot x)` be a *finite* Fourier series on T^3 with `q in Z^3`, coefficients in Q(i), conjugate symmetry `a_{-q}=conj(a_q)`, and a nonzero rational lambda satisfying

    q dot a_q = 0
    i*(q cross a_q) = lambda*a_q

for every mode. Then `curl V=lambda V`, `Delta V=-lambda^2 V` and the same explicit formula above works with `k` replaced by `lambda`. It is not necessary that wavevectors lie along coordinate axes or that all coefficients have the special ABC form.

The included engine checks *both* the linear identities and, independently, the full nonlinear plus pressure identity by convolution. In the Fourier basis the latter reads

    N_j(r) = i sum_{q+s=r} (a_q dot s) a_{s,j}
    p(r) = -(1/2) sum_{q+s=r} (a_q dot a_s)
    N_j(r) + i*r_j*p(r) = 0.

The check uses exact Gaussian rational pairs. This is stronger evidence than floating-point sample residuals, but it applies only to the finite-mode class specified above.

## Computation and reproducibility

From this directory:

    python3 -m research_lab.navier_stokes_beltrami demo
    python3 -m research_lab.navier_stokes_beltrami abc --a 1 --b 2 --c 3 --k 2 --nu 1/4
    python3 -m research_lab.navier_stokes_beltrami verify abc-proof-certificate.json
    python3 -m unittest discover -s research_lab/tests -p 'test_*.py' -q

The independent SymPy 1.14 check, for `(A,B,C,k,nu)=(1,2,3,2,1/4)`, yielded all-zero divergence, curl-eigenfield, heat, and nonlinear-plus-pressure residuals. The standard-library exact-mode engine emitted and verified a replayable certificate for rational parameters and a non-axis wavevector superposition. Its certificates reject tampered energy, status, scope and Fourier coefficients.

## What is still missing

The arbitrary-data 3D problem involves interactions between different curl eigenvalues and Fourier scales; for a general field `curl V` is not proportional to `V`, and the nonlinear term is not purely a gradient. That is precisely the mechanism the certificate does *not* control. The classical energy inequality alone is not an L-infinity or higher-derivative bound, as the earlier GPT-Doug Gaussian concentration calculation also demonstrated. No global regularity estimate, unforced blowup construction, novel theorem, or prize claim follows from these certificates.

## External references

- Clay Mathematics Institute, Navier-Stokes announcement, 2026-09-11: https://www.claymath.org/news/navier-stokes-announcement/
- OpenAI, On the Navier-Stokes Millennium Prize Problem, 2026-09-08: https://openai.com/index/navier-stokes-solution/
- Baron, *On a class of Beltrami vector fields and associated exact solutions to the Navier-Stokes equations*, Physics of Fluids (2025): https://doi.org/10.1063/5.0287737
- Classical ABC/Beltrami flow exact solutions: https://users.dma.unipi.it/berselli/html/papers/tg.pdf

This report and its computational certificate are a reproducible research baseline, not mathematical priority or independent formal proof of a new statement.
