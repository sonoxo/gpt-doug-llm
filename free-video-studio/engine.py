from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DEFAULT_MLX_MODEL = "AbstractFramework/wan2.2-ti2v-5b-diffusers-8bit"


def _default_ffmpeg() -> str:
    configured = os.getenv("FFMPEG_BIN")
    if configured:
        return configured
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


@dataclass(frozen=True)
class StudioConfig:
    backend: str
    wan_repo: Path
    wan_model: Path
    mlx_model: str
    mlxgen_bin: str
    mmaudio_repo: Path
    python_bin: str
    ffmpeg_bin: str

    @classmethod
    def from_env(cls) -> "StudioConfig":
        requested = os.getenv("STUDIO_BACKEND", "auto").strip().lower()
        if requested == "auto":
            backend = "mlx" if sys.platform == "darwin" else "cuda"
        elif requested in {"mlx", "cuda"}:
            backend = requested
        else:
            raise ValueError("STUDIO_BACKEND must be auto, mlx, or cuda")
        return cls(
            backend=backend,
            wan_repo=Path(os.getenv("WAN_REPO", ROOT / "vendor" / "Wan2.2")).expanduser().resolve(),
            wan_model=Path(os.getenv("WAN_MODEL", ROOT / "models" / "Wan2.2-TI2V-5B")).expanduser().resolve(),
            mlx_model=os.getenv("STUDIO_MLX_MODEL", DEFAULT_MLX_MODEL),
            mlxgen_bin=os.getenv("MLXGEN_BIN", "mlxgen"),
            mmaudio_repo=Path(os.getenv("MMAUDIO_REPO", ROOT / "vendor" / "MMAudio")).expanduser().resolve(),
            python_bin=os.getenv("STUDIO_PYTHON", sys.executable),
            ffmpeg_bin=_default_ffmpeg(),
        )


def _run(cmd: list[str], cwd: Optional[Path] = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = proc.stdout or ""
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd[:5])}\n\n{output[-6000:]}")
    return output


def seconds_to_frames(seconds: int, fps: int = 24) -> int:
    raw = max(17, int(round(seconds * fps)))
    return ((raw - 1) // 4) * 4 + 1


def compose_prompt(
    scene: str,
    action: str,
    camera: str,
    lighting: str,
    style: str,
    continuity: str,
) -> str:
    parts: list[str] = []
    if scene.strip():
        parts.append(f"Scene and subject: {scene.strip()}")
    if action.strip():
        parts.append(f"Action and timing: {action.strip()}")
    if camera.strip():
        parts.append(f"Camera: {camera.strip()}")
    if lighting.strip():
        parts.append(f"Lighting: {lighting.strip()}")
    if style.strip():
        parts.append(f"Visual style: {style.strip()}")
    if continuity.strip():
        parts.append(f"Continuity lock: {continuity.strip()}")
    parts.append(
        "Photorealistic physical motion, coherent anatomy, stable identity, natural skin and material texture, "
        "consistent geometry, realistic depth of field, physically plausible light and shadows, cinematic temporal continuity."
    )
    return ". ".join(parts).strip() + "."


def parse_storyboard(text: str) -> list[str]:
    shots: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^(?:[-*]\s*)?(?:shot\s*\d+\s*[:|.)-]?|\d+\s*[:|.)-])\s*", "", line, flags=re.I)
        if line:
            shots.append(line)
    return shots


def check_environment() -> str:
    cfg = StudioConfig.from_env()
    if cfg.backend == "mlx":
        engine_ok = shutil.which(cfg.mlxgen_bin) is not None
        engine_name = "MLX-Gen (Apple Silicon)"
        model_line = f"Model: {cfg.mlx_model} (downloaded/cached by mlxgen)"
    else:
        engine_ok = (cfg.wan_repo / "generate.py").exists()
        engine_name = "Wan2.2 CUDA checkout"
        model_ok = cfg.wan_model.exists() and any(cfg.wan_model.iterdir()) if cfg.wan_model.exists() else False
        model_line = f"{'✅' if model_ok else '❌'} Wan2.2 TI2V-5B weights"

    ffmpeg_ok = Path(cfg.ffmpeg_bin).exists() or shutil.which(cfg.ffmpeg_bin) is not None
    lines = [f"FREE VIDEO STUDIO // backend={cfg.backend}"]
    lines.append(f"{'✅' if engine_ok else '❌'} {engine_name}")
    lines.append(model_line)
    lines.append(f"{'✅' if ffmpeg_ok else '❌'} FFmpeg")
    lines.append(f"{'✅' if (cfg.mmaudio_repo / 'demo.py').exists() else '➖'} MMAudio (optional; Linux-oriented)")
    lines.append("No paid API keys are used by this studio.")
    return "\n".join(lines)


