# GPT-Doug-MAX CL1 Culture Growth Evidence

**Mode: OFFLINE / RESEARCH EVIDENCE ONLY.** This is not a bioreactor, cell-culture protocol, remote CL1 actuator, or a confirmed living culture.

## Start the visual growth dashboard

From a refreshed GPT-Doug repository:

\`\`\`bash
bash scripts/doug-max cl1 grow
\`\`\`

This opens a **real offline HTML dashboard** in your browser. Without lab measurements the screen visibly says **BIOLOGICAL GROWTH: NOT CONFIRMED** and **NO DIRECT GROWTH EVIDENCE**. These are accurate statuses, not a broken or simulated telemetry feed. The command prints a \`file://\` location if the default browser cannot open.

Other commands:

\`\`\`bash
bash scripts/doug-max cl1 status
bash scripts/doug-max cl1 template > cl1-lab-observations.json
bash scripts/doug-max cl1 hash /path/to/authorized-microscope-image.tif
bash scripts/doug-max cl1 assess cl1-lab-observations.json
bash scripts/doug-max cl1 grow --input cl1-lab-observations.json
bash scripts/doug-max cl1 grow --no-open
\`\`\`

**No API key, CL1 hardware, hosted server, or paid dependencies are needed** for the offline evidence dashboard.

## What physical CL1 growth requires

Cortical Labs [describes CL1](https://www.corticallabs.com/cl1.html) as living neurons cultured in nutrient solution on a silicon interface, with an integrated environment designed by the vendor to sustain them for **up to six months**. That is a **vendor claim**, not proof a GPT-Doug culture exists or that any particular culture is viable. The CL1 is specialized hardware; running \`pip install cl-sdk\` or source code cannot manufacture neurons.

For a real biological growth project:

1. **Obtain authorized CL1 access** from Cortical Labs or an approved partner and identify who is responsible for cell source and hardware support.
2. **Use an institutionally approved culture study** supervised by qualified cell-culture personnel. This software does not prescribe cell media, handling conditions, passaging or other wet-lab procedures.
3. **Collect real evidence** on multiple culture days, including microscopy-based coverage/morphology and independent viability assay results, plus culture identifiers, collector, method, timestamps, and original-file digests.
4. **Keep electrophysiology distinct**: the official [CL API](https://docs.corticallabs.com/) records multi-electrode array activity in HDF5 files; spiking does not demonstrate culture growth, mitochondrial ATP, ROS, or neuron proliferation.
5. **Review study outcomes independently** before claiming morphology change, viability, functional adaptation, learning, or a mature organoid. CL1 neural cultures must not automatically be called cerebral organoids.

The [official CL SDK simulator](https://github.com/Cortical-Labs/cl-sdk) is specifically a local development tool that can produce non-learning synthetic data. It is **not** a biological experiment. The CLI never calls \`cl.open()\`, \`stim()\`, or a network service. It only checks for the SDK module during \`status\`.

## Evidence schema

Use the \`template\` subcommand above; it creates an empty record, **not** fabricated biological observations. For every authorized timepoint a qualified lab must fill in:

| Field | Meaning |
| --- | --- |
| \`timestamp_utc\` | ISO 8601 timezone-aware collection time |
| \`day_in_culture\` | A nonnegative integer culture day |
| \`origin\` | \`LAB_OPERATOR_ATTESTED\` or \`SDK_SIMULATOR\` |
| \`metric\` | \`COVERAGE_PERCENT\`, \`VIABILITY_PERCENT\`, or \`MEA_SPIKE_RATE_HZ\` |
| \`value\` | Measured value in the metric's units |
| \`collector\` | Lab operator or process identifier |
| \`method\` | Method used to obtain the observation |
| \`evidence_sha256\` | SHA-256 of the original evidence artifact for lab-attested data |

**Example structure with placeholders, not real data:**

\`\`\`json
{
  "schema": "gpt-doug-cl1-culture-observations/v1",
  "culture_id": "CL1-CULTURE-REPLACE",
  "specimen_class": "CL1_NEURAL_CULTURE",
  "observations": []
}
\`\`\`

The \`hash\` command computes a local file digest but does **not** verify the biological interpretation of the file. Keep source artifacts in the approved laboratory evidence system and avoid putting private patient or biological sample information in a public repository.

## Classification rules

- **NO_DIRECT_GROWTH_EVIDENCE:** No laboratory observations.
- **SIMULATOR_ONLY_NO_BIOLOGICAL_GROWTH_EVIDENCE:** Synthetic spike observations only.
- **INSUFFICIENT_LONGITUDINAL_MICROSCOPY:** Some lab observations, but no two distinct microscopy timepoints and artifacts.
- **LAB_RECORDED_COVERAGE_INCREASE / DECREASE / UNCHANGED:** Change in *lab-entered coverage percentage points*, not validation of proliferation, organoid creation or neuronal viability.

All biological records are tagged **LAB_OPERATOR_ATTESTED_NOT_INDEPENDENTLY_VERIFIED**. Even two images showing increased coverage can reflect neurite extension, migration, changes in imaging, or segmentation differences; this tool **does not** certify neuron proliferation or biomedical efficacy.

## Tests

\`\`\`bash
python3 -m unittest tests.test_cl1_growth -v
bash -n scripts/doug-max
\`\`\`

The suite tests empty evidence, simulator-only records, real-evidence-shaped test fixtures, invalid timestamps and hashes, XML/HTML-safety conditions, and offline browser output. No living CL1 is contacted.

## Primary sources

- [Cortical Labs CL1 Product](https://www.corticallabs.com/cl1.html) — product claims, cell culture, life-support environment
- [Cortical Labs CL API Developer Guide](https://docs.corticallabs.com/) — device API and recordings
- [CL API Reference](https://docs.corticallabs.com/cl) — \`cl.is_simulator()\`, \`get_system_attributes()\`, recording API
- [Cortical Labs cl-sdk](https://github.com/Cortical-Labs/cl-sdk) — Python 3.12+ simulator and synthetic/non-learning control data

The sources above support the **separation between living culture, electrical recording, simulator output and image-based laboratory measurements**. They do not supply real GPT-Doug CL1 culture data.
