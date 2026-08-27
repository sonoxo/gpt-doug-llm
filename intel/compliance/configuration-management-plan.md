# ZYRA Intelligence Configuration Management Plan

## Controlled baseline
`main` is the source baseline. Material security, ontology, intelligence-policy, runtime, dependency, and workflow changes are versioned in Git and validated through CI.

## Required change controls
- Changes must be attributable to a commit.
- Python changes are tested and linted; changed production Python is security-scanned.
- Dependencies are audited and a CycloneDX SBOM is generated in the security gate.
- MASTER LOCK and Glass Onion locks protect intelligence artifact integrity through hashes.
- Security-control changes must update the SSP or POA&M when they alter readiness evidence.
- Emergency changes must be followed by retrospective evidence and regression coverage.

## Prohibited configuration behavior
No secrets committed to source, no silent disabling of gates, no untracked production changes, and no promotion of deployment-specific compliance claims from source-code evidence alone.

## Deployment evidence
Production configuration inventory, approved deviations/exceptions, infrastructure-as-code or equivalent configuration records, patch cadence, backup of configuration state, and change approval records are required for a target environment.