def _validate_core(cfg: StudioConfig) -> None:
    missing: list[str] = []
    if cfg.backend == "mlx":
        if shutil.which(cfg.mlxgen_bin) is None:
            missing.append("MLX-Gen executable (mlxgen)")
    else:
        if not (cfg.wan_repo / "generate.py").exists():
            missing.append(f"Wan2.2 checkout: {cfg.wan_repo}")
        if not cfg.wan_model.exists():
            missing.append(f"Wan2.2 TI2V-5B weights: {cfg.wan_model}")
    if not (Path(cfg.ffmpeg_bin).exists() or shutil.which(cfg.ffmpeg_bin)):
        missing.append(f"FFmpeg executable: {cfg.ffmpeg_bin}")
    if missing:
        raise RuntimeError("Missing required free runtime components:\n- " + "\n- ".join(missing) + "\nRun: bash install_free.sh")


def _run_wan_cuda(
    cfg: StudioConfig,
    *,
    prompt: str,
    output_file: Path,
    size: str,
    seconds: int,
    seed: int,
    reference_image: Optional[Path],
) -> str:
    cmd = [
        cfg.python_bin,
        str(cfg.wan_repo / "generate.py"),
        "--task",
        "ti2v-5B",
        "--size",
        size,
        "--ckpt_dir",
        str(cfg.wan_model),
        "--offload_model",
        "True",
        "--convert_model_dtype",
        "--t5_cpu",
        "--frame_num",
        str(seconds_to_frames(seconds, 24)),
        "--base_seed",
        str(seed),
        "--save_file",
        str(output_file.resolve()),
        "--prompt",
        prompt,
    ]
    if reference_image:
        cmd.extend(["--image", str(reference_image.resolve())])
    return _run(cmd, cwd=cfg.wan_repo)


def _run_wan_mlx(
    cfg: StudioConfig,
    *,
    prompt: str,
    output_file: Path,
    size: str,
    seconds: int,
    seed: int,
    reference_image: Optional[Path],
) -> str:
    width, height = [int(x) for x in size.split("*")]
    fps = 20
    cmd = [
        cfg.mlxgen_bin,
        "generate",
        "--model",
        cfg.mlx_model,
        "--prompt",
        prompt,
        "--width",
        str(width),
        "--height",
        str(height),
        "--frames",
        str(seconds_to_frames(seconds, fps)),
        "--steps",
        os.getenv("STUDIO_MLX_STEPS", "25"),
        "--guidance",
        os.getenv("STUDIO_MLX_GUIDANCE", "5"),
        "--fps",
        str(fps),
        "--seed",
        str(seed),
        "--low-ram",
        "--metadata",
        "--output",
        str(output_file.resolve()),
    ]
    if reference_image:
        cmd.extend(["--image", str(reference_image.resolve())])
    return _run(cmd, cwd=ROOT)


def run_wan(
    cfg: StudioConfig,
    *,
    prompt: str,
    output_file: Path,
    size: str,
    seconds: int,
    seed: int,
    reference_image: Optional[Path] = None,
) -> str:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if cfg.backend == "mlx":
        return _run_wan_mlx(
            cfg,
            prompt=prompt,
            output_file=output_file,
            size=size,
            seconds=seconds,
            seed=seed,
            reference_image=reference_image,
        )
    return _run_wan_cuda(
        cfg,
        prompt=prompt,
        output_file=output_file,
        size=size,
        seconds=seconds,
        seed=seed,
        reference_image=reference_image,
    )


def extract_last_frame(cfg: StudioConfig, video: Path, image_out: Path) -> None:
    _run(
        [
            cfg.ffmpeg_bin,
            "-y",
            "-sseof",
            "-0.10",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(image_out),
        ]
    )


def make_browser_playable(cfg: StudioConfig, source: Path, output: Path) -> None:
    """Create an MP4 that Safari, Chrome, Firefox, and Gradio can play reliably."""
    if not source.exists() or source.stat().st_size == 0:
        raise RuntimeError(f"Video engine did not create a usable file: {source}")
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            cfg.ffmpeg_bin,
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(f"Browser-compatible export was not created: {output}")


def concat_videos(cfg: StudioConfig, videos: list[Path], output: Path) -> None:
    intermediate = output.with_name(f"{output.stem}.source.mp4")
    if len(videos) == 1:
        make_browser_playable(cfg, videos[0], output)
        return
    concat_file = output.with_suffix(".concat.txt")
    concat_file.write_text(
        "\n".join("file '" + str(v.resolve()).replace("'", "'\\''") + "'" for v in videos) + "\n",
        encoding="utf-8",
    )
    try:
        _run([cfg.ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(intermediate)])
    except RuntimeError:
        _run(
            [
                cfg.ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                str(intermediate),
            ]
        )
    make_browser_playable(cfg, intermediate, output)
    intermediate.unlink(missing_ok=True)


