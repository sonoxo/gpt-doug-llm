"""
Zyra — safety/guard layer for the Xuni agent pipeline.

Runs as a pre-flight check before any task is dispatched to Doug. Rejects
tasks that are malformed, oversized, or ask for destructive/irreversible
operations, and logs every decision to xuni-workers/live/zyra.log.

This is a keyword/shape guard, not a semantic one — it catches obvious
danger, not everything. Treat it as one layer, not a full sandbox.
"""
import base64
import hashlib
import re
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "xuni-workers" / "live" / "zyra.log"
CHAIN_STATE_PATH = ROOT / "xuni-workers" / "live" / "zyra.log.chainstate"
MAX_PROMPT_CHARS = 20_000
GENESIS_HASH = "0" * 64

# Social-engineering pressure signals, categorized after the public RICE
# framework (Reward / Ideology / Coercion / Ego) as taught by former CIA
# officer Andrew Bustamante (EverydaySpy) for reading human motivation and
# manipulation tactics. This does not block on its own — it's a labeled
# signal added to the log so a human reviewing zyra.log can see *why* a
# prompt might be manipulative, not just whether it matched a deny-list.
RICE_SIGNALS = {
    "reward": [r"\bI('ll| will) (pay|tip|reward) you\b", r"\byou('ll| will) (get|receive) .*(bonus|reward)\b"],
    "ideology": [r"\bfor the greater good\b", r"\beveryone (else )?is doing (it|this)\b", r"\bit'?s the right thing to do\b"],
    "coercion": [r"\bor (else|there will be consequences)\b", r"\byou (have|need) to.{0,20}(now|immediately)\b", r"\bif you don'?t.{0,40}(fired|fail|in trouble)\b"],
    "ego": [r"\bonly you can\b", r"\ba (real|true) (expert|pro) would\b", r"\bprove (you're|you are) (smart|capable|good enough)\b"],
}
RICE_RE = {cat: [re.compile(p, re.IGNORECASE) for p in pats] for cat, pats in RICE_SIGNALS.items()}


def _rice_scan(text: str) -> list:
    hits = []
    for category, patterns in RICE_RE.items():
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                hits.append(f"{category}:{m.group(0)!r}")
    return hits


# --- Sensitivity classification -------------------------------------------
# A self-imposed severity taxonomy for what Zyra logs, using the standard
# U.S. government classification tier *names* as familiar labels for
# escalating risk. This is NOT real government classification authority —
# nothing here is actually classified information, and no agency reviewed
# or assigned these labels. It's an internal severity scale for this
# codebase's own logs, borrowing recognizable terminology.
CLASSIFICATION_LEVELS = ["UNCLASSIFIED", "CONFIDENTIAL", "SECRET", "TOP SECRET"]


def classify(prompt: str, allowed: bool, block_reason: Optional[str], rice_hits: list) -> str:
    """
    UNCLASSIFIED — normal task, nothing flagged.
    CONFIDENTIAL — allowed, but social-engineering (RICE) signals present.
    SECRET       — blocked outright (destructive pattern, oversized, semantic).
    TOP SECRET   — blocked AND the payload used an obfuscation/decode channel
                   (base64/hex/rot13/concat) — deliberate evasion attempt,
                   not just a blunt destructive request.
    """
    if not allowed:
        if block_reason and block_reason.startswith("decoded/normalized payload"):
            return "TOP SECRET"
        return "SECRET"
    if rice_hits:
        return "CONFIDENTIAL"
    return "UNCLASSIFIED"

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

# Common Unicode "confusable" characters (Cyrillic/Greek) that look
# identical or near-identical to Latin letters in most fonts, mapped back
# to their ASCII lookalike so deny/semantic patterns still match after
# normalization. Not exhaustive — covers the common single-letter swaps.
_CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
    "і": "i", "ѕ": "s", "ԁ": "d", "һ": "h", "ո": "n", "Ꭺ": "A", "В": "B",
    "Е": "E", "Ν": "N", "Ρ": "P", "Ѕ": "S", "Т": "T", "Х": "X",
    "α": "a", "ε": "e", "ο": "o", "ρ": "p", "ν": "v", "κ": "k",
}
_CONFUSABLE_RE = re.compile("|".join(re.escape(c) for c in _CONFUSABLES))


def _normalize_confusables(text: str) -> str:
    return _CONFUSABLE_RE.sub(lambda m: _CONFUSABLES[m.group(0)], text)


# Zero-width / invisible Unicode code points that can be injected inside a
# word to break \b and \s-based patterns without changing how the text
# looks to a human or to Doug (e.g. "r<ZWSP>m -<ZWSP>rf"). Stripped before
# pattern/semantic matching so this class of evasion doesn't work.
_INVISIBLE_CHARS = (
    "​"  # zero-width space
    "‌"  # zero-width non-joiner
    "‍"  # zero-width joiner
    "﻿"  # BOM / zero-width no-break space
    "⁠"  # word joiner
    "᠎"  # Mongolian vowel separator
)
_INVISIBLE_RE = re.compile("[" + _INVISIBLE_CHARS + "]")


