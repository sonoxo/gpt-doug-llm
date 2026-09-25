import unittest

from sovereignty_performance import (
    PerformancePolicy,
    TTLRUCache,
    choose_accelerator,
    detect_quantum_adapters,
    hardware_profile,
    runtime_report,
)


class SovereigntyPerformanceTests(unittest.TestCase):
    def test_cache_hits_and_expires(self):
        now = [100.0]
        cache = TTLRUCache(max_entries=2, ttl_seconds=5.0, clock=lambda: now[0])
        cache.put("ontology:asset:1", {"id": 1})
        self.assertEqual(cache.get("ontology:asset:1"), {"id": 1})
        now[0] += 6.0
        self.assertIsNone(cache.get("ontology:asset:1"))
        stats = cache.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)

    def test_cache_is_bounded_lru(self):
        cache = TTLRUCache(max_entries=2, ttl_seconds=60.0)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(cache.get("a"), 1)
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)
        self.assertEqual(cache.stats()["evictions"], 1)

    def test_accelerator_priority(self):
        self.assertEqual(choose_accelerator(["cpu", "mps"]), "mps")
        self.assertEqual(choose_accelerator(["cpu", "mlx"]), "mlx")
        self.assertEqual(choose_accelerator(["cpu", "mps", "cuda"]), "cuda")
        self.assertEqual(choose_accelerator(["cpu"]), "cpu")

    def test_hardware_profile_has_cpu_fallback(self):
        profile = hardware_profile(PerformancePolicy(max_concurrency=1))
        self.assertGreaterEqual(profile.cpu_count, 1)
        self.assertIn("cpu", profile.accelerators)
        self.assertIn(profile.preferred_accelerator, profile.accelerators)
        self.assertFalse(profile.quantum_hardware_proven)

    def test_quantum_detection_never_proves_qpu_access(self):
        self.assertIsInstance(detect_quantum_adapters(), tuple)
        report = runtime_report()
        self.assertFalse(report["quantum_truth"]["qpu_hardware_access_proven"])
        self.assertIn("L4", report["memory_fabric"])


if __name__ == "__main__":
    unittest.main()
