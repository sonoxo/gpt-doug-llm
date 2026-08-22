import unittest

from aegis_war_room import (
    DecisionCategory,
    DecisionEngine,
    DecisionOption,
    DecisionRejected,
    DecisionRequest,
    EvidenceItem,
)
from aegis_war_room.visualization import build_dashboard_payload


class AegisWarRoomTests(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()
        self.evidence = (
            EvidenceItem(
                evidence_id="e-1",
                source="service-health",
                summary="Primary communications service is degraded",
                confidence=0.9,
                timestamp="2026-08-19T23:50:00-04:00",
            ),
        )
        self.options = (
            DecisionOption(
                option_id="o-1",
                title="Fail over to backup communications service",
                description="Use an already-authorized backup service and verify health.",
                personnel_safety=1.0,
                civilian_safety=1.0,
                mission_continuity=0.9,
                resilience=0.9,
                reversibility=0.9,
                policy_fit=1.0,
                logistics_feasibility=0.8,
                cost_efficiency=0.7,
                recovery_speed=0.9,
                evidence_ids=("e-1",),
            ),
            DecisionOption(
                option_id="o-2",
                title="Remain on degraded service",
                description="Take no immediate change and continue monitoring.",
                personnel_safety=1.0,
                civilian_safety=1.0,
                mission_continuity=0.4,
                resilience=0.3,
                reversibility=1.0,
                policy_fit=1.0,
                logistics_feasibility=1.0,
                cost_efficiency=1.0,
                recovery_speed=0.1,
                evidence_ids=("e-1",),
            ),
        )

    def request(self, category=DecisionCategory.COMMUNICATIONS_RESILIENCE):
        return DecisionRequest(
            request_id="r-1",
            mission_id="m-1",
            principal_id="operator-1",
            category=category,
            objective="Maintain safe communications continuity",
            environment="test",
            options=self.options,
            evidence=self.evidence,
            constraints={"scope": "authorized-local-test"},
        )

    def test_ranks_non_lethal_options_and_requires_human_approval(self):
        result = self.engine.evaluate(self.request())
        self.assertEqual(result.status, "DECISION_SUPPORT_ONLY")
        self.assertEqual(result.recommended_option_id, "o-1")
        self.assertTrue(result.requires_human_approval)
        self.assertGreater(result.ranked_options[0].score, result.ranked_options[1].score)

    def test_rejects_target_selection(self):
        with self.assertRaises(DecisionRejected):
            self.engine.evaluate(self.request(DecisionCategory.TARGET_SELECTION))

    def test_rejects_weapon_release(self):
        with self.assertRaises(DecisionRejected):
            self.engine.evaluate(self.request(DecisionCategory.WEAPON_RELEASE))

    def test_rejects_offensive_cyber(self):
        with self.assertRaises(DecisionRejected):
            self.engine.evaluate(self.request(DecisionCategory.OFFENSIVE_CYBER))

    def test_unknown_confidence_when_option_has_no_linked_evidence(self):
        option = DecisionOption(
            option_id="o-x",
            title="Unverified option",
            description="No evidence linked",
            personnel_safety=1,
            civilian_safety=1,
            mission_continuity=1,
            resilience=1,
            reversibility=1,
            policy_fit=1,
            logistics_feasibility=1,
            cost_efficiency=1,
            recovery_speed=1,
            evidence_ids=("missing",),
        )
        request = DecisionRequest(
            request_id="r-x",
            mission_id="m-x",
            principal_id="operator-1",
            category=DecisionCategory.INFRASTRUCTURE_RECOVERY,
            objective="Recover authorized infrastructure",
            environment="test",
            options=(option,),
            evidence=self.evidence,
        )
        result = self.engine.evaluate(request)
        self.assertEqual(result.ranked_options[0].confidence, 0.0)
        self.assertEqual(result.risk_level.value, "unknown")

    def test_visualization_payload_preserves_safety_boundary(self):
        request = self.request()
        result = self.engine.evaluate(request)
        payload = build_dashboard_payload(request, result)
        self.assertEqual(payload["visualizationSafety"]["weaponControl"], "not_supported")
        self.assertEqual(payload["visualizationSafety"]["targetingData"], "not_supported")
        self.assertTrue(payload["requiresHumanApproval"])


if __name__ == "__main__":
    unittest.main()
