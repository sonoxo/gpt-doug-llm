# BioPineal Phase II — evidence graph and abstract material flow

This is offline, non-operational research software extending the verified merged PR #370. It does not control equipment or supply electrolysis steps, setpoints, yields, kinetics, energy requirements or plant designs.

## Commands

```sh
bash scripts/doug-max biopineal-phase2 graph
bash scripts/doug-max biopineal-phase2 flow --units 3
bash scripts/doug-max biopineal-phase2 report > /tmp/biopineal-phase2.json
bash scripts/doug-max biopineal-phase2 verify /tmp/biopineal-phase2.json
python3 -m unittest discover -s tests -p 'test_biopineal_phase2.py' -v
```

## Interpretation

The graph contains claim, patent excerpt, reaction and species nodes with typed edges. Its source remains `UNVERIFIED_USER_EXCERPT`, and official bibliographic verification and third-party technology-use rights remain open. The chemical equation can be atom-balanced without validating the patent, the specific reaction pathway, a feasible process, or a license.

The flow model scales *symbolic coefficients only* in arbitrary accounting units, not moles, masses, throughput, or field conditions. It reports the exact zero residual of Li, H, Cl and O and preserves the hydrogen-flammability, chlorine-toxicity, and lithium-hydroxide-corrosiveness warnings.

The SHA-256 field is for deterministic replay-integrity comparison, not authentication or proof of intellectual-property rights. Do not label excerpt claims verified until official primary-source records are independently reviewed and cited, including document numbers, dates, named inventors, current ownership, priority/continuity, and the full claim text. Rights-to-use and freedom-to-operate need separate professional evaluation.
