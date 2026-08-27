#!/usr/bin/env python3
"""Launch ZYRA with an expanded but still bounded mission envelope.

This profile is intended for long local repository/document-analysis missions
that need more than the default eight agent steps. It does not add shell,
network, push/deploy/send, or external-targeting capabilities.
"""
from __future__ import annotations

import os

from zyra_agent import MissionBudget, ZyraAgent


_ORIGINAL_INIT = ZyraAgent.__init__


def _env_int(name: str, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _max_init(
    self,
    root,
    *,
    model,
    base_url="http://127.0.0.1:11434",
    budget=None,
    state_dir=None,
):
    if budget is None:
        budget = MissionBudget(
            max_steps=_env_int("ZYRA_AGENT_MAX_STEPS", 32, 16),
            max_seconds=_env_int("ZYRA_AGENT_MAX_SECONDS", 1200, 300),
            max_model_calls=_env_int("ZYRA_AGENT_MAX_MODEL_CALLS", 48, 20),
        )
    _ORIGINAL_INIT(
        self,
        root,
        model=model,
        base_url=base_url,
        budget=budget,
        state_dir=state_dir,
    )


ZyraAgent.__init__ = _max_init

from zyra_chat import main  # noqa: E402  (patch must be installed before import)


if __name__ == "__main__":
    raise SystemExit(main())
