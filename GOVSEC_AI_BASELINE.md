# GPT-DOUG Government / National Security AI Security Shell

Command: `gpt-doug-govsec`

This shell is an engineering-readiness and evidence-collection tool. It does **not**
grant CMMC status, a FedRAMP authorization, FIPS validation, an RMF authorization/ATO,
or approval to process classified information.

## Layered model

AI:
- NIST AI RMF 1.0
- NIST AI 600-1
- DoD Responsible AI
- NIST SP 800-218 / 800-218A

Federal / RMF:
- NIST SP 800-53 Rev. 5
- NIST SP 800-53A
- FIPS 140-3

DoD contractor / CUI:
- FAR 52.204-21
- NIST SP 800-171
- CMMC / 32 CFR Part 170
- DFARS 252.204-7012 / 7019 / 7020 / 7021 / 7025

DoD / National Security:
- DoD Zero Trust Strategy
- DISA STIG / SRG
- FedRAMP + DoD Cloud SRG where applicable
- CNSS / NSA / mission-specific National Security System overlays

## Data-boundary rule

The public GitHub/Render prototypes are PUBLIC demonstration environments.
CUI, NSS, or classified workloads require separately approved boundaries and
mission/contract-specific authorization evidence.

## Quick start

```sh
cd ~/gpt-doug-llm
git fetch origin
git switch cloud/eagleeye-free
git pull --ff-only
chmod +x scripts/install-gpt-doug-govsec
./scripts/install-gpt-doug-govsec
gpt-doug-govsec
```

For a noninteractive scan:

```sh
gpt-doug-govsec scan
```
