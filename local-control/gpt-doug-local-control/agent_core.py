from __future__ import annotations

import json, os, shutil, subprocess, time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"
RUNTIME.mkdir(exist_ok=True)
POLICY = json.loads((ROOT / "policy.json").read_text())
ARM_FILE = RUNTIME / "armed.json"
PANIC_FILE = RUNTIME / "PANIC"
AUDIT = RUNTIME / "audit.jsonl"


def _expand(p: str) -> Path:
    return Path(os.path.expanduser(p)).resolve()


DENY = [_expand(p) for p in POLICY.get("deny_paths", [])]


def _blocked(path: Path) -> bool:
    rp = path.resolve()
    for denied in DENY:
        try:
            if rp == denied or denied in rp.parents:
                return True
        except Exception:
            pass
    return False


def _audit(entry: dict[str, Any]) -> None:
    entry = {"ts": time.time(), **entry}
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def panic_active() -> bool:
    return PANIC_FILE.exists()


def arm(seconds: int | None = None) -> dict[str, Any]:
    ttl = min(int(seconds or POLICY.get("arm_ttl_seconds", 300)), 300)
    until = time.time() + max(1, ttl)
    ARM_FILE.write_text(json.dumps({"until": until}))
    _audit({"event": "arm", "ttl": ttl})
    return {"armed": True, "remaining": ttl}


def disarm() -> None:
    ARM_FILE.unlink(missing_ok=True)
    _audit({"event": "disarm"})


def armed() -> bool:
    if panic_active() or not ARM_FILE.exists():
        return False
    try:
        data = json.loads(ARM_FILE.read_text())
        if float(data.get("until", 0)) > time.time():
            return True
    except Exception:
        pass
    ARM_FILE.unlink(missing_ok=True)
    return False


def panic() -> None:
    PANIC_FILE.write_text("STOP")
    disarm()
    _audit({"event": "panic"})


def clear_panic() -> None:
    PANIC_FILE.unlink(missing_ok=True)
    _audit({"event": "clear_panic"})


def _require_control(kind: str) -> None:
    if panic_active():
        raise RuntimeError("PANIC switch is active")
    if kind in {"control", "write", "shell"} and not armed():
        raise PermissionError("Control is disarmed. Arm locally for up to 5 minutes first.")


def _path_arg(action: dict[str, Any]) -> Path:
    p = _expand(str(action.get("path", "")))
    if _blocked(p):
        raise PermissionError(f"Path blocked by policy: {p}")
    return p


def execute(action: dict[str, Any]) -> dict[str, Any]:
    typ = str(action.get("type", ""))
    kind = POLICY.get("capabilities", {}).get(typ)
    if not kind:
        raise ValueError(f"Unknown action: {typ}")
    _require_control(kind)
    result: dict[str, Any]

    if typ == "list_dir":
        p = _path_arg(action)
        result = {"entries": sorted(x.name for x in p.iterdir())[:500]}
    elif typ == "read_file":
        p = _path_arg(action)
        result = {"text": p.read_text(encoding="utf-8", errors="replace")[:200000]}
    elif typ == "write_file":
        p = _path_arg(action)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(action.get("text", "")), encoding="utf-8")
        result = {"written": str(p)}
    elif typ == "move_file":
        src = _path_arg(action)
        dst = _expand(str(action.get("destination", "")))
        if _blocked(dst):
            raise PermissionError(f"Path blocked by policy: {dst}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        result = {"moved": [str(src), str(dst)]}
    elif typ == "trash_file":
        p = _path_arg(action)
        trash = _expand("~/.Trash") / p.name
        n = 1
        while trash.exists():
            trash = trash.with_name(f"{p.stem}-{n}{p.suffix}")
            n += 1
        shutil.move(str(p), str(trash))
        result = {"trashed": str(trash)}
    elif typ == "open_app":
        app = str(action.get("app", ""))
        subprocess.run(["open", "-a", app], check=True)
        result = {"opened_app": app}
    elif typ == "open_url":
        url = str(action.get("url", ""))
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Only http(s) URLs are allowed")
        subprocess.run(["open", url], check=True)
        result = {"opened_url": url}
    elif typ == "screenshot":
        out = RUNTIME / f"screen-{int(time.time())}.png"
        subprocess.run(["screencapture", "-x", str(out)], check=True)
        result = {"screenshot": str(out)}
    elif typ in {"type_text", "hotkey", "click"}:
        try:
            import pyautogui
        except Exception as e:
            raise RuntimeError("UI control requires: python3 -m pip install pyautogui") from e
        if typ == "type_text":
            text = str(action.get("text", ""))
            pyautogui.write(text, interval=float(action.get("interval", 0.01)))
            result = {"typed": True, "chars": len(text)}
        elif typ == "hotkey":
            keys = action.get("keys") or []
            if not isinstance(keys, list) or not keys:
                raise ValueError("keys must be a non-empty list")
            pyautogui.hotkey(*[str(k) for k in keys])
            result = {"hotkey": keys}
        else:
            x, y = int(action.get("x", 0)), int(action.get("y", 0))
            pyautogui.click(x=x, y=y, clicks=int(action.get("clicks", 1)))
            result = {"clicked": [x, y]}
    elif typ == "run_command":
        argv = action.get("argv")
        if not isinstance(argv, list) or not argv:
            raise ValueError("run_command requires argv as a non-empty list; shell strings are not accepted")
        proc = subprocess.run(
            [str(x) for x in argv],
            capture_output=True,
            text=True,
            timeout=int(action.get("timeout", 60)),
        )
        result = {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-50000:],
            "stderr": proc.stderr[-50000:],
        }
    else:
        raise ValueError(typ)

    safe_action = {k: v for k, v in action.items() if k not in {"text"}}
    _audit({"event": "execute", "action": safe_action, "ok": True})
    return result
