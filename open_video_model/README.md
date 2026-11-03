# GPT-DOUG Motion-1 — Original Open-Source Trainable Video Model

**Status:** runnable research model; pretrained photorealistic weights **not** included.

Motion-1 is an original, MIT-licensed text-conditioned denoising diffusion probabilistic model (DDPM) that learns short RGB motion sequences. It is developed inside `sonoxo/gpt-doug-llm`, distinct from the repository's existing **Wan2.2** video studio. It does **not** copy Higgsfield's proprietary model or imply Higgsfield-level performance.

## Architecture

```text
Human text prompt
   │ stable Blake2b token IDs (no network tokenizer)
   ▼
Trainable text embeddings ──────┐
Diffusion timestep sinusoid ────┤ concatenated conditioning + FiLM
                                ▼
Noisy RGB clip [B, 3, 8, 32, 32]
   │ 3D input projection
   ├── ResidualMotionBlock (spatial kernel 1×3×3, temporal kernel 3×1×1)
   ├── ResidualMotionBlock
   ├── ResidualMotionBlock
   ▼
Predicted noise εθ(xₜ, t, text)
   │ DDPM loss: MSE(predicted noise, actual noise)
   ▼
Trained state_dict checkpoint (.pt)
   │ DDPM reverse sampler (trained weights required)
   ▼
Real local frames → GIF (Pillow) or MP4 (FFmpeg)
```

Default: 8 RGB frames at 32×32, 48 diffusion steps, 24 hidden channels. Configurable 4–16 frames, 16–64 pixels, 4–128 diffusion steps. It is deliberately small and learnable on an Apple Silicon Mac. **A short demonstration training run will not produce cinematic video.** Meaningful results require additional authorized training clips, long training, validation and larger models.

## Free Mac setup

Use **Python 3.11 or 3.12** (not your earlier Python 3.15 dependency environment), Apple Silicon PyTorch with MPS where available. No account, paid API or credit card.

```bash
brew install python@3.12
git clone https://github.com/sonoxo/gpt-doug-llm.git
cd gpt-doug-llm
bash open_video_model/setup_mac.sh
```

If you already cloned the repo: `cd` into it and run `git pull --ff-only` rather than cloning again. The setup creates its own `open_video_model/.venv`, so it doesn't modify system Python.

Train the model from scratch using an original synthetic moving-circle/square curriculum:

```bash
open_video_model/.venv/bin/python -m open_video_model train --steps 500
```

After training, open the local browser studio:

```bash
open_video_model/.venv/bin/python -m open_video_model studio
```

Local URL: **http://127.0.0.1:8792/**. Hit **Generate from trained weights**. Outputs are stored under `~/.local/share/gpt-doug/motion-1/renders/`. The public XUNIA exhibit, `https://xunia.org/motion-1/`, **does not perform GPU inference on GitHub Pages**. Its render buttons become operational only through the local studio.

Generate directly from Terminal:

```bash
open_video_model/.venv/bin/python -m open_video_model generate \
  --prompt "red circle moving right" --out "$HOME/Movies/gpt-doug-motion.gif"

open_video_model/.venv/bin/python -m open_video_model doctor
```

If you have FFmpeg (`brew install ffmpeg`), change the output suffix to `.mp4` for local H.264 generation. GIF needs no FFmpeg.

### Preview without training

```bash
open_video_model/.venv/bin/python -m open_video_model preview \
  --prompt "blue square moving left" --out "$HOME/Movies/motion-demo.gif"
```

This is an **explicitly labeled procedural preview**, not inference from the trained neural network. The generated JSON receipt records `preview_not_ml=true`. The `generate` command refuses to run without a real trained checkpoint.

## Train on your own authorized clips

Organize frames you are legally permitted to process:

```text
my_clips/
  shot001/
    caption.txt                 # "a small boat moves from left to right"
    frames/
      0001.png
      0002.png
      0003.png
      0004.png
      ... (at least 8)
  shot002/
    caption.txt
    frames/
      0001.jpg
      ...
```

Then:

```bash
open_video_model/.venv/bin/python -m open_video_model train \
  --data-dir "$HOME/my_clips" --steps 1500 --batch 2 \
  --checkpoint "$HOME/Movies/my-trained-motion1.pt"
open_video_model/.venv/bin/python -m open_video_model generate \
  --checkpoint "$HOME/Movies/my-trained-motion1.pt" \
  --prompt "a small boat moves from left to right" \
  --out "$HOME/Movies/boat-motion.gif"
```

Use a reasonable image count and sufficient training. Low-resolution toy modeling is not expected to generalize to an arbitrary English prompt without broad, representative data.

## Model card

| Property | Fact |
|---|---|
| Name | GPT-DOUG Motion-1 |
| Owner | Sonoxo / GPT-DOUG |
| Version | 0.1.0 |
| Source license | MIT, same as parent repository |
| Model architecture | Text-conditioned spatiotemporal 3D convolutional DDPM |
| Training objective | Noise-prediction MSE |
| Trainable checkpoints bundled | No; user creates local weights |
| Default device | Apple Silicon MPS, else CUDA, else CPU |
| External inference | None |
| Required libraries | PyTorch and Pillow (both free); optional FFmpeg |
| Supported data | Original generated shapes or user-approved local frame clips |
| Known limits | Low resolution, short duration, untrained without user checkpoint, no voice/audio, no identity consistency guarantees |
| Responsible use | Obtain rights for training footage; do not represent synthetic media as evidence |
| Model comparison | Does not imitate or reproduce proprietary Higgsfield architecture/weights |

The text encoder uses **stable hashed word IDs**, not a pretrained language encoder. It learns only words encountered during training. The motion model is small enough to study and modify, rather than presenting a trivial third-party wrapper as an original foundation model.

Safe checkpoint loading uses `torch.load(..., weights_only=True)`; the server binds to loopback and has no permissive CORS. Training and inference use no network requests. All generated files and weights stay local unless you explicitly share them.

## Validation

```bash
open_video_model/.venv/bin/python -m unittest discover -s tests -p test_gpt_doug_motion_one.py -v
open_video_model/.venv/bin/python -m unittest discover -s tests -p test_gpt_doug_motion_server.py -v
```

The original source and complete audit trail are in `open_video_model/`. For production-quality video, use the separate existing `free-video-studio/` Wan2.2 backend and review its upstream weights license and memory requirements.
