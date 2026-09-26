from __future__ import annotations

import math
import time
from typing import Any


ALLOWED_BODY_STATES = (
    "IDLE",
    "LISTEN",
    "THINK",
    "TALK",
    "ACT",
    "LEARN",
    "POWER",
    "ERROR",
    "SLEEP",
)

_STATE_ALIASES = {
    "READY": "ACT",
    "OFFLINE": "SLEEP",
}

_ALLOWED_EMOTIONS = {
    "neutral",
    "calm",
    "focused",
    "engaged",
    "determined",
    "curious",
    "energized",
    "alert",
    "resting",
}

_DEFAULTS: dict[str, dict[str, Any]] = {
    "IDLE": {
        "emotion": "calm",
        "intensity": 0.25,
        "eyes": {"focus": 0.45, "blinkRate": 0.28},
        "mouth": {"active": False, "viseme": "rest", "amplitude": 0.0},
        "head": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
        "voice": {"active": False},
        "microphone": {"active": False},
        "speaker": {"active": False},
        "learning": {"active": False, "pulse": 0.0},
    },
    "LISTEN": {
        "emotion": "focused",
        "intensity": 0.62,
        "eyes": {"focus": 0.9, "blinkRate": 0.20},
        "mouth": {"active": False, "viseme": "rest", "amplitude": 0.0},
        "head": {"yaw": 0.0, "pitch": -0.02, "roll": 0.0},
        "voice": {"active": False},
        "microphone": {"active": True},
        "speaker": {"active": False},
        "learning": {"active": False, "pulse": 0.0},
    },
    "THINK": {
        "emotion": "focused",
        "intensity": 0.72,
        "eyes": {"focus": 0.8, "blinkRate": 0.25},
        "mouth": {"active": False, "viseme": "rest", "amplitude": 0.0},
        "head": {"yaw": 0.05, "pitch": -0.04, "roll": 0.0},
        "voice": {"active": False},
        "microphone": {"active": False},
        "speaker": {"active": False},
        "learning": {"active": False, "pulse": 0.0},
    },
    "TALK": {
        "emotion": "engaged",
        "intensity": 0.76,
        "eyes": {"focus": 0.75, "blinkRate": 0.24},
        "mouth": {"active": True, "viseme": "speech", "amplitude": 0.6},
        "head": {"yaw": 0.0, "pitch": -0.01, "roll": 0.0},
        "voice": {"active": True},
        "microphone": {"active": False},
        "speaker": {"active": True},
        "learning": {"active": False, "pulse": 0.0},
    },
    "ACT": {
        "emotion": "determined",
        "intensity": 0.85,
        "eyes": {"focus": 0.88, "blinkRate": 0.22},
        "mouth": {"active": False, "viseme": "rest", "amplitude": 0.0},
        "head": {"yaw": 0.0, "pitch": -0.03, "roll": 0.0},
        "voice": {"active": False},
        "microphone": {"active": False},
        "speaker": {"active": False},
        "learning": {"active": False, "pulse": 0.0},
    },
    "LEARN": {
        "emotion": "curious",
        "intensity": 0.8,
        "eyes": {"focus": 0.9, "blinkRate": 0.18},
        "mouth": {"active": False, "viseme": "rest", "amplitude": 0.0},
        "head": {"yaw": 0.0, "pitch": -0.03, "roll": 0.0},
        "voice": {"active": False},
        "microphone": {"active": False},
        "speaker": {"active": False},
        "learning": {"active": True, "pulse": 0.8},
    },
    "POWER": {
        "emotion": "energized",
        "intensity": 1.0,
        "eyes": {"focus": 1.0, "blinkRate": 0.15},
        "mouth": {"active": False, "viseme": "rest", "amplitude": 0.0},
        "head": {"yaw": 0.0, "pitch": -0.06, "roll": 0.0},
        "voice": {"active": False},
        "microphone": {"active": False},
        "speaker": {"active": False},
        "learning": {"active": False, "pulse": 0.0},
    },
    "ERROR": {
        "emotion": "alert",
        "intensity": 0.9,
        "eyes": {"focus": 1.0, "blinkRate": 0.1},
        "mouth": {"active": False, "viseme": "rest", "amplitude": 0.0},
        "head": {"yaw": 0.0, "pitch": 0.0, "roll": 0.01},
        "voice": {"active": False},
        "microphone": {"active": False},
        "speaker": {"active": False},
        "learning": {"active": False, "pulse": 0.0},
    },
    "SLEEP": {
        "emotion": "resting",
        "intensity": 0.12,
        "eyes": {"focus": 0.0, "blinkRate": 0.0},
        "mouth": {"active": False, "viseme": "rest", "amplitude": 0.0},
        "head": {"yaw": 0.0, "pitch": 0.05, "roll": 0.0},
        "voice": {"active": False},
        "microphone": {"active": False},
        "speaker": {"active": False},
        "learning": {"active": False, "pulse": 0.0},
    },
}


