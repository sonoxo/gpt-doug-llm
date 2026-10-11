"""GPT-Doug: exact, bounded evidence for all seven Millennium Prize Problems.

Each calculation is a known elementary/special-case result, NOT a new general
solution. Python stdlib only. No external requests, credentials, or agents.
The report records explicit limitations and can be replayed independently.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

MAX_REPORT_BYTES = 128 * 1024
PROBLEM_LABELS = (
    "p_vs_np", "riemann_hypothesis", "birch_swinnerton_dyer",
    "hodge_conjecture", "yang_mills_mass_gap", "navier_stokes",
    "poincare_conjecture",
)
CLAY_STATUS_2026_10_10 = {
    "p_vs_np": "UNSOLVED",
    "riemann_hypothesis": "UNSOLVED",
    "birch_swinnerton_dyer": "UNSOLVED",
    "hodge_conjecture": "UNSOLVED",
    "yang_mills_mass_gap": "UNSOLVED",
    "navier_stokes": "ACTIVE_REVIEW_OF_2026_FORCED_BLOWUP_CLAIM",
    "poincare_conjecture": "SOLVED_BY_PERELMAN_2002_2003",
}


def _frac(x: Fraction | int) -> str:
    return str(Fraction(x))


def _primes(bound: int) -> list[int]:
    if type(bound) is not int or not 3 <= bound <= 997:
        raise ValueError("prime bound must be an integer in [3,997]")
    sieve = bytearray(b"\x01") * (bound + 1)
    sieve[0:2] = b"\x00\x00"
    for p in range(2, math.isqrt(bound) + 1):
        if sieve[p]:
            sieve[p*p:bound+1:p] = b"\x00" * (((bound-p*p)//p)+1)
    return [i for i in range(2, bound+1) if sieve[i]]


def sat_pigeonhole(pigeons: int = 3, holes: int = 2) -> dict[str, Any]:
    """Exhaustive CNF proof for one small pigeonhole instance, not P != NP."""
    if type(pigeons) is not int or type(holes) is not int or not 1 <= pigeons <= 4 or not 1 <= holes <= 3:
        raise ValueError("bounded pigeonhole instance required")
    variables = pigeons * holes
    if variables > 12:
        raise ValueError("at most 4096 assignments")
    # Standard positive literals x+1, negated -(x+1).
    vid = lambda i, j: i * holes + j + 1
    clauses = [[vid(i, j) for j in range(holes)] for i in range(pigeons)]
    clauses += [[-vid(i, j), -vid(i, k)]
                for i in range(pigeons) for j in range(holes) for k in range(j+1, holes)]
    clauses += [[-vid(i, j), -vid(k, j)]
                for j in range(holes) for i in range(pigeons) for k in range(i+1, pigeons)]
    satisfying = []
    for assignment in range(1 << variables):
        if all(any(bool(assignment & (1 << (abs(lit)-1))) == (lit > 0)
                   for lit in clause) for clause in clauses):
            satisfying.append(assignment)
    expected = math.perm(holes, pigeons) if holes >= pigeons else 0
    if len(satisfying) != expected:
        raise ArithmeticError("pigeonhole enumeration contradicts injection count")
    first = [int(bool(satisfying[0] & (1 << i))) for i in range(variables)] if satisfying else None
    return {"instance": f"PHP({pigeons} pigeons, {holes} holes)", "variables": variables,
            "clauses": len(clauses), "assignments_checked": 1 << variables,
            "satisfying_assignments": len(satisfying), "independent_injection_count": expected,
            "first_witness": first,
            "deduction": "UNSAT" if not satisfying else "SAT",
            "scope_limit": "Finite exhaustive CNF instance; no asymptotic circuit or complexity-class separation"}


def finite_euler_product(bound: int = 29) -> dict[str, Any]:
    """Rigorous rational bounds for zeta(2) from finite Euler factors.

    P_B = product_{p <= B} (1-p^-2)^-1.
    P_B < zeta(2) < P_B*(B+1)/B using telescoping tail
    product_{n>B}(1-n^-2)^-1=(B+1)/B. Zero-freeness applies
    only to the FINITE Euler product for Re(s)>0.
    """
    primes = _primes(bound)
    product = Fraction(1)
    for p in primes:
        product *= Fraction(p*p, p*p-1)
    upper = product * Fraction(bound + 1, bound)
    return {"last_integer_cutoff": bound, "primes_included": primes,
            "finite_product_at_s_2": _frac(product),
            "certified_zeta_2_open_interval": [_frac(product), _frac(upper)],
            "interval_width": _frac(upper-product),
            "tail_bound_proof": "For integers n>B, product_{n>B}(1-n^-2)^-1=(B+1)/B; omitted primes form a subproduct",
            "zero_free_fact": "Every finite Euler-product factor 1-p^(-s) is nonzero when Re(s)>0",
            "scope_limit": "No critical-strip zero theorem; finite Euler products do not establish RH"}


def _legendre(a: int, p: int) -> int:
    a %= p
    if not a:
        return 0
    val = pow(a, (p-1)//2, p)
    if val == 1:
        return 1
    if val == p-1:
        return -1
    raise ArithmeticError("Legendre symbol computed at a composite modulus")


def elliptic_curves(bound: int = 29) -> dict[str, Any]:
    """Exact point counts for nonsingular E:y^2=x^3-x mod odd primes.

    For EVERY p == 3 mod 4, the known CM trace identity a_p=0
    has the elementary proof f(-x)=-f(x), chi(-1)=-1.
    """
    ps = [p for p in _primes(bound) if p >= 3]
    rows = []
    for p in ps:
        char_sum = sum(_legendre(x*x*x - x, p) for x in range(p))
        points = p + 1 + char_sum
        trace = p + 1 - points
        symmetric = all(_legendre((-x)**3 - (-x), p) == -_legendre(x**3-x, p)
                        for x in range(p)) if p % 4 == 3 else None
        if p % 4 == 3 and (trace != 0 or not symmetric):
            raise ArithmeticError("CM trace pairing failed")
        if trace*trace > 4*p:
            raise ArithmeticError("finite-field count violates Hasse bound")
        rows.append({"p": p, "points_including_infinity": points, "trace_a_p": trace,
                     "hasse_checked": True,
                     "pairing_verified": symmetric})
    return {
        "curve": "y^2=x^3-x (discriminant 64; good reduction at all odd primes)",
        "finite_field_traces": rows,
        "infinite_prime_family_theorem": "For every prime p=3 (mod 4), a_p=0: f(-x)=-f(x) and chi_p(-1)=-1 pair character sums to zero",
        "scope_limit": "Special CM-curve Frobenius traces, not a proof of BSD rank equals analytic rank"}


def projective_hodge(dimension: int = 4) -> dict[str, Any]:
    """Compute the known Hodge algebra of CP^n, not arbitrary varieties."""
    if type(dimension) is not int or not 1 <= dimension <= 6:
        raise ValueError("complex projective dimension must lie in 1..6")
    classes = []
    for k in range(dimension + 1):
        classes.append({"bidegree": [k, k], "rational_rank": 1,
                        "generator": f"h^{k}",
                        "algebraic_cycle": f"linear CP^{dimension-k} in CP^{dimension}"})
    mid = dimension // 2
    return {"variety": f"CP^{dimension}",
            "cohomology_ring": f"Q[h]/(h^{dimension+1})", "degree_h": 2,
            "nonzero_hodge_bidegrees": classes,
            "cup_product": f"h^{mid} cup h^{dimension-mid} = h^{dimension}, with integral 1",
            "hodge_classes_spanned_by_algebraic_cycles_in_this_model": True,
            "scope_limit": "Known projective-space case, not arbitrary smooth projective varieties"}


def _gf2_rank(bitrows: list[int]) -> int:
    pivots: dict[int, int] = {}
    for row in bitrows:
        while row:
            highest = row.bit_length()-1
            if highest not in pivots:
                pivots[highest] = row
                break
            row ^= pivots[highest]
    return len(pivots)


def z2_lattice_gauge(nx: int = 2, ny: int = 2) -> dict[str, Any]:
    """Exhaust all Z2 edge fields on a tiny OPEN planar 2D lattice.

    Weight per plaquette +1 -> 4, -1 -> 2, so tanh(beta)=1/3.
    Wilson loops are products of contained plaquette signs, giving
    exact area law E W(C)=(1/3)^area for this solvable toy model.
    """
    if type(nx) is not int or type(ny) is not int or not 1 <= nx <= 2 or not 1 <= ny <= 2:
        raise ValueError("lattice sizes must lie in [1,2]")
    edge_set = set()
    for x in range(nx+1):
        for y in range(ny+1):
            if x < nx:
                edge_set.add(tuple(sorted(((x,y),(x+1,y)))))
            if y < ny:
                edge_set.add(tuple(sorted(((x,y),(x,y+1)))))
    edges = sorted(edge_set)
    idx = {e: i for i,e in enumerate(edges)}
    plaquette_masks = {}
    for x in range(nx):
        for y in range(ny):
            verts = [(x,y),(x+1,y),(x+1,y+1),(x,y+1)]
            boundary = [tuple(sorted((verts[i],verts[(i+1)%4]))) for i in range(4)]
            plaquette_masks[(x,y)] = sum(1 << idx[e] for e in boundary)
    P,E = nx*ny,len(edges)
    rank = _gf2_rank(list(plaquette_masks.values()))
    if rank != P:
        raise ArithmeticError("open-boundary plaquette signs are not independent")
    rectangles = []
    for xa in range(nx):
        for xb in range(xa+1,nx+1):
            for ya in range(ny):
                for yb in range(ya+1,ny+1):
                    mask = 0
                    for x in range(xa,xb):
                        for y in range(ya,yb):
                            mask ^= plaquette_masks[(x,y)]
                    rectangles.append(((xb-xa)*(yb-ya), mask))
    Z,nums = 0,[0]*len(rectangles)
    for config in range(1<<E):
        signs = [1 if (config & mask).bit_count()%2==0 else -1
                 for mask in plaquette_masks.values()]
        weight = math.prod(4 if sign == 1 else 2 for sign in signs)
        Z += weight
        for i,(_,mask) in enumerate(rectangles):
            nums[i] += weight * (1 if (config & mask).bit_count()%2 == 0 else -1)
    z_expected = (1 << (E-P)) * 6**P
    if Z != z_expected:
        raise ArithmeticError("partition function disagrees with plaquette independence")
    by_area: dict[int, dict[str, Any]] = {}
    for (area,_),numer in zip(rectangles,nums):
        measured = Fraction(numer, Z)
        target = Fraction(1,3)**area
        if measured != target:
            raise ArithmeticError("exact Wilson rectangle area law failed")
        item = by_area.setdefault(area, {"area":area,"tested_rectangles":0,"wilson_expectation":_frac(measured)})
        item["tested_rectangles"] += 1
    return {"theory": "2D planar open-boundary Z2 lattice gauge (NOT 4D continuum Yang-Mills)",
            "plaquettes":P,"edges":E,"gauge_assignments_enumerated":1<<E,
            "plaquette_map_rank_over_GF2":rank,
            "exact_partition_function":Z,
            "rectangular_wilson_loops": [by_area[k] for k in sorted(by_area)],
            "area_law_proof": "Independent plaquette variables; E W(C)=((4-2)/(4+2))^area=(1/3)^area",
            "scope_limit":"Solvable finite Z2 area law, not existence or mass gap of 4D SU(N) continuum quantum Yang-Mills"}


def unforced_shear_navier_stokes() -> dict[str, Any]:
    """Exact special smooth unforced 3D NS shear on the 2pi-torus."""
    A,nu,k=Fraction(2),Fraction(1,4),2
    # u=(A e^(-nu k^2 t) sin(k y), 0, 0).
    d_amplitude=-nu*k*k
    diffusion_amplitude=nu*(-k*k)
    if d_amplitude!=diffusion_amplitude:
        raise ArithmeticError("linear shear heat evolution identity failed")
    energy_density=A*A/4  # E/vol at t=0, E = 1/2 integral |u|^2
    grad_density=A*A*k*k/2
    e_rate=2*d_amplitude*energy_density
    if e_rate!=-nu*grad_density:
        raise ArithmeticError("kinetic energy dissipation identity failed")
    return {"exact_solution":"u(t,x,y,z)=(2 exp(-t) sin(2y),0,0), p=0, nu=1/4",
            "periodic_domain":"(R/2pi Z)^3",
            "divergence":"0", "nonlinear_advection":"0",
            "time_derivative_minus_viscous_laplacian":"0",
            "initial_kinetic_energy_divided_by_volume":_frac(energy_density),
            "initial_gradient_norm_squared_divided_by_volume":_frac(grad_density),
            "initial_energy_derivative_divided_by_volume":_frac(e_rate),
            "identity":"dE/dt=-nu * integral |grad u|^2; smooth globally by explicit exponential formula",
            "scope_limit":"One exact globally smooth flow, not a proof for arbitrary unforced smooth 3D data or a forced blowup construction"}


def _rank_rational(matrix: list[list[int]]) -> int:
    if not matrix:
        return 0
    rows=[list(map(Fraction,row)) for row in matrix]
    m,n=len(rows),len(rows[0]);rank=0
    for col in range(n):
        pivot=next((i for i in range(rank,m) if rows[i][col]),None)
        if pivot is None:continue
        rows[rank],rows[pivot]=rows[pivot],rows[rank]
        d=rows[rank][col]
        rows[rank]=[x/d for x in rows[rank]]
        for i in range(rank+1,m):
            z=rows[i][col]
            if z:
                rows[i]=[x-z*y for x,y in zip(rows[i],rows[rank])]
        rank+=1
        if rank==m:break
    return rank


def poincare_simplex_boundary() -> dict[str, Any]:
    """Compute homology and trivial pi1 for ONE explicit triangulated S^3."""
    vertices=tuple(range(5))
    simplices={k:list(itertools.combinations(vertices,k+1)) for k in range(4)}
    ranks={0:0,4:0};boundaries={}
    for k in range(1,4):
        prev={face:i for i,face in enumerate(simplices[k-1])}
        mat=[[0 for _ in simplices[k]] for _ in simplices[k-1]]
        for j,face in enumerate(simplices[k]):
            for i in range(k+1):
                sub=face[:i]+face[i+1:]
                mat[prev[sub]][j] =(-1)**i
        boundaries[k]=mat
        ranks[k]=_rank_rational(mat)
    for k in range(1,3):
        first,second=boundaries[k],boundaries[k+1]
        for row in first:
            for j in range(len(second[0])):
                if sum(row[i]*second[i][j] for i in range(len(second))) != 0:
                    raise ArithmeticError("simplicial boundary squared is nonzero")
    betti=[len(simplices[k])-ranks[k]-ranks[k+1] for k in range(4)]
    if betti != [1,0,0,1]:
        raise ArithmeticError("4-simplex boundary homology not S3")
    # Fundamental group of the 2-skeleton: choose the tree (0,i),
    # and use triangles (0,i,j) to kill every remaining (i,j) edge.
    non_tree_edges=list(itertools.combinations(range(1,5),2))
    relator_triangles=[(0,)+edge for edge in non_tree_edges]
    if any(t not in simplices[2] for t in relator_triangles):
        raise ArithmeticError("fundamental group triangle relators missing")
    return {"complex":"boundary of the 4-simplex, a triangulation of S^3",
            "number_of_k_simplices":{str(k):len(simplices[k]) for k in range(4)},
            "ranks_of_boundary_maps":{str(k):ranks[k] for k in range(1,4)},
            "betti_numbers":betti,
            "euler_characteristic":sum((-1)**k * len(simplices[k]) for k in range(4)),
            "fundamental_group":"TRIVIAL",
            "non_tree_edge_generators":len(non_tree_edges),
            "triangle_relators_killing_them":len(relator_triangles),
            "scope_limit":"One known simply connected closed 3-manifold, not a substitute for Perelman's proof of the general conjecture"}


def make_report(prime_bound: int = 29, pigeons: int = 3, holes: int = 2,
                projective_dimension: int = 4, lattice_width: int = 2,
                lattice_height: int = 2) -> dict[str, Any]:
    settings={"prime_bound":prime_bound,"pigeons":pigeons,"holes":holes,
              "projective_dimension":projective_dimension,
              "lattice_width":lattice_width,"lattice_height":lattice_height}
    calculations={
        "p_vs_np":sat_pigeonhole(pigeons,holes),
        "riemann_hypothesis":finite_euler_product(prime_bound),
        "birch_swinnerton_dyer":elliptic_curves(prime_bound),
        "hodge_conjecture":projective_hodge(projective_dimension),
        "yang_mills_mass_gap":z2_lattice_gauge(lattice_width,lattice_height),
        "navier_stokes":unforced_shear_navier_stokes(),
        "poincare_conjecture":poincare_simplex_boundary(),
    }
    result={
        "project":"GPT-Doug Millennium Forge",
        "reference_status_as_of":"2026-10-10",
        "source":"https://www.claymath.org/millennium-problems/",
        "settings":settings,
        "results":{name:{"clay_status_snapshot":CLAY_STATUS_2026_10_10[name],
                         "certificate_type":"KNOWN_SPECIAL_CASE_OR_FINITE_BENCHMARK",
                         "global_clay_problem_solved_by_this_report":False,
                         **calculations[name]} for name in PROBLEM_LABELS},
        "truth_boundary":"Exact finite certificates and known special cases do not solve unrestricted open Millennium Problems",
        "external_effects":0,
    }
    stable=json.dumps(result,sort_keys=True,separators=(",", ":"),ensure_ascii=True)
    result["evidence_sha256"]=hashlib.sha256(stable.encode("ascii")).hexdigest()
    return result


def verify_report(doc: Any) -> bool:
    if not isinstance(doc,dict) or not isinstance(doc.get("settings"),dict):
        return False
    allowed={"prime_bound","pigeons","holes","projective_dimension","lattice_width","lattice_height"}
    if set(doc["settings"])!=allowed:
        return False
    try:
        return doc==make_report(**doc["settings"])
    except (ValueError,TypeError,ArithmeticError,OverflowError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="cmd",required=True)
    demo=sub.add_parser("demo",help="produce complete seven-problem exact research report")
    demo.add_argument("--prime-bound",type=int,default=29)
    demo.add_argument("--pigeons",type=int,default=3)
    demo.add_argument("--holes",type=int,default=2)
    demo.add_argument("--projective-dimension",type=int,default=4)
    demo.add_argument("--lattice-width",type=int,default=2)
    demo.add_argument("--lattice-height",type=int,default=2)
    verify=sub.add_parser("verify",help="exactly replay an existing report")
    verify.add_argument("file",type=Path)
    sub.add_parser("status",help="show fixed dated Clay status snapshot; not a live API")
    args=parser.parse_args(argv)
    try:
        if args.cmd=="status":
            for name in PROBLEM_LABELS:
                print(f"{name:<27} {CLAY_STATUS_2026_10_10[name]}")
            return 0
        if args.cmd=="verify":
            if args.file.stat().st_size>MAX_REPORT_BYTES:
                raise ValueError("report exceeds 128KiB")
            doc=json.loads(args.file.read_text(encoding="utf8"))
            ok=verify_report(doc)
            print(json.dumps({"status":"VERIFIED" if ok else "INVALID"},indent=2))
            return 0 if ok else 1
        argsd={"prime_bound":args.prime_bound,"pigeons":args.pigeons,
               "holes":args.holes,"projective_dimension":args.projective_dimension,
               "lattice_width":args.lattice_width,"lattice_height":args.lattice_height}
        print(json.dumps(make_report(**argsd),indent=2,sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,ArithmeticError,OverflowError,json.JSONDecodeError) as exc:
        print(json.dumps({"status":"ERROR","kind":type(exc).__name__,"message":str(exc)[:120]}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
