"""Bounded, auditable symbolic mathematics for GPT-Doug.

No raw eval/sympify/parse_expr. This is an algebra checker, not a solver of
arbitrary mathematical conjectures and not a substitute for peer review.
"""
from __future__ import annotations

import argparse
import ast
import itertools
import json
import math
import re
import sys
from typing import Any, Optional


class MathInputError(ValueError):
    """Invalid, unsafe or resource-excessive input."""


class MathMitochondria:
    """Solve small exact polynomial problems, certify roots, triage open claims."""

    MAX_EQUATIONS = 4
    MAX_VARIABLES = 4
    MAX_EXPRESSION = 256
    MAX_NODES = 70
    MAX_DEGREE = 4
    _VARIABLE = re.compile(r"[A-Za-z][A-Za-z_0-9]{0,23}\Z")

    def __init__(self) -> None:
        try:
            import sympy as sp
        except ImportError as exc:
            raise MathInputError(
                "SymPy not installed; use pip install 'gpt-doug-llm[math]'"
            ) from exc
        self.sp = sp

    def _parse(self, source: str) -> Any:
        if not isinstance(source, str) or not source.strip() or len(source) > self.MAX_EXPRESSION:
            raise MathInputError("expression must contain 1..256 characters")
        source = source.replace("^", "**").strip()
        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            raise MathInputError("invalid mathematical syntax") from exc
        if sum(1 for _ in ast.walk(tree)) > self.MAX_NODES:
            raise MathInputError("expression is too complex")
        sp = self.sp

        def convert(node: ast.AST) -> Any:
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                val = node.value
                if abs(val) > 1_000_000 or (isinstance(val, float) and not math.isfinite(val)):
                    raise MathInputError("numeric literal exceeds bounds")
                return sp.Rational(str(val))
            if isinstance(node, ast.Name):
                if not self._VARIABLE.fullmatch(node.id) or "__" in node.id:
                    raise MathInputError("variable name is invalid")
                return sp.Symbol(node.id)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                val = convert(node.operand)
                return val if isinstance(node.op, ast.UAdd) else -val
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Pow):
                    if not isinstance(node.right, ast.Constant) or type(node.right.value) is not int:
                        raise MathInputError("exponent must be an integer literal from 0 to 8")
                    if not 0 <= node.right.value <= 8:
                        raise MathInputError("exponent exceeds safe limit")
                    return convert(node.left) ** node.right.value
                a, b = convert(node.left), convert(node.right)
                if isinstance(node.op, ast.Add):
                    return a + b
                if isinstance(node.op, ast.Sub):
                    return a - b
                if isinstance(node.op, ast.Mult):
                    return a * b
                if isinstance(node.op, ast.Div):
                    if b.free_symbols:
                        raise MathInputError("variable denominators require explicit domain exclusions")
                    if b == 0:
                        raise MathInputError("division by zero")
                    return a / b
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "sqrt" and len(node.args) == 1 and not node.keywords:
                    arg = convert(node.args[0])
                    if arg.free_symbols:
                        raise MathInputError("variable-dependent radicals are outside scope")
                    return sp.sqrt(arg)
            raise MathInputError("unsupported expression (no function execution or indexing)")

        expr = convert(tree.body)
        if expr.has(sp.nan, sp.zoo, sp.oo, -sp.oo):
            raise MathInputError("nonfinite expression")
        if len(expr.free_symbols) > self.MAX_VARIABLES:
            raise MathInputError("too many unknowns")
        return expr

    def _equality(self, text: str) -> Any:
        if not isinstance(text, str) or text.count("=") != 1:
            raise MathInputError("provide one equality using a single '='")
        left, right = text.split("=", 1)
        return self._parse(left) - self._parse(right)

    def _validated_equations(self, equations: list[str]) -> tuple[list[Any], list[Any]]:
        if not isinstance(equations, (list, tuple)) or not 1 <= len(equations) <= self.MAX_EQUATIONS:
            raise MathInputError("provide 1 to 4 equations")
        exprs = [self._equality(s) for s in equations]
        symbols = sorted(set().union(*(expr.free_symbols for expr in exprs)), key=lambda s: s.name)
        if len(symbols) > self.MAX_VARIABLES:
            raise MathInputError("too many unknowns")
        return exprs, symbols

    def solve(self, equations: list[str], *, variables: Optional[list[str]] = None,
              domain: str = "real") -> dict[str, Any]:
        sp = self.sp
        if domain not in ("real", "complex"):
            raise MathInputError("domain must be real or complex")
        exprs, detected = self._validated_equations(equations)
        vars_ = detected
        if variables is not None:
            if not isinstance(variables, (list, tuple)) or not 1 <= len(variables) <= 4:
                raise MathInputError("provide 1 to 4 distinct variable names")
            if any(not isinstance(n, str) or not self._VARIABLE.fullmatch(n) for n in variables):
                raise MathInputError("invalid variable")
            if len(set(variables)) != len(variables):
                raise MathInputError("variable names must be unique")
            vars_ = [sp.Symbol(n) for n in variables]
            if any(s not in vars_ for s in detected):
                return self._result("underdetermined", equations, domain,
                                    reason="missing variable constraints", variables=[str(s) for s in detected])
        if not detected:
            status = "underdetermined" if all(e == 0 for e in exprs) else "inconsistent"
            return self._result(status, equations, domain,
                                reason="no unknown variable is constrained")
        if len(vars_) == 0:
            return self._result("underdetermined", equations, domain, reason="no solve variables")
        if len(exprs) == 1 and len(vars_) == 1:
            x = vars_[0]
            try:
                poly = sp.Poly(exprs[0], x)
            except (sp.PolynomialError, ValueError, TypeError):
                return self._result("outside_scope", equations, domain,
                                    reason="only polynomial equalities are supported")
            if poly.degree() > self.MAX_DEGREE:
                return self._result("outside_scope", equations, domain,
                                    reason="polynomial degree exceeds 4")
            exact = sp.solveset(exprs[0], x, domain=sp.S.Reals if domain == "real" else sp.S.Complexes)
            if exact is sp.S.EmptySet:
                return self._result("no_real_solution" if domain == "real" else "inconsistent",
                                    equations, domain, reason="no roots in selected domain")
            if not isinstance(exact, sp.FiniteSet):
                return self._result("outside_scope", equations, domain,
                                    reason="solver did not return a finite exact solution set")
            solutions = []
            for root in sorted(exact, key=sp.default_sort_key):
                residual = sp.simplify(exprs[0].subs(x, root))
                if residual != 0 or (domain == "real" and root.is_real is not True):
                    return self._result("unverified", equations, domain,
                                        reason="candidate root failed exact substitution")
                solutions.append({str(x): sp.sstr(root), "residual": sp.sstr(residual), "verified": True})
            return self._result("verified", equations, domain, solutions=solutions,
                                certificate="exact symbolic substitution")
        if len(exprs) > self.MAX_EQUATIONS or len(vars_) > self.MAX_VARIABLES:
            raise MathInputError("system size exceeds limit")
        try:
            for e in exprs:
                p = sp.Poly(e, *vars_)
                if p.total_degree() > 1:
                    return self._result("outside_scope", equations, domain,
                                        reason="multivariable systems must be linear")
            A, b = sp.linear_eq_to_matrix(exprs, vars_)
            sols = sp.linsolve((A, b), vars_)
        except (sp.PolynomialError, ValueError, TypeError):
            return self._result("outside_scope", equations, domain,
                                reason="only linear systems are supported")
        if sols is sp.S.EmptySet:
            return self._result("inconsistent", equations, domain,
                                reason="linear constraints contradict")
        if A.rank() != len(vars_):
            return self._result("underdetermined", equations, domain,
                                reason="not enough independent constraints to determine every variable")
        solution_tuple = list(sols)[0]
        substitutions = dict(zip(vars_, solution_tuple))
        residuals = [sp.simplify(e.subs(substitutions)) for e in exprs]
        if any(r != 0 for r in residuals):
            return self._result("unverified", equations, domain,
                                reason="computed solution fails exact substitution")
        if domain == "real" and any(v.is_real is not True for v in solution_tuple):
            return self._result("no_real_solution", equations, domain)
        output = {str(x): sp.sstr(v) for x, v in substitutions.items()}
        output.update(verified=True, residuals=[sp.sstr(r) for r in residuals])
        return self._result("verified", equations, domain, solutions=[output],
                            certificate="exact linear-algebra substitution")

    def verify(self, identity: str) -> dict[str, Any]:
        sp = self.sp
        difference = self._equality(identity)
        variables = sorted(difference.free_symbols, key=lambda x: x.name)
        if not variables:
            zero = sp.simplify(difference) == 0
            return {"status": "verified" if zero else "refuted", "identity": identity,
                    "residual": sp.sstr(difference),
                    "proof": "exact constant equality" if zero else None,
                    "counterexample": None if zero else {"residual": sp.sstr(difference)},
                    "scope": "exact polynomial identity (degree <= 4)"}
        try:
            poly = sp.Poly(difference, *variables) if variables else sp.Poly(difference)
        except (sp.PolynomialError, ValueError, TypeError):
            return {"status": "outside_scope", "identity": identity,
                    "proof": None, "reason": "nonpolynomial identities require domain analysis"}
        if poly.total_degree() > self.MAX_DEGREE:
            return {"status": "outside_scope", "identity": identity,
                    "proof": None, "reason": "polynomial identity degree exceeds 4"}
        zero = poly.is_zero
        counterexample = None
        if not zero:
            for coords in itertools.product((0, 1, 2, -1, 3), repeat=len(variables)):
                candidate = dict(zip(variables, coords))
                value = difference.subs(candidate)
                if value != 0 and value.is_finite is True:
                    counterexample = {str(k): str(v) for k, v in candidate.items()}
                    counterexample["residual"] = sp.sstr(value)
                    break
        return {"status": "verified" if zero else "refuted", "identity": identity,
                "residual": "0" if zero else sp.sstr(difference),
                "proof": "polynomial coefficient equality" if zero else None,
                "counterexample": counterexample,
                "scope": "exact polynomial identity (degree <= 4)"}

    @staticmethod
    def theory(claim: str) -> dict[str, Any]:
        if not isinstance(claim, str) or not claim.strip() or len(claim) > 1000:
            raise MathInputError("theory must contain 1 to 1000 characters")
        return {"status": "unverified", "claim": claim.strip(), "proof": None,
                "required": ["formal statement", "explicit assumptions", "reproducible proof",
                             "independent review"],
                "reason": "No claim is established solely by stating a conjecture"}

    @staticmethod
    def _result(status: str, source: list[str], domain: str, *, solutions: Optional[list[dict]] = None,
                certificate: Optional[str] = None, reason: Optional[str] = None,
                variables: Optional[list[str]] = None) -> dict[str, Any]:
        return {"engine": "GPT-DOUG-MATH-MITOCHONDRIA", "status": status,
                "equations": list(source), "domain": domain,
                "solutions": solutions or [], "certificate": certificate,
                "reason": reason, "variables": variables,
                "limits": "bounded algebra only; not a universal theorem prover"}


