<div align="center">

# 🛡️ FRONTLINE TOOL COMPLIANCE GATE

### `SHADOW GLASS` → `AIP AGENTIC WORKFLOW` → `BUILD AUTHORIZATION` → `VALIDATION` → `FIELD RELEASE`

**Classify first. Build second. Deploy only with evidence.**

</div>

---

## 30-second explanation

This gate exists so ZYRA / XUNIA / GPT-DOUG-LLM / VIRGINIA-LLM can build lawful, auditable tools for frontline and mission-support users without assuming that every defense-related project has the same legal or security requirements.

The workflow does **not** treat “defense” as one blanket category. It evaluates the actual mission, contract, data, users, environment, export posture, and operational impact.

```text
MISSION REQUEST
   ↓
MISSION / USE-CASE CLASSIFICATION
   ↓
DATA CLASSIFICATION
   ↓
CONTRACT + EXPORT + SECURITY CHECKS
   ↓
ENVIRONMENT AUTHORIZATION
   ↓
MODEL / TOOL / AIP BOUNDARY CHECK
   ↓
BUILD AUTHORIZATION
   ↓
TEST + EVAL + HUMAN REVIEW
   ↓
FIELD RELEASE + AUDIT
```

---

## Safe frontline build lanes

This control plane is intended to support bounded, human-accountable capabilities such as:

- logistics and supply visibility;
- maintenance and readiness workflows;
- public / authorized intelligence fusion and briefing;
- defensive cybersecurity and incident response;
- search, retrieval, translation, summarization, and knowledge management;
- communications support and workflow coordination;
- geospatial visualization using authorized data;
- medical, rescue, disaster-response, and personnel-support workflows;
- sensor/telemetry analysis for monitoring and maintenance;
- training, simulation, test, evaluation, and after-action review.

The repository does **not** grant authority for autonomous target selection, weapon release, fire-control decisions, unrestricted offensive cyber operations, or other lethal/irreversible actions. Those require separate lawful authority, program controls, accredited environments, and human command responsibility outside this project.

---

## Compliance decision tree

### Gate 1 — What are we building?

Record:

- mission owner;
- intended users;
- deployment context;
- whether the tool is advisory or can cause an external side effect;
- whether the tool is reversible;
- whether the tool touches safety-critical, classified, export-controlled, CUI, personal, or operational data.

### Gate 2 — What data is involved?

Every data source must receive a handling label before model/tool access.

| Label | Example | Default workflow posture |
| --- | --- | --- |
| `PUBLIC` | public NASA data, public guidance, public web sources | eligible after provenance validation |
| `INTERNAL` | company engineering/project data | approved tenant/provider only |
| `FCI` | Federal Contract Information | contract controls apply |
| `CUI` | Controlled Unclassified Information | NARA/contract handling + applicable NIST/CMMC controls |
| `CUI_CTI` | Controlled Technical Information | treat as CUI with technical-data restrictions |
| `EXPORT_CONTROLLED` | ITAR/EAR-controlled technical data/software | export jurisdiction + recipient + environment gate required |
| `CLASSIFIED` | Confidential/Secret/Top Secret etc. | **blocked unless an accredited classified environment and authorized program explicitly permit processing** |
| `SECRET_CREDENTIAL` | passwords, private keys, tokens | never place in model prompts |

CUI is not the same thing as classified information. CUI rules apply where law, regulation, government-wide policy, or a contract requires safeguarding or dissemination controls.

### Gate 3 — Does export control apply?

Do not assume ITAR applies merely because a project is “military.” Determine jurisdiction first.

Checks:

1. Is the article, software, service, or technical data on / related to the U.S. Munitions List?
2. Is it instead subject to the Export Administration Regulations (EAR)?
3. Is the information public-domain / otherwise excluded or exempt under the applicable rules?
4. Will any foreign person, foreign system, offshore support team, or external model provider receive controlled technical data?
5. Does the organization need DDTC registration or a specific license/approval for the contemplated activity?
6. Is a Technology Control Plan or equivalent project-specific access plan required by the contract/program?

**Important:** ITAR registration is activity-specific. 22 CFR 122.1 requires registration for persons engaged in specified manufacturing/exporting/temporary importing/furnishing defense-service activities, but also contains exemptions. Registration itself does not confer export rights.

### Gate 4 — Does CMMC / NIST 800-171 apply?

The contract is authoritative.

When an information system processes, stores, or transmits FCI/CUI for a DoD contract, the workflow records the required CMMC status/level from the solicitation or contract and maps the system boundary accordingly.

For CUI in nonfederal systems, the security baseline is mapped to NIST SP 800-171 Rev. 3 and its assessment procedures in SP 800-171A Rev. 3 when required by the governing contract/agreement. For critical programs/high-value assets, the program may additionally select enhanced requirements from NIST SP 800-172 Rev. 3.

### Gate 5 — Is classified access involved?

If `CLASSIFIED = true`:

