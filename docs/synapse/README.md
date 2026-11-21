# CL1 SENSORY SYNAPSE / GPT-DOUG-LLM

**Public route after GitHub Pages deploy:** https://xunia.org/synapse/

A browser-only, free **multisensory neural graph simulation** connecting the existing
XUNIA / GPT-DOUG-LLM ontology. It is an experiential software interface,
**not** a Neuralink implant integration, biological computing platform, or real
brain stimulation and recording device.

## Source integration

Three source-qualified, same-origin JSON files are loaded without API keys:

| Source | Objects | Evidence |
| --- | ---: | --- |
| `../molecules/catalogs/seed.json` | 33 | Curated chemical teaching models; 3D coordinates illustrative |
| `../cosmos/planets/catalog.json` | 8 | NASA/JPL sourced physical and approximate orbital metadata |
| `../fusion/ontology.json` | 21 | Local schema / proposed infrastructure / synthetic operations |
| **Total** | **62** | Source link and evidence label preserved |

The canvas displays an original **56-node/112-link synthetic neural mesh**, not living
neurons, cortical spike recordings, EEG, or neural-decode output. Generated
sound frequency is a deterministic function of selected ontology ID, **not**
measured chemical spectra, neuronal frequency or any property of a planet.

## Five perceptual channels

- **Sight**: live procedural graph animation, synapse/cortex/field modes, orbit/zoom, visual pulses. Honors reduced-motion settings; paused still views remain interactive.
- **Hearing**: explicitly enabled original short oscillator sounds using Web Audio, with capped low gain (max 0.009), stereo panning where supported. Sound is disabled on page exit or tab hiding and can be silenced immediately. No autoplay.
- **Speech**: manually requested browser text-to-speech for object description. Depending on browser/OS voice provider, speech could be synthesized through a service. No guaranteed offline speech processing, and no microphone/voice recognition is used.
- **Touch**: pointer/touch/keyboard input paints a virtual pressure halo and visual response. **No physical vibration, gamepad force feedback or nerve actuation.**
- **Smell / Taste**: optional **conceptual vocabulary**, not sensed or produced odors/flavors, not factual chemical sensory properties or safety-to-consume claims. The browser cannot physically deliver smells/tastes with this app.

Each channel can be toggled, and the UI maintains accessible controls and text descriptions.

## Working tools

Choose an ontology domain, filter objects, select one, rotate or zoom canvas,
send pulses, change visual mode and intensity, explore a local event log,
save a real Canvas PNG, export a source-labeled session JSON, and run a self-test.

Cmd/Ctrl+K focuses the finite, **not-shell** command console:

```text
/domain planets
/select Earth
/view cortex
/intensity 75
/pulse
/health
```

Other commands include `/find`, `/pause`, `/play`, `/export`,
`/capture`, and `/reset`. All outputs are local; no runtime data is sent
to external servers.

## Run on Mac (one command)

```bash
cd ~/xunia-xenology-live && git pull --ff-only && bash scripts/xunia-cosmos
```

Open the root server's `/synapse/` route using the printed localhost port.
For an existing server at port 8873, this is
`http://127.0.0.1:8873/synapse/`.

## Verification

```bash
node --check docs/synapse/synapse.js
python3 -m unittest discover -s tests -p 'test_xunia_synapse.py' -v
python3 tests/xunia_synapse_chrome_smoke.py
```

The COSMOS GitHub Actions workflow tests real Chromium rendering in normal and
reduced-motion modes and ensures that all 62 source objects can be reached,
all five UI channels exist, audio begins off, and interaction controls work.

## Not a clinical or research hardware bridge

Neuralink's public technology pages describe implant and decoding technology,
not authorization for this website to access an implant. Cortical Labs
publishes a CL SDK for simulated research, but its real neural recording and
electrical stimulation require authorized hardware, laboratory controls and
ethical safeguards. This interface deliberately has **no endpoint, code path
or hardware connector** for stimulation, closed-loop BCI, invasive interfaces,
sensor acquisition or other physical actuation.

Public references:

- https://docs.corticallabs.com/
- https://github.com/Cortical-Labs/cl-sdk
- https://neuralink.com/technology/
- https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API
- https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis

**Privacy:** No stored personal sensor data, permission request, paid key,
camera, microphone, tracking network call, or physical actuation.
