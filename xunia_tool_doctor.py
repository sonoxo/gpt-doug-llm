"""Report which free/open-source XUNIA security binaries are available locally."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass

from xunia_security import TOOL_CATALOG


@dataclass(frozen=True)
class ToolReadiness:
    tool_id: str
    check: str
    installed: bool
    executable: str | None
    target_types: tuple[str, ...]


def inspect_tools() -> list[ToolReadiness]:
    results = []
    for tool in TOOL_CATALOG:
        binary = "zap-baseline.py" if tool.id == "zap-baseline" else tool.id
        executable = shutil.which(binary)
        results.append(
            ToolReadiness(
                tool_id=tool.id,
                check=tool.check,
                installed=bool(executable),
                executable=executable,
                target_types=tool.target_types,
            )
        )
    return results


def main() -> None:
    results = inspect_tools()
    print(json.dumps({"tools": [asdict(item) for item in results]}, indent=2))
    missing = [item.tool_id for item in results if not item.installed]
    if missing:
        print("\nMissing optional OSS tools: " + ", ".join(missing))
        print("The runtime remains usable; only checks backed by installed binaries can execute.")
    else:
        print("\nAll registered XUNIA OSS security tools are available.")


if __name__ == "__main__":
    main()
