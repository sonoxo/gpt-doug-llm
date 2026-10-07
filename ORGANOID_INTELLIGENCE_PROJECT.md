# GPT-DOUG // ORGANOID INTELLIGENCE PROJECT

## Mission
Build a governed research and software program around brain-organoid / organoid-intelligence science without embedding unreviewed wet-lab recipes into the software.

## Scientific basis
Brain organoids are 3D stem-cell-derived models that recapitulate selected aspects of developing brain tissue. Organoid Intelligence (OI) is an emerging research field combining neural organoids, electrophysiology, high-content imaging, bioengineering, and machine learning to study learning, memory, and biological computing.

## Program architecture
1. LITERATURE + GOVERNANCE
   - living literature registry
   - ISSCR standards and ethics review
   - provenance for every protocol, dataset, cell source, and model version
2. CELL SOURCE + QUALITY
   - institutional/qualified wet-lab partner
   - documented source, consent, identity, contamination and genomic-quality checks under the lab's approved SOPs
3. ORGANOID MODEL
   - model versioning and morphology records
   - no recipe parameters stored in public UI
   - lot/batch/replicate tracking
4. INTERFACE
   - microscopy and imaging metadata
   - multielectrode/electrophysiology data import
   - environmental and device metadata
5. COMPUTE
   - signal cleaning and feature extraction
   - temporal knowledge graph
   - digital twin / simulation
   - machine-learning analysis with uncertainty and provenance
6. TEVV + HUMAN GATE
   - validation against controls
   - drift/reproducibility checks
   - explicit human approval before experiment-state changes

## GPT-DOUG data plane
OBSERVE -> INGEST -> QC -> MODEL -> SIMULATE -> COMPARE -> TEVV -> HUMAN GATE -> VERSIONED MEMORY -> AUDIT

## What the software tracks
- model / batch / replicate IDs
- cell-source provenance metadata
- assay and instrument metadata
- morphology and image-derived features
- electrophysiology summary features
- QC / validation status
- experiment notes and approvals
- analysis model versions
- uncertainty and reproducibility measures

## Safety / ethics boundary
The public project does not contain culture media recipes, reagent concentrations, incubation schedules, seeding densities, electrical-stimulation protocols, genetic-modification instructions, or other step-by-step experimental procedures. Wet-lab work should be performed by qualified personnel under institutionally approved SOPs and applicable oversight.

## Research references
- ISSCR Standards for Human Stem Cell Use in Research: https://www.isscr.org/basic-research-standards
- ISSCR Guidelines for Stem Cell Research and Clinical Translation: https://www.isscr.org/guidelines-online
- Organoid Intelligence review / roadmap: https://www.frontiersin.org/journals/science/articles/10.3389/fsci.2023.1017235/full
- Organoid Intelligence workshop: https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2023.1116870/full
- FinalSpark research updates: https://finalspark.com/articles/
