<div align="center">

# ◈ GSPO // GPT-DOUG-LLLM WATCH DOG

### ZYRA-INFLUENCED LOCAL VISION + EVENT INTELLIGENCE PIPELINE

<a href="https://github.com/sonoxo/zyra/blob/main/ZYRA.README.md">
  <img src="https://raw.githubusercontent.com/sonoxo/zyra/main/docs/assets/zyra-credential-pathway.svg" width="280" alt="ZYRA Application Credential — Verified Credential Pathway" />
</a>

**ZYRA APPLICATION CREDENTIAL · VERIFIED CREDENTIAL PATHWAY**

**PRIVATE CAMERA → LOCAL AI → ALARM → ZYRA GEOVISION → PALANTIR CONTAINER**

![TypeScript](https://img.shields.io/badge/TypeScript-Local_AI-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![ZYRA](https://img.shields.io/badge/ZYRA-GeoVision-7B2CFF?style=for-the-badge)
![GSPO](https://img.shields.io/badge/GSPO-One_Command-00C2FF?style=for-the-badge)
![Privacy](https://img.shields.io/badge/Public_CCTV-BLOCKED-111111?style=for-the-badge)
![Identity](https://img.shields.io/badge/Identity_Recognition-DISABLED-111111?style=for-the-badge)

`LOCAL-FIRST` · `PRIVATE CAMERA ONLY` · `HUMAN-GOVERNED PALANTIR HANDOFF`

</div>

---

## ◈ SYSTEM OVERVIEW

GSPO is the one-command runtime for the GPT-DOUG Watch Dog stack. It watches an explicitly authorized Living Room camera view, performs local dog detection and temporal bathroom-event scoring, triggers an alarm, forwards the structured event into ZYRA GeoVision, and prepares the event for a governed Palantir/Foundry handoff.

```mermaid
flowchart LR
    PHONE["📱 iPhone\nOsaio / Living Room"] --> MIRROR["🪞 Apple iPhone Mirroring"]
    MIRROR --> CAPTURE["🎯 Private Screen ROI\nmacOS capture"]

    subgraph WATCHDOG["◈ GSPO WATCH DOG // LOCAL CONTAINER"]
        direction LR
        DETECT["🐕 Dog Detector\nCOCO-SSD"] --> FLOOR["⌗ Floor-Zone Filter"]
        FLOOR --> TEMP["⏱ Temporal Posture\n+ Hold Scoring"]
        TEMP --> EVENT["⚡ Suspected Bathroom Event"]
    end

    CAPTURE --> DETECT
    EVENT --> ALARM["🚨 macOS Alarm"]
    EVENT --> ZYRA["🟣 ZYRA GeoVision\n:5050"]

    subgraph PALANTIR["⬡ PALANTIR CONTAINER // GOVERNED DOWNSTREAM"]
        direction TB
        QUEUE["📥 Pending Event Queue"]
        ONTOLOGY["🧬 Ontology Envelope"]
        APPROVAL["🛡 Human Approval Gate"]
        FOUNDRY["🏛 Foundry / Action Interface"]
        QUEUE --> ONTOLOGY --> APPROVAL --> FOUNDRY
    end

    ZYRA --> QUEUE

    PUBLIC["🌐 Public CCTV"] -. HARD BLOCK .-> CAPTURE
```

> **Palantir container status:** Watch Dog and ZYRA currently prepare the event for the Palantir/Foundry boundary. Foundry writes remain approval-gated; the README does not claim autonomous Palantir mutation when credentials/actions have not been explicitly configured and approved.

---

## ◈ LIVE STACK

| Layer | Runtime | Role | Default State |
|---|---|---|---|
| **GSPO** | Terminal command | Boots the monitoring stack | `READY` |
| **Watch Dog** | `127.0.0.1:8787` | Local vision + bathroom scoring | `LOCAL` |
| **ZYRA GeoVision** | `127.0.0.1:5050` | Structured event ingestion + queue | `AUTO-BOOT BY GSPO` |
| **Palantir Container** | Governed downstream boundary | Ontology/action envelope | `PENDING_HUMAN_APPROVAL` |
| **Public CCTV** | Any public/internet camera source | Not permitted by this profile | `BLOCKED` |
| **Identity Recognition** | Face/identity inference | Not part of Watch Dog | `DISABLED` |

---

## ◈ ONE COMMAND: `GSPO`

Install/update the launcher once:

```bash
cd ~/gpt-doug-llm/gpt-doug-llm/watch-dog
git pull --ff-only origin gpt-doug-lllm-watch-dog
npm install
npm link --force
```

Then run the full stack from anywhere:

```bash
GSPO
```

GSPO checks ZYRA first. If `:5050` is offline, it starts ZYRA, waits for it to become available, and then launches Watch Dog.

```text
GSPO          → start ZYRA if needed + start Watch Dog
GSPO status   → show current Watch Dog state
GSPO test     → trigger alarm + ZYRA pipeline test
GSPO stop     → stop Watch Dog; stop ZYRA only if GSPO started it
```

---

## ◈ EVENT INTELLIGENCE

Watch Dog deliberately does **not** treat one dog detection as a bathroom event. The event scorer combines multiple signals over time.

```mermaid
stateDiagram-v2
    [*] --> WATCHING
    WATCHING --> DOG_SEEN: dog confidence passes
    DOG_SEEN --> WATCHING: dog disappears
    DOG_SEEN --> FLOOR_CANDIDATE: inside floor ROI
    FLOOR_CANDIDATE --> POSTURE_HOLD: low motion / compact posture
    POSTURE_HOLD --> FLOOR_CANDIDATE: movement resumes
    POSTURE_HOLD --> ALARM: hold + total score pass
    ALARM --> COOLDOWN
    COOLDOWN --> WATCHING: cooldown expires
```

### Signal fusion

```mermaid
flowchart TD
    A["Dog confidence"] --> S["Bathroom-event score"]
    B["Floor ROI"] --> S
    C["Low motion"] --> S
    D["Posture evidence"] --> S
    E["Hold duration"] --> S
    S -->|threshold passed| X["🚨 Alarm + ZYRA event"]
```

The current result should be interpreted as a **suspected bathroom event** until real camera examples have been collected and posture-specific training has been validated.

---

## ◈ CURRENT PRIVATE CAMERA PATH

The working Mac/iPhone route avoids depending on nonexistent Osaio macOS software:

```text
C360 CAMERA
    ↓
OSAIO ON iPHONE
    ↓
APPLE iPHONE MIRRORING
    ↓
PRIVATE SCREEN REGION ON MAC
    ↓
WATCH DOG LOCAL AI
    ↓
ALARM + ZYRA GEOVISION
    ↓
PALANTIR CONTAINER / APPROVAL QUEUE
```

Current calibrated profile:

```env
CAMERA_SOURCE=macos-screen
CAMERA_NAME=Living Room
SCREEN_REGION=1164,134,352,226
SCREEN_POLL_MS=750
DOG_CONFIDENCE=0.30
LOG_FRAMES=true
```

Do not move the mirrored camera window after calibrating `SCREEN_REGION` unless you recalibrate the region.

---

## ◈ ZYRA GEOVISION BRIDGE

Watch Dog forwards alarm events to:

```text
POST http://127.0.0.1:5050/api/va3lm/geovision/watch-dog/events
```

ZYRA exposes the Watch Dog stream and the Palantir-pending view through its GeoVision interface.

```text
GET /api/va3lm/geovision/watch-dog/events
GET /api/va3lm/geovision/watch-dog/palantir-pending
```

### Event envelope

```json
{
  "type": "suspected-dog-bathroom-event",
  "camera": "Living Room",
  "score": 0.84,
  "heldMs": 4200,
  "reasons": [
    "floor-zone",
    "low-motion",
    "held-posture",
    "compact-posture"
  ],
  "timestamp": "2026-08-30T09:30:00.000Z"
}
```

---

## ◈ PALANTIR CONTAINER

The Palantir block is modeled as a **governed integration container**, not as an unrestricted actuator.

```mermaid
flowchart TB
    IN["ZYRA GeoVision Event"] --> Q["Palantir Pending Queue"]

    subgraph C["⬡ PALANTIR CONTAINER"]
        Q --> V["Validate schema + provenance"]
        V --> O["Map to ontology object/action"]
        O --> H{"Human approval?"}
        H -->|NO| HOLD["Hold / Review"]
        H -->|YES| F["Foundry action interface"]
    end

    F --> AUDIT["Immutable audit context"]
```

### Container contract

- receives only structured Watch Dog / ZYRA events
- rejects public-CCTV provenance
- identity recognition remains disabled
- maps events to a reviewable ontology/action envelope
- holds state at `PENDING_HUMAN_APPROVAL` until explicitly approved
- does not invent Foundry credentials, ontology names, or action endpoints

---

## ◈ LOCAL CONTROL API

Watch Dog binds to loopback by default.

```bash
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/status
curl -X POST http://127.0.0.1:8787/alarm/test
```

Inject a local JPEG through the same inference path:

```bash
curl -X POST \
  -H 'Content-Type: image/jpeg' \
  --data-binary @frame.jpg \
  http://127.0.0.1:8787/frame
```

---

## ◈ OPTIONAL CAMERA SOURCES

### macOS screen / iPhone Mirroring

```env
CAMERA_SOURCE=macos-screen
SCREEN_REGION=1164,134,352,226
```

### Osaio event bridge

The repository also contains an Osaio event adapter. It requires valid private request-signing/session material and is not needed for the current phone + Mac mirrored workflow.

```env
CAMERA_SOURCE=osaio
OSAIO_DEVICE_NAME=Living Room
```

### Private RTSP fallback

```env
CAMERA_SOURCE=rtsp
CAMERA_URL=rtsp://user:password@192.168.1.50:554/stream1
```

Only explicit private/local RTSP addresses are accepted by the Watch Dog privacy gate. Public CCTV and arbitrary internet camera feeds are blocked.

---

## ◈ ALERT MATRIX

| Mode | Configuration | Result |
|---|---|---|
| **macOS** | `ALERT_MODE=macos` | System sound + spoken warning |
| **console** | `ALERT_MODE=console` | Terminal event |
| **webhook** | `ALERT_MODE=webhook` | POST structured event |
| **MQTT** | `ALERT_MODE=mqtt` | QoS event on configured topic |

The proprietary C360 built-in siren endpoint is **not claimed as working** until it is proven against the actual device protocol.

---

## ◈ MODEL ROADMAP

```mermaid
flowchart LR
    V1["COCO dog detector"] --> V2["Posture classifier"]
    V2 --> V3["2–5 sec temporal model"]
    V3 --> V4["Open-vocabulary adapter"]
    V4 --> V5["DART / SAM-style real-time direction"]
    V5 --> V6["Validated bathroom-event classifier"]
```

Reference direction supplied for this project:

- https://x.com/rsasaki0109/status/2093677539705409827
- https://x.com/rsasaki0109/status/2093678821656646043

These references are architectural inspiration only; Watch Dog does not claim to copy or depend on those projects.

---

## ◈ PRIVACY / SECURITY BOUNDARY

```mermaid
flowchart LR
    HOME["🏠 Authorized Home Camera"] --> LOCAL["💻 Local Watch Dog Inference"]
    LOCAL --> META["Structured Event Metadata"]
    META --> Z["🟣 ZYRA"]
    Z --> P["⬡ Palantir Approval Container"]

    RAW["Raw Home Frames"] -. not committed .-> GIT["GitHub"]
    CREDS["Passwords / Tokens"] -. never committed .-> GIT
    CCTV["Public CCTV"] -. blocked .-> LOCAL
    ID["Identity Recognition"] -. disabled .-> LOCAL
```

Never commit `.env`, camera passwords, Osaio tokens, private snapshots, private stream URLs, or Foundry credentials.

---

<div align="center">

### ◈ GSPO STATUS PHILOSOPHY

`SEE LOCALLY` → `SCORE TEMPORALLY` → `ALERT IMMEDIATELY` → `STRUCTURE IN ZYRA` → `GOVERN IN PALANTIR`

**GPT-DOUG-LLLM // ZYRA GEOVISION // GSPO WATCH DOG**

</div>
