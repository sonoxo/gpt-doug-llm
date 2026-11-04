"""GPT-DOUG Cinema Studio — free offline MP4 renderer and optional pretrained Wan adapter.

FFmpeg modes produce real original camera/motion videos but are NOT AI generation.
Wan mode executes a separately installed, licensed open-weight MLX-Gen model.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
from time import monotonic
from typing import Callable

MODEL = "AbstractFramework/wan2.2-ti2v-5b-diffusers-8bit"
MODEL_CACHE = "models--AbstractFramework--wan2.2-ti2v-5b-diffusers-8bit"
MAX_UPLOAD = 8 * 1024 * 1024
MAX_SHOTS = 4
MAX_PROMPT = 600
RESOLUTIONS = {"draft": (320, 192), "standard": (640, 352)}
PROJECT_ROOT = Path(os.environ.get("GPT_DOUG_CINEMA_HOME", str(Path.home() / ".local/share/gpt-doug/cinema-studio"))).expanduser()


class StudioError(ValueError):
    pass


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def mlxgen_path() -> str | None:
    return (shutil.which("mlxgen") or
            str(Path(__file__).parent / ".venv/bin/mlxgen") if
            (shutil.which("mlxgen") or (Path(__file__).parent / ".venv/bin/mlxgen").is_file())
            else None)


def model_cached() -> bool:
    home = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface"))).expanduser()
    root = home / "hub" / MODEL_CACHE / "snapshots"
    if not root.is_dir():
        return False
    return any((item / "model_index.json").exists() and (item / "transformer").is_dir()
               for item in root.iterdir() if item.is_dir())


def status() -> dict:
    return {
        "ffmpeg": bool(ffmpeg_path()),
        "mlxgen": bool(mlxgen_path()),
        "wan_model_cached": model_cached(),
        "ai_ready": bool(mlxgen_path()) and model_cached() and platform.system() == "Darwin"
        and platform.machine() == "arm64",
        "platform": platform.system(),
        "architecture": platform.machine(),
        "modes": ["motion", "image", "wan"],
        "no_paid_api": True,
        "wan_download_gib": "~17 (plus installation and cache overhead)",
        "model": MODEL,
    }


def normalize_request(value: dict) -> dict:
    if not isinstance(value, dict):
        raise StudioError("Request must be a JSON object")
    mode = value.get("mode", "motion")
    if mode not in ("motion", "image", "wan"):
        raise StudioError("Mode must be motion, image or wan")
    prompt = value.get("prompt", "")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= MAX_PROMPT:
        raise StudioError("Prompt must contain 1–600 characters")
    if any(c in prompt for c in ("\x00", "\r")):
        raise StudioError("Prompt contains unsupported characters")
    storyboard = value.get("storyboard", "")
    if not isinstance(storyboard, str) or len(storyboard) > 2000:
        raise StudioError("Storyboard is too long")
    shots = [line.strip() for line in storyboard.splitlines() if line.strip()]
    if not shots:
        shots = [prompt.strip()]
    if len(shots) > MAX_SHOTS or any(len(shot) > MAX_PROMPT for shot in shots):
        raise StudioError("Storyboard supports up to 4 shots of 600 characters each")
    if mode == "wan" and len(shots) > 1:
        raise StudioError("Wan mode currently generates one shot at a time; queue separately for longer films")
    preset = value.get("quality", "draft")
    if preset not in RESOLUTIONS:
        raise StudioError("Choose draft or standard quality")
    seconds = value.get("seconds", 3)
    fps = value.get("fps", 16)
    seed = value.get("seed", 42)
    if type(seconds) is not int or not 2 <= seconds <= 8:
        raise StudioError("Each shot must be 2–8 seconds")
    if type(fps) is not int or not 8 <= fps <= 24:
        raise StudioError("FPS must be 8–24")
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise StudioError("Seed must be 0–2147483647")
    direction = value.get("camera", "dolly")
    if direction not in ("dolly", "pan-left", "pan-right", "static"):
        raise StudioError("Unknown camera direction")
    palette = value.get("palette", "aqua")
    if palette not in ("aqua", "violet", "amber", "scarlet"):
        raise StudioError("Unknown palette")
    image = value.get("image")
    if image is not None:
        if not isinstance(image, str) or len(image) > MAX_UPLOAD * 2:
            raise StudioError("Reference image exceeds 8 MB")
        if not re.fullmatch(r"data:image/(png|jpeg);base64,[a-zA-Z0-9+/=]+", image):
            raise StudioError("Reference image must be a PNG or JPEG data URL")
        _, body = image.split(",", 1)
        try:
            decoded = base64.b64decode(body, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise StudioError("Invalid image encoding") from exc
        if not 16 <= len(decoded) <= MAX_UPLOAD:
            raise StudioError("Reference image must be 16 bytes to 8 MB")
        png = decoded.startswith(b"\x89PNG\r\n\x1a\n")
        jpeg = decoded.startswith(b"\xff\xd8\xff")
        if not (png or jpeg):
            raise StudioError("Image content is not PNG or JPEG")
        image = decoded
    if mode == "image" and image is None:
        raise StudioError("Image animation requires an uploaded PNG/JPEG")
    if mode == "wan" and not status()["ai_ready"]:
        raise StudioError("Free Wan AI is not installed or its model isn't cached. Use Motion/Image now, or install the optional model on a high-memory Apple Silicon Mac")
    return {"mode": mode, "prompt": prompt.strip(), "shots": shots, "quality": preset,
            "seconds": seconds, "fps": fps, "seed": seed, "camera": direction,
            "palette": palette, "image": image, "sound": value.get("sound") is True}


def _run(command: list[str], limit: int = 150, callback: Callable[[str], None] | None = None) -> None:
    if callback:
        callback("Rendering video locally")
    try:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.DEVNULL, timeout=limit, check=False)
    except subprocess.TimeoutExpired as exc:
        raise StudioError("Local render timed out. Reduce frames or resolution") from exc
    if proc.returncode:
        message = proc.stderr.decode("utf-8", "replace")[-1800:]
        # Do not leak large raw logs or paths into the public UI.
        raise StudioError("Render process failed (exit " + str(proc.returncode) + "): " + message)


def _motion(ffmpeg: str, output: Path, request: dict, index: int) -> None:
    w, h = RESOLUTIONS[request["quality"]]
    duration, fps = request["seconds"], request["fps"]
    bg, accent = {
        "aqua": ("0x061827", "0x46f8d5"),
        "violet": ("0x140e2b", "0xbc8bff"),
        "amber": ("0x251608", "0xffbb66"),
        "scarlet": ("0x240c16", "0xff668a"),
    }[request["palette"]]
    r, g, b = {"aqua": (70, 248, 213), "violet": (189, 145, 255),
               "amber": (255, 188, 92), "scarlet": (255, 92, 135)}[request["palette"]]
    phase = 1 + (index % 3) * .3
    if request["camera"] == "static":
        xx, yy = "(W-w)/2", "(H-h)/2"
    elif request["camera"] == "pan-left":
        xx, yy = "(W-w)*(.85-t/" + str(duration) + "*.7)", "(H-h)/2"
    elif request["camera"] == "pan-right":
        xx, yy = "(W-w)*(.15+t/" + str(duration) + "*.7)", "(H-h)/2"
    else:
        xx, yy = "(W-w)/2+(W-w)*.35*sin(t*" + str(phase) + ")", "(H-h)/2+(H-h)*.27*cos(t*1.4)"
    orb = min(w, h) // 3
    # A real FFmpeg-generated kinetic film. Not a text-to-video neural model.
    filt = (f"[0:v]drawgrid=w=32:h=32:t=1:c=0x427689@0.19[base];"
            f"[1:v]format=rgba,geq=r='{r}':g='{g}':b='{b}':"
            f"a='if(lte((X-W/2)^2+(Y-H/2)^2,(W*.42)^2),225,0)'[orb];"
            f"[base][orb]overlay=x='{xx}':y='{yy}':shortest=1:eval=frame,format=yuv420p[v]")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
           "-f", "lavfi", "-i", f"color=c={bg}:s={w}x{h}:r={fps}:d={duration}",
           "-f", "lavfi", "-i", f"color=c={accent}:s={orb}x{orb}:r={fps}:d={duration}",
           "-filter_complex", filt, "-map", "[v]", "-t", str(duration),
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "21", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(output)]
    _run(cmd, limit=120)


def _image(ffmpeg: str, source: Path, output: Path, request: dict, index: int) -> None:
    w, h = RESOLUTIONS[request["quality"]]
    fps, seconds = request["fps"], request["seconds"]
    camera = request["camera"]
    if camera == "pan-left":
        xx, zoom = "(iw-iw/zoom)*(1-on/" + str(fps*seconds) + ")", "1.18"
    elif camera == "pan-right":
        xx, zoom = "(iw-iw/zoom)*on/" + str(fps*seconds), "1.18"
    elif camera == "static":
        xx, zoom = "(iw-iw/zoom)/2", "1.0"
    else:
        xx, zoom = "(iw-iw/zoom)/2", "min(zoom+0.0015,1.22)"
    vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
          f"crop={w*2}:{h*2},zoompan=z='{zoom}':x='{xx}':"
          f"y='(ih-ih/zoom)/2':d=1:s={w}x{h}:fps={fps},format=yuv420p")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-loop", "1",
           "-framerate", str(fps), "-i", str(source), "-vf", vf,
           "-frames:v", str(fps*seconds), "-t", str(seconds),
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(output)]
    _run(cmd, limit=120)


def _wan(output: Path, request: dict, source: Path | None) -> None:
    binary = mlxgen_path()
    if not binary or not model_cached():
        raise StudioError("Wan model files are missing. Install the free weights explicitly first")
    w, h = RESOLUTIONS[request["quality"]]
    frames = ((request["seconds"] * request["fps"] - 1) // 4) * 4 + 1
    frames = max(17, min(frames, 121))
    cmd = [binary, "generate", "--model", MODEL, "--prompt", request["prompt"],
           "--width", str(w), "--height", str(h), "--frames", str(frames),
           "--steps", "20", "--guidance", "5", "--fps", str(request["fps"]),
           "--seed", str(request["seed"]), "--low-ram", "--output", str(output)]
    if source is not None:
        cmd += ["--image", str(source)]
    _run(cmd, limit=3600)


def _assemble(ffmpeg: str, files: list[Path], output: Path) -> None:
    if len(files) == 1:
        shutil.copyfile(files[0], output)
        return
    listing = output.parent / "concat.txt"
    listing.write_text("".join("file '" + f.name + "'\n" for f in files), encoding="utf-8")
    _run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
          "-f", "concat", "-safe", "0", "-i", str(listing),
          "-c", "copy", "-movflags", "+faststart", str(output)], limit=90)
    listing.unlink(missing_ok=True)


def render(project: Path, request: dict, callback: Callable[[str], None] | None = None) -> dict:
    project.mkdir(parents=True, exist_ok=True)
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise StudioError("Free FFmpeg is required. On Mac run: brew install ffmpeg")
    source = None
    if request["image"] is not None:
        kind = ".png" if request["image"].startswith(b"\x89PNG") else ".jpg"
        source = project / ("reference" + kind)
        source.write_bytes(request["image"])
    shots = []
    start = monotonic()
    for idx, prompt in enumerate(request["shots"]):
        if callback:
            callback("Shot " + str(idx + 1) + " of " + str(len(request["shots"])))
        out = project / f"shot-{idx+1:02}.mp4"
        shot_request = {**request, "prompt": prompt}
        if request["mode"] == "motion":
            _motion(ffmpeg, out, shot_request, idx)
        elif request["mode"] == "image":
            _image(ffmpeg, source, out, shot_request, idx)
        else:
            _wan(out, shot_request, source)
        if not out.is_file() or out.stat().st_size < 1000:
            raise StudioError("Render engine produced no usable MP4")
        shots.append(out)
    if callback:
        callback("Assembling and exporting MP4")
    final = project / "final.mp4"
    _assemble(ffmpeg, shots, final)
    if request["sound"]:
        length = len(shots)*request["seconds"]
        with_sound = project / "final-sound.mp4"
        _run([ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y","-i",str(final),
              "-f","lavfi","-i",f"sine=frequency=110:sample_rate=44100:duration={length}",
              "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","96k",
              "-af","volume=0.055","-shortest","-movflags","+faststart",str(with_sound)],limit=60)
        with_sound.replace(final)
    manifest = {
        "schema": "gpt-doug.cinema-studio.v1", "mode": request["mode"],
        "model": MODEL if request["mode"] == "wan" else "FFmpeg kinetic compositor (not a generative AI model)",
        "prompt": request["prompt"], "shots": request["shots"],
        "quality": request["quality"], "camera": request["camera"],
        "palette": request["palette"], "seed": request["seed"],
        "fps": request["fps"], "seconds_per_shot": request["seconds"],
        "video": "final.mp4", "audio": "original minimal synth tone" if request["sound"] else "none",
        "elapsed_seconds": round(monotonic()-start,2),
        "video_sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
        "cost": "No paid inference API", "model_weights_bundled": False,
    }
    (project / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    return manifest
