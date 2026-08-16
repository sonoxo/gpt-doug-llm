import sys, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import pytest

class TestGeminiBackend:
    def test_config_defaults(self):
        from google.gemini_backend import GeminiConfig
        c = GeminiConfig()
        assert c.model == "gemini-2.5-flash"
    def test_auto_select(self):
        from google.gemini_backend import auto_select_backend
        r = auto_select_backend()
        assert r["backend"] in ("gemini", "openai", "ollama")

class TestADKWrapper:
    def test_tools(self):
        from google.adk_wrapper import DougADKAgent
        agent = DougADKAgent()
        tools = agent.list_tools()
        assert len(tools) == 6
    def test_knowledge(self):
        from google.adk_wrapper import DougADKAgent
        agent = DougADKAgent()
        r = agent.call_tool("knowledge_search", query="cia")
        assert "results" in r
    def test_shield_block(self):
        from google.adk_wrapper import DougADKAgent
        agent = DougADKAgent()
        r = agent.call_tool("golden_shield_check", text="rm -rf /", source="test")
        assert r["action"] in ("BLOCK", "ELIMINATE")
    def test_agent_scan(self):
        from google.adk_wrapper import DougADKAgent
        agent = DougADKAgent()
        r = agent.run("scan for vulnerabilities")
        assert r["status"] == "completed"
    def test_agent_blocked(self):
        from google.adk_wrapper import DougADKAgent
        agent = DougADKAgent()
        r = agent.run("rm -rf / destroy everything")
        assert r["status"] == "blocked"

class TestCloudRun:
    def test_deploy(self):
        from google.cloud_run import deploy_cloud_run
        r = deploy_cloud_run("test-project")
        assert "service" in r and "url" in r
    def test_firestore(self):
        from google.cloud_run import setup_firestore
        r = setup_firestore("test-project")
        assert "agents" in r["collections"]
    def test_pubsub(self):
        from google.cloud_run import setup_pubsub
        r = setup_pubsub("test-project")
        assert "topic" in r["config"]
    def test_full(self):
        from google.cloud_run import full_deployment
        r = full_deployment("test-project")
        assert r["track"] == "The Fortified Enterprise Fleet"
        assert "1_gemini" in r["mandatory_requirements"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
