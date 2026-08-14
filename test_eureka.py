import unittest

from eureka import EurekaMessage, Signal


class EurekaTests(unittest.TestCase):
    def test_round_trip(self):
        message = EurekaMessage.create(Signal.PLAN, "doug", "zyra", "review", {"steps": ["test"]}, "owner")
        decoded = EurekaMessage.from_json(message.to_json())
        self.assertEqual(decoded.signal, Signal.PLAN)
        self.assertEqual(decoded.payload["steps"], ["test"])

    def test_rejects_missing_authorization(self):
        with self.assertRaises(ValueError):
            EurekaMessage.create(Signal.REQUEST, "doug", "zyra", "deploy", {}, "")

    def test_rejects_oversized_payload(self):
        with self.assertRaises(ValueError):
            EurekaMessage.create(Signal.EVIDENCE, "doug", "zyra", "review", {"data": "x" * 40_000}, "owner")

    def test_rejects_unknown_protocol(self):
        message = EurekaMessage.create(Signal.HELLO, "doug", "zyra", "connect", {}, "owner")
        raw = message.to_json().replace("EUREKA/1.0", "EUREKA/999")
        with self.assertRaises(ValueError):
            EurekaMessage.from_json(raw)


if __name__ == "__main__":
    unittest.main()
