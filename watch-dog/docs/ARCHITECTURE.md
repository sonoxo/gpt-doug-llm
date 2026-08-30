# GPT-DOUG-LLLM Watch Dog — Visual Architecture

Reference direction supplied by the project owner:

- https://x.com/rsasaki0109/status/2093677539705409827
- https://x.com/rsasaki0109/status/2093678821656646043

These diagrams are project-specific architecture visuals. They do not copy source code or model weights from the referenced work.

## 1. Live system map

```mermaid
flowchart LR
    CAM["NKCCNUR C360\nLiving Room"] --> OSAIO["Osaio Cloud / Event Store"]
    OSAIO --> SNAP["Newest motion-event snapshot"]
    SNAP --> DOG["Local COCO-SSD\nDog Detector"]
    DOG --> ROI["Living-room Floor ROI"]
    ROI --> TRACK["Temporal posture +\nlow-motion tracker"]
    TRACK --> SCORE["Bathroom-event score"]
    SCORE -->|below threshold| WAIT["Keep Watching"]
    SCORE -->|hold >= 3 sec + threshold| ALARM["WATCH DOG ALARM"]
    ALARM --> MAC["Mac audible voice / bell"]
    ALARM --> MQTT["MQTT optional"]
    ALARM --> WEBHOOK["Webhook optional"]
    MQTT --> SIREN["Future IoT / camera siren bridge"]
    WEBHOOK --> SIREN
```

## 2. Detection decision graph

```mermaid
flowchart TD
    F["New camera event frame"] --> D{"Dog detected?"}
    D -->|No| IDLE["IDLE"]
    D -->|Yes| Z{"Dog intersects floor zone?"}
    Z -->|No| MONITOR["MONITOR ONLY"]
    Z -->|Yes| M{"Low movement / lingering?"}
    M -->|No| RESET["Reset hold timer"]
    M -->|Yes| P["Accumulate posture evidence"]
    P --> H{"Held >= EVENT_HOLD_MS?"}
    H -->|No| P
    H -->|Yes| T{"Score >= EVENT_THRESHOLD?"}
    T -->|No| MONITOR
    T -->|Yes| A["SUSPECTED BATHROOM EVENT"]
    A --> C{"Cooldown active?"}
    C -->|Yes| SUPPRESS["Suppress duplicate alert"]
    C -->|No| FIRE["Fire alarm + record state"]
```

## 3. Osaio integration path

```mermaid
sequenceDiagram
    participant WD as Watch Dog
    participant OA as Osaio API
    participant CAM as Living Room C360
    participant AI as Local AI
    participant AL as Alarm Adapter

    WD->>OA: Authenticate / resolve account region
    WD->>OA: Resolve "Living Room" device UUID
    loop Every OSAIO_POLL_MS
        CAM-->>OA: Motion / event snapshot
        WD->>OA: Request newest event metadata
        OA-->>WD: Snapshot URL + event metadata
        WD->>OA: Download new snapshot only
        WD->>AI: Run dog detection
        AI-->>WD: Dog box + confidence
        WD->>WD: Floor-zone + motion + hold scoring
        alt suspected bathroom event
            WD->>AL: Trigger alarm
        end
    end
```

## 4. Living-room region model

The supplied camera view is treated as a normalized frame. The starting ROI is intentionally conservative and must be calibrated after real events.

```mermaid
quadrantChart
    title Living Room Detection Priority
    x-axis Left side --> Right side
    y-axis Upper image --> Lower image
    quadrant-1 "Primary floor watch"
    quadrant-2 "Furniture / ignore-heavy"
    quadrant-3 "Low priority"
    quadrant-4 "Primary floor watch"
    "Sectional / couch": [0.24, 0.58]
    "Open floor center": [0.56, 0.78]
    "TV-side floor": [0.78, 0.76]
    "Back wall": [0.62, 0.30]
```

Runtime rectangle:

```text
FLOOR_ZONE=0.18,0.40,0.98,1
```

Coordinates are normalized `x1,y1,x2,y2` values from 0 to 1.

## 5. Detector evolution — current to DART-style direction

```mermaid
flowchart LR
    V1["v0.2\nCOCO-SSD dog"] --> V2["Dog posture classifier\nstand / sit / squat / lie"]
    V2 --> V3["Temporal clip model\n2-5 second context"]
    V3 --> V4["Open-vocabulary detector adapter"]
    V4 --> V5["DART/SAM-style\nreal-time multi-class direction"]

    V1 -. stable interface .-> API["Detector Interface"]
    V2 -. same interface .-> API
    V4 -. same interface .-> API
```

The detector boundary should stay replaceable so the runtime, alerting, camera ingestion, cooldown, and API layers do not depend on one model family.

## 6. Privacy boundary

```mermaid
flowchart TB
    HOME["Home network / local Mac"]
    CLOUD["Osaio cloud event snapshot"]
    AI["Local inference"]
    STORE["Optional local event log"]
    OUT["Optional MQTT / webhook"]

    CLOUD -->|event image| HOME
    HOME --> AI
    AI --> STORE
    AI --> OUT

    NOTE["No camera credentials, tokens, snapshots, or private stream URLs belong in Git"]
    NOTE -. policy .-> HOME
```

## 7. Operational state machine

```mermaid
stateDiagram-v2
    [*] --> Starting
    Starting --> Ready: model + source initialized
    Starting --> Degraded: source auth/config error
    Degraded --> Starting: restart after config fix
    Ready --> DogSeen: dog detected
    DogSeen --> Ready: dog disappears
    DogSeen --> Candidate: floor zone + low motion
    Candidate --> DogSeen: motion resumes
    Candidate --> Alarm: hold + score threshold
    Alarm --> Cooldown
    Cooldown --> Ready: cooldown expires
```

## Status

- GitHub architecture visual: implemented
- Osaio event source: implemented on the feature branch
- local dog inference: implemented
- Mac audible alarm: implemented
- exact C360 built-in siren command: not yet proven
- posture-specific training data: not yet collected
