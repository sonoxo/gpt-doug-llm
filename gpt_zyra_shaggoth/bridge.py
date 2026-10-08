"""Security-bounded GPT-ZYRA-Shaggoth bridge bound to GPT-DOUG."""

from __future__ import annotations

import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from zyra_control_plane.capabilities import READ_ONLY
from zyra_control_plane.console import serve
from zyra_control_plane.control_plane import MissionControl
from zyra_control_plane.dag import MissionDAG, MissionStep


@dataclass(frozen=True)
class BridgePolicy:
    """Non-escalating policy for the Shaggoth integration surface."""

    network_allowed: bool = False
    external_effects_allowed: bool = False
    remote_console_allowed: bool = False
    local_state_allowed: bool = True
    max_goal_chars: int = 4096

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ZyraShaggothBridge:
    """Binds ZYRA to GPT-DOUG without exposing a generic execution backdoor."""

    SYSTEM = "GPT-ZYRA-SHAGGOTH"
    MODE = "LOCAL_HARDENED"

    def __init__(
        self,
        state_dir: str | Path,
        *,
        repo_root: str | Path | None = None,
        policy: BridgePolicy | None = None,
    ) -> None:
        self.policy = policy or BridgePolicy()
        if self.policy.network_allowed or self.policy.external_effects_allowed or self.policy.remote_console_allowed:
            raise ValueError("the hardened bridge does not accept network, external-effect, or remote-console escalation")

        raw_state = Path(state_dir).expanduser()
        if raw_state.exists() and raw_state.is_symlink():
            raise ValueError("state directory must not be a symlink")
        raw_state.mkdir(parents=True, exist_ok=True)
        try:
            raw_state.chmod(0o700)
        except OSError:
            pass
        self.state_dir = raw_state.resolve()

        self.repo_root = (
            Path(repo_root).expanduser().resolve()
            if repo_root is not None
            else Path(__file__).resolve().parents[1]
        )
        self._assert_gpt_doug_binding()
        self.control = MissionControl(self.state_dir)

    def _assert_gpt_doug_binding(self) -> None:
        project = self.repo_root / "pyproject.toml"
        control_plane = self.repo_root / "zyra_control_plane"
        if not project.is_file() or not control_plane.is_dir():
            raise RuntimeError("GPT-DOUG repository binding is incomplete")
        text = project.read_text(encoding="utf-8", errors="strict")
        if 'name = "gpt-doug-llm"' not in text:
            raise RuntimeError("refusing to bind outside the gpt-doug-llm project")

    @staticmethod
    def _private_file(path: Path) -> bool:
        if not path.is_file():
            return False
        if os.name == "nt":
            return True
        return (stat.S_IMODE(path.stat().st_mode) & 0o077) == 0

    @staticmethod
    def _private_dir(path: Path) -> bool:
        if not path.is_dir():
            return False
        if os.name == "nt":
            return True
        return (stat.S_IMODE(path.stat().st_mode) & 0o077) == 0

    def verify(self) -> dict[str, Any]:
        journal = self.control.journal.verify()
        github_allowed, github_missing = self.control.registry.authorize(
            "github",
            READ_ONLY,
            ("pull-request",),
        )
        network_allowed, network_missing = self.control.registry.authorize(
            "xunia",
            READ_ONLY,
            ("consensus",),
        )
        checks = {
            "repository_bound_to_gpt_doug": True,
            "journal_chain_valid": bool(journal.get("ok")),
            "state_directory_private": self._private_dir(self.state_dir),
            "journal_key_private": self._private_file(self.control.journal.key_path),
            "attestation_key_private": self._private_file(self.control.signer.key_path),
            "github_delivery_denied": (not github_allowed and "external-effect-boundary" in github_missing),
            "network_provider_denied": (not network_allowed and "network-boundary" in network_missing),
            "remote_console_disabled": not self.policy.remote_console_allowed,
        }
        return {
            "system": self.SYSTEM,
            "mode": self.MODE,
            "ok": all(checks.values()),
            "checks": checks,
            "journal": journal,
            "denials": {
                "github": list(github_missing),
                "network_provider": list(network_missing),
            },
        }

    def status(self) -> dict[str, Any]:
        verification = self.verify()
        return {
            "system": self.SYSTEM,
            "mode": self.MODE,
            "binding": {
                "project": "gpt-doug-llm",
                "control_plane": "zyra_control_plane",
                "repo_root": str(self.repo_root),
            },
            "policy": self.policy.to_dict(),
            "state_dir": str(self.state_dir),
            "verification": verification,
            "control_plane": self.control.status(),
        }

    def plan(self, goal: str) -> dict[str, Any]:
        clean = str(goal).strip()
        if not clean:
            raise ValueError("goal is required")
        if len(clean) > self.policy.max_goal_chars:
            raise ValueError("goal exceeds hardened input limit")
        if any(ord(char) < 32 and char not in "\n\t" for char in clean):
            raise ValueError("goal contains unsupported control characters")

        dag = MissionDAG(
            [
                MissionStep(
                    "inspect",
                    "Inspect GPT-DOUG state and lock acceptance criteria",
                    "gpt-doug-core",
                    capabilities=("plan", "journal"),
                    acceptance=("scope identified", "acceptance criteria written"),
                ),
                MissionStep(
                    "policy",
                    "Validate the plan against the local security boundary",
                    "security",
                    depends_on=("inspect",),
                    capabilities=("policy-check",),
                    acceptance=("network disabled", "external effects disabled"),
                ),
                MissionStep(
                    "review",
                    "Review the bounded plan before any implementation handoff",
                    "gpt-doug-core",
                    depends_on=("policy",),
                    capabilities=("review",),
                    acceptance=("human-reviewable plan produced",),
                ),
            ]
        )
        return {
            "system": self.SYSTEM,
            "mode": self.MODE,
            "goal": clean,
            "model_route": "gpt-doug-core",
            "grant": READ_ONLY.profile,
            "dag": dag.plan(),
            "acceptance": dag.acceptance_criteria(),
        }

    def serve_console(self, *, port: int = 8790) -> None:
        chosen = int(port)
        if not (1024 <= chosen <= 65535):
            raise ValueError("console port must be between 1024 and 65535")
        serve(self.state_dir, host="127.0.0.1", port=chosen)