def _finite_number(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return round(max(low, min(number, high)), 4)


def _boolean(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _text(value: Any, default: str, maximum: int) -> str:
    if not isinstance(value, str):
        return default
    cleaned = " ".join(value.split()).strip()
    return cleaned[:maximum] if cleaned else default


def normalize_state_name(value: Any) -> str:
    name = str(value or "IDLE").strip().upper()
    name = _STATE_ALIASES.get(name, name)
    if name not in ALLOWED_BODY_STATES:
        raise ValueError(f"unsupported body state: {name}")
    return name


def runtime_body_state(
    state: str,
    detail: str = "",
    *,
    timestamp: float | None = None,
) -> dict[str, Any]:
    name = normalize_state_name(state)
    base = _DEFAULTS[name]
    return {
        "schema": "gptdoug/body-state-v1",
        "state": name,
        "emotion": base["emotion"],
        "intensity": base["intensity"],
        "detail": " ".join(str(detail).split()).strip()[:160],
        "eyes": dict(base["eyes"]),
        "mouth": dict(base["mouth"]),
        "head": dict(base["head"]),
        "voice": dict(base["voice"]),
        "microphone": dict(base["microphone"]),
        "speaker": dict(base["speaker"]),
        "learning": dict(base["learning"]),
        "timestamp": round(float(timestamp if timestamp is not None else time.time()), 3),
    }


def sanitize_body_state(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("body state must be an object")

    state = normalize_state_name(payload.get("state"))
    defaults = runtime_body_state(state, payload.get("detail", ""))
    eyes = payload.get("eyes") if isinstance(payload.get("eyes"), dict) else {}
    mouth = payload.get("mouth") if isinstance(payload.get("mouth"), dict) else {}
    head = payload.get("head") if isinstance(payload.get("head"), dict) else {}
    voice = payload.get("voice") if isinstance(payload.get("voice"), dict) else {}
    microphone = payload.get("microphone") if isinstance(payload.get("microphone"), dict) else {}
    speaker = payload.get("speaker") if isinstance(payload.get("speaker"), dict) else {}
    learning = payload.get("learning") if isinstance(payload.get("learning"), dict) else {}

    emotion = _text(
        payload.get("emotion"),
        defaults["emotion"],
        24,
    ).lower()
    if emotion not in _ALLOWED_EMOTIONS:
        emotion = defaults["emotion"]

    timestamp = _finite_number(
        payload.get("timestamp"),
        defaults["timestamp"],
        0.0,
        4_102_444_800.0,
    )

    return {
        "schema": "gptdoug/body-state-v1",
        "state": state,
        "emotion": emotion,
        "intensity": _finite_number(payload.get("intensity"), defaults["intensity"], 0.0, 1.5),
        "detail": _text(payload.get("detail"), "", 160),
        "eyes": {
            "focus": _finite_number(eyes.get("focus"), defaults["eyes"]["focus"], 0.0, 1.0),
            "blinkRate": _finite_number(
                eyes.get("blinkRate"),
                defaults["eyes"]["blinkRate"],
                0.0,
                2.0,
            ),
        },
        "mouth": {
            "active": _boolean(mouth.get("active"), defaults["mouth"]["active"]),
            "viseme": _text(mouth.get("viseme"), defaults["mouth"]["viseme"], 24),
            "amplitude": _finite_number(
                mouth.get("amplitude"),
                defaults["mouth"]["amplitude"],
                0.0,
                1.0,
            ),
        },
        "head": {
            "yaw": _finite_number(head.get("yaw"), defaults["head"]["yaw"], -1.0, 1.0),
            "pitch": _finite_number(head.get("pitch"), defaults["head"]["pitch"], -1.0, 1.0),
            "roll": _finite_number(head.get("roll"), defaults["head"]["roll"], -1.0, 1.0),
        },
        "voice": {
            "active": _boolean(voice.get("active"), defaults["voice"]["active"]),
        },
        "microphone": {
            "active": _boolean(
                microphone.get("active"),
                defaults["microphone"]["active"],
            ),
        },
        "speaker": {
            "active": _boolean(speaker.get("active"), defaults["speaker"]["active"]),
        },
        "learning": {
            "active": _boolean(learning.get("active"), defaults["learning"]["active"]),
            "pulse": _finite_number(
                learning.get("pulse"),
                defaults["learning"]["pulse"],
                0.0,
                1.0,
            ),
        },
        "timestamp": timestamp,
    }
