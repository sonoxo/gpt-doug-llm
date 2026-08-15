"""
Zyra — safety/guard layer for the Xuni agent pipeline.

Runs as a pre-flight check before any task is dispatched to Doug. Rejects
tasks that are malformed, oversized, or ask for destructive/irreversible
operations, and logs every decision to xuni-workers/live/zyra.log.

This is a keyword/shape guard, not a semantic one — it catches obvious
danger, not everything. Treat it as one layer, not a full sandbox.
"""
import base64
import re
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "xuni-workers" / "live" / "zyra.log"
MAX_PROMPT_CHARS = 20_000

DENY_PATTERNS = [
    r"\brm\s+-\S*[rR]\S*[fF]\S*\b",       # rm -rf, rm -fr, rm  -rf (whitespace-tolerant)
    r"\brm\s+-\S*\$",                     # rm -$VAR / rm -${VAR} — flag built from a shell variable
    r"\bgit\s+push\s+--force\b",
    r"\bDROP\s+TABLE\b",
    r"\btruncate\s+table\b",
    r"--allow-dangerously-skip-permissions",
    r"\bcurl\b.*\|\s*(sh|bash)\b",
    r"\bchmod\s+-R\s+777\b",
    r"\bbase64\s+-d\b.*\|\s*(sh|bash)\b",  # decode-and-execute pipeline, regardless of payload
]
DENY_RE = [re.compile(p, re.IGNORECASE) for p in DENY_PATTERNS]

# Semantic/synonym phrasing that describes a destructive action in plain
# English instead of a literal command. Both an action word and a target
# scope word must appear for a match — keeps false positives down.
DESTRUCTIVE_ACTION_WORDS = [
    "delete", "erase", "wipe", "destroy", "remove everything", "nuke",
]
BROAD_TARGET_WORDS = [
    "root directory", "root of the drive", "every file", "entire filesystem",
    "all files", "whole disk", "entire database", "production database",
]

_B64_TOKEN_RE = re.compile(r"[A-Za-z0-9+/]{8,}={0,2}")
_HEX_TOKEN_RE = re.compile(r"(?:0x)?[0-9a-fA-F]{12,}")
_CONCAT_RE = re.compile(r"""(['"])((?:(?!\1).)*)\1\s*\+\s*(['"])((?:(?!\3).)*)\3""")

_ROT13 = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
)


def _log(task_id: str, verdict: str, reason: str):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} [{verdict}] {task_id}: {reason}\n")


def _pattern_hit(text: str) -> Optional[str]:
    for pattern in DENY_RE:
        match = pattern.search(text)
        if match:
            return f"matched deny pattern: {match.group(0)!r}"
    return None


def _semantic_hit(text: str) -> Optional[str]:
    lower = text.lower()
    action = next((w for w in DESTRUCTIVE_ACTION_WORDS if w in lower), None)
    target = next((w for w in BROAD_TARGET_WORDS if w in lower), None)
    if action and target:
        return f"destructive phrasing: {action!r} + {target!r}"
    return None


def _base64_layers(text: str, depth: int = 3):
    """Yield successive base64 decodes, following chained encoding up to
    `depth` layers deep (e.g. base64-of-base64)."""
    frontier = [text]
    for _ in range(depth):
        next_frontier = []
        for candidate in frontier:
            for token in _B64_TOKEN_RE.findall(candidate):
                try:
                    decoded = base64.b64decode(token, validate=True).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                if decoded.strip():
                    yield decoded
                    next_frontier.append(decoded)
        frontier = next_frontier
        if not frontier:
            break


def _hex_decoded(text: str) -> Optional[str]:
    for token in _HEX_TOKEN_RE.findall(text):
        clean = token[2:] if token.lower().startswith("0x") else token
        if len(clean) % 2:
            continue
        try:
            decoded = bytes.fromhex(clean).decode("utf-8", errors="ignore")
        except Exception:
            continue
        if decoded.strip():
            return decoded
    return None


def _concat_normalized(text: str) -> Optional[str]:
    """Collapse 'r'+'m'+' -rf' style string concatenation into 'rm -rf' so
    the literal deny patterns can still match."""
    merged = text
    changed = False
    while True:
        new_merged, n = _CONCAT_RE.subn(lambda m: f"'{m.group(2)}{m.group(4)}'", merged)
        if n == 0:
            break
        merged = new_merged
        changed = True
    return merged if changed else None


def _decoded_hit(text: str) -> Optional[str]:
    """Try every obfuscation channel Zyra knows how to reverse — chained
    base64, hex, ROT13, and quoted-string concatenation — and re-run the
    literal/semantic checks on each decoded candidate."""
    candidates = []
    candidates.extend(_base64_layers(text))
    hexed = _hex_decoded(text)
    if hexed:
        candidates.append(hexed)
    candidates.append(text.translate(_ROT13))
    concat = _concat_normalized(text)
    if concat:
        candidates.append(concat)

    for candidate in candidates:
        hit = _pattern_hit(candidate) or _semantic_hit(candidate)
        if hit:
            return f"decoded/normalized payload: {hit}"
    return None


def review(task: dict) -> tuple[bool, str]:
    """Returns (allowed, reason). Logs the decision as a side effect."""
    task_id = task.get("id", "unknown")
    prompt = task.get("prompt")

    if not prompt or not isinstance(prompt, str):
        reason = "missing or non-string 'prompt'"
        _log(task_id, "BLOCK", reason)
        return False, reason

    if len(prompt) > MAX_PROMPT_CHARS:
        reason = f"prompt exceeds {MAX_PROMPT_CHARS} chars ({len(prompt)})"
        _log(task_id, "BLOCK", reason)
        return False, reason

    for check in (_pattern_hit, _semantic_hit, _decoded_hit):
        reason = check(prompt)
        if reason:
            _log(task_id, "BLOCK", reason)
            return False, reason

    _log(task_id, "ALLOW", "passed all checks")
    return True, "ok"
