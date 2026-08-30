# GPT-DOUG-LLLM Watch Dog

Local-first TypeScript IoT watchdog for a living-room camera.

Pipeline:

`RTSP camera -> FFmpeg frames -> local dog detector -> temporal bathroom-event scorer -> cooldown -> console/webhook/MQTT alarm`

The design is inspired by the real-time/open-vocabulary direction shown in the DART reference supplied for this project:

https://x.com/rsasaki0109/status/2093678821656646043?s=20

This repository does **not** copy or depend on DART. Version 0.1 uses a local COCO-SSD dog detector and exposes a detector boundary that can later be replaced by an open-vocabulary/SAM-style model.

## Important accuracy note

A generic object detector can detect a dog, but it cannot reliably label defecation by itself. This v0.1 therefore combines:

- dog confidence
- user-defined floor zone
- low motion / lingering
- compact posture evidence
- minimum hold time
- confidence threshold
- alert cooldown

Treat the result as a **suspected bathroom event** until the camera angle is calibrated. The next accuracy upgrade is a small posture classifier trained on clips from this exact living-room view.

## C360 camera status

The camera photos supplied for this project identify a C360-style battery/solar camera with a built-in siren. The missing integration detail is whether its app exposes RTSP/ONVIF or only a proprietary cloud/P2P stream.

Do not invent a siren endpoint. Until the actual camera API is identified, use one of these alert paths:

1. `console` for testing
2. `webhook` to Home Assistant / a local bridge / the camera API once known
3. `mqtt` to a local siren or automation broker

## Requirements

- Node.js 20+
- FFmpeg installed and available as `ffmpeg`
- An RTSP stream URL or an RTSP bridge for the camera

### macOS

```bash
brew install ffmpeg
```

## Install

```bash
cd watch-dog
npm install
cp .env.example .env
```

Edit `.env` and set `CAMERA_URL`.

## Run

```bash
npm start
```

Optional verbose scoring:

```bash
LOG_FRAMES=true npm start
```

## Local API

The control API binds to `127.0.0.1` by default.

```bash
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/status
curl -X POST http://127.0.0.1:8787/alarm/test
```

Keep it on loopback unless you intentionally add authentication and expose it to the LAN.

## Floor-zone calibration

`FLOOR_ZONE=x1,y1,x2,y2` uses normalized frame coordinates from `0` to `1`.

Default:

```text
0,0.30,1,1
```

That means the entire width and the lower 70% of the image. Once a screenshot from the mounted living-room camera is available, replace it with a tighter polygon/zone around the floor where accidents actually happen.

## Alert modes

### Console

```env
ALERT_MODE=console
```

### Webhook

```env
ALERT_MODE=webhook
ALERT_WEBHOOK_URL=http://127.0.0.1:8123/api/webhook/dog_alarm
ALERT_WEBHOOK_TOKEN=
```

### MQTT

```env
ALERT_MODE=mqtt
MQTT_URL=mqtt://127.0.0.1:1883
MQTT_TOPIC=home/living-room/dog-poop-alarm
```

Example event:

```json
{
  "type": "suspected-dog-bathroom-event",
  "camera": "living-room",
  "score": 0.84,
  "heldMs": 4200,
  "reasons": ["floor-zone", "low-motion", "held-posture", "compact-posture"],
  "timestamp": "2026-08-30T09:30:00.000Z"
}
```

## Recommended next upgrades

- identify the exact C360 app and stream protocol
- connect the real built-in siren endpoint if locally controllable
- draw an exact living-room floor ROI from a camera screenshot
- save event clips for false-positive review
- train `dog-squat / dog-sit / dog-lie / dog-walk` posture classes
- add an open-vocabulary detector adapter following the DART-style real-time architecture direction
- optionally run inference on an Apple Silicon Mac, NVIDIA edge box, or dedicated local server

## Privacy

Keep camera inference local. Do not commit `.env`, camera passwords, tokens, or public-facing stream URLs to GitHub.
