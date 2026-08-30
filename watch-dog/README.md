# GPT-DOUG-LLLM Watch Dog

> **Living Room AI Watchdog** — Osaio camera events → local dog detection → temporal bathroom-event scoring → audible / IoT alarm.

```mermaid
flowchart LR
    C["📷 Living Room C360"] --> O["☁️ Osaio event"]
    O --> D["🐕 Local dog detector"]
    D --> Z["⌗ Floor-zone filter"]
    Z --> P["⏱ Posture + hold score"]
    P -->|suspected event| A["🚨 WATCH DOG ALARM"]
    A --> M["🔊 Mac"]
    A --> Q["📡 MQTT / Webhook"]
```

**Full GitHub-rendered visual architecture:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Current architecture

The original RTSP-only prototype has been upgraded for the camera ecosystem shown in the supplied screenshots. `CAMERA_SOURCE=osaio` polls new Osaio motion-event snapshots and runs inference locally. RTSP remains available as a fallback for cameras that expose it.

The implementation direction is informed by the real-time/open-vocabulary references supplied for this project:

- https://x.com/rsasaki0109/status/2093677539705409827
- https://x.com/rsasaki0109/status/2093678821656646043

This project does **not** copy or depend on those projects. The current detector is COCO-SSD with a replaceable detector boundary so a stronger open-vocabulary / SAM-style model can be introduced later.

## What Watch Dog considers a suspected bathroom event

A generic dog detector does not understand defecation. Watch Dog therefore combines multiple signals instead of triggering from one frame:

- dog confidence
- living-room floor ROI
- low movement / lingering
- compact posture evidence
- minimum hold duration
- total confidence threshold
- alert cooldown

```mermaid
stateDiagram-v2
    [*] --> Watching
    Watching --> DogSeen: dog detected
    DogSeen --> Watching: dog disappears
    DogSeen --> Candidate: floor zone + low motion
    Candidate --> DogSeen: movement resumes
    Candidate --> Alarm: hold >= 3 sec and score passes
    Alarm --> Cooldown
    Cooldown --> Watching: 60 sec expires
```

Treat the result as a **suspected bathroom event** until the camera angle is calibrated and posture-specific training clips are collected.

## Requirements

- Node.js 20+
- macOS, Linux, or Windows for inference
- Osaio credentials/session for `CAMERA_SOURCE=osaio`, **or** an RTSP URL for `CAMERA_SOURCE=rtsp`
- FFmpeg only when using RTSP mode

## Install

```bash
cd watch-dog
npm install
cp .env.example .env
npm run typecheck
npm start
```

Do not commit `.env`.

## Osaio mode

Default configuration:

```env
CAMERA_SOURCE=osaio
CAMERA_NAME=Living Room
OSAIO_DEVICE_NAME=Living Room
OSAIO_POLL_MS=2000
ALERT_MODE=macos
```

Watch Dog can use either an authenticated Osaio session or account login configuration. Keep all authentication material local.

A separate shared Osaio account is preferable to putting the primary mobile-app account into an unattended service.

## RTSP fallback

```env
CAMERA_SOURCE=rtsp
CAMERA_URL=rtsp://user:password@camera.local:554/stream1
```

## Living-room floor region

Starting ROI derived from the supplied living-room framing:

```env
FLOOR_ZONE=0.18,0.40,0.98,1
```

Values are normalized `x1,y1,x2,y2` coordinates. Tune this after mounting the camera permanently.

## Alarm modes

### Mac audible alarm

```env
ALERT_MODE=macos
```

The runtime emits a terminal bell and uses macOS `say` for an audible warning.

### Console

```env
ALERT_MODE=console
```

### Webhook

```env
ALERT_MODE=webhook
ALERT_WEBHOOK_URL=http://127.0.0.1:8123/api/webhook/dog_alarm
```

### MQTT

```env
ALERT_MODE=mqtt
MQTT_URL=mqtt://127.0.0.1:1883
MQTT_TOPIC=home/living-room/dog-poop-alarm
```

The exact proprietary C360 built-in siren command is **not claimed as working until it is proven against the real device**. MQTT/webhook remain the safe integration boundary for that final adapter.

## Local API

The API binds to loopback by default.

```bash
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/status
curl -X POST http://127.0.0.1:8787/alarm/test
```

You can also inject a JPEG into the exact inference path for calibration/testing:

```bash
curl -X POST \
  -H 'Content-Type: image/jpeg' \
  --data-binary @frame.jpg \
  http://127.0.0.1:8787/frame
```

## Runtime event

```json
{
  "type": "suspected-dog-bathroom-event",
  "camera": "Living Room",
  "score": 0.84,
  "heldMs": 4200,
  "reasons": ["floor-zone", "low-motion", "held-posture", "compact-posture"],
  "timestamp": "2026-08-30T09:30:00.000Z"
}
```

## Roadmap

```mermaid
flowchart LR
    A["v0.2 COCO dog"] --> B["posture classifier"]
    B --> C["temporal clip model"]
    C --> D["open-vocabulary adapter"]
    D --> E["real-time DART/SAM-style direction"]
```

Next accuracy upgrades:

- calibrate the exact floor ROI
- collect false-positive and true-event clips locally
- train `stand / sit / squat / lie / walk` posture classes
- add temporal 2–5 second clip inference
- connect and verify the exact C360 siren command, if the device exposes one

## Privacy and security

Camera inference is intended to remain local after the Osaio event image is obtained. Never commit camera credentials, Osaio tokens, `.env`, snapshots from inside the home, or private stream URLs to GitHub.
