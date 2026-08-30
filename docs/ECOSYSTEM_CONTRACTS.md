# XUNIA/ZYRA/GPT-DOUG-LLM Ecosystem Contracts

**Version:** 0.1.0  
**Date:** 2026-08-30  
**Status:** DEFINING

This document defines the shared contracts across the three-repository ecosystem.

---

## Repository Roles

| Repository | Owner | Role | Contracts |
|---|---|---|---|
| **sonoxo/gpt-doug-llm** | GPT-DOUG-LLM | Orchestration, reasoning, coding agent | MissionBudget, DougRuntime, ZYRA watchdog |
| **sonoxo/zyra** | ZYRA | Credential/evidence ontology, shared types | VirginiaMission, EvidenceState, CredentialEvidence |
| **sonoxo/gods-eye-viewXUNIA** | XUNIA Glass Onion | Public-source spatial intelligence | EvidenceState, GeospatialObject, SourceProvenance |
| **RVAI** | (Reserved) | Downstream consumer | Unresolved |

---

## P1 Cross-Repo Contracts

### 1. VIRGINIA Mission Language

**Producer:** sonoxo/zyra (`apps/zyra-live-implement/src/virginia.ts`)  
**Consumers:** sonoxo/gpt-doug-llm, sonoxo/zyra

**TypeScript Definition:**
```typescript
export type VirginiaStep = {
  op:
    | "LIST_ONTOLOGIES"
    | "LIST_OBJECT_TYPES"
    | "LIST_OBJECTS"
    | "APPLY_ACTION"
    | "GEOVISION_STATUS"
    | "GEOVISION_CAMERAS"
    | "GEOVISION_DETECTIONS"
    | "MISSION_TWIN_STATUS"
    | "SPACEX_LAUNCH_LATEST"
    | "SPACEX_LAUNCHES"
    | "FPRIME_TELEMETRY"
    | "BRAIN_UPDATE_SOURCE"
    | "SHUTDOWN_ZYRA"
    | "NOTE";
  ontology?: string;
  objectType?: string;
  action?: string;
  parameters?: Record<string, unknown>;
  text?: string;
};

export type VirginiaMission = {
  mode: "VIRGINIA" | "VAL3M" | "VA3LM" | "RICHMONDVA3LM";
  agents: number;
  stopWhen: string;
  profile?: string;
  steps: VirginiaStep[];
};
```

**Status:** ✅ DEFINED in TypeScript  
**Required Consumer Updates:** gpt-doug-llm must import and validate missions

---

### 2. Evidence State Enum

**Producer:** sonoxo/gods-eye-viewXUNIA (README documents; code needs implementation)  
**Consumers:** sonoxo/zyra, sonoxo/gpt-doug-llm

**TypeScript Definition:**
```typescript
export enum EvidenceState {
  LIVE = "LIVE",
  DELAYED = "DELAYED",
  RECONSTRUCTED = "RECONSTRUCTED",
  MODELED = "MODELED",
  PARTIAL = "PARTIAL",
  UNAVAILABLE = "UNAVAILABLE",
}

export interface EvidenceObject {
  id: string;
  state: EvidenceState;
  source: string;
  retrievedAt: ISO8601Timestamp;
  confidence?: number; // 0-100
  provenance?: {
    sourceUrl: string;
    attribution: string;
    licenseTerms?: string;
  };
}
```

**Status:** 🚧 NEEDS IMPLEMENTATION in gods-eye-viewXUNIA  
**Required Action:** Add TypeScript types file and export

---

### 3. Credential Evidence (sonoxo/zyra)

**Producer:** sonoxo/zyra  
**Consumers:** sonoxo/gpt-doug-llm, agency_cloud

