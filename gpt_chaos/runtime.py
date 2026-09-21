from __future__ import annotations

from typing import Iterable

from cloud_nxyz import CloudNXYZEngine
from universal_hive import AdaptiveAutomationAccelerator, UniversalHiveRuntime

from .aerospace import pattern as blended_wing_pattern
from .aerospace import stress_test as stress_test_blended_wing


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
            "learned_patterns": ["US-20260274413-A1:BLENDED_WING_PUSHER_BLI_V1"],
            "execution_boundary": "PROPOSE_VALIDATE_EXECUTE_CRITIC",
        }

    def cloud_nxyz(self, root: str = ".") -> CloudNXYZEngine:
        """Return the APM-governed Cloud-NXYZ control plane shared with this hive."""
        accelerator = AdaptiveAutomationAccelerator(
            self.hive.state_dir / "automation-acceleration"
        )
        return CloudNXYZEngine(
            root=root,
            state_dir=self.hive.state_dir / "cloud-nxyz",
            accelerator=accelerator,
        )

    def cloud_plan(self, command: str, manifest: dict, root: str = ".") -> dict:
        return self.cloud_nxyz(root).plan(command, manifest)

    def aerospace_pattern(self) -> dict:
        return blended_wing_pattern()

    def aerospace_stress_test(self) -> dict:
        return stress_test_blended_wing()

    def status(self) -> dict:
        return {
            "gpt_chaos": "WORKER_FABRIC_READY",
            "worker_fabric": list(self.WORKER_FABRIC),
            "hive": self.hive.status(),
            "apm_law": "APM-001 ACTIVE",
            "cloud_nxyz": "READY",
        }
