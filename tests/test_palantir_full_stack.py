import tempfile

from palantir_aip import AIPTestCase, PalantirAIPClient
from palantir_apollo import validate_apollo_manifest
from palantir_automate import AutomateEffect, PalantirAutomateBridge
from palantir_gotham import PalantirGothamClient
from palantir_stack import PalantirStack
from wakeup3lm import Wakeup3LM
from wakeup3lm.palantir import Wakeup3LMPalantirBridge


class FakeFoundry:
    def __init__(self):
        self.calls = []
        self.actions = []
        self.writes_enabled = True

    def request(self, method, path, *, body=None, query=None, write=False):
        self.calls.append((method, path, body, query, write))
        if "/queryTypes/" in path and method == "GET":
            return {"apiName": path.rsplit("/", 1)[-1], "version": "1.0.0"}
        if path.endswith("/execute"):
            params = (body or {}).get("parameters", {})
            return {"value": params.get("value", params)}
        if "chat/completions" in path:
            return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        if "/objects/" in path:
            return {"id": path.rsplit("/", 1)[-1]}
        return {"data": []}

    def apply_action(self, ontology, action, parameters, **kwargs):
        self.actions.append((ontology, action, parameters))
        return {"validation": {"result": "VALID"}}

    def status(self):
        return {"configured": True, "writes_enabled": True}


def test_aip_model_proxy_and_logic_execution():
    foundry = FakeFoundry()
    aip = PalantirAIPClient(foundry)
    chat = aip.openai_chat_completions(
        model="ri.language-model-service..language-model.test",
        messages=[{"role": "user", "content": "hello"}],
    )
    assert chat["choices"][0]["message"]["content"] == "ok"
    result = aip.execute_logic("main", "buildApp", {"value": "done"})
    assert result["value"] == "done"
    assert any("/api/v2/llm/proxy/openai/v1/chat/completions" == call[1] for call in foundry.calls)
    assert any("/api/v2/ontologies/main/queries/buildApp/execute" == call[1] for call in foundry.calls)


def test_external_eval_harness_executes_real_logic_contract():
    aip = PalantirAIPClient(FakeFoundry())
    report = aip.run_eval_suite(
        "main",
        "echo",
        [
            AIPTestCase("one", {"value": 1}, expected=1),
            AIPTestCase("two", {"value": 2}, expected=2),
        ],
    )
    assert report.success is True
    assert report.passed == 2


def test_automate_effects_route_to_action_and_logic():
    foundry = FakeFoundry()
    automate = PalantirAutomateBridge(foundry)
    logic = automate.execute_effect(AutomateEffect("aip-logic", "main", "triage", {"value": "ok"}))
    assert logic["value"] == "ok"
    action = automate.execute_effect(AutomateEffect("ontology-action", "main", "ApproveBuild", {"id": "1"}))
    assert action["validation"]["result"] == "VALID"
    assert foundry.actions == [("main", "ApproveBuild", {"id": "1"})]


def test_gotham_adapter_uses_documented_v1_path():
    foundry = FakeFoundry()
    gotham = PalantirGothamClient(foundry)
    result = gotham.get_object("ri.gotham.example")
    assert result["id"] == "ri.gotham.example"
    assert foundry.calls[-1][1] == "/api/gotham/v1/objects/ri.gotham.example"


def test_apollo_manifest_contract():
    good = {
        "product-type": "service.v1",
        "product-group": "com.sonoxo",
        "product-name": "wakeup3lm",
        "product-version": "1.0.0",
    }
    assert validate_apollo_manifest(good) == []
    assert "product-version" in validate_apollo_manifest({**good, "product-version": ""})


def test_wakeup3lm_invokes_aip_and_records_external_run():
    with tempfile.TemporaryDirectory() as tmp:
        wakeup = Wakeup3LM(tmp)
        bridge = Wakeup3LMPalantirBridge(wakeup, FakeFoundry())
        result = bridge.invoke_logic(
            ontology="main",
            query_api_name="echo",
            parameters={"value": "green"},
        )
        assert result["value"] == "green"
        runs = wakeup.ontology.query("AgentRun", platform="palantir")
        assert runs
        assert runs[-1].properties["status"] == "PASSED"


def test_every_palantir_code_plane_is_implemented():
    stack = PalantirStack(FakeFoundry()).status()
    assert stack["all_code_planes_implemented"] is True
    assert {"AIP", "Ontology", "Gotham", "Apollo", "JupyterLab", "Automate"}.issubset(
        set(stack["implemented_planes"])
    )
