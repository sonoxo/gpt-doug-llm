from __future__ import annotations

from .models import Dimension, ProblemSpec

ALL_DIMENSIONS = tuple(Dimension)

MILLENNIUM_PROBLEMS: dict[str, ProblemSpec] = {
    "riemann": ProblemSpec(
        slug="riemann",
        title="Riemann Hypothesis",
        status="open",
        statement="Every nontrivial zero of the Riemann zeta function has real part 1/2.",
        decisive_obligation=(
            "Prove a positivity, spectral, or equivalent principle that forces every "
            "nontrivial zero onto the critical line without assuming the conclusion."
        ),
        dimensions=ALL_DIMENSIONS,
        barriers=("finite_zero_checks_are_not_a_proof", "equivalent_criterion_must_be_closed"),
        reference_url="https://www.claymath.org/millennium/riemann-hypothesis/",
    ),
    "navier-stokes": ProblemSpec(
        slug="navier-stokes",
        title="Navier-Stokes Existence and Smoothness",
        status="open",
        statement=(
            "For three-dimensional incompressible Navier-Stokes, establish global smooth "
            "existence for smooth finite-energy data or construct a valid finite-time breakdown."
        ),
        decisive_obligation=(
            "Close a scale-critical a priori estimate sufficient to exclude singularity, "
            "or rigorously construct a finite-time singular solution satisfying the formulation."
        ),
        dimensions=ALL_DIMENSIONS,
        barriers=("supercritical_energy_control_is_insufficient", "numerical_smoothness_is_not_proof"),
        reference_url="https://www.claymath.org/millennium/navier-stokes-equation/",
    ),
    "p-vs-np": ProblemSpec(
        slug="p-vs-np",
        title="P versus NP",
        status="open",
        statement="Determine whether every language in NP is also in P.",
        decisive_obligation=(
            "Prove an appropriate superpolynomial lower bound or give a polynomial-time "
            "algorithm for an NP-complete problem, with all known barrier interactions addressed."
        ),
        dimensions=ALL_DIMENSIONS,
        barriers=("relativization", "natural_proofs", "algebrization"),
        reference_url="https://www.claymath.org/millennium/p-vs-np-problem/",
    ),
    "yang-mills": ProblemSpec(
        slug="yang-mills",
        title="Yang-Mills Existence and Mass Gap",
        status="open",
        statement=(
            "Construct a nontrivial quantum Yang-Mills theory on R^4 for a compact simple "
            "gauge group and prove a positive mass gap."
        ),
        decisive_obligation=(
            "Establish a rigorous continuum construction and a strictly positive spectral "
            "gap that survives removal of the ultraviolet cutoff."
        ),
        dimensions=ALL_DIMENSIONS,
        barriers=("lattice_evidence_is_not_continuum_construction", "gap_must_be_uniform_in_cutoff"),
        reference_url="https://www.claymath.org/millennium/yang-mills-the-maths-gap/",
    ),
    "bsd": ProblemSpec(
        slug="bsd",
        title="Birch and Swinnerton-Dyer Conjecture",
        status="open",
        statement=(
            "For an elliptic curve over Q, relate the Mordell-Weil rank to the order of "
            "vanishing of its L-function at s=1, together with the leading-term formula."
        ),
        decisive_obligation=(
            "Control higher-rank Selmer groups and the analytic leading term strongly enough "
            "to prove the rank equality and full leading-coefficient formula in general."
        ),
        dimensions=ALL_DIMENSIONS,
        barriers=("rank_zero_and_one_methods_do_not_automatically_generalize",),
        reference_url="https://www.claymath.org/millennium/birch-and-swinnerton-dyer-conjecture/",
    ),
    "hodge": ProblemSpec(
        slug="hodge",
        title="Hodge Conjecture",
        status="open",
        statement=(
            "Every rational Hodge class on a smooth projective complex variety is a rational "
            "linear combination of classes of algebraic cycles."
        ),
        decisive_obligation=(
            "Construct algebraic cycles representing arbitrary rational (p,p) Hodge classes "
            "or prove an equivalent general theorem that supplies those cycles."
        ),
        dimensions=ALL_DIMENSIONS,
        barriers=("verified_special_families_do_not_imply_general_case",),
        reference_url="https://www.claymath.org/millennium/hodge-conjecture/",
    ),
    "poincare": ProblemSpec(
        slug="poincare",
        title="Poincare Conjecture",
        status="solved_reference",
        statement=(
            "Every closed, simply connected three-dimensional manifold is homeomorphic "
            "to the three-sphere."
        ),
        decisive_obligation="Reference track only: formalize and verify the established proof lineage.",
        dimensions=ALL_DIMENSIONS,
        reference_url="https://www.claymath.org/millennium/poincare-conjecture/",
    ),
}


def get_problem(slug: str) -> ProblemSpec:
    try:
        return MILLENNIUM_PROBLEMS[slug]
    except KeyError as exc:
        raise KeyError(f"unknown Millennium problem: {slug}") from exc


def open_problem_slugs() -> list[str]:
    return [slug for slug, spec in MILLENNIUM_PROBLEMS.items() if spec.status == "open"]
