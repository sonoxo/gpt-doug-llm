# RVIA Federal Intel Public-Source Layer

VA3LM / BIG VIRGINIA exposes a provenance-first public-source catalog for the five intelligence blocks shown in the operator reference:

1. Central Intelligence Agency (CIA)
2. National Security Agency (NSA)
3. National Reconnaissance Office (NRO)
4. National Geospatial-Intelligence Program (NGP), mapped to National Geospatial-Intelligence Agency (NGA) public resources
5. General Defense Intelligence Program (GDIP), mapped to Defense Intelligence Agency (DIA) public resources

## Scope

This is an **OSINT and open-source software catalog**, not an intelligence-collection system. It indexes public government publications, public code, open standards, declassified/FOIA records, and public program/news material.

The runtime rejects the idea that every agency has an official GitHub presence. As verified on 2026-09-01:

- NSA: official public GitHub organizations `NationalSecurityAgency` and `nsacyber`.
- NGA: official public GitHub organization `ngageoint`; NGP is mapped to this NGA surface.
- CIA: no official GitHub organization verified by this catalog; use CIA.gov public sources.
- NRO: no official GitHub organization verified by this catalog; use NRO.gov public sources.
- DIA/GDIP: no official GitHub organization verified by this catalog; use DIA.mil public sources.

Third-party repositories are never promoted to `official` without independent verification.

## Curated official GitHub software

### NSA

- `NationalSecurityAgency/ghidra` — software reverse-engineering framework
- `NationalSecurityAgency/datawave` — ingest/query framework
- `NationalSecurityAgency/Foundation` — formal cryptographic specifications and assurance artifacts

### NGA / NGP

- `ngageoint/geoint-standards` — GEOINT standards
- `ngageoint/GeoPackage` — OGC GeoPackage implementations and ecosystem
- `ngageoint/hootenanny` — map conflation tooling
- `ngageoint/mage-server` — Mobile Awareness GEOINT Environment server

## Government-source surfaces

### CIA

- `https://www.cia.gov/`
- `https://www.cia.gov/the-world-factbook/`
- `https://www.cia.gov/readingroom/`

### NSA

- `https://www.nsa.gov/`
- `https://code.nsa.gov/`
- `https://github.com/NationalSecurityAgency`
- `https://github.com/nsacyber`

### NRO

- `https://www.nro.gov/`
- `https://www.nro.gov/news-media-featured-stories/`
- `https://www.nro.gov/foia-home/foia-resources-reading-room/`

### NGA / NGP

- `https://www.nga.mil/`
- `https://www.nga.mil/about/About_Us.html`
- `https://github.com/ngageoint`

### DIA / GDIP

- `https://www.dia.mil/`
- `https://www.dia.mil/FOIA/FOIA-Electronic-Reading-Room/`
- `https://www.dia.mil/News-Features/The-DIA-60th-Anniversary/The-1970s/`

## Runtime

```bash
va3lm federal-intel
va3lm federal-intel --github-only
va3lm federal-intel --entity nsa
va3lm federal-intel --entity ngp
```

API:

```text
GET /api/federal-intel
GET /api/federal-intel/github
GET /api/federal-intel/{entity_id}
```

Supported entity IDs:

```text
cia
nsa
nro
ngp
gdip
```

## RVIA processing contract

```text
PUBLIC / OFFICIAL SOURCE
          ↓
SOURCE IDENTITY + PROVENANCE
          ↓
AGENCY / PROGRAM CLASSIFICATION
          ↓
PUBLIC-SOURCE NORMALIZATION
          ↓
RVIA / VA3LM CATALOG
          ↓
ZYRA + XUNIAHUB CONSUMERS
          ↓
ANALYST / HUMAN REVIEW
```

## Hard boundaries

The catalog does not authorize or implement:

- classified, leaked, stolen, credentialed, or access-controlled collection;
- communications interception or SIGINT collection;
- covert tracking of people;
- biometric identification or persistent person identifiers;
- operational targeting/tasking;
- bypassing security controls or government access restrictions.

The phrase `intelligence` in this module means **public-source research and software/standards intelligence** unless a source is explicitly documented otherwise.
