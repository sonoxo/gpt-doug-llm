# npm dependency remediation — 2026-10-13

## Root cause and scope

Run https://github.com/sonoxo/gpt-doug-llm/actions/runs/38390230636
failed in `Zyra + NXYZ + Zyra Cloud RVIA Full Gate`. That job explicitly
checks out `sonoxo/zyra@main`, not GPT-Doug's source. Its log identifies Zyra
commit `7c241ced0c4716a6e9a59cfd02918d708b051472` and six audit findings.
The completion verdict fails closed as a consequence of the failed Zyra job.

GPT-Doug's own root lockfile independently contains the vulnerable
`express -> proxy-addr` and `express/body-parser -> qs` dependencies.
This PR repairs those two entries and adds behavioral regressions and a
dedicated Node 20/22 npm security workflow. Express remains at 5.2.1;
direct dependency ranges, other security gates, and patent assertions are unchanged.

| Dependency | GPT-Doug root | Zyra companion change | Advisory |
| --- | --- | --- | --- |
| proxy-addr | 2.0.7 → 2.0.8 | 2.0.7 → 2.0.8 | GHSA-jqcg-44mw-7w3h |
| qs | 6.15.3 → 6.16.0 | 6.15.3 → 6.16.0 | GHSA-x5fp-wj9c-mxmx; GHSA-4mjr-xmp4-gh2g |
| source-map-js | Absent | 1.2.1 → 1.2.2 | GHSA-68fv-2mgg-jv7q |
| ip-address | Absent | 10.5.0 → 10.7.4 | GHSA-rpw4-54j3-4h4q; GHSA-2vr4-cq9g-pvrc; GHSA-j6r3-76f7-8jcv; GHSA-h3mg-xc3c-68pw |

Only the named transitive dependencies were refreshed using ordinary
`npm update <names> --package-lock-only --ignore-scripts`, followed by
`npm ci`. No forced update or transitive override was applied.

## Validation

- Root `npm ci`, three behavioral regressions, and
  `npm audit --audit-level=high` pass; root audit reports zero vulnerabilities.
- Regression tests fail on the original lockfile for forwarded-IP spoofing
  and attacker-controlled `constructor.isBuffer`, then pass with patched dependencies.
- Zyra companion validation passes five dependency regressions, 48 existing
  application/kernel tests, TypeScript checking, and client/server compilation.
- The local environment prohibits the Unix socket used by the `tsx` CLI.
  Zyra tests/build were additionally run through `node --import tsx` using
  the same files; hosted CI must verify the exact npm scripts on Node 20.
- The new workflow checks root dependencies. The existing cross-repository
  job continues to check Zyra main, so it cannot validate the unmerged
  Zyra companion branch. Its status must remain separate from PR-local CI.

## Remaining work and review requirement

Zyra still reports two moderate audit entries: `postcss-selector-parser@6.0.10`
and the dependent `@tailwindcss/typography@0.5.20`. The underlying advisory is
GHSA-rj75-hqrm-r3gf, patched in parser 7.1.6. Typography pins parser 6.0.10.
The audit's suggested forced change is a typography downgrade to 0.5.4;
it is deliberately excluded. A separate compatibility review must evaluate
an upstream typography release or a narrowly scoped parser override, compare
generated typography CSS, and validate selector handling and the production build.
Passing the existing high-severity threshold does not mean this moderate risk is fixed.

PR #351 concerns Dependabot coverage, not remediation. PR #354's patent
assertion correction is independent and is not included here.

Require independent approval before merging both remediation PRs.
Do not enable auto-merge. After the Zyra companion is reviewed and merged,
rerun the failed full-completion jobs and verify both the Zyra audit/build
and the aggregate completion verdict. An unmerged companion cannot make
the cross-repository main-branch gate green.
