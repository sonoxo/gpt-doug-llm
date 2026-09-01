# BIG VIRGINIA // VA3LM

**Virginia Agentic Large Learning Language Model — v0.4.0**

Coding, orchestration, ontology, capability, geospatial, public-source intelligence, and evidence command center for **GPT-DOUG-LLM**, **ZYRA**, **XUNIAHUB**, and the wider RVIA/VA stack.

- Port: **8088**
- Agent swarm
- PACK-inspired capability plane
- Authorized non-identifying geospatial tracking
- Google Maps visualization surface
- RVIA Federal Intel public-source catalog
- Coding workflows
- Palantir-style ontology blueprint
- Test + security gates
- Human approval before write/publish actions
- Commercial/explainer agent for plain-language demos

## BIG VIRGINIA capability plane

VA3LM adapts architecture patterns from `sonoxo/pack` and extends the plane with authorization-bounded geospatial and public-source intelligence capabilities:

`CORE → AUTH → SCHEMA → DOCUMENTS → STATE → CODEGEN → SDK → APP → GEOSPATIAL → FEDERAL-INTEL-OSINT → MONOREPO/CI`

PACK itself is marked **ALPHA / not intended for production use**, so VA3LM treats it as an architectural reference rather than blindly importing it as a production dependency. VA3LM-owned tests, security gates, approval gates, and deployment validation remain authoritative.

```bash
va3lm capabilities
```

Full PACK mapping: [`docs/PACK_CAPABILITY_PLANE.md`](docs/PACK_CAPABILITY_PLANE.md)

## RVIA Federal Intel public-source catalog

The public-source layer implements the five intelligence blocks represented in the operator reference:

- **CIA** — Central Intelligence Agency
- **NSA** — National Security Agency
- **NRO** — National Reconnaissance Office
- **NGP** — National Geospatial-Intelligence Program, mapped to NGA public sources
- **GDIP** — General Defense Intelligence Program, mapped to DIA public sources

The catalog promotes only verified official GitHub organizations. As verified for this catalog date, NSA exposes `NationalSecurityAgency` and `nsacyber`; NGA exposes `ngageoint`. CIA, NRO, and DIA/GDIP are sourced from their official government public sites rather than third-party GitHub repositories.

```bash
va3lm federal-intel
va3lm federal-intel --github-only
va3lm federal-intel --entity cia
va3lm federal-intel --entity nsa
va3lm federal-intel --entity nro
va3lm federal-intel --entity ngp
va3lm federal-intel --entity gdip
```

Full guide: [`docs/RVIA_FEDERAL_INTEL.md`](docs/RVIA_FEDERAL_INTEL.md)

## Geospatial tracking + Google Maps

The requested public reference is NSA's **How We Found Bin Laden: The Basics of Foreign Signals Intelligence**. VA3LM adapts only high-level workflow concepts such as provenance, timestamps, correlation, confidence/uncertainty, map context, and human review. It does not implement communications interception, biometrics, or covert person tracking.

```bash
va3lm tracking
va3lm tracking --sample
```

The deterministic sample emits Google Maps-compatible GeoJSON for an imaginary authorized Virginia asset.

To enable the browser map:

```bash
export GOOGLE_MAPS_BROWSER_KEY='YOUR_BROWSER_RESTRICTED_KEY'
va3lm serve
```

Then open:

```text
http://127.0.0.1:8088/tracking-map
```

Never commit a Google Maps API key. Enable the Maps JavaScript API in the associated Google Cloud project and restrict the browser key by HTTP referrer.

Full guide: [`docs/GOOGLE_MAPS_TRACKING.md`](docs/GOOGLE_MAPS_TRACKING.md)

## Run

```bash
cd va3lm
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
va3lm serve
```

Open `http://127.0.0.1:8088`.

## Interactive command deck

```bash
va3lm agents
va3lm capabilities
va3lm federal-intel
va3lm federal-intel --github-only
va3lm tracking
va3lm tracking --sample
va3lm ontology
va3lm plan "Build a FastAPI endpoint with tests"
va3lm explain "VA3LM ontology workflow"
```

Activate the configured GPT-DOUG-LLM brain:

```bash
export VA3LM_MODEL_URL=http://127.0.0.1:11434/v1
export VA3LM_MODEL_NAME=gpt-doug-llm
va3lm brain "Refactor this service safely"
```

Start the 8088 command center:

```bash
va3lm serve --host 127.0.0.1 --port 8088
```

## Ecosystem

```mermaid
flowchart TD
    U[Operator] --> C[BIG VIRGINIA / VA3LM :8088]
    C --> P[Capability Plane]
    P --> PC[Core]
    P --> PA[Auth]
    P --> PS[Schema + Documents]
    P --> PST[State]
    P --> PG[Codegen + SDK]
    P --> APP[App Surface]
    P --> GEO[Authorized Geospatial Tracking]
    GEO --> GJ[GeoJSON]
    GJ --> GM[Google Maps]
    GM --> HR[Human Review]
    P --> FI[RVIA Federal Intel OSINT]
    FI --> CIA[CIA public sources]
    FI --> NSA[NSA official GitHub + public sources]
    FI --> NRO[NRO public sources]
    FI --> NGA[NGA / NGP official GitHub + public sources]
    FI --> DIA[DIA / GDIP public sources]
    FI --> HR
    C --> B[GPT-DOUG-LLM Brain]
    C --> A[Architect]
    A --> D[Coder]
    D --> O[Ontology]
    O --> T[Test]
    T --> S[Security]
    S --> R[Reviewer]
    R --> G{Human approval}
    G -->|approve| E[Evidence + Build]
    G -->|hold| D
    E --> O
```

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/healthz` | health |
| GET | `/api/status` | runtime + capability status |
| GET | `/api/agents` | agent roster |
| GET | `/api/ontology` | ontology |
| GET | `/api/capabilities` | Big Virginia capability manifest |
| GET | `/api/federal-intel` | CIA/NSA/NRO/NGP/GDIP public-source catalog |
| GET | `/api/federal-intel/github` | verified official GitHub organizations/repositories only |
| GET | `/api/federal-intel/{entity_id}` | one agency/program public-source manifest |
| GET | `/api/tracking` | tracking source/boundary manifest |
| GET | `/api/tracking/sample` | deterministic Virginia demo GeoJSON |
| POST | `/api/tracking/geojson` | validate/normalize authorized observations |
| GET | `/tracking-map` | Google Maps visualization |
| POST | `/api/plan` | build workflow |
| POST | `/api/brain` | ask configured model |
| POST | `/api/explain` | generate commercial-style explainer |

## Public-source security boundary

RVIA Federal Intel is limited to publicly released, lawfully accessible sources. It does not authorize classified/leaked collection, credential bypass, communications interception, covert person tracking, biometric identification, operational targeting, or evasion of government/security controls.

## Development

```bash
pytest -q
ruff check src tests
bandit -q -ll -r src
python -m compileall -q src
```

The dedicated `VA3LM Big Virginia` GitHub Actions gate verifies the installed CLI and capability manifest. Tracking regression tests verify GeoJSON generation and identity-field rejection; federal-intel tests verify official-source labeling and program/agency classification.

Private software project. Not a government agency.