def add_mmaudio(cfg: StudioConfig, video: Path, prompt: str, duration: int, output: Path) -> str:
    demo = cfg.mmaudio_repo / "demo.py"
    if not demo.exists():
        raise RuntimeError("MMAudio is not installed. On Linux re-run: INSTALL_MMAUDIO=1 bash install_free.sh")
    mmaudio_output = cfg.mmaudio_repo / "output"
    mmaudio_output.mkdir(exist_ok=True)
    started = time.time()
    log = _run(
        [
            cfg.python_bin,
            str(demo),
            "--duration",
            str(duration),
            "--video",
            str(video.resolve()),
            "--prompt",
            prompt.strip() or "natural synchronized ambience matching the visible scene",
        ],
        cwd=cfg.mmaudio_repo,
    )
    candidates = sorted(mmaudio_output.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    generated = next((p for p in candidates if p.stat().st_mtime >= started - 2), None)
    if generated is None:
        raise RuntimeError("MMAudio completed but no new MP4 was found in its output directory.")
    shutil.copy2(generated, output)
    return log


def generate_project(
    mode: str,
    scene: str,
    action: str,
    storyboard: str,
    reference_image: Optional[str],
    camera: str,
    lighting: str,
    style: str,
    continuity: str,
    orientation: str,
    seconds_per_shot: int,
    seed: int,
    chain_shots: bool,
    add_audio: bool,
    audio_prompt: str,
) -> tuple[str, str]:
    cfg = StudioConfig.from_env()
    _validate_core(cfg)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    project_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    project = OUTPUTS / project_id
    project.mkdir(parents=True, exist_ok=False)

    size = "704*1280" if orientation.lower().startswith("portrait") else "1280*704"
    ref: Optional[Path] = Path(reference_image).resolve() if reference_image else None

    if mode == "Storyboard":
        shot_actions = parse_storyboard(storyboard)
        if not shot_actions:
            raise ValueError("Storyboard mode needs at least one non-empty shot line.")
    else:
        shot_actions = [action.strip() or scene.strip()]

    if mode == "Image → Video" and ref is None:
        raise ValueError("Image → Video mode requires a reference image.")

    logs: list[str] = [f"BACKEND: {cfg.backend}"]
    shot_files: list[Path] = []
    prompts: list[str] = []
    current_ref = ref if mode in {"Image → Video", "Storyboard"} else None

    effective_seed = int(seed) if int(seed) >= 0 else secrets.randbelow(2_147_483_647)

    for index, shot_action in enumerate(shot_actions, start=1):
        prompt = compose_prompt(scene, shot_action, camera, lighting, style, continuity)
        prompts.append(prompt)
        shot_file = project / f"shot-{index:02d}.mp4"
        logs.append(f"SHOT {index}/{len(shot_actions)}\n{prompt}\n")
        logs.append(
            run_wan(
                cfg,
                prompt=prompt,
                output_file=shot_file,
                size=size,
                seconds=int(seconds_per_shot),
                seed=effective_seed,
                reference_image=current_ref,
            )[-2500:]
        )
        shot_files.append(shot_file)

        if chain_shots and index < len(shot_actions):
            chained_frame = project / f"continuity-{index:02d}.jpg"
            extract_last_frame(cfg, shot_file, chained_frame)
            current_ref = chained_frame

    final = project / "final.mp4"
    concat_videos(cfg, shot_files, final)

    if add_audio:
        with_audio_source = project / "final-with-audio.source.mp4"
        with_audio = project / "final-with-audio.mp4"
        logs.append(
            add_mmaudio(
                cfg,
                final,
                audio_prompt,
                int(seconds_per_shot) * len(shot_actions),
                with_audio_source,
            )[-2500:]
        )
        make_browser_playable(cfg, with_audio_source, with_audio)
        with_audio_source.unlink(missing_ok=True)
        final = with_audio

    manifest = {
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "backend": cfg.backend,
        "engine": "Wan2.2-TI2V-5B",
        "model": cfg.mlx_model if cfg.backend == "mlx" else str(cfg.wan_model),
        "paid_api_keys": False,
        "size": size,
        "seconds_per_shot": int(seconds_per_shot),
        "seed": effective_seed,
        "chain_shots": bool(chain_shots),
        "audio_engine": "MMAudio" if add_audio else None,
        "prompts": prompts,
        "final": str(final),
    }
    (project / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logs.append(f"\n✅ Exported: {final}\n✅ Manifest: {project / 'manifest.json'}")
    return str(final), "\n".join(logs)
