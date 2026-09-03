# FREE VIDEO STUDIO

A **zero-paid-inference-API** workflow for cinematic AI video generation. It reproduces the practical creation loop demonstrated in modern Seedance tutorials—prompt direction, image/reference starts, storyboarded shots, camera/lighting control, continuity chaining, synchronized sound, refinement, and export—using open/free local components instead of a Seedance subscription.

## Stack

- **Wan2.2 TI2V-5B** — text-to-video + image-to-video at 720p/24 FPS.
- **FFmpeg** — frame extraction, connected-shot chaining, and final assembly.
- **MMAudio** *(optional)* — synchronized video-to-audio generation.
- **Gradio** — local browser UI.

No paid API keys are wired into this module.

## What it can do

| Seedance-style workflow | Free implementation |
|---|---|
| Text → video | Wan2.2 TI2V-5B |
| Image → video | Wan2.2 TI2V-5B with reference frame |
| Shot-by-shot prompting | Storyboard mode, one shot per line |
| Camera / lighting / look control | Structured director fields compiled into each shot prompt |
| Visual continuity | Shared continuity lock + optional previous-shot final-frame chaining |
| Synchronized ambience / Foley | Optional MMAudio pass |
| Connected sequence export | FFmpeg concat + per-project manifest |
| Reproducibility | Explicit seed + saved prompt manifest |

## Reality check

This matches the **workflow and tool behavior**, not ByteDance's proprietary Seedance model weights. There is no honest way to promise identical Seedance 2.5 output from a different open model.

The software path is free, but video diffusion is compute-heavy. The official Wan2.2 TI2V-5B single-GPU path is designed around an NVIDIA/CUDA GPU with about **24 GB VRAM**. A Mac can host/view the UI, but the default Wan backend is not an Apple-Silicon-native inference path.

## Install

Prerequisites: Linux, Python 3, Git, FFmpeg, and a compatible NVIDIA GPU/CUDA stack.

```bash
cd free-video-studio
bash install_free.sh
bash run.sh
```

Open `http://127.0.0.1:7860`.

### Add free synchronized audio

```bash
INSTALL_MMAUDIO=1 bash install_free.sh
bash run.sh
```

MMAudio downloads its pretrained weights on first audio generation.

## Best workflow for realism

1. Start with a strong reference image when identity matters.
2. Write one objective per shot instead of asking for an entire film in one prompt.
3. Describe physical action, camera motion, lens behavior, motivated lighting, and material/skin texture.
4. Put immutable identity/clothing/environment details in **Continuity lock**.
5. In Storyboard mode, keep **Chain shots** enabled so the next shot can start from the previous shot's final frame.
6. Generate video first; add audio as a separate final pass.
7. Re-run weak shots instead of changing every variable at once; keep the seed and continuity text stable.

## Environment variables

| Variable | Default |
|---|---|
| `WAN_REPO` | `./vendor/Wan2.2` |
| `WAN_MODEL` | `./models/Wan2.2-TI2V-5B` |
| `MMAUDIO_REPO` | `./vendor/MMAudio` |
| `STUDIO_PYTHON` | current Python |
| `FFMPEG_BIN` | `ffmpeg` |
| `STUDIO_HOST` | `127.0.0.1` |
| `STUDIO_PORT` | `7860` |

## Output

Every run creates `outputs/<project-id>/` with generated shots, continuity frames, `final.mp4`, and `manifest.json`. The manifest records prompts, seed, dimensions, engine, and whether audio was used.

## Licensing note

The studio code itself introduces no paid service dependency. Wan2.2's upstream repository is Apache-2.0. MMAudio's code is MIT; its upstream documentation separately cautions that pretrained-model/data licensing should be reviewed for your intended commercial use. Always keep upstream license files and follow the model card terms for the weights you download.
