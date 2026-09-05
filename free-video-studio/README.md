# gpt-doug-llm-max-AsTra

A **zero-paid-inference-API** cinematic AI-video studio. It reproduces the practical creation loop demonstrated in modern Seedance 2.5 tutorials—prompt direction, image/reference starts, storyboarded shots, camera/lighting control, continuity chaining, synchronized sound, refinement, and export—using local/free components instead of a Seedance subscription.

## Backends: automatic and free

| Machine | Backend | Video model |
|---|---|---|
| Apple Silicon macOS | **MLX-Gen** | Wan2.2 TI2V-5B 8-bit package |
| Linux + NVIDIA CUDA | **Official Wan2.2** | Wan2.2 TI2V-5B |

`STUDIO_BACKEND=auto` is the default. The app selects MLX on macOS and CUDA elsewhere.

- **Wan2.2 TI2V-5B** — text-to-video + image-to-video.
- **MLX-Gen** — Apple-Silicon-native local Wan runtime.
- **FFmpeg / imageio-ffmpeg** — frame extraction, connected-shot chaining, and final assembly.
- **MMAudio** *(optional, Linux-oriented)* — synchronized video-to-audio generation.
- **Gradio** — local browser UI.

No paid API keys are wired into this module.

## What it can do

| Seedance-style workflow | Free implementation |
|---|---|
| Text → video | Wan2.2 TI2V-5B |
| Image → video | Wan2.2 TI2V-5B with reference frame |
| Shot-by-shot prompting | Storyboard mode, one shot per line |
| Camera / lighting / look control | Structured director fields compiled into every prompt |
| Visual continuity | Shared identity/wardrobe/location lock + previous-shot final-frame chaining |
| Synchronized ambience / Foley | Optional MMAudio pass on supported Linux setup |
| Connected sequence export | FFmpeg concat + per-project manifest |
| Reproducibility | Explicit seed + saved prompt manifest |

## Install

```bash
cd free-video-studio
bash install_free.sh
bash run.sh
```

Open `http://127.0.0.1:7860`.

The installer downloads the free local model required for your platform. On Apple Silicon it installs MLX-Gen and downloads `AbstractFramework/wan2.2-ti2v-5b-diffusers-8bit`. On CUDA Linux it installs the official Wan2.2 implementation and `Wan-AI/Wan2.2-TI2V-5B`.

### Linux: add synchronized audio

```bash
INSTALL_MMAUDIO=1 bash install_free.sh
bash run.sh
```

MMAudio downloads its pretrained weights on first audio generation.

## Best workflow for ultra-realistic output

1. Start with a strong reference image when identity matters.
2. Write one objective per shot rather than an entire film in one generation.
3. Describe physical action, camera motion, lens behavior, motivated lighting, and material/skin texture.
4. Put immutable face/wardrobe/location details in **Continuity lock**.
5. In Storyboard mode, keep **Chain shots** enabled. The studio extracts the prior shot's last frame and sends it into the next image-to-video generation.
6. Generate the visuals first and add sound as a final pass.
7. Re-run weak shots while keeping the seed and continuity lock stable instead of changing every variable.

## Compute reality

This matches the **workflow and tool behavior**, not ByteDance's proprietary Seedance weights, so identical output cannot be guaranteed.

The code and model-access path are free, but diffusion still consumes your hardware. Official Wan2.2 documents its CUDA TI2V-5B route around a 24 GB VRAM GPU. On Apple Silicon, MLX-Gen provides a native Wan2.2 TI2V-5B path; its published 8-bit package is about 16.9 GiB on disk, and current MLX-Gen documentation notes that this q8 package primarily reduces storage/download size rather than runtime memory. Higher unified memory is therefore strongly preferred for full-resolution renders.

## Environment variables

| Variable | Default |
|---|---|
| `STUDIO_BACKEND` | `auto` (`mlx` on macOS, `cuda` otherwise) |
| `STUDIO_MLX_MODEL` | `AbstractFramework/wan2.2-ti2v-5b-diffusers-8bit` |
| `STUDIO_MLX_STEPS` | `25` |
| `STUDIO_MLX_GUIDANCE` | `5` |
| `WAN_REPO` | `./vendor/Wan2.2` |
| `WAN_MODEL` | `./models/Wan2.2-TI2V-5B` |
| `MMAUDIO_REPO` | `./vendor/MMAudio` |
| `STUDIO_PYTHON` | current Python |
| `FFMPEG_BIN` | system FFmpeg or bundled imageio-ffmpeg binary |
| `STUDIO_HOST` | `127.0.0.1` |
| `STUDIO_PORT` | `7860` |

## Output

Every run creates `outputs/<project-id>/` with generated shots, continuity frames, `final.mp4`, and `manifest.json`. The manifest records the backend, model, prompts, seed, dimensions, and audio state.

The final file is always normalized to browser-safe H.264 video, AAC audio,
`yuv420p`, and MP4 fast-start metadata. This prevents a successful model render
from appearing as a blank or unplayable result in Gradio, Safari, or Chrome.

## Other free/open model options

“Unlimited” here means local generation with no per-render API bill; generation
is still limited by the machine's RAM/VRAM, storage, and run time.

| Need | Free/open option | Practical note |
|---|---|---|
| Default text/image → video | **Wan2.2 TI2V-5B** | Already integrated; best fit for a 24 GB NVIDIA GPU or a high-memory Apple Silicon Mac through MLX-Gen. |
| Faster/lower-VRAM video experiments | **LTX-Video** | Good next backend for speed-focused local workflows; requires a separate adapter. |
| Alternative video backend | **CogVideoX** | Diffusers-supported family with text/image-to-video variants; requires a separate adapter. |
| Larger cinematic video experiments | **HunyuanVideo** | Open local stack, but materially heavier than the default 5B route. |
| Prompt writing / shot planning | **Qwen3 via Ollama** | Local LLM; use smaller parameter sizes when memory is tight. |
| Coding and pipeline repair | **Qwen3-Coder via Ollama** | Local coding model; choose the quantization that fits the machine. |
| Lightweight general assistant | **Gemma 3 via Ollama** | Useful local prompt/refinement option with smaller variants. |

The video studio does not silently route footage or prompts to a hosted service.
Additional backends should be exposed only after their command line and output
contract are implemented and tested; UI-only model labels are not real engines.

## Licensing note

The studio introduces no paid-service dependency. Wan2.2's upstream repository is Apache-2.0. MLX-Gen is MIT. MMAudio code is MIT; its upstream documentation separately cautions that pretrained-model/data licensing should be reviewed for the intended commercial use. Model weights remain subject to their upstream model-card/license terms.
