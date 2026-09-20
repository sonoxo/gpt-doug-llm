from __future__ import annotations

from typing import Iterable

from universal_hive import UniversalHiveRuntime


class GPTChaos:
    """Bounded simulation/specialist worker fabric attached to GPT-Doug's hive."""

    WORKER_FABRIC = (
        "simulation",
        "alternate-strategy",
        "stress-test",
        "adversarial-evaluation",
        "verification",
    )

    def __init__(self, hive: UniversalHiveRuntime | None = None) -> None:
        self.hive = hive or UniversalHiveRuntime()

    def summon(
        self,
        job: str,
        *,
        builders: Iterable[str] | None = None,
        request_id: str | None = None,
    ) -> dict:
        swarm = self.hive.summon_swarm(
            job,
            builders=builders,
            source="gpt-chaos",
            request_id=request_id,
        )
        return {
            **swarm,
            "controller": "GPT_DOUG",
            "simulation_layer": "GPT_CHAOS",
            "worker_fabric": list(self.WORKER_FABRIC),
            "execution_boundary": "PROPOSE_VALIDATE_EXECUTE_CRITIC",
        }

    def status(self) -> dict:
        return {
            "gpt_chaos": "WORKER_FABRIC_READY",
            "worker_fabric": list(self.WORKER_FABRIC),
            "hive": self.hive.status(),
        }
