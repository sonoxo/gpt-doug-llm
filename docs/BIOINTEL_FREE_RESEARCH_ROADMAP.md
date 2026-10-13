# BioPineal free knowledge and CL1 research roadmap

## Access with no hardware purchase
- CL SDK simulator: https://github.com/Cortical-Labs/cl-sdk
- CL1 development notebooks: https://github.com/Cortical-Labs/cl-api-doc
- Developer guide: https://docs.corticallabs.com/
- NASA UAP primary material: https://science.nasa.gov/uap/

Local Python 3.12+:
```sh
python3 -m research_lab.biointel_atlas --format json
python3 -m research_lab.biointel_atlas --topic UAP
python3 -m unittest tests.test_biointel_atlas
python3.12 -m venv .venv && . .venv/bin/activate && python -m pip install cl-sdk
```

## Research provenance rules
The software knowledge atlas catalogs Hermeticism, Atlantis, Egyptian archaeology, UAP reports and biocomputing claims. Every entry contains its source, evidence label and caveat. In particular, Plato's description of Atlantis is documented as literature, not proof of an Atlantis civilization, and UAP observations are not evidence of extraterrestrial technology without corroboration. Hermetic writings are analyzed as historical texts, not empirical laws of physics.

This dataset is a starter bibliography, not a scraped or comprehensive corpus. The classifications are catalog labels, not machine-validated scientific conclusions. CL1 simulator material is classified as `vendor-documentation`, not as a government report.

## Model roadmap
1. Keep the CL SDK simulator isolated from the ontology. Confirm record/read examples from the official developer guide.
2. Ingest explicitly authorized public research documents with retrieval timestamps, source text references and uncertainty.
3. Use a local retrieval/embedding index, with controlled and measured resource budgets.
4. Add symbolic reasoning for comparisons, without presenting Hermetic or occult principles as empirically validated physical laws.
5. Evaluate claims using independent public scientific evidence; a hypothetical SI/AGI/QI label is not a capability benchmark.
6. Keep any future CL1 experimental actions human-approved, supervised and separate from the agent swarm.

**No self-propagating installation, unauthorized network access, autonomous control of neural tissue, or biological fabrication is implemented.** The simulator is synthetic and not capable of validating biological learning or creating a physical organoid.