**TypeScript Definition (from audit):**
```typescript
export interface CredentialEvidence {
  id: string;
  type: "BADGE" | "CERTIFICATE" | "SKILL" | "LICENSE" | "CLEARANCE" | "PLATFORM_ACCESS";
  issuer: string;
  issuedDate: ISO8601Date;
  expiresDate?: ISO8601Date;
  verificationId?: string;
  issuanceSource: string; // e.g., "credly", "course-platform", "palantir-org"
  evidence: string; // proof URL or artifact hash
  isExpired: boolean;
  isAuthorization: boolean; // true only if it grants actual access rights
  auditState: "VERIFIED" | "UNDER_REVIEW" | "REVOKED" | "HISTORICAL";
}
```

**Status:** 🚧 NEEDS DEFINITION  
**Required Action:** Define in sonoxo/zyra/shared/types/CredentialEvidence.ts

---

### 4. VA3LM / GeoVision Operations

**Producer:** sonoxo/zyra (`apps/zyra-live-implement`)  
**Consumers:** sonoxo/gpt-doug-llm, sonoxo/gods-eye-viewXUNIA

**Operations:**
- `GEOVISION_STATUS` → Get detector health + configuration
- `GEOVISION_CAMERAS` → List authorized camera objects
- `GEOVISION_DETECTIONS` → List detection events with evidence state

**OpenAPI Schema:**
```yaml
/api/va3lm/geovision/status:
  get:
    responses:
      200:
        schema:
          type: object
          properties:
            foundryConfigured: boolean
            foundryOnline: boolean
            eyerisModelService: { online: boolean, version: string }
            wgs84Pipeline: { operational: boolean }
            privacyBoundary: string # "non-identifying-object-scene-recognition"

/api/va3lm/geovision/cameras:
  post:
    parameters:
      - name: ontology
        in: query
        type: string
    responses:
      200:
        schema:
          type: object
          properties:
            cameras:
              type: array
              items: { $ref: "#/components/schemas/EvidenceObject" }

/api/va3lm/geovision/detections:
  post:
    parameters:
      - name: ontology
        in: query
        type: string
    responses:
      200:
        schema:
          type: object
          properties:
            detections:
              type: array
              items:
                type: object
                properties:
                  id: string
                  state: { $ref: "#/components/schemas/EvidenceState" }
                  confidence: number
                  timestamp: string
                  location: { lat: number, lon: number }
```

**Status:** 🚧 NEEDS IMPLEMENTATION  
**Required Action:** Implement endpoints in sonoxo/zyra/apps/zyra-live-implement/server.ts

---

### 5. Palantir Foundry Integration

**Producer:** sonoxo/gpt-doug-llm (foundry_guard.py, palantir_foundry.py)  
**Consumers:** sonoxo/zyra (apps/zyra-live-implement), agency_cloud

**Contract:**
- All Foundry write operations must require `writes_enabled=True`
- All Foundry actions require human approval gate in calling code
- No persistent authentication without explicit caller authorization
- Server-side tokens only; never send to browser

**Status:** ✅ DEFINED in Python  
**Required Consumer Updates:** ZYRA must import FoundryClient from gpt-doug-llm

---

## P1 Implementation Order

1. **Create shared types package:** `sonoxo/zyra/shared/types/`
   - Export VirginiaMission, VirginiaMission, EvidenceState, CredentialEvidence
   - Provide JSON Schema validation

2. **Add Evidence State enum to gods-eye-viewXUNIA**
   - Create `src/types/EvidenceState.ts`
   - Export and document

3. **Wire gpt-doug-llm → ZYRA imports**
   - Import VirginiaMission from sonoxo/zyra/shared
   - Add validation in agent core

4. **Implement VA3LM endpoints in zyra-live-implement**
   - Add `/api/va3lm/geovision/*` routes
   - Connect to Foundry or mock for tests

5. **Add ecosystem integration tests**
   - Test VIRGINIA parsing across repos
   - Test EvidenceState labeling in Glass Onion
   - Test credential evidence in agency_cloud

---

## Validation Checklist

- [ ] VirginiaMission types shared and imported
- [ ] EvidenceState enum defined and exported
- [ ] CredentialEvidence schema in ZYRA
- [ ] VA3LM operations documented + tested
- [ ] Foundry contract contract enforced in all consumers
- [ ] Integration tests passing
- [ ] Cross-repo CI matrix added

