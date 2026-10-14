# THE FALLEN — governed research federation

THE FALLEN is the GPT-Doug name for a **bounded, permission-aware research federation**.

It is designed to coordinate up to 555 logical research workers across explicitly
authorized repositories and public scientific datasets. It does not inject itself
into third-party repositories, bypass GitHub permissions, escape sandboxes, revive
dead biological material, or autonomously control physical machines.

## Worker topology

The default portfolio contains five 111-worker groups:

- discovery
- evidence verification
- experimental design
- replication / adversarial review
- translation / deployment

The workers are logical task identities. Creating a 555-worker plan does not launch
555 background processes by itself.

## Repository federation

A repository is eligible only when:

1. the operator explicitly lists it in the manifest;
2. the GitHub connection has the necessary permission;
3. integration occurs as read-only analysis or a pull request; and
4. merges remain human-controlled.

This makes the same framework usable across Sonoxo-owned repositories and any
enterprise repository whose owner has explicitly installed/authorized the GitHub
integration.

## Biological-data hunt

The public-source registry covers ClinicalTrials.gov, NCI GDC, NCBI GEO, NCBI SRA,
PubMed, and UniProt. Controlled-access datasets remain controlled: their presence in
the registry is not authorization to retrieve them.

Every evidence record should preserve:

`source → dataset/accession → publication/trial → evidence class → timestamp → checksum → confidence`

## Biochip and organoid integration

CL1, organoid, and other wet-lab interfaces remain separate governed adapters.
Measured biological telemetry must never be merged with synthetic/simulator output
without a source label.

## Physical embodiment

Humanoids/androids may be modeled or connected only through operator-authorized,
rate-limited adapters with physical actuation disabled by default. No autonomous
weapons or uncontrolled self-assembly behavior belongs in this subsystem.

## Emergency stop

THE FALLEN must respect the repository's existing operator-owned kill-switch and
must fail closed if authorization or provenance is missing.