def math_cli(argv: Optional[list[str]] = None) -> int:
    """Reproducible JSON console interface; no network and no implicit archive."""
    p = argparse.ArgumentParser(prog="gpt-doug math")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("solve", help="exact polynomial equation or linear system")
    s.add_argument("equations", nargs="+")
    s.add_argument("--for", dest="variables", action="append")
    s.add_argument("--domain", choices=("real", "complex"), default="real")
    v = sub.add_parser("verify", help="certify a polynomial identity")
    v.add_argument("identity")
    t = sub.add_parser("theory", help="identify missing proof, without inventing one")
    t.add_argument("claim")
    for cmd in (s, v, t):
        cmd.add_argument("--remember", action="store_true",
                         help="persist verified result only to GPT-Doug brain memory")
        cmd.add_argument("--memory-file", help="custom local memory file for explicit --remember")
    sub.add_parser("doctor", help="print math subsystem readiness")
    a = p.parse_args(argv)
    try:
        engine = MathMitochondria()
        if a.command == "solve":
            result = engine.solve(a.equations, variables=a.variables, domain=a.domain)
        elif a.command == "verify":
            result = engine.verify(a.identity)
        elif a.command == "theory":
            result = engine.theory(a.claim)
        else:
            result = {"engine": "GPT-DOUG-MATH-MITOCHONDRIA", "status": "ready",
                      "backend": f"SymPy {engine.sp.__version__}",
                      "scope": "exact bounded algebra, no arbitrary conjecture solving", "network": False}
        if getattr(a, "remember", False):
            if result["status"] != "verified":
                raise MathInputError("only independently checked algebra results may be archived")
            if a.memory_file and not a.memory_file.strip():
                raise MathInputError("invalid memory path")
            from .memory import BrainMemory
            memory = BrainMemory(a.memory_file)
            memory.add("decision", json.dumps(result, sort_keys=True, ensure_ascii=False),
                       provenance="math-mitochondria:operator-authorized",
                       metadata={"verification": "symbolic_substitution" if a.command == "solve"
                                 else "polynomial_coefficient_check", "status": "verified"})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (MathInputError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": "math_check_failed", "detail": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(math_cli())
