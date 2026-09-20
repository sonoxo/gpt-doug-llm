from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from universal_hive import AdaptiveAutomationAccelerator
from universal_hive.apm_law import APMLaw


SUPPORTED_IAC = {
    "terraform",
    "cloudformation",
    "ansible",
    "kubernetes",
}
SUPPORTED_PROVIDERS = {
    "aws",
    "azure",
    "gcp",
    "generic",
    "local",
    "ibm",
}
SUCCESS = {"PASSED", "READY", "SUCCESS", "SUCCEEDED"}


@dataclass(frozen=True)
class CloudComponent:
    component_id: str
    provider: str
    iac_tool: str
    config_path: str
    depends_on: tuple[str, ...]
    monitoring: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "provider": self.provider,
            "iac_tool": self.iac_tool,
            "config_path": self.config_path,
            "depends_on": list(self.depends_on),
            "monitoring": self.monitoring,
        }


class CloudNXYZEngine:
    """APM-governed cloud planner/executor using a provider-neutral IaC graph.

    The engine follows a generalized architecture:
    one command -> normalized manifest -> IaC mapping -> execution plan ->
    monitoring attachment -> outcome telemetry -> APM.

    Planning is always available. External mutation requires both execute=True
    and GPT_DOUG_CLOUD_NXYZ_EXECUTE=1. The engine never reads or prints cloud
    credentials; provider tools remain responsible for their normal credential
    resolution.
    """

    SOURCE = {
        "type": "patent_architecture_reference",
        "document": "US Patent 12,739,267",
        "title": "Automated cloud infrastructure deployment",
        "date": "2026-09-15",
        "assignee": "Fortinet, Inc.",
        "use": "generalized architecture inspiration; independent implementation",
    }

    def __init__(
        self,
        root: str | Path = ".",
        *,
        state_dir: str | Path | None = None,
        accelerator: AdaptiveAutomationAccelerator | None = None,
        apm_law: APMLaw | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.state_dir = Path(
            state_dir or (Path.home() / ".gpt-doug" / "cloud-nxyz")
        ).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir = self.state_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.accelerator = accelerator or AdaptiveAutomationAccelerator(
            self.state_dir / "apm"
        )
        self.apm_law = apm_law or APMLaw()

    def _inside_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root)
            return True
        except ValueError:
            return False

    def _normalize_component(self, value: Mapping[str, Any]) -> CloudComponent:
        component_id = str(value.get("id") or value.get("component_id") or "").strip()
        provider = str(value.get("provider") or "generic").strip().lower()
        iac_tool = str(value.get("iac_tool") or "").strip().lower()
        config_path = str(value.get("config_path") or "").strip()
        monitoring = str(value.get("monitoring") or "api").strip().lower()
        depends_on = tuple(str(x).strip() for x in value.get("depends_on") or [] if str(x).strip())

        if not component_id:
            raise ValueError("component id is required")
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported provider: {provider}")
        if iac_tool not in SUPPORTED_IAC:
            raise ValueError(f"unsupported IaC tool: {iac_tool}")
        if not config_path:
            raise ValueError(f"config_path is required for {component_id}")

        resolved = (self.root / config_path).resolve()
        if not self._inside_root(resolved):
            raise ValueError(f"config_path escapes Cloud-NXYZ root: {config_path}")
        if not resolved.exists():
            raise FileNotFoundError(f"Cloud-NXYZ config does not exist: {config_path}")

        return CloudComponent(
            component_id=component_id,
            provider=provider,
            iac_tool=iac_tool,
            config_path=str(Path(config_path)),
            depends_on=depends_on,
            monitoring=monitoring,
        )

    def _toposort(self, components: list[CloudComponent]) -> list[CloudComponent]:
        by_id = {item.component_id: item for item in components}
        if len(by_id) != len(components):
            raise ValueError("component ids must be unique")
        for item in components:
            missing = [dep for dep in item.depends_on if dep not in by_id]
            if missing:
                raise ValueError(f"{item.component_id} has missing dependencies: {missing}")

        ordered: list[CloudComponent] = []
        pending = dict(by_id)
        while pending:
            ready = [
                item for item in pending.values()
                if all(dep in {done.component_id for done in ordered} for dep in item.depends_on)
            ]
            if not ready:
                raise ValueError("component dependency graph contains a cycle")
            for item in sorted(ready, key=lambda row: row.component_id):
                ordered.append(item)
                pending.pop(item.component_id)
        return ordered

    def _commands(self, component: CloudComponent) -> dict[str, list[str]]:
        config = (self.root / component.config_path).resolve()
        if component.iac_tool == "terraform":
            directory = config if config.is_dir() else config.parent
            return {
                "validate": ["terraform", f"-chdir={directory}", "validate"],
                "plan": ["terraform", f"-chdir={directory}", "plan", "-input=false"],
                "apply": ["terraform", f"-chdir={directory}", "apply", "-input=false", "-auto-approve"],
            }
        if component.iac_tool == "cloudformation":
            return {
                "validate": ["aws", "cloudformation", "validate-template", "--template-body", f"file://{config}"],
                "plan": ["aws", "cloudformation", "validate-template", "--template-body", f"file://{config}"],
                "apply": [],
            }
        if component.iac_tool == "ansible":
            return {
                "validate": ["ansible-playbook", "--syntax-check", str(config)],
                "plan": ["ansible-playbook", "--check", str(config)],
                "apply": ["ansible-playbook", str(config)],
            }
        if component.iac_tool == "kubernetes":
            return {
                "validate": ["kubectl", "apply", "--dry-run=client", "-f", str(config)],
                "plan": ["kubectl", "diff", "-f", str(config)],
                "apply": ["kubectl", "apply", "-f", str(config)],
            }
        raise AssertionError(component.iac_tool)

    def plan(
        self,
        command: str,
        manifest: Mapping[str, Any],
    ) -> dict[str, Any]:
        normalized_command = " ".join(str(command).split()).strip()
        if not normalized_command:
            raise ValueError("single deployment command must not be empty")

        raw_components = manifest.get("components")
        if not isinstance(raw_components, list) or not raw_components:
            raise ValueError("manifest.components must be a non-empty list")

        components = self._toposort(
            [self._normalize_component(item) for item in raw_components]
        )
        payload = {
            "schema": "cloud-nxyz/plan-v1",
            "command": normalized_command,
            "project": str(manifest.get("project") or "nxyz"),
            "components": [
                {
                    **item.to_dict(),
                    "commands": self._commands(item),
                }
                for item in components
            ],
            "monitoring": {
                "required": True,
                "mode": str(manifest.get("monitoring") or "api"),
                "attach_after_component_apply": True,
                "feedback_to_apm": True,
            },
            "authorization_boundary": "EXPLICIT_RUNTIME_GATE_REQUIRED_FOR_EXTERNAL_MUTATION",
            "context_validation": "VALIDATE_IAC_BEFORE_APPLY",
            "rollback": "PROVIDER_OR_IAC_NATIVE_ROLLBACK_OR_COMPENSATING_ACTION_REQUIRED",
            "procedure_verified": True,
            "provenance": {
                "source": self.SOURCE,
                "manifest_sha256": hashlib.sha256(
                    json.dumps(manifest, sort_keys=True).encode("utf-8")
                ).hexdigest(),
            },
        }
        payload["plan_id"] = "nxyz-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]
        payload["apm_validation"] = self.apm_law.validate_procedure(
            payload,
            requires_mutation=True,
        )
        if not payload["apm_validation"]["valid"]:
            raise ValueError(
                "APM law rejected Cloud-NXYZ plan: "
                + ", ".join(payload["apm_validation"]["failed"])
            )
        return payload

    def modification_plan(
        self,
        base_plan: Mapping[str, Any],
        *,
        component_id: str,
        config_path: str,
    ) -> dict[str, Any]:
        matches = [
            dict(item) for item in base_plan.get("components") or []
            if str(item.get("component_id")) == component_id
        ]
        if not matches:
            raise KeyError(f"unknown Cloud-NXYZ component: {component_id}")
        original = matches[0]
        replacement = self._normalize_component({
            "id": component_id,
            "provider": original["provider"],
            "iac_tool": original["iac_tool"],
            "config_path": config_path,
            "depends_on": [],
            "monitoring": original.get("monitoring") or "api",
        })
        payload = {
            "schema": "cloud-nxyz/modification-plan-v1",
            "command": f"modify {component_id}",
            "project": base_plan.get("project") or "nxyz",
            "base_plan_id": base_plan.get("plan_id"),
            "modification_scope": "ISOLATED_COMPONENT",
            "affected_components": [component_id],
            "preserved_components": [
                str(item.get("component_id"))
                for item in base_plan.get("components") or []
                if str(item.get("component_id")) != component_id
            ],
            "components": [{
                **replacement.to_dict(),
                "commands": self._commands(replacement),
            }],
            "monitoring": dict(base_plan.get("monitoring") or {
                "required": True,
                "mode": "api",
                "feedback_to_apm": True,
            }),
            "authorization_boundary": "EXPLICIT_RUNTIME_GATE_REQUIRED_FOR_EXTERNAL_MUTATION",
            "context_validation": "VALIDATE_TARGET_COMPONENT_AND_PRESERVE_UNRELATED_COMPONENTS",
            "rollback": "RESTORE_PREVIOUS_COMPONENT_CONFIGURATION_OR_COMPENSATING_ACTION",
            "procedure_verified": True,
            "provenance": {
                "source": self.SOURCE,
                "base_plan_id": base_plan.get("plan_id"),
                "replacement_config_sha256": hashlib.sha256(
                    (self.root / config_path).resolve().read_bytes()
                ).hexdigest(),
            },
        }
        payload["plan_id"] = "nxyz-mod-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]
        payload["apm_validation"] = self.apm_law.validate_procedure(
            payload,
            requires_mutation=True,
        )
        if not payload["apm_validation"]["valid"]:
            raise ValueError(
                "APM law rejected Cloud-NXYZ modification plan: "
                + ", ".join(payload["apm_validation"]["failed"])
            )
        return payload

    def write_plan(self, plan: Mapping[str, Any]) -> Path:
        plan_id = str(plan["plan_id"])
        destination = self.runs_dir / f"{plan_id}.json"
        destination.write_text(
            json.dumps(dict(plan), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return destination

    def execute(self, plan: Mapping[str, Any], *, execute: bool = False) -> dict[str, Any]:
        if not execute:
            return {
                "plan_id": plan["plan_id"],
                "status": "PLANNED",
                "executed": False,
                "message": "Preview only. External cloud mutation was not requested.",
            }
        if os.getenv("GPT_DOUG_CLOUD_NXYZ_EXECUTE", "").strip() != "1":
            raise PermissionError(
                "set GPT_DOUG_CLOUD_NXYZ_EXECUTE=1 and explicitly request execution"
            )

        results = []
        overall = "PASSED"
        for component in plan["components"]:
            commands = component["commands"]
            component_result = {
                "component_id": component["component_id"],
                "provider": component["provider"],
                "iac_tool": component["iac_tool"],
                "steps": [],
            }
            for phase in ("validate", "plan", "apply"):
                argv = list(commands.get(phase) or [])
                if not argv:
                    if phase == "apply":
                        component_result["steps"].append({
                            "phase": phase,
                            "status": "BLOCKED",
                            "reason": "no deterministic apply adapter configured",
                        })
                        overall = "BLOCKED"
                        break
                    continue
                started = time.monotonic()
                proc = subprocess.run(
                    argv,
                    cwd=self.root,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=900,
                    check=False,
                )
                component_result["steps"].append({
                    "phase": phase,
                    "status": "PASSED" if proc.returncode == 0 else "FAILED",
                    "exit_code": proc.returncode,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "command": shlex.join(argv),
                    "output_bytes": len(proc.stdout.encode("utf-8")),
                    "output_sha256": hashlib.sha256(proc.stdout.encode("utf-8")).hexdigest(),
                    **({"output_tail": proc.stdout[-4000:]} if os.getenv("GPT_DOUG_CLOUD_NXYZ_CAPTURE_OUTPUT", "").strip() == "1" else {}),
                })
                if proc.returncode != 0:
                    overall = "FAILED"
                    break
            results.append(component_result)
            if overall != "PASSED":
                break

        receipt = {
            "schema": "cloud-nxyz/execution-receipt-v1",
            "plan_id": plan["plan_id"],
            "status": overall,
            "executed": True,
            "components": results,
            "monitoring_attachment_status": (
                "READY_FOR_MONITORING_BIND"
                if overall == "PASSED"
                else "NOT_ATTACHED"
            ),
        }
        self.record_outcome(plan, receipt)
        return receipt

    def record_outcome(
        self,
        plan: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ) -> dict[str, Any]:
        status = str(receipt.get("status") or "UNKNOWN").upper()
        if not receipt.get("executed"):
            raise ValueError("APM refuses to learn a deployment outcome without an executed receipt")
        if status in SUCCESS and not receipt.get("components"):
            raise ValueError("APM refuses to promote success without component execution evidence")
        return self.accelerator.record_event(
            automation_type="cloud-nxyz",
            stage="deploy",
            status=status,
            attributes={
                "plan_id": plan["plan_id"],
                "project": plan.get("project"),
                "providers": sorted({
                    str(item["provider"]) for item in plan.get("components") or []
                }),
                "iac_tools": sorted({
                    str(item["iac_tool"]) for item in plan.get("components") or []
                }),
                "monitoring_attachment_status": receipt.get("monitoring_attachment_status"),
            },
            requirements=[
                "preserve_provenance",
                "validate_before_external_mutation",
                "keep_rollback_path",
                "attach_monitoring",
                "do_not_expand_authority_from_memory",
            ],
            metrics={
                "component_count": len(plan.get("components") or []),
            },
            source="cloud-nxyz.execute",
            run_id=str(plan["plan_id"]),
        )

    def learned_template(self) -> dict[str, Any]:
        return self.accelerator.template("cloud-nxyz")

    def status(self) -> dict[str, Any]:
        return {
            "name": "CLOUD-NXYZ",
            "status": "READY",
            "law": self.apm_law.status(),
            "supported_iac": sorted(SUPPORTED_IAC),
            "supported_providers": sorted(SUPPORTED_PROVIDERS),
            "apm": self.accelerator.status(),
            "source": self.SOURCE,
            "execution_gate": "GPT_DOUG_CLOUD_NXYZ_EXECUTE=1",
        }
