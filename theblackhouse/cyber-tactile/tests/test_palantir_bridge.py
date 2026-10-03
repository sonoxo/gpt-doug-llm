import asyncio
import unittest

from palantir.bridge import (
    CyberTactileEdge,
    DefenseController,
    GothamPlatformAdapter,
    LinkHealth,
    OperatorContext,
    OperatorGesture,
    PalantirConfig,
    PalantirMirror,
    ThreatEvent,
    Vec3,
)


class MockSink:
    def __init__(self):
        self.frames = []
        self.disarmed = False

    def apply(self, projection):
        if self.disarmed:
            return False
        self.frames.append(projection)
        return True

    def disarm(self):
        self.disarmed = True


class MockOntology:
    def __init__(self):
        self.threats = []
        self.operator_actions = []
        self.mitigations = []

    def upsert_threat(self, event, projection):
        self.threats.append((event, projection))
        return event.ontology_entity_rid or f"ri.object.{event.event_id}"

    def record_operator_action(self, **kwargs):
        self.operator_actions.append(kwargs)
        return kwargs["gesture"].gesture_id

    def apply_mitigation(self, action, parameters):
        self.mitigations.append((action, parameters))
        return f"audit:{action}:{parameters['threatEventId']}"


class MockGotham:
    def __init__(self):
        self.targets = []
        self.layers = []

    def validate_target_binding(self, target_rid):
        self.targets.append(target_rid)
        return True

    def add_ontology_object_to_gaia(self, object_rid, *, label):
        self.layers.append((object_rid, label))
        return "layer-1"


class MockAudit:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)
        return "local-audit-1"


def threat(kind="privilege_escalation"):
    return ThreatEvent(
        event_id="evt-1",
        threat_kind=kind,
        source_asset="identity-proxy",
        target_asset="db-prod-7",
        source_position=Vec3(-1.0, 0.0, 0.0),
        target_position=Vec3(1.0, 2.0, 3.0),
        cvss=10.0,
        anomaly_confidence=1.0,
        bytes_per_second=2 * 1024**3,
        observed_at_unix_ms=1,
        gotham_target_rid="ri.gotham.target.1",
        ontology_entity_rid="ri.object.cyber-threat.1",
        geotime_track_rid="ri.gotham.geotime.1",
        source_indicator="203.0.113.0/24",
        session_id="session-1",
    )


def authorized_operator():
    return OperatorContext(
        operator_id="operator-7",
        mtls_verified=True,
        hardware_token_verified=True,
        pq_channel_verified=True,
        rbac_allowed=True,
        deliberate_confirmation=True,
    )


