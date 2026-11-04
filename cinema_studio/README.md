# GPT-DOUG CINEMA OS · End-to-end free local video studio

A **working production loop**, not a design mockup: prompt and/or upload image → validate → queue a job → render a real MP4 → preview in Chrome → download video and a SHA-256 manifest → reopen from the local gallery. Runs from Python 3 standard library, with free FFmpeg for MP4 output. No paid APIs, tokens, credit cards or subscriptions.

## One command on Mac

From any Terminal folder:

```bash
curl -fsSLo "$HOME/Downloads/gpt-doug-cinema-start.sh" https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/cinema_studio/bootstrap_mac.sh && bash "$HOME/Downloads/gpt-doug-cinema-start.sh"
```

The bootstrap reuses a valid `~/GPT-DOUG-Motion1` checkout if possible, otherwise uses a clean `~/GPT-DOUG-Cinema` sparse clone. It does **not** overwrite your existing non-Git `~/gpt-doug-llm` folder, delete files or download AI weights. It may install free FFmpeg with Homebrew if missing. Launch URL: **http://127.0.0.1:8793/**. Keep Terminal open. Your older Motion-1 toy model remains at port 8792; it is not required for Cinema OS.

### Three genuine rendering engines

| Mode | What it does today | Dependencies | Claims |
|---|---|---|---|
| **Motion Lab** | Renders original kinetic graphic sequences from a palette, camera control and shot list; real MP4 | FFmpeg | Procedural video, **not neural text-to-video** |
| **Image → Video** | User-supplied JPEG/PNG → moving, animated pan/zoom MP4; up to 4 shots | FFmpeg | Camera animation, **not neural I2V** |
| **Wan2.2 AI** | Original prompt → local neural text-to-video MP4, optional first-frame image | Installed open-source [MLX-Gen](https://github.com/lpalbou/mlx-gen) + [Wan2.2 TI2V-5B q8 model](https://huggingface.co/AbstractFramework/wan2.2-ti2v-5b-diffusers-8bit) | **Real pretrained AI**, only on suitable Apple Silicon hardware |

Do not confuse this with `open_video_model/`, the 347k-parameter low-resolution Motion-1 research DDPM. Cinema OS's optional Wan path calls a separate **pretrained five-billion-parameter** model; neither is proprietary Higgsfield AI. Free code does not imply low memory, fast rendering or identical Higgsfield output.

### Optional AI setup (large download, explicit opt-in)

```bash
cd "$HOME/GPT-DOUG-Motion1"  # or your GPT-DOUG-Cinema checkout
bash cinema_studio/install_ai_mac.sh
```

The script checks Apple Silicon, at least 30 GiB available disk, and **48 GiB unified memory for the recommended attempt** before installing the free MLX-Gen runtime and roughly 17 GiB of Wan weights. Upstream reports higher peak memory for native-resolution generation: q8 primarily reduces *download/storage*, not runtime memory. Low-resolution/low-RAM mode may still fail. On 8/16 GB Macs, use Motion Lab and Image → Video; don't automatically download massive AI weights. To explicitly attempt below 48 GiB, `CINEMA_ALLOW_LOW_MEMORY=1 bash cinema_studio/install_ai_mac.sh` (at your own risk). No paid API fallback.

### Interface features

- Project prompt, presets, camera motion and palette control.
- Storyboard: 1–4 shots, independent local renders, concatenated to one MP4.
- Image upload with 8 MB cap and PNG/JPEG signature check; image files stay in your local project directory.
- 320×192 drafts / 640×352 standard output, 8–24 fps, 2–8 seconds/shot.
- Optional minimal original synthesized ambient tone (not AI music).
- Serial queued rendering with per-job stage updates; failed jobs preserve error evidence rather than producing misleading fake outputs.
- Local gallery persisted in JSON, playable video and JSON manifest with SHA-256 output checksum.
- Loopback-only HTTP, same-origin POST protection, bounded jobs/payloads, no arbitrary file access.

Data is stored in `~/.local/share/gpt-doug/cinema-studio/<project-id>/`. The app never publishes or uploads your reference images. Model download (if explicitly requested) uses Hugging Face public model hosting, which still requires Internet for the initial download. Review upstream model license for your use.

### Validate

```bash
python3 -m unittest discover -s cinema_studio/tests -v
node --check cinema_studio/web/app.js
```

Unit and HTTP tests exercise the real FFmpeg pipeline, an uploaded image, two-shot assembly, optional ambient sound, invalid requests, local-only access, gallery persistence and MP4/manifest export. CI installs only free FFmpeg. A live pretrained Wan generation is **not tested** in GitHub Actions, because the full model download and Apple GPU memory are unavailable there.

### Other platforms

The FFmpeg editor runs on Linux too, using `python3 -m cinema_studio.server` and a system `ffmpeg`. The optional `install_ai_mac.sh` and MLX Wan backend are Apple Silicon-only. NVIDIA/CUDA video generation remains in the existing `free-video-studio/` stack.
