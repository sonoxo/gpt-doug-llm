# BioPineal hydrogen and lithium — provenance-first research module

## Source and scope

The user-provided **Patent Public Search 4.4.0** excerpt lists **US 12760393 B1**, published **October 13, 2026**, titled *Methods and apparatuses for Li extraction and generation of high purity lithium hydroxide*. The supplied record attributes it to **PolyPlus Battery Company** and named inventors **Steven J. Visco, Yevgeniy S. Nimon and Bruce D. Katz**. Application number: **18/149524**, filing date **January 3, 2023**. This module keeps the source as **user-provided excerpt, not independently authenticated**.

The source describes electrochemical dry transfer of lithium ions through a ceramic membrane, with an adjacent cation-exchange membrane inhibiting hydroxide transport. Its public claim 1 describes a cell membrane structure, claim 7 a plant, and claim 10 a circuit. The illustrative reaction is:

\`2 LiCl + 2 H2O → 2 LiOH + H2 + Cl2\`

The module checks that Li, Cl, H and O atom counts balance **exactly**. It does **not** infer conversion efficiency, commercial feasibility, performance, environmental superiority, permission to practice the patent, or actual hydrogen production. Hydrogen can ignite; chlorine is toxic; lithium hydroxide is corrosive. There are no recipes, plant setpoints, actuator controls or chemical experiments in this repository.

## Terminal

~~~sh
python3 -m research_lab.biopineal_patent show
python3 -m research_lab.biopineal_patent report > /tmp/gpt-doug-biopineal-patent.json
python3 -m research_lab.biopineal_patent verify /tmp/gpt-doug-biopineal-patent.json
python3 -m unittest discover -s tests -p 'test_biopineal_patent.py' -v
~~~

The \`sha256\` is a **replay integrity digest**, not patent validity verification. Ownership is **not** assigned to GPT-Doug, and BioPineal is a research-software label, **not** a fabricated biological or quantum processor.

## Next engineering milestones (pending separate review)

1. Independently verify the official USPTO bibliographic record and claims against a stable official source.
2. Develop a lawful, non-operational literature comparison and prior-art citation map.
3. Add explicit rights-to-use review for third-party patent claims, before any technology implementation.
4. Develop safe, simulated material-flow diagrams without providing hazardous lab procedures.
5. Preserve provenance, uncertainty, and human approval inside the GPT-Doug ontology.

This module is distinct from the PeaceLab Nobel nomination work. It does not establish a peace impact or Nobel eligibility.
