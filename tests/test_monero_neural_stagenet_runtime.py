import json
import urllib.request
from pathlib import Path

from monero_neural.cli import _probe_rpc
from monero_neural.rpc import MoneroRPCClient


def test_stagenet_wallet_rpc_default_is_38088(monkeypatch):
    monkeypatch.delenv("MONERO_WALLET_RPC", raising=False)
    client = MoneroRPCClient.wallet_from_env()
    assert client.endpoint == "http://127.0.0.1:38088/json_rpc"


def test_wallet_doctor_probe_uses_service_version_not_balance():
    class FakeWallet:
        def wallet_version(self):
            return {"version": 65539, "release": True}

        def wallet_balance(self, **kwargs):
            raise AssertionError("doctor should not require an open wallet")

    result = _probe_rpc(FakeWallet(), "wallet")
    assert result["reachable"] is True
    assert result["rpc_version"] == 65539
    assert result["release"] is True


def test_installer_migrates_old_wallet_rpc_default():
    root = Path(__file__).resolve().parent.parent
    text = (root / "scripts" / "install-xmr-neural").read_text(encoding="utf-8")
    assert "38082/json_rpc" in text
    assert "38088/json_rpc" in text
    assert "migrated stagenet wallet RPC 38082 -> 38088" in text


def test_stagenet_helper_is_local_authenticated_and_non_custodial():
    root = Path(__file__).resolve().parent.parent
    text = (root / "scripts" / "start-xmr-stagenet").read_text(encoding="utf-8")
    assert "--rpc-bind-ip 127.0.0.1" in text
    assert "--rpc-bind-port 38081" in text
    assert "--rpc-bind-port 38088" in text
    assert "--rpc-login" in text
    assert "--digest" in text
    assert "--stagenet" in text
    assert "create_wallet" not in text
    assert "transfer(" not in text
    assert "spend key was loaded" in text


def test_rpc_login_uses_http_digest_not_basic(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"jsonrpc": "2.0", "id": "gpt-doug-xmr-neural", "result": {"version": 1}}
            ).encode("utf-8")

    class FakeOpener:
        def open(self, request, timeout):
            captured["authorization"] = request.headers.get("Authorization")
            captured["timeout"] = timeout
            return FakeResponse()

    def fake_build_opener(handler):
        captured["handler"] = handler
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", fake_build_opener)

    client = MoneroRPCClient(
        "http://127.0.0.1:38088/json_rpc",
        username="gptdoug",
        password="secret",
    )
    result = client.wallet_version()

    assert result["version"] == 1
    assert isinstance(captured["handler"], urllib.request.HTTPDigestAuthHandler)
    assert captured["authorization"] is None
