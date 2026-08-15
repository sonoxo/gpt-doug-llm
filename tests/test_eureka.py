import unittest

from eureka import EurekaMessage, Signal


class EurekaTests(unittest.TestCase):
    KEY = b"k" * 32

    def test_round_trip(self):
        message = EurekaMessage.create(Signal.PLAN, "doug", "zyra", "review", {"steps": ["test"]}, "owner", self.KEY)
        decoded = EurekaMessage.from_json(message.to_json(), self.KEY)
        self.assertEqual(decoded.signal, Signal.PLAN)
        self.assertEqual(decoded.payload["steps"], ["test"])

    def test_rejects_missing_authorization(self):
        with self.assertRaises(ValueError):
            EurekaMessage.create(Signal.REQUEST, "doug", "zyra", "deploy", {}, "", self.KEY)

    def test_rejects_oversized_payload(self):
        with self.assertRaises(ValueError):
            EurekaMessage.create(Signal.EVIDENCE, "doug", "zyra", "review", {"data": "x" * 40_000}, "owner", self.KEY)

    def test_rejects_unknown_protocol(self):
        message = EurekaMessage.create(Signal.HELLO, "doug", "zyra", "connect", {}, "owner", self.KEY)
        raw = message.to_json().replace("EUREKA/1.0", "EUREKA/999")
        with self.assertRaises(ValueError):
            EurekaMessage.from_json(raw, self.KEY)

    def test_rejects_tampering_and_replay(self):
        message = EurekaMessage.create(Signal.REQUEST, "doug", "zyra", "review", {"id": 1}, "owner", self.KEY)
        raw = message.to_json()
        with self.assertRaises(ValueError): EurekaMessage.from_json(raw.replace('"id":1', '"id":2'), self.KEY)
        seen = set(); EurekaMessage.from_json(raw, self.KEY, seen)
        with self.assertRaises(ValueError): EurekaMessage.from_json(raw, self.KEY, seen)


if __name__ == "__main__":
    unittest.main()
