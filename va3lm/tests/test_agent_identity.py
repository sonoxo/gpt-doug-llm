from va3lm.agent_identity import AgentAccessRequest, AgentIdentity, evaluate_agent_access
from va3lm.auth_manager import AuthProvider, broker_auth
from va3lm.defense_ontology import DEFENSE_ONTOLOGY


def identity() -> AgentIdentity:
    return AgentIdentity(
        agent_id="va3lm:test",
        spiffe_id="spiffe://xuniaverse.local/va3lm/agent/test",
        runtime="VA3LM",
        credential_mode="SHORT_LIVED",
        scopes=("crm.read", "evidence.read"),
        provenance=("test:identity",),
    )


def test_scoped_agent_identity_is_allowed() -> None:
    decision = evaluate_agent_access(
        AgentAccessRequest(identity(), "provider:test", ("crm.read",))
    )
    assert decision.decision == "ALLOW"


def test_shared_and_long_lived_credentials_are_blocked() -> None:
    assert evaluate_agent_access(
        AgentAccessRequest(identity(), "provider:test", ("crm.read",), shared_credential=True)
    ).decision == "BLOCK"
    assert evaluate_agent_access(
        AgentAccessRequest(identity(), "provider:test", ("crm.read",), long_lived_credential=True)
    ).decision == "BLOCK"


def test_broad_agent_grant_requires_review() -> None:
    decision = evaluate_agent_access(
        AgentAccessRequest(identity(), "provider:test", ("crm.read",), project_wide_grant=True)
    )
    assert decision.decision == "REVIEW"


def test_auth_broker_returns_reference_not_raw_secret() -> None:
    request = AgentAccessRequest(identity(), "provider:test", ("crm.read",))
    provider = AuthProvider("provider:test", "OAUTH2", ("crm.read",), requires_token_binding=True)
    result = broker_auth(request, provider)
    assert result.decision.decision == "ALLOW"
    assert result.credential is not None
    assert result.credential.raw_secret_exposed is False
    assert result.credential.credential_class == "SHORT_LIVED_REFERENCE"
    assert "DPOP" in result.credential.token_binding


def test_defense_ontology_is_rooted_in_xuniadao() -> None:
    assert DEFENSE_ONTOLOGY["root"] == "sonoxo/xuniadao"
    assert DEFENSE_ONTOLOGY["layers"] == ["GCPXUNIA", "VIRGINIA", "VA3LM", "ZYRA_ACTION_GATE"]
    assert DEFENSE_ONTOLOGY["claims"]["googleDeployment"] is False
    assert DEFENSE_ONTOLOGY["claims"]["palantirDeployment"] is False
