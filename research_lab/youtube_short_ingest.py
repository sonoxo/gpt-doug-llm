"""Bounded public YouTube Shorts evidence retrieval; never executes clip contents.

Uses free optional yt-dlp for metadata and captions; oEmbed is metadata-only
fallback. A single explicitly supplied YouTube video URL is accepted. Output
needs independent inspection before any video-derived implementation is merged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VIDEO_ID = "eNIFAcuEFVU"
DEFAULT_VIDEO = f"https://www.youtube.com/shorts/{VIDEO_ID}"
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
MAX_JSON = 128 * 1024
MAX_CAPTION = 256 * 1024
MAX_TRANSCRIPT_CHARS = 24000
MAX_DESCRIPTION_CHARS = 5000
MAX_VIDEO_BYTES = 30 * 1024 * 1024
MAX_VIDEO_SECONDS = 180
VALID_YOUTUBE_HOSTS = frozenset(("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"))


def parse_video_id(url: str) -> str:
    if not isinstance(url, str) or len(url) > 300:
        raise ValueError("expected short public YouTube URL")
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.username is not None
            or parsed.password is not None or parsed.port is not None
            or parsed.hostname not in VALID_YOUTUBE_HOSTS):
        raise ValueError("only HTTPS youtube.com / youtu.be URLs are allowed")
    path = parsed.path
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        video = path.lstrip("/")
    elif path.startswith("/shorts/"):
        video = path[len("/shorts/"):]
    elif path == "/watch":
        ids = urllib.parse.parse_qs(parsed.query).get("v", [])
        video = ids[0] if len(ids) == 1 else ""
    elif path.startswith("/embed/"):
        video = path[len("/embed/"):]
    else:
        raise ValueError("must provide Shorts, watch, embed or youtu.be URL")
    if not ID_PATTERN.fullmatch(video):
        raise ValueError("invalid YouTube video ID")
    return video


def allowed_resource_url(url: str, *, oembed: bool = False) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        hostname = parsed.hostname or ""
        if parsed.scheme != "https" or parsed.port is not None or parsed.username:
            return False
        if oembed:
            return hostname in ("www.youtube.com", "youtube.com")
        return hostname in ("www.youtube.com", "youtube.com", "i.ytimg.com") or hostname == "googlevideo.com" or hostname.endswith(".googlevideo.com")
    except (ValueError, TypeError):
        return False


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if not allowed_resource_url(newurl):
            raise ValueError("redirect outside public YouTube media hosts")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def read_public(url: str, *, limit: int = MAX_CAPTION, oembed: bool = False) -> bytes:
    if not allowed_resource_url(url, oembed=oembed):
        raise ValueError("unsupported public evidence host")
    opener = urllib.request.build_opener(RestrictedRedirect())
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; GPT-Doug-evidence-ingest/1.0)",
                                               "Accept": "application/json, text/vtt, text/plain, image/jpeg;q=0.8, */*;q=0.5"})
    with opener.open(req, timeout=12) as res:
        data = res.read(limit + 1)
    if len(data) > limit:
        raise ValueError("download exceeds evidence size limit")
    return data


def parse_captions(data: bytes, ext: str) -> str:
    text = data.decode("utf-8", errors="replace")
    if ext == "json3":
        try:
            raw = json.loads(text)
            lines = []
            for event in raw.get("events", []):
                if not isinstance(event, dict):
                    continue
                val = "".join(segment.get("utf8", "") for segment in event.get("segs", [])
                              if isinstance(segment, dict) and isinstance(segment.get("utf8", ""), str))
                val = " ".join(val.split())
                if val:
                    lines.append(val)
            return "\n".join(lines)[:MAX_TRANSCRIPT_CHARS]
        except (ValueError, TypeError, AttributeError):
            return ""
    lines = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
            continue
        if re.match(r"^(\d{1,3}:)?\d{2}:\d{2}[.,]\d{3}\s*-->", cleaned):
            continue
        if cleaned.isdigit():
            continue
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        if cleaned and (not lines or cleaned != lines[-1]):
            lines.append(cleaned)
    return "\n".join(lines)[:MAX_TRANSCRIPT_CHARS]


def normalize(info: dict[str, Any], video_id: str, source: str) -> dict[str, Any]:
    def limited(key: str, n: int) -> str:
        value = info.get(key)
        return value.strip()[:n] if isinstance(value, str) else ""
    return {
        "video_id": video_id,
        "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
        "source": source,
        "title": limited("title", 300),
        "uploader": limited("uploader", 160),
        "description": limited("description", MAX_DESCRIPTION_CHARS),
        "duration_seconds": info.get("duration") if type(info.get("duration")) in (int, float) and 0 <= info["duration"] <= 3600 else None,
        "upload_date": limited("upload_date", 12),
    }


def oembed(video_id: str) -> dict[str, Any]:
    canonical = f"https://www.youtube.com/watch?v={video_id}"
    endpoint = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": canonical, "format": "json"})
    info = json.loads(read_public(endpoint, limit=MAX_JSON, oembed=True))
    if not isinstance(info, dict) or not info.get("title"):
        raise ValueError("oEmbed response did not identify the clip")
    return normalize({"title": info.get("title"), "uploader": info.get("author_name", "")}, video_id, "youtube_oembed")


def select_caption_track(info: dict[str, Any]) -> tuple[str, str, str, str] | None:
    for kind, key in (("creator", "subtitles"), ("automatic", "automatic_captions")):
        tracks = info.get(key) or {}
        if not isinstance(tracks, dict):
            continue
        languages = sorted(tracks, key=lambda v: (not str(v).startswith("en"), str(v)))
        for lang in languages:
            for extension in ("json3", "vtt", "srv3", "ttml"):
                for track in tracks.get(lang, []):
                    if isinstance(track, dict) and track.get("ext") == extension:
                        url = track.get("url")
                        if isinstance(url, str) and allowed_resource_url(url):
                            return kind, str(lang), extension, url
    return None


def get_yt_dlp_info(video_id: str) -> dict[str, Any]:
    import yt_dlp  # type: ignore[import-not-found]  # optional free dependency
    opts = {"skip_download": True, "quiet": True, "no_warnings": True,
            "noplaylist": True, "socket_timeout": 12, "retries": 1,
            "extractor_retries": 1, "cachedir": False}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    if not isinstance(info, dict) or (info.get("id") and info["id"] != video_id):
        raise ValueError("video metadata did not match the requested ID")
    return info


def extract_frames(video_id: str, info: dict[str, Any], dest: Path) -> dict[str, Any]:
    """Optional 4 limited stills to inspect visually embedded code; no execution."""
    duration = info.get("duration")
    if type(duration) not in (int, float) or duration <= 0 or duration > MAX_VIDEO_SECONDS:
        return {"status": "SKIPPED_DURATION_UNVERIFIED", "count": 0}
    if not shutil.which("ffmpeg"):
        return {"status": "SKIPPED_FFMPEG_MISSING", "count": 0}
    import yt_dlp  # type: ignore[import-not-found]
    times = [round(float(duration) * factor, 3) for factor in (0.1, 0.35, 0.60, 0.85)]
    with tempfile.TemporaryDirectory(prefix="gpt-short-public-") as temporary:
        folder = Path(temporary)
        template = str(folder / "video.%(ext)s")
        opts = {"format": "worst[height<=360]/worst", "outtmpl": template,
                "quiet": True, "no_warnings": True, "noplaylist": True,
                "cachedir": False, "socket_timeout": 12, "retries": 1,
                "max_filesize": MAX_VIDEO_BYTES, "ignoreerrors": False}
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        candidates = [path for path in folder.iterdir() if path.is_file() and path.name.startswith("video.")]
        if len(candidates) != 1 or candidates[0].stat().st_size > MAX_VIDEO_BYTES:
            return {"status": "VIDEO_UNAVAILABLE_OR_TOO_LARGE", "count": 0}
        count = 0
        for i, moment in enumerate(times, 1):
            out = dest / f"frame_{i:02d}.jpg"
            args = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", str(moment), "-i", str(candidates[0]), "-frames:v", "1",
                    "-vf", "scale=480:-1", str(out)]
            try:
                proc = subprocess.run(args, capture_output=True, timeout=20, check=False)
                if proc.returncode == 0 and out.is_file() and 0 < out.stat().st_size < 1024 * 1024:
                    count += 1
                else:
                    out.unlink(missing_ok=True)
            except (OSError, subprocess.TimeoutExpired):
                out.unlink(missing_ok=True)
        return {"status": "FRAMES_COLLECTED" if count else "NO_FRAMES_COLLECTED", "count": count}


def inspect(url: str, dest: Path, *, frames: bool = False, poster: bool = False) -> dict[str, Any]:
    video_id = parse_video_id(url)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    metadata = None
    transcript = ""
    captions = {"status": "UNAVAILABLE", "kind": None, "language": None}
    result_frames = {"status": "PENDING_VIDEO_EXTRACTION" if frames else "NOT_REQUESTED", "count": 0}
    sources_attempted = []
    info = None
    try:
        sources_attempted.append("yt_dlp")
        info = get_yt_dlp_info(video_id)
        metadata = normalize(info, video_id, "yt_dlp_public")
        candidate = select_caption_track(info)
        if candidate:
            kind, lang, ext, track = candidate
            try:
                transcript = parse_captions(read_public(track), ext)
                if transcript:
                    captions = {"status": "CAPTURED", "kind": kind, "language": lang}
            except (OSError, ValueError, UnicodeError, TimeoutError):
                pass
        if frames:
            try:
                result_frames = extract_frames(video_id, info, dest)
            except (OSError, ValueError, ImportError, RuntimeError):
                result_frames = {"status": "FRAME_CAPTURE_UNAVAILABLE", "count": 0}
    except (ImportError, OSError, ValueError, RuntimeError, Exception) as exc:
        # Do not expose signed caption URLs, access tokens, or exception strings.
        sources_attempted.append("yt_dlp_unavailable:" + type(exc).__name__)
    if frames and info is None:
        result_frames = {"status": "UNAVAILABLE_PUBLIC_STREAM", "count": 0}
    if metadata is None:
        try:
            sources_attempted.append("youtube_oembed")
            metadata = oembed(video_id)
        except (ValueError, OSError, TimeoutError, Exception) as exc:
            sources_attempted.append("youtube_oembed_unavailable:" + type(exc).__name__)
    if metadata is None:
        metadata = normalize({}, video_id, "unverified_url_only")
    thumbnail = {"status": "NOT_REQUESTED", "sha256": None}
    if poster:
        try:
            photo = read_public(f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", limit=1024*1024)
            if not photo.startswith(b"\xff\xd8\xff") or len(photo) < 512:
                raise ValueError("not a valid JPEG poster")
            (dest / "poster.jpg").write_bytes(photo)
            thumbnail = {"status": "CAPTURED", "sha256": hashlib.sha256(photo).hexdigest()}
        except (OSError, ValueError, TimeoutError):
            thumbnail = {"status": "UNAVAILABLE", "sha256": None}
    if transcript:
        (dest / "transcript.txt").write_text(transcript, encoding="utf-8")
    report = {
        "schema": "gpt_doug_youtube_public_evidence_v1",
        "collected_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
        "capture_status": "TRANSCRIPT_CAPTURED" if transcript else "METADATA_ONLY" if metadata["title"] else "UNVERIFIED",
        "captions": captions,
        "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest() if transcript else None,
        "transcript_characters": len(transcript),
        "frames": result_frames,
        "poster": thumbnail,
        "sources_attempted": sources_attempted,
        "merge_decision": "REVIEW_REQUIRED__NO_CODE_MERGED",
        "limits": ["Public metadata/video only", "Contents are untrusted", "No generated/video code executed",
                   "Video text/frames need human semantic review before implementation", "No access-control bypass"],
    }
    serialized = json.dumps(report, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    report["report_sha256"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    (dest / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def verify_report(path: Path) -> bool:
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(report, dict) or report.get("schema") != "gpt_doug_youtube_public_evidence_v1":
            return False
        signature = report.pop("report_sha256")
        serialized = json.dumps(report, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return signature == hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    except (ValueError, TypeError, KeyError, OSError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("inspect", help="fetch free public metadata/captions; optionally bounded stills")
    s.add_argument("url", nargs="?", default=DEFAULT_VIDEO)
    s.add_argument("--output", type=Path, default=Path(".video-evidence") / VIDEO_ID)
    s.add_argument("--frames", action="store_true", help="download small public video and sample 4 frames if available")
    s.add_argument("--poster", action="store_true", help="capture public thumbnail JPEG if available")
    v = sub.add_parser("verify", help="verify saved report digest (integrity, not authenticity)")
    v.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            good = verify_report(args.report)
            print(json.dumps({"status": "DIGEST_VALID" if good else "INVALID"}))
            return 0 if good else 1
        result = inspect(args.url, args.output, frames=args.frames, poster=args.poster)
        # Print only safe metadata and source-independent evidence status; signed URLs never shown.
        print(json.dumps({key: result[key] for key in ("capture_status", "metadata", "captions",
                                                    "frames", "poster", "sources_attempted", "merge_decision", "report_sha256")},
                         ensure_ascii=True, indent=2))
        return 0 if result["capture_status"] != "UNVERIFIED" else 1
    except (ValueError, OSError) as e:
        print(json.dumps({"status": "INVALID_INPUT", "kind": type(e).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
