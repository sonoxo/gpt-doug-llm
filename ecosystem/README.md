# XUNIA Ecosystem v4

This directory is the canonical map for the multi-repository XUNIA / GPT-DOUG-LLM ecosystem.

## One ecosystem, distinct planes

| Plane | Repository | Primary responsibility |
|---|---|---|
| **The Black House / GPT-DOUG-LLM MAX** | `sonoxo/gpt-doug-llm` | global governance, ontology, orchestration, AI-layer contract, policy and evidence |
| **XUNIA HQ / HOLO Forge** | `sonoxo/xuniahub` | operator interface, RVIA, digital twin / HOLO, learning and mission visualization |
| **XUNIA / XuniaDAO** | `sonoxo/xuniadao` | XUNIAverse domain ontology, repository registry, identity graph, CRM, compliance and licensing |
| **ZYRA** | `sonoxo/zyra` | security gate, approval, bounded execution, audit and CI evidence |
| **The Red House** | `sonoxo/theredhouse` | authorized security assessment, findings, risk and remediation |
| **The Green House** | `sonoxo/thegreenhouse` | free/public situational intelligence across environment, bio/pharma, regulation and global events |
| **The Orange House** | `sonoxo/theorangehouse` | deterministic economic scenario planning and stress analysis |
| **Glass Onion / God's Eye View** | `sonoxo/gods-eye-viewXUNIA` | public-source geospatial visualization, provenance and spatial correlation |

**Authority split:** The Black House is the ecosystem-wide global control plane. XuniaDAO is the XUNIAverse domain ontology and registry root. It does not supersede the Black House.

Machine-readable source of truth: [`registry.v4.json`](registry.v4.json).

## Six AI layers

The ecosystem retains the six-layer architecture contract already enforced by [`config/ai-layer-manifest.json`](../config/ai-layer-manifest.json):

```text
AGENTIC AI
    ↑
GENERATIVE AI
    ↑
DEEP LEARNING
    ↑
NEURAL NETWORKS
    ↑
MACHINE LEARNING
    ↑
CLASSICAL AI
```

This is **collective ecosystem coverage**, not a claim that every repository independently implements every algorithm shown in a conceptual AI stack.

## Canonical mission flow

```text
HUMAN OPERATOR
      ↓
XUNIA HQ / RVIA / HOLO
      ↓
THE BLACK HOUSE / GPT-DOUG-LLM MAX
      ↓
XUNIA / XuniaDAO DOMAIN GRAPH
      ↓
ONTOLOGY + POLICY + SOURCE / EVIDENCE STATE
      ↓
ZYRA SECURITY + APPROVAL + EXECUTION BOUNDARY
      ↓
DOMAIN PLANE
  ├─ RED HOUSE      authorized security
  ├─ GREEN HOUSE    public situational intelligence
  ├─ ORANGE HOUSE   economic scenarios
  └─ GLASS ONION    public-source geospatial visualization
      ↓
APPROVED TOOLS / DATA / SERVICES
      ↓
TESTS + LOGS + ARTIFACTS + PROVENANCE
      ↓
HUMAN REVIEW / CONTROLLED RELEASE
```

## Cross-repository rules

1. **Authority is explicit.** A model, repository, badge, fork, or ecosystem relationship never creates external authorization.
2. **Global and domain authority are separated.** Black House governs the ecosystem control plane; XuniaDAO owns the XUNIAverse domain graph.
3. **Evidence is typed.** Live, delayed, modeled, reconstructed, inferred, and unavailable states stay distinguishable.
4. **Execution is bounded.** Consequential operations use explicit capabilities, permissions, validation and human approval where required.
5. **Upstream stays upstream.** Forks and imported research repositories preserve original attribution and licensing.
6. **Security work stays authorized.** Red-team and assessment tooling is limited to owned or explicitly authorized environments.
7. **Financial research is not custody.** Privacy/cryptography satellites are not treated as an automatic wallet, trading or transaction authority.
8. **CI is proof of configured checks, not external certification.** Passing workflows prove those checks passed for that revision only.

## Research satellites

Repositories such as `xuniaxmr`, `xmRXuniA`, `AI-Pentest`, model/runtime forks and imported toolchains can support research without becoming canonical control-plane components. Their role and boundaries are declared in the registry rather than inferred from repository names.

## Versioning

`ecosystem_version` is advanced when the canonical plane map, cross-repository authority model, or routing contract materially changes. Repository-local feature releases can evolve independently.