- stop commercial/local development paths;
- require an authorized classified program/environment;
- record facility/personnel access prerequisites from the sponsoring government/prime;
- verify the organization/facility clearance posture where applicable;
- do not copy classified material into GitHub, public SaaS, consumer AI, or unapproved model endpoints.

A Facility Clearance is sponsorship-based; contractors do not self-sponsor. The presence of a defense project by itself does not automatically create a clearance.

### Gate 6 — Is the compute environment authorized?

Record the environment that is permitted by the customer/program/contract. Examples may include commercial, government-authorized cloud, DoD cloud impact-level environments, disconnected enclaves, or classified systems.

**Do not hard-code “IL5/IL6” as universal requirements.** The required impact level and authorization depend on the specific data and program.

### Gate 7 — Can an outside model see the data?

Every model boundary must pass SHADOW GLASS external-model governance.

For each model/provider:

- provider/model identity registered;
- tenant and endpoint approved;
- retention/training terms recorded;
- region recorded;
- data class permitted;
- prompt/context minimized;
- secrets stripped;
- tool/action scope bounded;
- full audit event written.

`CUI`, `EXPORT_CONTROLLED`, and `CLASSIFIED` data are **external-egress denied by default** unless the exact provider/environment has explicit authorization for that data and mission.

---

## Build authorization states

| State | Meaning | Result |
| --- | --- | --- |
| 🟢 `GREEN` | required controls satisfied for the current mission/data/environment | build/test may proceed |
| 🟠 `AMBER` | unresolved compliance, contract, export, environment, or human-approval question | hold for review |
| 🔴 `RED` | known policy violation or unauthorized data/model/environment | deny build/deploy action |
| ⚫ `BLACK` | classified/controlled spill, compromised route, or integrity incident | quarantine + incident response |

---

## Agentic workflow integration

The compliance gate is inserted before any side-effecting development workflow:

```text
REQUEST
  ↓
FRONTLINE COMPLIANCE MANIFEST
  ↓
SHADOW GLASS PRECHECK
  ↓
AIP / AGENT PLAN
  ↓
CODE / ONTOLOGY / ACTION DESIGN
  ↓
POLICY-AS-CODE TEST
  ↓
SECURITY + EVAL + HUMAN REVIEW
  ↓
DEPLOYMENT AUTHORIZATION
  ↓
FIELD RELEASE
  ↓
AUDIT / MONITOR / REVOKE
```

No agent may convert an `AMBER`, `RED`, or `BLACK` manifest into `GREEN` by reasoning alone. The missing evidence must be supplied by an authorized human/program source.

---

## Required evidence package

A frontline tool release should carry:

- `frontline-build-manifest.json`;
- mission owner and technical owner;
- contract/program authority reference, when applicable;
- data inventory + classification;
- export-jurisdiction determination/status when relevant;
- system boundary / environment authorization;
- model/provider registry entries;
- tool/action scopes;
- threat model;
- security tests;
- AIP/agent eval results;
- human-approval record for elevated-impact actions;
- software bill of materials / dependency evidence as required;
- rollback and kill-switch behavior;
- deployment receipt/version;
- audit/lineage record.

Machine-readable manifest: [`schemas/frontline-build-manifest.schema.json`](./schemas/frontline-build-manifest.schema.json)  
Policy: [`policies/frontline-tool-compliance.rego`](./policies/frontline-tool-compliance.rego)  
Deterministic checker: [`../scripts/frontline_compliance_check.py`](../scripts/frontline_compliance_check.py)

---

## Source hierarchy

Use sources in this order:

1. contract / solicitation / DD254 / program security guidance / customer authorization;
2. current U.S. law and regulation;
3. authoritative government implementation guidance;
4. approved platform/tenant documentation;
5. internal policy;
6. search-engine summaries and third-party pages only as discovery leads.

The user-supplied search result that prompted this gate correctly identified themes such as ITAR, clearances, AIP licensing, and secure hosting, but search-generated AI summaries are **not** treated as legal authority.

---

## Public reference anchors

- eCFR, ITAR Part 120 (definitions/jurisdiction): https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120
- eCFR, ITAR Part 122 (registration): https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-122
- NARA CUI Registry: https://www.archives.gov/cui/registry
- NIST SP 800-171 Rev. 3: https://csrc.nist.gov/pubs/sp/800/171/r3/final
- NIST SP 800-171A Rev. 3: https://csrc.nist.gov/pubs/sp/800/171/A/r3/final
- NIST SP 800-172 Rev. 3: https://csrc.nist.gov/pubs/sp/800/172/r3/final
- DoD CMMC: https://dodcio.defense.gov/CMMC/
- DCSA Facility Clearances: https://www.dcsa.mil/FCL/
- Palantir AIP for Defense: https://www.palantir.com/platforms/aip/defense/

---

## Independence / legal boundary

This repository provides an engineering control framework, not legal advice, a security clearance, an export authorization, a CMMC certification, an Authority to Operate, or permission to access government systems. Actual authority must come from the applicable government customer, contract, regulator, security office, accrediting authority, or approved platform tenant.