class BridgeTests(unittest.TestCase):
    def test_target_track_to_haptic_and_gaia_mirror(self):
        sink = MockSink()
        edge = CyberTactileEdge(sink)
        event = threat()
        projection = edge.process(event, LinkHealth(True, 1.2, True))
        self.assertIsNotNone(projection)
        self.assertEqual(len(sink.frames), 1)
        self.assertLessEqual(projection.normalized_amplitude, 0.65)

        ontology = MockOntology()
        gotham = MockGotham()
        mirror = PalantirMirror(ontology, gotham)
        rid = asyncio.run(mirror.mirror(event, projection))
        self.assertEqual(rid, "ri.object.cyber-threat.1")
        self.assertEqual(gotham.targets, ["ri.gotham.target.1"])
        self.assertEqual(gotham.layers[0][0], "ri.object.cyber-threat.1")

    def test_jitter_fail_passive(self):
        sink = MockSink()
        edge = CyberTactileEdge(sink)
        result = edge.process(threat(), LinkHealth(True, 15.1, True))
        self.assertIsNone(result)
        self.assertTrue(edge.disarmed)
        self.assertTrue(sink.disarmed)

    def test_token_failure_fail_passive(self):
        sink = MockSink()
        edge = CyberTactileEdge(sink)
        result = edge.process(threat(), LinkHealth(True, 1.0, False))
        self.assertIsNone(result)
        self.assertTrue(sink.disarmed)

    def test_squeeze_executes_isolate_host(self):
        sink = MockSink()
        edge = CyberTactileEdge(sink)
        event = threat()
        projection = edge.process(event, LinkHealth(True, 1.0, True))
        ontology, audit = MockOntology(), MockAudit()
        controller = DefenseController(ontology, audit)
        receipt = controller.handle(
            gesture=OperatorGesture("g1", "squeeze", event.event_id, event.target_asset),
            operator=authorized_operator(),
            event=event,
            projection=projection,
        )
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.action, "IsolateHost")
        self.assertEqual(ontology.mitigations[0][0], "IsolateHost")

    def test_pinch_executes_revoke_session(self):
        sink = MockSink()
        edge = CyberTactileEdge(sink)
        event = threat()
        projection = edge.process(event, LinkHealth(True, 1.0, True))
        ontology, audit = MockOntology(), MockAudit()
        controller = DefenseController(ontology, audit)
        receipt = controller.handle(
            gesture=OperatorGesture("g2", "pinch", event.event_id, event.target_asset),
            operator=authorized_operator(),
            event=event,
            projection=projection,
        )
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.action, "RevokeSession")
        self.assertEqual(ontology.mitigations[0][1]["sessionId"], "session-1")

    def test_press_executes_block_ip_range(self):
        sink = MockSink()
        edge = CyberTactileEdge(sink)
        event = threat("ddos_volumetric")
        projection = edge.process(event, LinkHealth(True, 1.0, True))
        ontology, audit = MockOntology(), MockAudit()
        controller = DefenseController(ontology, audit)
        receipt = controller.handle(
            gesture=OperatorGesture("g3", "press", event.event_id, event.target_asset),
            operator=authorized_operator(),
            event=event,
            projection=projection,
        )
        self.assertTrue(receipt.accepted)
        self.assertEqual(receipt.action, "BlockIPRange")
        self.assertEqual(ontology.mitigations[0][1]["indicator"], "203.0.113.0/24")

    def test_unauthorized_operator_never_reaches_action(self):
        sink = MockSink()
        edge = CyberTactileEdge(sink)
        event = threat()
        projection = edge.process(event, LinkHealth(True, 1.0, True))
        ontology, audit = MockOntology(), MockAudit()
        controller = DefenseController(ontology, audit)
        operator = authorized_operator()
        operator = operator.__class__(**{**operator.__dict__, "hardware_token_verified": False})
        receipt = controller.handle(
            gesture=OperatorGesture("g4", "squeeze", event.event_id, event.target_asset),
            operator=operator,
            event=event,
            projection=projection,
        )
        self.assertFalse(receipt.accepted)
        self.assertEqual(ontology.mitigations, [])


class GothamAdapterContractTests(unittest.TestCase):
    def test_official_client_surface_is_used(self):
        class Targets:
            def __init__(self): self.calls = []
            def get(self, rid, preview=None): self.calls.append((rid, preview)); return object()
        class TWB:
            def __init__(self): self.Targets = Targets()
        class Map:
            def __init__(self): self.calls = []
            def add_objects(self, map_rid, *, label, object_rids, preview=None):
                self.calls.append((map_rid, label, object_rids, preview))
                return type("R", (), {"data_layer_ids": ["layer-x"]})()
        class Gaia:
            def __init__(self): self.Map = Map()
        class Client:
            def __init__(self): self.target_workbench = TWB(); self.gaia = Gaia()

        config = PalantirConfig("host", "id", "secret", "osdk", "map-1", True)
        client = Client()
        adapter = GothamPlatformAdapter(config, client=client)
        self.assertTrue(adapter.validate_target_binding("target-1"))
        self.assertEqual(adapter.add_ontology_object_to_gaia("object-1", label="Cyber"), "layer-x")
        self.assertEqual(client.target_workbench.Targets.calls[0], ("target-1", True))
        self.assertEqual(client.gaia.Map.calls[0][2], ["object-1"])


if __name__ == "__main__":
    unittest.main()
