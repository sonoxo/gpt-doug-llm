# GPT-DOUG MATH-MITOCHONDRIA -- Specification

The engine solves bounded polynomial equalities and linear systems with exact SymPy arithmetic, verifies every reported root by exact substitution, verifies bounded polynomial identities with coefficient checks, and marks research conjectures as unverified until external proof is independently established. No program can promise to resolve every open mathematical theory.

- User expression parsing is implemented with a strict Python AST whitelist, **not** `eval`, `sympify` on raw user text, or `parse_expr` on raw input.
- Input bounds: <=256 characters per equation, <=4 equations and unknowns, polynomial degree <=4 for one variable, linear-only for multi-variable systems, numeric literal <=1000000, exponent 0..8 (final polynomial degree <=4), bounded AST size.
- Exact solutions include a substitution certificate. If there are insufficient constraints, report underdetermined rather than invent missing information. If a claim cannot be proven within the supported calculus, report unverified/outside_scope.
- The mathematical subsystem is offline-first and never accesses government/vendor systems or persistent memory without explicit operator action.
- ALM OGA information is separate documentation: no agency impersonation, role misrepresentation, classified portal login assistance, automatic form signatures, or access claims.
