"""GPT-DOUG sovereignty/performance runtime.

This module translates the sovereignty stack used by the GPT-DOUG / Palantir
integration into concrete local runtime controls for memory, compute, GPU
selection, and speed. It does not control Palantir infrastructure or grant any
Palantir capability. Foundry/Ontology remain authoritative for governed state.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import subprocess
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Callable, Generic, Iterable, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen=True)
class HardwareProfile:
    system: str
    machine: str
    cpu_count: int
    memory_bytes: int | None
    accelerators: tuple[str, ...]
    preferred_accelerator: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["accelerators"] = list(self.accelerators)
        return result


@dataclass(frozen=True)
class PerformancePolicy:
    cache_entries: int = 256
    cache_ttl_seconds: float = 300.0
    max_concurrency: int = 8
    preferred_accelerators: tuple[str, ...] = ("cuda", "mps", "mlx", "cpu")

    @classmethod
    def from_environment(cls) -> "PerformancePolicy":
        cpu_count = max(1, os.cpu_count() or 1)
        return cls(
            cache_entries=max(16, int(os.getenv("GPT_DOUG_CACHE_ENTRIES", "256"))),
            cache_ttl_seconds=max(1.0, float(os.getenv("GPT_DOUG_CACHE_TTL_SECONDS", "300"))),
            max_concurrency=max(1, min(int(os.getenv("GPT_DOUG_MAX_CONCURRENCY", "8")), cpu_count)),
        )


class TTLRUCache(Generic[K, V]):
    """Bounded in-process TTL + LRU cache for repeat knowledge/Ontology reads."""

    def __init__(
        self,
        max_entries: int = 256,
        ttl_seconds: float = 300.0,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._data: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: K) -> V | None:
        item = self._data.get(key)
        if item is None:
            self.misses += 1
            return None
        created_at, value = item
        if self.clock() - created_at > self.ttl_seconds:
            del self._data[key]
            self.misses += 1
            return None
        self._data.move_to_end(key)
        self.hits += 1
        return value

    def put(self, key: K, value: V) -> None:
        if key in self._data:
            del self._data[key]
        self._data[key] = (self.clock(), value)
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)
            self.evictions += 1

    def clear(self) -> None:
        self._data.clear()

    def stats(self) -> dict[str, int | float]:
        lookups = self.hits + self.misses
        return {
            "entries": len(self._data),
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": (self.hits / lookups) if lookups else 0.0,
        }


def _memory_bytes() -> int | None:
    system = platform.system()
    try:
        if system == "Darwin":
            completed = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                check=True,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            return int(completed.stdout.strip())
        if hasattr(os, "sysconf"):
            pages = int(os.sysconf("SC_PHYS_PAGES"))
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            return pages * page_size
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return None


def detect_accelerators() -> tuple[str, ...]:
    found: list[str] = []

    # Torch is optional. If present, use its runtime checks rather than assuming
    # that an installed package implies accelerator availability.
    if importlib.util.find_spec("torch") is not None:
        try:
            import torch  # type: ignore

            if bool(torch.cuda.is_available()):
                found.append("cuda")
            mps = getattr(getattr(torch, "backends", None), "mps", None)
            if mps is not None and bool(mps.is_available()):
                found.append("mps")
        except Exception:
            pass

    # MLX is Apple-silicon-specific. Package presence is useful as a local
    # routing capability even when Torch is not installed.
    if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        if importlib.util.find_spec("mlx") is not None:
            found.append("mlx")

    found.append("cpu")
    return tuple(dict.fromkeys(found))


def choose_accelerator(
    available: Iterable[str],
    preferred: Iterable[str] = ("cuda", "mps", "mlx", "cpu"),
) -> str:
    available_set = set(available)
    for backend in preferred:
        if backend in available_set:
            return backend
    return "cpu"


def hardware_profile(policy: PerformancePolicy | None = None) -> HardwareProfile:
    policy = policy or PerformancePolicy.from_environment()
    accelerators = detect_accelerators()
    return HardwareProfile(
        system=platform.system(),
        machine=platform.machine(),
        cpu_count=max(1, os.cpu_count() or 1),
        memory_bytes=_memory_bytes(),
        accelerators=accelerators,
        preferred_accelerator=choose_accelerator(accelerators, policy.preferred_accelerators),
    )


def benchmark(iterations: int = 250_000) -> dict[str, float | int]:
    """Small dependency-free CPU/memory benchmark for regression snapshots.

    The number is comparative only. It is not a model tokens/second benchmark.
    """

    iterations = max(10_000, int(iterations))
    start = time.perf_counter()
    data = [i ^ (i >> 3) for i in range(iterations)]
    checksum = sum(data)
    elapsed = max(time.perf_counter() - start, 1e-9)
    return {
        "iterations": iterations,
        "elapsed_seconds": round(elapsed, 6),
        "iterations_per_second": round(iterations / elapsed, 2),
        "checksum": checksum,
    }


def runtime_report(run_benchmark: bool = False) -> dict[str, object]:
    policy = PerformancePolicy.from_environment()
    profile = hardware_profile(policy)
    result: dict[str, object] = {
        "sovereignty_runtime": "gpt-doug-local",
        "policy": {
            "cache_entries": policy.cache_entries,
            "cache_ttl_seconds": policy.cache_ttl_seconds,
            "max_concurrency": policy.max_concurrency,
            "preferred_accelerators": list(policy.preferred_accelerators),
        },
        "hardware": profile.to_dict(),
        "memory_authority": "Ontology/governed source remains authoritative; local cache is disposable",
        "palantir_infrastructure_controlled": False,
    }
    if run_benchmark:
        result["benchmark"] = benchmark()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect GPT-DOUG local compute sovereignty profile")
    parser.add_argument("--benchmark", action="store_true", help="run the local microbenchmark")
    args = parser.parse_args()
    print(json.dumps(runtime_report(run_benchmark=args.benchmark), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