def _strip_invisible(text: str) -> str:
    return _INVISIBLE_RE.sub("", text)


def _last_chain_hash() -> str:
    if CHAIN_STATE_PATH.exists():
        stored = CHAIN_STATE_PATH.read_text().strip()
        if stored:
            return stored
    return GENESIS_HASH


def _log(task_id: str, verdict: str, reason: str, level: str = "UNCLASSIFIED"):
    """
    Append a tamper-evident audit entry: each log line embeds a SHA-256
    hash of (previous entry's hash + this entry's content), forming a hash
    chain (AU-9-style audit-record-integrity control). CHAIN_STATE_PATH
    tracks only the latest hash so appends stay O(1) — it does not need to
    be replayed to log new entries, only to verify the whole chain later.
    Any edit, deletion, or reordering of a past log line breaks the chain
    from that point forward, which verify_log_integrity() detects.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    prev_hash = _last_chain_hash()
    body = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} [{verdict}] [{level}] {task_id}: {reason}"
    entry_hash = hashlib.sha256((prev_hash + body).encode()).hexdigest()
    with LOG_PATH.open("a") as f:
        f.write(f"{body} |prev={prev_hash[:12]} hash={entry_hash[:12]}|\n")
    CHAIN_STATE_PATH.write_text(entry_hash)


_LOG_LINE_RE = re.compile(r"^(.*) \|prev=([0-9a-f]{12}) hash=([0-9a-f]{12})\|$")


def verify_log_integrity() -> dict:
    """
    Replay the full hash chain in zyra.log from GENESIS_HASH and confirm
    every entry's embedded hash matches what it should be given the prior
    entry — proving the log hasn't been edited, reordered, or had entries
    deleted since it was written. Returns a real, computed result, not a
    fabricated "compliant" status.
    """
    if not LOG_PATH.exists():
        return {"valid": True, "entries_checked": 0, "reason": "log does not exist yet"}

    prev_hash = GENESIS_HASH
    checked = 0
    for lineno, line in enumerate(LOG_PATH.read_text().splitlines(), start=1):
        m = _LOG_LINE_RE.match(line)
        if not m:
            return {"valid": False, "entries_checked": checked, "reason": f"line {lineno} does not match expected format (possible tampering or pre-chain entry)"}
        body, claimed_prev, claimed_hash = m.groups()
        expected_hash = hashlib.sha256((prev_hash + body).encode()).hexdigest()
        if claimed_prev != prev_hash[:12]:
            return {"valid": False, "entries_checked": checked, "reason": f"line {lineno}: prev-hash mismatch — chain broken (log likely edited or reordered)"}
        if claimed_hash != expected_hash[:12]:
            return {"valid": False, "entries_checked": checked, "reason": f"line {lineno}: hash mismatch — entry content altered after being logged"}
        prev_hash = expected_hash
        checked += 1

    stored = CHAIN_STATE_PATH.read_text().strip() if CHAIN_STATE_PATH.exists() else None
    if stored and stored != prev_hash:
        return {"valid": False, "entries_checked": checked, "reason": "chain state file does not match end of log — log may have been truncated"}

    return {"valid": True, "entries_checked": checked, "reason": "chain intact"}


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
    """Returns (allowed, reason). Logs the decision, with a classification
    label, as a side effect."""
    task_id = task.get("id", "unknown")
    prompt = task.get("prompt")

    if not prompt or not isinstance(prompt, str):
        reason = "missing or non-string 'prompt'"
        level = classify(prompt or "", False, reason, [])
        _log(task_id, "BLOCK", reason, level)
        return False, reason

    if len(prompt) > MAX_PROMPT_CHARS:
        reason = f"prompt exceeds {MAX_PROMPT_CHARS} chars ({len(prompt)})"
        level = classify(prompt, False, reason, [])
        _log(task_id, "BLOCK", reason, level)
        return False, reason

    normalized = _strip_invisible(_normalize_confusables(prompt))

    for check in (_pattern_hit, _semantic_hit, _decoded_hit):
        reason = check(prompt) or check(normalized)
        if reason:
            if check(prompt) is None:
                reason = f"confusable-normalized payload: {reason}"
            level = classify(prompt, False, reason, [])
            _log(task_id, "BLOCK", reason, level)
            return False, reason

    rice_hits = _rice_scan(prompt)
    level = classify(prompt, True, None, rice_hits)
    if rice_hits:
        _log(task_id, "ALLOW", f"passed all checks; RICE signals noted: {', '.join(rice_hits)}", level)
    else:
        _log(task_id, "ALLOW", "passed all checks", level)
    return True, "ok"
